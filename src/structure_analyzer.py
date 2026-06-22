"""Structure analyzer module for detecting intro, verse, chorus, bridge, outro."""

import librosa
import numpy as np
from typing import List, Dict, Tuple


def detect_beats_and_bars(audio_data: np.ndarray, sr: int, time_signature: int = 4) -> Dict:
    """
    Detect beats and bar boundaries for beat-aligned editing.

    Args:
        audio_data: Audio signal as numpy array
        sr: Sample rate
        time_signature: Beats per bar (default: 4 for 4/4 time)

    Returns:
        Dict with tempo, beats, and downbeats (bar boundaries)
    """
    # Detect tempo and beats
    tempo, beat_frames = librosa.beat.beat_track(y=audio_data, sr=sr)
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)

    # Convert tempo to scalar (librosa may return array or scalar)
    if isinstance(tempo, np.ndarray):
        tempo = float(tempo.item())  # Use .item() for safe array-to-scalar conversion
    else:
        tempo = float(tempo)

    # Estimate downbeats (first beat of each bar)
    # Group beats into bars based on time signature
    downbeat_indices = list(range(0, len(beat_times), time_signature))
    downbeats = beat_times[downbeat_indices]

    return {
        'tempo': tempo,
        'beats': beat_times,
        'downbeats': downbeats,
        'bars': len(downbeats)
    }


def find_nearest_downbeat(target_time: float, downbeats: np.ndarray) -> float:
    """
    Find the nearest downbeat to a target time for clean cuts.

    Args:
        target_time: Target time in seconds
        downbeats: Array of downbeat times

    Returns:
        Nearest downbeat time
    """
    if len(downbeats) == 0:
        return target_time

    idx = np.argmin(np.abs(downbeats - target_time))
    return downbeats[idx]


def detect_structure_boundaries(audio_data: np.ndarray, sr: int) -> np.ndarray:
    """
    Detect structural boundaries using spectral novelty.

    Args:
        audio_data: Audio signal as numpy array
        sr: Sample rate

    Returns:
        Array of boundary times in seconds
    """
    # Compute mel spectrogram
    S = librosa.feature.melspectrogram(y=audio_data, sr=sr, n_mels=128)
    S_db = librosa.power_to_db(S, ref=np.max)

    # Use librosa's agglomerative clustering for segmentation with k parameter
    # Set k to estimate number of sections based on song length
    duration = len(audio_data) / sr
    k = max(4, int(duration / 30))  # Roughly one section per 30 seconds

    boundaries = librosa.segment.agglomerative(S_db, k=k)
    boundary_times = librosa.frames_to_time(boundaries, sr=sr)

    return boundary_times


