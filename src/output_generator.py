"""Output generator module for rendering audio with strategies applied."""

import numpy as np
import soundfile as sf
import json
from pathlib import Path
from typing import List, Tuple, Dict, Any
from src.trim_engine import TrimStrategy
from src.crossfade import DEFAULT_CROSSFADE_MS, ms_to_samples


def _convert_to_serializable(obj: Any) -> Any:
    """
    Convert numpy types to Python native types for JSON serialization.

    Args:
        obj: Object to convert (can be dict, list, numpy type, or primitive)

    Returns:
        Object with numpy types converted to Python types
    """
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: _convert_to_serializable(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [_convert_to_serializable(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(_convert_to_serializable(item) for item in obj)
    else:
        return obj


def apply_cuts(audio: np.ndarray, sr: int, cut_points: List[Tuple[float, float]]) -> np.ndarray:
    """
    Apply cuts to audio by removing specified regions, with ENHANCED crossfades at boundaries.

    Merges overlapping cut regions before applying.
    Applies standard constant-power crossfades (500ms) for smoother, more natural transitions.

    Args:
        audio: Audio signal as numpy array
        sr: Sample rate
        cut_points: List of (start_time, end_time) tuples for sections to remove

    Returns:
        Audio with cut regions removed and smoothly crossfaded
    """
    if not cut_points:
        return audio.copy()

    # Sort cut points by start time
    sorted_cuts = sorted(cut_points, key=lambda c: c[0])

    # Merge overlapping cuts
    merged_cuts = []
    current_start, current_end = sorted_cuts[0]

    for start, end in sorted_cuts[1:]:
        if start <= current_end:
            # Overlapping or adjacent - merge by extending the end
            current_end = max(current_end, end)
        else:
            # No overlap - save current and start new
            merged_cuts.append((current_start, current_end))
            current_start, current_end = start, end

    # Add the last cut
    merged_cuts.append((current_start, current_end))

    # Build segments to keep with crossfades at boundaries
    from src.crossfade import constant_power_crossfade, apply_smooth_fade_out, apply_smooth_fade_in

    segments = []
    last_end = 0
    crossfade_samples = ms_to_samples(DEFAULT_CROSSFADE_MS, sr)  # 500ms crossfade for smooth transitions

    for i, (cut_start, cut_end) in enumerate(merged_cuts):
        cut_start_sample = int(cut_start * sr)
        cut_end_sample = int(cut_end * sr)

        # Add segment before cut
        if cut_start_sample > last_end:
            segment = audio[last_end:cut_start_sample]

            # Apply fade-out to end of segment (smooth ending before cut)
            fade_out_duration = min(crossfade_samples, len(segment) // 2)
            segment = apply_smooth_fade_out(segment, fade_out_duration)

            segments.append(segment)

        # Move past the cut
        last_end = cut_end_sample

    # Add final segment after last cut
    if last_end < len(audio):
        final_segment = audio[last_end:]

        # Apply fade-in to start of final segment (smooth entry after cut)
        fade_in_duration = min(crossfade_samples, len(final_segment) // 2)
        final_segment = apply_smooth_fade_in(final_segment, fade_in_duration)

        # Apply fade-out to end of final segment (smooth ending)
        fade_out_duration = min(crossfade_samples, len(final_segment) // 2)
        final_segment = apply_smooth_fade_out(final_segment, fade_out_duration)

        segments.append(final_segment)

    # Concatenate segments with crossfades between them
    if len(segments) == 0:
        return np.array([], dtype=audio.dtype)
    elif len(segments) == 1:
        return segments[0]
    else:
        result = segments[0]
        for i in range(1, len(segments)):
            # Apply constant-power crossfade between segments (500ms overlap)
            result = constant_power_crossfade(result, segments[i], crossfade_samples)
        return result


def apply_loops(audio: np.ndarray, sr: int, loop_points: List[Tuple[float, float, int]]) -> np.ndarray:
    """
    Apply loops to audio by repeating specified segments with constant-power crossfades at boundaries.

    Repeats loop segments with 500ms constant-power crossfades between each repetition
    for seamless, natural-sounding loops.

    Args:
        audio: Audio signal as numpy array
        sr: Sample rate
        loop_points: List of (start_time, end_time, repeat_count) tuples for sections to repeat

    Returns:
        Audio with loop regions repeated and crossfaded at boundaries
    """
    if not loop_points:
        return audio.copy()

    from src.crossfade import constant_power_crossfade

    # Sort loop points by start time
    sorted_loops = sorted(loop_points, key=lambda l: l[0])

    # Build segments with loops applied and crossfaded
    segments = []
    last_end = 0
    crossfade_samples = ms_to_samples(DEFAULT_CROSSFADE_MS, sr)  # 500ms crossfade

    for loop_start, loop_end, repeat_count in sorted_loops:
        loop_start_sample = int(loop_start * sr)
        loop_end_sample = int(loop_end * sr)

        # Add segment before loop
        if loop_start_sample > last_end:
            segments.append(audio[last_end:loop_start_sample])

        # Add the loop segment repeated repeat_count times with crossfades
        loop_segment = audio[loop_start_sample:loop_end_sample]

        # Build the repeated loop with crossfades between each repetition
        if repeat_count > 0:
            looped_audio = loop_segment.copy()
            for _ in range(repeat_count - 1):
                # Apply constant-power crossfade between repetitions
                looped_audio = constant_power_crossfade(looped_audio, loop_segment, crossfade_samples)
            segments.append(looped_audio)

        # Move past the loop
        last_end = loop_end_sample

    # Add final segment after last loop
    if last_end < len(audio):
        final_segment = audio[last_end:]

        # Apply fade-out to end of final segment (smooth outro ending)
        from src.crossfade import apply_smooth_fade_out
        fade_out_duration = min(crossfade_samples, len(final_segment) // 2)
        final_segment = apply_smooth_fade_out(final_segment, fade_out_duration)

        segments.append(final_segment)

    # Concatenate all segments
    if segments:
        return np.concatenate(segments)
    else:
        return np.array([], dtype=audio.dtype)


def apply_crossfades(audio: np.ndarray, sr: int, fade_regions: List[Tuple[float, float]]) -> np.ndarray:
    """
    Apply crossfades to audio using linear fade curves.

    Args:
        audio: Audio signal as numpy array
        sr: Sample rate
        fade_regions: List of (fade_start, fade_end) tuples for crossfade locations

    Returns:
        Audio with crossfades applied
    """
    if not fade_regions:
        return audio.copy()

    # Work on a copy of the audio
    result = audio.copy()

    # Apply each fade
    for fade_start, fade_end in fade_regions:
        fade_start_sample = int(fade_start * sr)
        fade_end_sample = int(fade_end * sr)

        # Ensure fade region is within bounds
        fade_start_sample = max(0, fade_start_sample)
        fade_end_sample = min(len(result), fade_end_sample)

        if fade_start_sample >= fade_end_sample:
            continue

        # Calculate fade length
        fade_length = fade_end_sample - fade_start_sample

        # Apply linear fade curve (0 to 1)
        fade_curve = np.linspace(0, 1, fade_length)

        # Apply fade to audio
        result[fade_start_sample:fade_end_sample] *= fade_curve

    return result


def render_strategy(strategy: TrimStrategy, audio: np.ndarray, sr: int, beat_info: Dict = None) -> np.ndarray:
    """
    Render a complete trim strategy by applying loops, cuts, and constant-power crossfades in sequence.

    Order of operations:
    1. Apply loops (extends audio)
    2. Apply cuts (shortens audio)
    3. Apply constant-power crossfades (smooths transitions)

    Args:
        strategy: TrimStrategy with cut_points, loop_points, and fade_regions
        audio: Original audio signal as numpy array
        sr: Sample rate
        beat_info: Optional dict with tempo, beats for beat-synced crossfading

    Returns:
        Rendered audio with strategy applied
    """
    # Step 1: Apply loops (extends audio)
    result = apply_loops(audio, sr, strategy.loop_points)

    # Step 2: Apply cuts (shortens audio)
    result = apply_cuts(result, sr, strategy.cut_points)

    # Step 3: Apply constant-power crossfades (smooths transitions)
    # Use beat-synced crossfading if beat info is available
    from src.crossfade import apply_smooth_fade_in, apply_smooth_fade_out

    # Apply fade-in at the beginning (intro) and fade-out at the end (outro)
    fade_samples = ms_to_samples(DEFAULT_CROSSFADE_MS, sr)  # 500ms fade
    result = apply_smooth_fade_in(result, fade_samples)
    result = apply_smooth_fade_out(result, fade_samples)

    return result


def generate_outputs(
    audio: np.ndarray,
    sr: int,
    strategies: List[TrimStrategy],
    scores: List[Dict],
    output_dir: Path,
    input_file: str,
    target_length: float,
    protected_regions: List[Tuple[float, float]],
    processing_time: float
) -> None:
    """
    Generate output files for all strategies with metadata.

    Creates:
    - Audio files: option_{i}_{stars}stars.wav
    - summary.json: Complete metadata
    - summary.txt: Human-readable summary

    Args:
        audio: Original audio signal
        sr: Sample rate
        strategies: List of TrimStrategy objects
        scores: List of score dicts with star_rating, total_points, breakdown
        output_dir: Directory to save output files
        input_file: Original input filename
        target_length: Target length in seconds
        protected_regions: List of protected region tuples
        processing_time: Processing time in seconds
    """
    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Render and save each strategy
    rendered_outputs = []
    for i, (strategy, score) in enumerate(zip(strategies, scores)):
        # Render strategy
        rendered_audio = render_strategy(strategy, audio, sr)

        # Calculate resulting length
        resulting_length = len(rendered_audio) / sr

        # Format star rating for filename (rounded to 0.1)
        stars = score['star_rating']

        # Generate filename: option_{i}_{stars}stars.wav
        output_filename = f"option_{i}_{stars:.1f}stars.wav"
        output_path = output_dir / output_filename

        # Save audio file with high quality (PCM 16-bit)
        sf.write(output_path, rendered_audio, sr, subtype='PCM_16')

        # Store info for metadata
        rendered_outputs.append({
            'filename': output_filename,
            'strategy_name': strategy.name,
            'star_rating': stars,
            'total_points': score['total_points'],
            'breakdown': score['breakdown'],
            'resulting_length': resulting_length,
            'cut_points': strategy.cut_points,
            'loop_points': strategy.loop_points,
            'fade_regions': strategy.fade_regions
        })

    # Generate summary.json
    summary_data = {
        'input_file': input_file,
        'target_length': target_length,
        'protected_regions': protected_regions,
        'processing_time': processing_time,
        'options': rendered_outputs
    }

    # Convert numpy types to Python types for JSON serialization
    summary_data = _convert_to_serializable(summary_data)

    summary_json_path = output_dir / "summary.json"
    with open(summary_json_path, 'w') as f:
        json.dump(summary_data, f, indent=2)

    # Generate summary.txt
    summary_txt_path = output_dir / "summary.txt"
    with open(summary_txt_path, 'w') as f:
        f.write("Music Smart Trim - Summary\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"Input file: {input_file}\n")
        f.write(f"Target length: {target_length}s\n")
        f.write(f"Processing time: {processing_time:.2f}s\n")
        f.write(f"Protected regions: {len(protected_regions)}\n\n")

        f.write("Output Options:\n")
        f.write("-" * 50 + "\n\n")

        for output in rendered_outputs:
            # Format star rating with symbols
            star_rating = output['star_rating']
            full_stars = int(star_rating)
            half_star = (star_rating - full_stars) >= 0.5
            star_display = "★" * full_stars
            if half_star:
                star_display += "½"
            empty_stars = 5 - full_stars - (1 if half_star else 0)
            star_display += "☆" * empty_stars

            f.write(f"File: {output['filename']}\n")
            f.write(f"Rating: {star_display} ({star_rating} stars)\n")
            f.write(f"Strategy: {output['strategy_name']}\n")
            f.write(f"Points: {output['total_points']:.1f}/100\n")
            f.write(f"Resulting length: {output['resulting_length']:.2f}s\n")
            f.write(f"Cuts: {len(output['cut_points'])}\n")
            f.write(f"Loops: {len(output['loop_points'])}\n")
            f.write(f"Fades: {len(output['fade_regions'])}\n")
            f.write("\n")
