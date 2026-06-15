"""Audio loader module for multi-format audio file loading and normalization."""

import librosa
import numpy as np
from pathlib import Path
from typing import Tuple


# Supported audio formats
SUPPORTED_FORMATS = {'.mp3', '.wav', '.flac', '.m4a', '.ogg'}


class AudioLoadError(Exception):
    """Exception raised for errors during audio loading."""
    pass


def load_audio(audio_path: Path, target_sr: int = 22050) -> Tuple[np.ndarray, int]:
    """
    Load audio file and normalize to target sample rate and mono.

    Args:
        audio_path: Path to audio file
        target_sr: Target sample rate (default: 22050 Hz)

    Returns:
        Tuple of (audio_data, sample_rate)
        - audio_data: 1D numpy array of audio samples
        - sample_rate: Sample rate of the audio

    Raises:
        AudioLoadError: If file cannot be loaded
    """
    # Convert to Path object if string
    audio_path = Path(audio_path)

    # Check if file exists
    if not audio_path.exists():
        raise AudioLoadError(f"File not found: {audio_path}")

    # Check if format is supported
    file_extension = audio_path.suffix.lower()
    if file_extension not in SUPPORTED_FORMATS:
        raise AudioLoadError(
            f"Unsupported format: {file_extension}. "
            f"Supported formats: {', '.join(sorted(SUPPORTED_FORMATS))}"
        )

    # Load audio file
    try:
        audio_data, sample_rate = librosa.load(audio_path, sr=target_sr, mono=True)
        return audio_data, sample_rate
    except Exception as e:
        raise AudioLoadError(f"Failed to load audio file: {e}")



def check_normalized_size(audio_data: np.ndarray, max_mb: float = 15.0) -> None:
    """
    Check if normalized audio data exceeds maximum size limit.

    Args:
        audio_data: Audio data array
        max_mb: Maximum size in megabytes (default: 15.0)

    Raises:
        ValueError: If audio data exceeds the size limit
    """
    # Calculate size in bytes (float32 = 4 bytes per sample)
    size_bytes = audio_data.nbytes
    size_mb = size_bytes / (1024 * 1024)

    if size_mb > max_mb:
        raise ValueError(
            f"Audio data exceeds {max_mb}MB limit: {size_mb:.2f}MB"
        )