def label_sections(
    audio_data: np.ndarray,
    sr: int,
    boundaries: np.ndarray,
    chroma: np.ndarray,
    repeated_segments: List[Dict] = None
) -> List[Dict]:
    """
    Label sections as intro/verse/chorus/bridge/outro using multiple features.

    IMPROVED VERSION V2: Integrates spectral analyzer's repeated segments
    - Chorus: Overlaps with many repeated segments + high energy + 12-30s
    - Verse: Overlaps with some repeated segments + medium energy + 25-60s
    - Bridge: Few/no overlaps + varies

    Args:
        audio_data: Audio signal
        sr: Sample rate
        boundaries: Section boundary times
        chroma: Chroma features for the entire audio
        repeated_segments: List of repeated segment dicts from spectral_analyzer

    Returns:
        List of section dicts with start, end, label, repetition_count, energy
    """
    import librosa

    sections = []
    duration = len(audio_data) / sr

    # Compute RMS energy (use longer frames for stability)
    rms = librosa.feature.rms(y=audio_data, frame_length=4096, hop_length=2048)[0]
    spectral_centroid = librosa.feature.spectral_centroid(
        y=audio_data, sr=sr, n_fft=4096, hop_length=2048
    )[0]

    times = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=2048)

    # Calculate energy thresholds (chorus typically in top 40%)
    energy_threshold = np.percentile(rms, 60)  # 60th percentile
    centroid_threshold = np.percentile(spectral_centroid, 60)

    # Define intro/outro as 10s (will be extended to section boundaries by get_protected_intro_outro)
    intro_threshold = 10.0
    outro_start = duration - 10.0

    # Build repetition map from repeated_segments if provided
    repetition_map = {}
    if repeated_segments:
        # For each section boundary, count overlapping repeated segments
        for i in range(len(boundaries) - 1):
            start = float(boundaries[i])
            end = float(boundaries[i + 1])
            overlap_count = 0

            for seg_dict in repeated_segments:
                # Each repeated segment has start_time_1, start_time_2, duration
                seg1_start = seg_dict['start_time_1']
                seg1_end = seg1_start + seg_dict['duration']
                seg2_start = seg_dict['start_time_2']
                seg2_end = seg2_start + seg_dict['duration']

                # Check if either occurrence overlaps with this section
                overlap1 = not (seg1_end <= start or seg1_start >= end)
                overlap2 = not (seg2_end <= start or seg2_start >= end)

                if overlap1 or overlap2:
                    overlap_count += 1

            repetition_map[i] = overlap_count

    for i in range(len(boundaries) - 1):
        start_time = float(boundaries[i])
        end_time = float(boundaries[i + 1])
        section_duration = end_time - start_time

        start_frame = librosa.time_to_frames(start_time, sr=sr)
        end_frame = librosa.time_to_frames(end_time, sr=sr)
        segment_chroma = chroma[:, start_frame:end_frame]

        # Get energy statistics for this section
        mask = (times >= start_time) & (times < end_time)
        section_rms = rms[mask]
        section_centroid = spectral_centroid[mask]

        avg_energy = np.mean(section_rms) if len(section_rms) > 0 else 0
        avg_brightness = np.mean(section_centroid) if len(section_centroid) > 0 else 0

        is_high_energy = avg_energy > energy_threshold
        is_bright = avg_brightness > centroid_threshold

        # Get repetition count from map or fallback to old method
        if repeated_segments and i in repetition_map:
            repetition_count = min(repetition_map[i] // 100, 10)  # Normalize (5132 segments → ~0-10 scale)
        else:
            # Fallback: compare to other sections
            repetition_count = 0
            for j in range(len(boundaries) - 1):
                if i == j:
                    continue

                other_start = librosa.time_to_frames(float(boundaries[j]), sr=sr)
                other_end = librosa.time_to_frames(float(boundaries[j + 1]), sr=sr)
                other_chroma = chroma[:, other_start:other_end]

                similarity = compute_chroma_similarity(segment_chroma, other_chroma)
                if similarity > 0.75:  # High similarity threshold
                    repetition_count += 1

        # Multi-feature classification
        if start_time < intro_threshold:
            label = "intro"
        elif start_time >= outro_start:
            label = "outro"
        elif (repetition_count >= 2 and is_high_energy and is_bright and
              12.0 <= section_duration <= 30.0):
            label = "chorus"  # Repeated + high energy + bright + short = chorus
        elif (repetition_count >= 1 and 25.0 <= section_duration <= 60.0):
            label = "verse"  # Some repetition + longer duration = verse
        elif repetition_count == 0 and section_duration < 25.0:
            label = "bridge"  # No repetition + short = bridge
        else:
            # Fallback: use energy + duration
            if is_high_energy and section_duration < 25.0:
                label = "chorus"
            elif section_duration >= 25.0:
                label = "verse"
            else:
                label = "bridge"

        sections.append({
            'start': float(start_time),
            'end': float(end_time),
            'label': label,
            'repetition_count': repetition_count,
            'duration': float(section_duration),
            'avg_energy': float(avg_energy),
            'avg_brightness': float(avg_brightness)
        })

    return sections


def compute_chroma_similarity(chroma1: np.ndarray, chroma2: np.ndarray) -> float:
    """
    Compute similarity between two chroma segments.

    Args:
        chroma1: First chroma segment
        chroma2: Second chroma segment

    Returns:
        Similarity score (0-1)
    """
    # Normalize to same length for comparison
    min_len = min(chroma1.shape[1], chroma2.shape[1])
    if min_len == 0:
        return 0.0

    c1 = chroma1[:, :min_len]
    c2 = chroma2[:, :min_len]

    # Flatten and compute cosine similarity
    c1_flat = c1.flatten()
    c2_flat = c2.flatten()

    norm1 = np.linalg.norm(c1_flat)
    norm2 = np.linalg.norm(c2_flat)

    if norm1 == 0 or norm2 == 0:
        return 0.0

    similarity = np.dot(c1_flat, c2_flat) / (norm1 * norm2)
    return max(0.0, similarity)  # Ensure non-negative


def analyze_structure(audio_data: np.ndarray, sr: int, chroma: np.ndarray, repeated_segments: List[Dict] = None) -> Dict:
    """
    Analyze audio structure: beats, boundaries, and section labels.

    Args:
        audio_data: Audio signal
        sr: Sample rate
        chroma: Chroma features from spectral_analyzer
        repeated_segments: Optional list of repeated segment dicts from spectral_analyzer (V2 improvement)

    Returns:
        Dict with beat_info, boundaries, and sections
    """
    # Detect beats and bars
    beat_info = detect_beats_and_bars(audio_data, sr)

    # Detect structural boundaries
    boundaries = detect_structure_boundaries(audio_data, sr)

    # Label sections (V2: now integrates repeated_segments)
    sections = label_sections(audio_data, sr, boundaries, chroma, repeated_segments)

    return {
        'beat_info': beat_info,
        'boundaries': boundaries,
        'sections': sections
    }
    """
    Complete structure analysis: beats, bars, boundaries, and section labels.

    Args:
        audio_data: Audio signal
        sr: Sample rate
        chroma: Pre-computed chroma features

    Returns:
        Dict with beat_info, boundaries, and sections
    """
    # Detect beats and bars
    beat_info = detect_beats_and_bars(audio_data, sr)

    # Detect structural boundaries
    boundaries = detect_structure_boundaries(audio_data, sr)

    # Label sections
    sections = label_sections(audio_data, sr, boundaries, chroma)

    return {
        'beat_info': beat_info,
        'boundaries': boundaries,
        'sections': sections
    }


def get_protected_intro_outro(audio_data: np.ndarray, sr: int, sections: List[Dict] = None) -> List[Tuple[float, float]]:
    """
    Get intro and outro regions that should be protected.

    NEW: Protection is 10s OR first section boundary, whichever is longer.
    This ensures we don't cut mid-verse.

    Args:
        audio_data: Audio signal
        sr: Sample rate
        sections: Optional list of section dicts with start, end, label

    Returns:
        List of (start, end) tuples for intro and outro
    """
    duration = len(audio_data) / sr

    # Intro: 10 seconds OR end of first section, whichever is longer
    intro_duration = 10.0
    if sections and len(sections) > 0:
        first_section_end = sections[0]['end']
        intro_duration = max(10.0, first_section_end)  # Don't cut mid-section
    intro = (0.0, intro_duration)

    # Outro: 10 seconds OR start of last section, whichever is earlier
    outro_duration = 10.0
    if sections and len(sections) > 0:
        last_section_start = sections[-1]['start']
        outro_start = min(duration - 10.0, last_section_start)  # Don't cut mid-section
    else:
        outro_start = duration - outro_duration
    outro = (outro_start, duration)

    return [intro, outro]
