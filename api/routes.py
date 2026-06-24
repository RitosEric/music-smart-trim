# api/routes.py
"""API routes for Music Smart Trim."""
import os
import sys
from pathlib import Path
from flask import Blueprint, request, jsonify, send_file
from werkzeug.utils import secure_filename

# Add parent directory to import src modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.audio_loader import load_audio, AudioLoadError
from api.storage import (
    save_uploaded_file,
    generate_job_id,
    get_file_path,
    get_job_dir,
    cleanup_job,
    extract_cover_art,
    extract_display_name,
)
from api.processing import process_audio

api = Blueprint('api', __name__, url_prefix='/api')

# In-memory job status storage (use Redis in production)
job_status = {}


@api.route('/upload', methods=['POST'])
def upload_file():
    """
    Upload audio file for processing.

    Request: multipart/form-data with 'file' field
    Response: JSON with job_id, filename, original_length
    """
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        # Generate job ID and save file
        job_id = generate_job_id()
        filepath = save_uploaded_file(file, job_id)

        # Get audio metadata
        try:
            audio_data, sample_rate = load_audio(filepath)
            original_length = len(audio_data) / sample_rate
        except AudioLoadError as e:
            return jsonify({'error': f'Invalid audio file: {str(e)}'}), 400

        # Best-effort cover-art extraction. Failure here doesn't fail the upload.
        cover_filename = extract_cover_art(filepath, get_job_dir(job_id))

        # Display name: prefer ID3 "artist - title", then "title", then the
        # ORIGINAL unicode filename (secure_filename strips CJK characters,
        # which is why a Japanese file like "ヨルシカ - 老人と海.mp3" was
        # showing up as "-_.mp3" in the Recent list).
        safe_filename = secure_filename(file.filename)
        original_name = file.filename or safe_filename
        display_name = extract_display_name(filepath, fallback=original_name)

        # Initialize job status
        job_status[job_id] = {
            'status': 'uploaded',
            'filename': safe_filename,
            'display_name': display_name,
            'original_length': original_length,
            'progress': 0,
            'message': 'File uploaded successfully',
            'cover_filename': cover_filename,
        }

        return jsonify({
            'job_id': job_id,
            'filename': safe_filename,
            'display_name': display_name,
            'original_length': original_length,
            'cover_filename': cover_filename,
        }), 200

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500


@api.route('/process', methods=['POST'])
def process_file():
    """
    Start audio processing.

    Request: JSON with job_id, target_length, protected_regions, auto_protect, strict_length
    Response: JSON with status
    """
    try:
        data = request.get_json()

        if not data or 'job_id' not in data:
            return jsonify({'error': 'Missing job_id'}), 400

        job_id = data['job_id']

        if job_id not in job_status:
            return jsonify({'error': 'Invalid job_id'}), 404

        # Extract parameters
        params = {
            'target_length': data.get('target_length'),
            'protected_regions': data.get('protected_regions', []),
            'auto_protect': data.get('auto_protect', False),
            'min_segment_duration': data.get('min_segment_duration', 10.0),
            'regenerate_seed': data.get('regenerate_seed', None),
            'strict_length': data.get('strict_length', False),
            # Used to name output files "<song> - option n - score.wav".
            'song_name': job_status[job_id].get('display_name'),
        }

        if params['target_length'] is None or params['target_length'] <= 0:
            return jsonify({'error': 'Invalid target_length'}), 400

        # Get input file path
        job_dir = get_job_dir(job_id)
        input_files = list(job_dir.glob('*.mp3')) + list(job_dir.glob('*.wav')) + \
                     list(job_dir.glob('*.flac')) + list(job_dir.glob('*.m4a'))

        if not input_files:
            return jsonify({'error': 'Input file not found'}), 404

        input_path = str(input_files[0])

        # Update status
        job_status[job_id]['status'] = 'processing'
        job_status[job_id]['progress'] = 0

        # Capture socketio reference NOW (in request context) so the background
        # thread doesn't need Flask's current_app proxy
        from flask import current_app
        from api.websocket import emit_progress
        socketio = current_app.config.get('SOCKETIO')

        # Define progress callback (closes over socketio captured above)
        def progress_callback(message, progress):
            job_status[job_id]['message'] = message
            job_status[job_id]['progress'] = progress
            if socketio:
                emit_progress(socketio, job_id, message, progress)

        # Process audio asynchronously
        from api.processing import process_audio_async
        process_audio_async(job_id, input_path, params, progress_callback, socketio)

        return jsonify({'status': 'processing_started', 'job_id': job_id}), 200

    except Exception as e:
        return jsonify({'error': f'Processing failed: {str(e)}'}), 500


@api.route('/status/<job_id>', methods=['GET'])
def get_status(job_id):
    """
    Get processing status for a job.

    Response: JSON with status, progress, message, result
    """
    if job_id not in job_status:
        return jsonify({'error': 'Job not found'}), 404

    return jsonify(job_status[job_id]), 200


@api.route('/download/<job_id>/<filename>', methods=['GET'])
def download_file(job_id, filename):
    """
    Serve audio file (original upload or processed output).

    Inline by default so <audio> elements can play the response.
    Pass ?download=1 to force a save-as download.
    """
    # Strip any path components to block traversal, but keep unicode and spaces
    # so song-name outputs like "ヨルシカ - 老人と海 - option 1 - 5.0 stars.wav"
    # still resolve. secure_filename() can't be used here: it deletes CJK
    # characters and replaces spaces, so it would never match the on-disk name.
    safe_name = os.path.basename(filename)
    if (
        not safe_name
        or safe_name in ('.', '..')
        or '/' in safe_name
        or '\\' in safe_name
    ):
        return jsonify({'error': 'Invalid filename'}), 400

    job_dir = get_job_dir(job_id)
    output_path = job_dir / "output" / safe_name
    upload_path = job_dir / safe_name

    if output_path.exists():
        filepath = output_path
    elif upload_path.exists():
        filepath = upload_path
    else:
        return jsonify({'error': 'File not found'}), 404

    as_attachment = request.args.get('download', '').lower() in ('1', 'true', 'yes')
    return send_file(
        str(filepath.absolute()),
        as_attachment=as_attachment,
        download_name=filename,
    )


@api.route('/job/<job_id>', methods=['DELETE'])
def delete_job(job_id):
    """
    Remove every file associated with a job (audio, outputs, cover art) and
    drop its in-memory status. Idempotent — returns 200 even if the job is
    already gone, so the frontend's eviction loop never has to special-case it.
    """
    job_dir = get_job_dir(job_id)
    existed = job_dir.exists()
    cleanup_job(job_id)
    job_status.pop(job_id, None)
    return jsonify({'job_id': job_id, 'existed': existed}), 200
