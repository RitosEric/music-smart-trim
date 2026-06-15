"""Quality scorer module for rating trim strategies."""

from typing import Dict, List, Tuple
import numpy as np
import librosa
from src.trim_engine import TrimStrategy


def score_transition_smoothness(
    audio: np.ndarray,
    sr: int,
    cut_points: List[Tuple[float, float]],
    fade_regions: List[Tuple[float, float]]
) -> float:
    """
    Score transition smoothness (max 40 points).

    Components:
    - Phase alignment (15 points): Check amplitude at cut points
    - Zero-crossing (10 points): Check if cuts are near zero-crossings
    - Fade quality (15 points): Check fade duration and smoothness

    Args:
        audio: Audio signal as numpy array
        sr: Sample rate
        cut_points: List of (start_time, end_time) tuples for cuts
        fade_regions: List of (fade_start, fade_end) tuples for fades

    Returns:
        Score from 0 to 40 points
    """
    if not cut_points:
        # No cuts means perfect smoothness
        return 40.0

    phase_score = 0.0
    zero_crossing_score = 0.0
    fade_score = 0.0

    # Phase alignment scoring (15 points max)
    for cut_start, cut_end in cut_points:
        start_idx = int(cut_start * sr)
        end_idx = int(cut_end * sr)

        # Check amplitude at cut points (lower is better)
        if start_idx < len(audio):
            start_amp = abs(audio[start_idx])
            # Score: 0.0 amplitude = full points, 1.0 amplitude = 0 points
            phase_score += (1.0 - min(start_amp, 1.0)) * (7.5 / len(cut_points))

        if end_idx < len(audio):
            end_amp = abs(audio[end_idx])
            phase_score += (1.0 - min(end_amp, 1.0)) * (7.5 / len(cut_points))

    # Zero-crossing scoring (10 points max)
    for cut_start, cut_end in cut_points:
        start_idx = int(cut_start * sr)
        end_idx = int(cut_end * sr)

        # Check for zero-crossings within ±100 samples
        window = 100
        if start_idx < len(audio):
            start_window = audio[max(0, start_idx - window):min(len(audio), start_idx + window)]
            if len(start_window) > 0:
                # Check if there's a zero crossing (sign change)
                zero_crossings = np.where(np.diff(np.sign(start_window)))[0]
                if len(zero_crossings) > 0:
                    zero_crossing_score += 5.0 / len(cut_points)

        if end_idx < len(audio):
            end_window = audio[max(0, end_idx - window):min(len(audio), end_idx + window)]
            if len(end_window) > 0:
                zero_crossings = np.where(np.diff(np.sign(end_window)))[0]
                if len(zero_crossings) > 0:
                    zero_crossing_score += 5.0 / len(cut_points)

    # Fade quality scoring (15 points max)
    for fade_start, fade_end in fade_regions:
        fade_duration = fade_end - fade_start

        # Ideal fade durations: 0.15s (conservative), 0.075s (balanced), 0.0375s (aggressive)
        # Score based on duration: 0.05-0.3s is good range
        if 0.05 <= fade_duration <= 0.3:
            fade_score += 10.0 / len(fade_regions)
        elif 0.03 <= fade_duration <= 0.5:
            fade_score += 5.0 / len(fade_regions)

        # Check fade smoothness (fade regions should have gradual amplitude change)
        fade_start_idx = int(fade_start * sr)
        fade_end_idx = int(fade_end * sr)

        if fade_start_idx < len(audio) and fade_end_idx < len(audio):
            fade_segment = audio[fade_start_idx:fade_end_idx]
            if len(fade_segment) > 1:
                # Check if amplitude changes gradually (low variance in differences)
                amp_envelope = np.abs(fade_segment)
                if len(amp_envelope) > 2:
                    gradients = np.diff(amp_envelope)
                    gradient_variance = np.var(gradients)
                    # Lower variance = smoother fade
                    if gradient_variance < 0.01:
                        fade_score += 5.0 / len(fade_regions)
                    elif gradient_variance < 0.05:
                        fade_score += 2.5 / len(fade_regions)

    total_score = phase_score + zero_crossing_score + fade_score
    return min(40.0, total_score)


