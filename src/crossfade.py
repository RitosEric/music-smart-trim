"""Advanced crossfading module for seamless audio transitions."""

import numpy as np
import librosa


def constant_power_crossfade(
    audio1: np.ndarray,
    audio2: np.ndarray,
    fade_duration_samples: int
) -> np.ndarray:
    """
    Apply constant-power crossfade between two audio segments.
    Maintains perceived loudness during transition (gold standard for DJ transitions).

    Args:
        audio1: First audio segment
        audio2: Second audio segment
        fade_duration_samples: Crossfade duration in samples

    Returns:
        Crossfaded audio
    """
    fade_len = min(fade_duration_samples, len(audio1), len(audio2))

    if fade_len == 0:
        return np.concatenate([audio1, audio2])

    # Constant-power fade curves using cosine (equal power law)
    # fade_out^2 + fade_in^2 = 1 (maintains constant power)
    fade_out = np.cos(np.linspace(0, np.pi / 2, fade_len))
    fade_in = np.sin(np.linspace(0, np.pi / 2, fade_len))

    # Apply fades
    audio1_end = audio1[-fade_len:].copy() * fade_out
    audio2_start = audio2[:fade_len].copy() * fade_in

    # Crossfaded region
    crossfaded = audio1_end + audio2_start

    # Concatenate
    result = np.concatenate([
        audio1[:-fade_len],
        crossfaded,
        audio2[fade_len:]
    ])

    return result


def beat_sync_crossfade(
    audio1: np.ndarray,
    audio2: np.ndarray,
    sr: int,
    fade_beats: int = 2
) -> np.ndarray:
    """
    Crossfade synchronized to beat grid for DJ-style seamless transitions.

    Args:
        audio1: First audio segment
        audio2: Second audio segment
        sr: Sample rate
        fade_beats: Number of beats to fade over (default: 2)

    Returns:
        Beat-synced crossfaded audio
    """
    # Detect tempo of first segment
    try:
        tempo, _ = librosa.beat.beat_track(y=audio1, sr=sr)
        if tempo == 0:
            tempo = 120  # Default fallback
    except Exception:
        tempo = 120  # Default fallback

    # Calculate fade duration based on tempo
    beat_duration = 60.0 / tempo
    fade_duration = fade_beats * beat_duration
    fade_samples = int(fade_duration * sr)

    # Apply constant-power crossfade
    return constant_power_crossfade(audio1, audio2, fade_samples)


def apply_smooth_fade_in(audio: np.ndarray, fade_duration_samples: int) -> np.ndarray:
    """
    Apply smooth fade-in to audio segment using raised cosine (Hann window).

    Args:
        audio: Audio signal
        fade_duration_samples: Fade duration in samples

    Returns:
        Audio with fade-in applied
    """
    if fade_duration_samples >= len(audio):
        fade_duration_samples = len(audio) - 1

    if fade_duration_samples <= 0:
        return audio

    result = audio.copy()
    fade_curve = np.sin(np.linspace(0, np.pi / 2, fade_duration_samples)) ** 2
    result[:fade_duration_samples] *= fade_curve

    return result


def apply_smooth_fade_out(audio: np.ndarray, fade_duration_samples: int) -> np.ndarray:
    """
    Apply smooth fade-out to audio segment using raised cosine (Hann window).

    Args:
        audio: Audio signal
        fade_duration_samples: Fade duration in samples

    Returns:
        Audio with fade-out applied
    """
    if fade_duration_samples >= len(audio):
        fade_duration_samples = len(audio) - 1

    if fade_duration_samples <= 0:
        return audio

    result = audio.copy()
    fade_curve = np.cos(np.linspace(0, np.pi / 2, fade_duration_samples)) ** 2
    result[-fade_duration_samples:] *= fade_curve

    return result
