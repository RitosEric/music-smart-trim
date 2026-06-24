"""Structure analyzer module for detecting intro, verse, chorus, bridge, outro."""

import librosa
import numpy as np
from typing import List, Dict, Tuple


def _downbeats_via_madmom(audio_data: np.ndarray, sr: int):
    """Detect downbeats with madmom's DBN tracker, or return None if unavailable.

    madmom's neural downbeat tracker locates true bar lines far more reliably
    than grouping librosa beats into fixed 4-beat bars — which matters because
    every cut and loop endpoint snaps to a downbeat. It is an *optional*
    dependency, though: madmom 0.16.x does not run on Python 3.12 (it imports
    the removed ``pkg_resources`` and ``collections.MutableSequence``). Any
    import or runtime failure returns None so the caller falls back to the
    librosa estimate; on a compatible interpreter (Python <= 3.11) the better
    detector is used automatically with no code change.
    """
    try:
        from madmom.features.downbeats import (
            RNNDownBeatProcessor,
            DBNDownBeatTrackingProcessor,
        )
        from madmom.audio.signal import Signal
    except Exception:
        return None
    try:
        signal = Signal(
            np.asarray(audio_data, dtype=np.float32),
            sample_rate=sr,
            num_channels=1,
        )
        activations = RNNDownBeatProcessor()(signal)
        tracker = DBNDownBeatTrackingProcessor(beats_per_bar=[3, 4], fps=100)
        beats = tracker(activations)  # rows of [time, beat_position_in_bar]
        downbeats = np.asarray(
            [time for time, position in beats if int(position) == 1], dtype=float
        )
        return downbeats if downbeats.size > 0 else None
    except Exception:
        return None


def detect_beats_and_bars(audio_data: np.ndarray, sr: int, time_signature: int = 4) -> Dict:
    """
    Detect beats and bar boundaries for beat-aligned editing.

    Downbeats come from madmom when it is installed and working; otherwise they
    are estimated by grouping librosa beats into bars of ``time_signature``
    beats. Cuts and loops snap to these downbeats, so better downbeats mean
    cleaner edits.

    Args:
        audio_data: Audio signal as numpy array
        sr: Sample rate
        time_signature: Beats per bar (default: 4 for 4/4 time)

    Returns:
        Dict with tempo, beats, and downbeats (bar boundaries)
    """
    # Detect tempo and beats (librosa is always available).
    tempo, beat_frames = librosa.beat.beat_track(y=audio_data, sr=sr)
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)

    # Convert tempo to scalar (librosa may return array or scalar)
    if isinstance(tempo, np.ndarray):
        tempo = float(tempo.item())  # Use .item() for safe array-to-scalar conversion
    else:
        tempo = float(tempo)

    # Prefer madmom's downbeats; fall back to grouping beats into bars.
    downbeats = _downbeats_via_madmom(audio_data, sr)
    if downbeats is None:
        downbeat_indices = list(range(0, len(beat_times), time_signature))
        downbeats = beat_times[downbeat_indices]

    return {
        'tempo': tempo,
        'beats': beat_times,
        'downbeats': downbeats,
        'bars': len(downbeats)
    }


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

    # Use librosa's agglomerative clustering for segmentation with k parameter.
    # Aim for roughly one section per 20s (min 6) so even short songs yield
    # enough interior sections for the planner to choose from.
    duration = len(audio_data) / sr
    k = max(6, int(duration / 20))

    boundaries = librosa.segment.agglomerative(S_db, k=k)
    boundary_times = librosa.frames_to_time(boundaries, sr=sr)

    # agglomerative returns segment *start* frames, so the final segment (last
    # boundary → end of song) would otherwise be dropped, hiding the song's
    # tail from the planner. Force the boundary set to span [0, duration].
    boundary_times = np.concatenate(([0.0], boundary_times, [duration]))
    boundary_times = np.unique(np.round(boundary_times, 3))

    return boundary_times


def count_section_repetitions(
    section_chromas: List[np.ndarray],
    similarity_threshold: float = 0.85,
) -> List[int]:
    """Count, per section, how many other sections share its harmonic content.

    Each input is a section's (mean) chroma vector. Two sections "repeat" when
    their cosine similarity meets ``similarity_threshold``. The returned count
    is the direct, robust signal of repetition that distinguishes repeated
    sections (verse/chorus) from one-off sections (bridge) — replacing the old
    repeated-segment overlap heuristic.
    """
    vecs = [np.asarray(v, dtype=float) for v in section_chromas]
    norms = [float(np.linalg.norm(v)) for v in vecs]
    counts = []
    for i in range(len(vecs)):
        c = 0
        for j in range(len(vecs)):
            if i == j or norms[i] < 1e-9 or norms[j] < 1e-9:
                continue
            cos = float(np.dot(vecs[i], vecs[j]) / (norms[i] * norms[j]))
            if cos >= similarity_threshold:
                c += 1
        counts.append(c)
    return counts


def label_sections(
    audio_data: np.ndarray,
    sr: int,
    boundaries: np.ndarray,
    chroma: np.ndarray,
) -> List[Dict]:
    """
    Label sections as intro/verse/chorus/bridge/outro from energy + repetition.

    A chorus is a repeated, high-energy section; a verse repeats but isn't the
    loud hook; a bridge is a one-off. Repetition is measured by chroma
    similarity between sections (see count_section_repetitions).

    Args:
        audio_data: Audio signal
        sr: Sample rate
        boundaries: Section boundary times
        chroma: Chroma features for the entire audio

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

    # How often each section repeats elsewhere in the song, measured directly
    # from harmonic content: count the other sections whose mean chroma matches.
    # This replaces a brittle overlap-count//100 heuristic that collapsed to
    # noise on real songs. ``repeated_segments`` is no longer needed for this.
    section_mean_chromas = []
    for i in range(len(boundaries) - 1):
        sf = librosa.time_to_frames(float(boundaries[i]), sr=sr)
        ef = librosa.time_to_frames(float(boundaries[i + 1]), sr=sr)
        seg = chroma[:, sf:ef]
        section_mean_chromas.append(
            seg.mean(axis=1) if seg.shape[1] > 0 else np.zeros(chroma.shape[0])
        )
    repetition_counts = count_section_repetitions(section_mean_chromas, similarity_threshold=0.9)

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

        repetition_count = repetition_counts[i]

        # Multi-feature classification. A chorus is the *repeated, loud* section;
        # a verse repeats but is not the energetic hook; a bridge is a one-off.
        # The duration window is generous (8-45s) so real choruses outside the
        # old rigid 12-30s band are still caught.
        if start_time < intro_threshold:
            label = "intro"
        elif start_time >= outro_start:
            label = "outro"
        elif repetition_count >= 1 and is_high_energy and 8.0 <= section_duration <= 45.0:
            label = "chorus"   # repeated + high energy = the hook
        elif repetition_count >= 1:
            label = "verse"    # repeated but not the loud hook
        elif section_duration < 30.0:
            label = "bridge"   # unique, shortish
        else:
            label = "verse"    # long one-off → treat as a verse

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


def analyze_structure(audio_data: np.ndarray, sr: int, chroma: np.ndarray) -> Dict:
    """
    Analyze audio structure: beats, boundaries, and section labels.

    Args:
        audio_data: Audio signal
        sr: Sample rate
        chroma: Chroma features from spectral_analyzer

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
