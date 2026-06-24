"""Spectral feature extraction.

The new section-enumeration engine works from beat/section structure, not from
self-similarity clustering, so the old O(n^2) SSM builder and diagonal
repeated-segment detector have been removed — they were computed on every run
and their output is no longer consumed. Chroma extraction is all that remains;
`structure_analyzer` uses it for boundary detection and chorus identification.
"""
import librosa
import numpy as np


def extract_chroma_features(
    audio_data: np.ndarray,
    sample_rate: int,
    hop_length: int = 2048,
    n_chroma: int = 12,
) -> np.ndarray:
    """
    Extract chroma features from audio using the Constant-Q Transform.

    Args:
        audio_data: 1D numpy array of audio samples
        sample_rate: Sample rate of the audio
        hop_length: Samples between successive frames (default: 2048)
        n_chroma: Number of chroma bins (default: 12)

    Returns:
        2D numpy array of shape (n_chroma, n_frames) of chroma features.
    """
    return librosa.feature.chroma_cqt(
        y=audio_data,
        sr=sample_rate,
        hop_length=hop_length,
        n_chroma=n_chroma,
    )