def score_musical_coherence(
    audio: np.ndarray,
    sr: int,
    cut_points: List[Tuple[float, float]]
) -> float:
    """
    Score musical coherence (max 40 points).

    Components:
    - Beat alignment (20 points): Check if cuts are near beats
    - Harmonic continuity (10 points): Check chroma similarity at cut boundaries
    - Section order (10 points): Penalize cuts in intro/outro

    Args:
        audio: Audio signal as numpy array
        sr: Sample rate
        cut_points: List of (start_time, end_time) tuples for cuts

    Returns:
        Score from 0 to 40 points
    """
    if not cut_points:
        # No cuts means perfect coherence
        return 40.0

    beat_score = 0.0
    harmonic_score = 0.0
    section_score = 0.0

    # Get beat times using librosa
    try:
        tempo, beat_frames = librosa.beat.beat_track(y=audio, sr=sr)
        beat_times = librosa.frames_to_time(beat_frames, sr=sr)
    except Exception:
        # If beat tracking fails, give partial credit
        beat_times = np.array([])

    # Calculate audio duration
    duration = len(audio) / sr

    # Beat alignment scoring (20 points max)
    if len(beat_times) > 0:
        for cut_start, cut_end in cut_points:
            # Check if cut_start is near a beat (within ±0.1s)
            start_distances = np.abs(beat_times - cut_start)
            if len(start_distances) > 0 and np.min(start_distances) <= 0.1:
                beat_score += 10.0 / len(cut_points)

            # Check if cut_end is near a beat (within ±0.1s)
            end_distances = np.abs(beat_times - cut_end)
            if len(end_distances) > 0 and np.min(end_distances) <= 0.1:
                beat_score += 10.0 / len(cut_points)
    else:
        # If no beats detected, give partial credit based on timing regularity
        beat_score = 10.0

    # Harmonic continuity scoring (10 points max)
    try:
        # Compute chromagram for harmonic analysis
        chroma = librosa.feature.chroma_cqt(y=audio, sr=sr)

        for cut_start, cut_end in cut_points:
            # Get chroma at cut boundaries
            start_frame = librosa.time_to_frames(cut_start, sr=sr)
            end_frame = librosa.time_to_frames(cut_end, sr=sr)

            if start_frame < chroma.shape[1] and end_frame < chroma.shape[1]:
                # Get chroma vectors before cut_start and after cut_end
                before_chroma = chroma[:, max(0, start_frame - 2):start_frame + 1]
                after_chroma = chroma[:, end_frame:min(chroma.shape[1], end_frame + 3)]

                if before_chroma.size > 0 and after_chroma.size > 0:
                    # Average chroma for before and after
                    before_avg = np.mean(before_chroma, axis=1)
                    after_avg = np.mean(after_chroma, axis=1)

                    # Calculate cosine similarity
                    similarity = np.dot(before_avg, after_avg) / (
                        np.linalg.norm(before_avg) * np.linalg.norm(after_avg) + 1e-8
                    )

                    # Higher similarity = better score
                    harmonic_score += similarity * (10.0 / len(cut_points))
    except Exception:
        # If chroma analysis fails, give partial credit
        harmonic_score = 5.0

    # Section order scoring (10 points max)
    intro_duration = min(10.0, duration * 0.1)  # First 10s or 10% of song
    outro_duration = min(10.0, duration * 0.1)  # Last 10s or 10% of song

    for cut_start, cut_end in cut_points:
        # Check if cut is in intro
        if cut_start < intro_duration:
            # Penalize intro cuts
            section_score -= 5.0 / len(cut_points)
        # Check if cut is in outro
        elif cut_end > (duration - outro_duration):
            # Penalize outro cuts
            section_score -= 5.0 / len(cut_points)
        else:
            # Reward middle cuts
            section_score += 10.0 / len(cut_points)

    total_score = beat_score + harmonic_score + section_score
    return max(0.0, min(40.0, total_score))


