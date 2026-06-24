# api/processing.py
"""Audio processing wrapper with progress callbacks."""
import sys
import os
import threading
from pathlib import Path
from typing import Dict, Callable, Optional, List

# Add parent directory to path to import src modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.cli import run_pipeline
from api.storage import get_job_dir


class ProcessingError(Exception):
    """Exception raised during audio processing."""
    pass


def process_audio(
    job_id: str,
    input_path: str,
    params: Dict,
    progress_callback: Optional[Callable[[str, int], None]] = None
) -> Dict:
    """
    Process audio using existing pipeline with progress updates.

    Args:
        job_id: Unique job identifier
        input_path: Path to input audio file
        params: Processing parameters dict with keys:
            - target_length: float (seconds)
            - protected_regions: List[str] (MM:SS-MM:SS format)
            - auto_protect: bool
            - min_segment_duration: float
            - regenerate_seed: Optional[int]
        progress_callback: Optional callback function(message: str, progress: int)

    Returns:
        Dict with keys:
            - status: 'completed' or 'failed'
            - result: Dict with processing results
            - error: Optional error message

    Raises:
        ProcessingError: If processing fails
    """
    try:
        # Setup output directory in job storage
        job_dir = get_job_dir(job_id)
        output_dir = job_dir / "output"
        output_dir.mkdir(exist_ok=True)

        # Send initial progress
        if progress_callback:
            progress_callback("Loading audio...", 10)

        # Extract parameters
        target_length = params.get('target_length')
        protected_regions = params.get('protected_regions', [])
        auto_protect = params.get('auto_protect', False)
        min_segment_duration = params.get('min_segment_duration', 10.0)
        regenerate_seed = params.get('regenerate_seed', None)
        strict_length = params.get('strict_length', False)

        if progress_callback:
            progress_callback("Analyzing audio structure...", 30)

        # Run pipeline. We deliberately do NOT pass excluded_strategies — the
        # engine has only five strategy names per generation, so excluding by
        # name would cut the result count below five on every regenerate.
        # Variation across regenerate calls is driven by regenerate_seed.
        result = run_pipeline(
            audio_path=Path(input_path),
            target_length=target_length,
            protected_regions=protected_regions,
            output_dir=output_dir,
            regenerate_seed=regenerate_seed,
            excluded_strategies=None,
            auto_protect=auto_protect,
            min_segment_duration=min_segment_duration,
            strict_length=strict_length,
            progress_callback=progress_callback,
        )

        if progress_callback:
            # Bumped from 80 → 90 so retry messages emitted by
            # retry_for_quality / retry_for_strict_length (which top out at
            # 75%) don't get visually undercut by this post-pipeline milestone.
            progress_callback("Generating outputs...", 90)

        # Format response - return top 3 strategies from the pipeline
        strategies = result.get('strategies', [])
        outputs = []
        for i, (score, output_file) in enumerate(zip(result['scores'], result['output_files'])):
            strategy_name = strategies[i].name if i < len(strategies) else None
            outputs.append({
                'rank': i + 1,
                'rating': score['star_rating'],
                'length': score['resulting_length'],
                'filename': Path(output_file).name,
                'path': str(output_file),
                'strategy_name': strategy_name,
            })

        if progress_callback:
            progress_callback("Complete!", 100)

        return {
            'status': 'completed',
            'result': {
                'original_length': result['original_length'],
                'target_length': target_length,
                'processing_time': result['processing_time'],
                'best_rating': result['scores'][0]['star_rating'],
                'outputs': outputs,
                'mode': 'trim' if target_length < result['original_length'] else 'extend',
                'all_strategy_names': result.get('all_strategy_names', []),
                'strict_length_requested': result.get('strict_length_requested', False),
                'strict_length_met': result.get('strict_length_met', False),
                'auto_protect_requested': auto_protect,
            }
        }

    except Exception as e:
        error_msg = str(e)
        if progress_callback:
            progress_callback(f"Error: {error_msg}", 0)

        return {
            'status': 'failed',
            'error': error_msg
        }


def process_audio_async(job_id, input_path, params, progress_callback, socketio):
    """
    Process audio in background thread.

    Args:
        Same as process_audio, plus socketio instance
    """
    def run():
        result = process_audio(job_id, input_path, params, progress_callback)
        # Update global job_status after completion
        from api.routes import job_status
        job_status[job_id].update({
            'status': result['status'],
            'progress': 100 if result['status'] == 'completed' else 0,
            'result': result.get('result'),
            'error': result.get('error')
        })
        # Emit final status
        if socketio:
            from api.websocket import emit_progress
            if result['status'] == 'completed':
                emit_progress(socketio, job_id, 'Processing complete!', 100)
            else:
                emit_progress(socketio, job_id, f"Error: {result.get('error')}", 0)

    thread = threading.Thread(target=run)
    thread.start()
    return thread

