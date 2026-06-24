# api/storage.py
"""File storage management for uploaded and processed audio files."""
import os
import shutil
import uuid
from pathlib import Path
from typing import Optional
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

# Storage directory for all jobs
STORAGE_DIR = Path("api/storage_data")
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

# Allowed audio file extensions
ALLOWED_EXTENSIONS = {'mp3', 'wav', 'flac', 'm4a'}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB in bytes


def allowed_file(filename: str) -> bool:
    """Check if filename has allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_job_dir(job_id: str) -> Path:
    """Get directory path for a job."""
    return STORAGE_DIR / job_id


def save_uploaded_file(file: FileStorage, job_id: str) -> str:
    """
    Save an uploaded file to job storage directory.

    Args:
        file: Werkzeug FileStorage object
        job_id: Unique job identifier

    Returns:
        Absolute path to saved file

    Raises:
        ValueError: If file is invalid or too large
    """
    if not file or not file.filename:
        raise ValueError("No file provided")

    if not allowed_file(file.filename):
        raise ValueError(f"File type not allowed. Supported: {ALLOWED_EXTENSIONS}")

    # Create job directory
    job_dir = get_job_dir(job_id)
    job_dir.mkdir(parents=True, exist_ok=True)

    # Secure filename and save
    filename = secure_filename(file.filename)
    filepath = job_dir / filename
    file.save(str(filepath))

    # Check file size after saving
    if filepath.stat().st_size > MAX_FILE_SIZE:
        filepath.unlink()
        raise ValueError(f"File too large. Maximum size: {MAX_FILE_SIZE / 1024 / 1024}MB")

    return str(filepath.absolute())


def get_file_path(job_id: str, filename: str) -> Optional[str]:
    """
    Get path to a file in job storage.

    Args:
        job_id: Job identifier
        filename: File name

    Returns:
        Absolute path if file exists, None otherwise
    """
    filepath = get_job_dir(job_id) / secure_filename(filename)
    return str(filepath.absolute()) if filepath.exists() else None


def cleanup_job(job_id: str) -> None:
    """
    Remove all files for a job.

    Args:
        job_id: Job identifier to clean up
    """
    job_dir = get_job_dir(job_id)
    if job_dir.exists():
        shutil.rmtree(job_dir)


def generate_job_id() -> str:
    """Generate a unique job ID."""
    return str(uuid.uuid4())


def extract_display_name(audio_path: str, fallback: str) -> str:
    """
    Build a human-friendly display name from ID3 / Vorbis / MP4 tags.

    Preference: ``"<artist> - <title>"`` → ``"<title>"`` → ``fallback``.

    The fallback should be the original (unicode-preserving) filename so a
    CJK-named file without tags is still rendered correctly — Werkzeug's
    secure_filename strips non-ASCII characters and we never want that
    mangled string to reach the UI.
    """
    try:
        from mutagen import File as MutagenFile
    except ImportError:
        return fallback

    try:
        audio = MutagenFile(audio_path, easy=True)
        if audio is None:
            return fallback

        title = (audio.get("title") or [None])[0]
        artist = (audio.get("artist") or [None])[0]

        if title:
            title = str(title).strip()
        if artist:
            artist = str(artist).strip()

        if title and artist:
            return f"{artist} - {title}"
        if title:
            return title
    except Exception:
        pass

    return fallback


def extract_cover_art(audio_path: str, job_dir: Path) -> Optional[str]:
    """
    Extract embedded ID3 cover art from an audio file and save as cover.jpg
    under the given job directory. Returns the saved filename on success,
    or None if there's no embedded artwork (or the file format is unsupported).

    Best-effort: any extraction error is swallowed — the rest of the upload
    flow must not depend on this.
    """
    try:
        from mutagen import File as MutagenFile
        from mutagen.id3 import APIC
        from mutagen.flac import Picture as FlacPicture
        from mutagen.mp4 import MP4Cover
    except ImportError:
        return None

    try:
        audio = MutagenFile(audio_path)
        if audio is None:
            return None

        image_data: Optional[bytes] = None
        mime = "image/jpeg"

        # MP3 (ID3 APIC frames)
        tags = getattr(audio, "tags", None)
        if tags is not None:
            for key in tags.keys():
                if key.startswith("APIC"):
                    frame = tags[key]
                    if isinstance(frame, APIC):
                        image_data = frame.data
                        mime = frame.mime or mime
                        break

        # FLAC / OGG (Picture blocks)
        if image_data is None and hasattr(audio, "pictures") and audio.pictures:
            pic = audio.pictures[0]
            if isinstance(pic, FlacPicture):
                image_data = pic.data
                mime = pic.mime or mime

        # MP4 / M4A (covr atom)
        if image_data is None and tags is not None and "covr" in tags:
            covers = tags["covr"]
            if covers:
                cover = covers[0]
                image_data = bytes(cover)
                if isinstance(cover, MP4Cover):
                    if cover.imageformat == MP4Cover.FORMAT_PNG:
                        mime = "image/png"
                    else:
                        mime = "image/jpeg"

        if not image_data:
            return None

        ext = ".png" if "png" in mime.lower() else ".jpg"
        cover_name = "cover" + ext
        (job_dir / cover_name).write_bytes(image_data)
        return cover_name
    except Exception:
        return None