def score_length_accuracy(target_length: float, resulting_length: float) -> float:
    """
    Score length accuracy (max 20 points).

    Thresholds:
    - ±0-3s → 20 points
    - ±3-8s → 15 points
    - ±8-15s → 10 points
    - >±15s → 0 points

    Args:
        target_length: Target length in seconds
        resulting_length: Resulting length after applying strategy

    Returns:
        Score from 0 to 20 points
    """
    error = abs(resulting_length - target_length)

    if error <= 3.0:
        return 20.0
    elif error <= 8.0:
        return 15.0
    elif error <= 15.0:
        return 10.0
    else:
        return 0.0


def score_strategy(
    strategy: TrimStrategy,
    audio: np.ndarray,
    sr: int,
    original_length: float
) -> Dict:
    """
    Score a complete trim strategy.

    Calculates resulting length, scores all 3 components (transition smoothness,
    musical coherence, length accuracy), and converts total to star rating.

    Scoring weights:
    - Transition smoothness: 40% (40 points max)
    - Musical coherence: 40% (40 points max)
    - Length accuracy: 20% (20 points max)
    Total: 100 points → converted to 0.5-5.0 star rating

    Args:
        strategy: TrimStrategy object with cut_points, loop_points, fade_regions, target_length
        audio: Audio signal as numpy array
        sr: Sample rate
        original_length: Original audio length in seconds

    Returns:
        Dict with keys:
            - total_points: Total score (0-100)
            - star_rating: Star rating (0.5-5.0)
            - breakdown: Dict with component scores
                - transition_smoothness: 0-40 points
                - musical_coherence: 0-40 points
                - length_accuracy: 0-20 points
    """
    # Calculate resulting length after applying strategy
    resulting_length = strategy.calculate_resulting_length(original_length)

    # Score transition smoothness (40 points max)
    transition_score = score_transition_smoothness(
        audio, sr, strategy.cut_points, strategy.fade_regions
    )

    # Score musical coherence (40 points max)
    coherence_score = score_musical_coherence(
        audio, sr, strategy.cut_points
    )

    # Score length accuracy (20 points max)
    length_score = score_length_accuracy(
        strategy.target_length, resulting_length
    )

    # Calculate total points
    total_points = transition_score + coherence_score + length_score

    # Convert to star rating
    star_rating = points_to_stars(total_points)

    return {
        'total_points': total_points,
        'star_rating': star_rating,
        'breakdown': {
            'transition_smoothness': transition_score,
            'musical_coherence': coherence_score,
            'length_accuracy': length_score
        }
    }


def points_to_stars(points: float) -> float:
    """
    Convert points (0-100 scale) to star rating.

    Thresholds:
    - ≥90 points → 5.0 stars
    - ≥85 points → 4.5 stars
    - ≥80 points → 4.0 stars
    - ≥75 points → 3.5 stars
    - ≥70 points → 3.0 stars
    - ≥65 points → 2.5 stars
    - ≥60 points → 2.0 stars
    - ≥55 points → 1.5 stars
    - ≥50 points → 1.0 star
    - <50 points → 0.5 stars

    Args:
        points: Score on 0-100 scale

    Returns:
        Star rating (0.5 to 5.0)
    """
    if points >= 90:
        return 5.0
    elif points >= 85:
        return 4.5
    elif points >= 80:
        return 4.0
    elif points >= 75:
        return 3.5
    elif points >= 70:
        return 3.0
    elif points >= 65:
        return 2.5
    elif points >= 60:
        return 2.0
    elif points >= 55:
        return 1.5
    elif points >= 50:
        return 1.0
    else:
        return 0.5
