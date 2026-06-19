"""Spectral analyzer module for extracting melodic features and detecting repeated segments."""

import librosa
import numpy as np
from scipy.spatial.distance import cosine
from typing import Tuple, List, Dict


def extract_chroma_features(
    audio_data: np.ndarray,
    sample_rate: int,
    hop_length: int = 2048,
    n_chroma: int = 12
) -> np.ndarray:
    """
    Extract chroma features from audio using Constant-Q Transform.

    Args:
        audio_data: 1D numpy array of audio samples
        sample_rate: Sample rate of the audio
        hop_length: Number of samples between successive frames (default: 2048)
        n_chroma: Number of chroma bins (default: 12)

    Returns:
        2D numpy array of shape (n_chroma, n_frames) containing chroma features
    """
    chroma = librosa.feature.chroma_cqt(
        y=audio_data,
        sr=sample_rate,
        hop_length=hop_length,
        n_chroma=n_chroma
    )
    return chroma


def build_self_similarity_matrix(chroma: np.ndarray) -> np.ndarray:
    """
    Build self-similarity matrix using cosine similarity between chroma vectors.

    Args:
        chroma: 2D numpy array of shape (n_chroma, n_frames)

    Returns:
        2D numpy array of shape (n_frames, n_frames) containing similarity values
        Values range from 0 (dissimilar) to 1 (identical)
    """
    n_frames = chroma.shape[1]
    ssm = np.zeros((n_frames, n_frames))

    # Compute pairwise cosine similarity
    for i in range(n_frames):
        for j in range(n_frames):
            # Cosine similarity = 1 - cosine distance
            ssm[i, j] = 1 - cosine(chroma[:, i], chroma[:, j])

    return ssm


def detect_repeated_segments(
    ssm: np.ndarray,
    sample_rate: int = 22050,
    hop_length: int = 2048,
    min_segment_duration: float = 15.0,
    max_segment_duration: float = 60.0,
    similarity_threshold: float = 0.75
) -> List[Dict]:
    """
    Detect repeated segments by scanning SSM for diagonal lines.

    Args:
        ssm: Self-similarity matrix (n_frames x n_frames)
        sample_rate: Sample rate of the audio (default: 22050)
        hop_length: Hop length used for chroma extraction (default: 2048)
        min_segment_duration: Minimum segment duration in seconds (default: 15.0, raised for musical coherence)
        max_segment_duration: Maximum segment duration in seconds (default: 60.0, to filter false positives)
        similarity_threshold: Minimum similarity for a match (default: 0.75, raised for quality)

    Returns:
        List of dicts with keys: start_time_1, start_time_2, duration, similarity
    """
    n_frames = ssm.shape[0]
    frame_duration = hop_length / sample_rate
    min_frames = int(min_segment_duration / frame_duration)
    max_frames = int(max_segment_duration / frame_duration)

    repeated_segments = []

    # Scan upper triangle of SSM (exclude main diagonal)
    for i in range(n_frames):
        for j in range(i + 1, n_frames):
            # Check if this point has high similarity
            if ssm[i, j] >= similarity_threshold:
                # Follow the diagonal to see how long the repetition lasts
                diagonal_length = 0
                total_similarity = 0.0

                # Follow diagonal while similarity remains high
                k = 0
                while (i + k < n_frames and j + k < n_frames and
                       ssm[i + k, j + k] >= similarity_threshold and
                       k < max_frames):  # Stop if exceeds max duration
                    total_similarity += ssm[i + k, j + k]
                    diagonal_length += 1
                    k += 1

                # Check if diagonal is long enough but not too long
                if min_frames <= diagonal_length <= max_frames:
                    # Calculate average similarity along diagonal
                    avg_similarity = total_similarity / diagonal_length

                    # Convert frame indices to time
                    start_time_1 = i * frame_duration
                    start_time_2 = j * frame_duration
                    duration = diagonal_length * frame_duration

                    segment = {
                        'start_time_1': start_time_1,
                        'start_time_2': start_time_2,
                        'duration': duration,
                        'similarity': avg_similarity
                    }

                    repeated_segments.append(segment)

    return repeated_segments


def analyze_audio_structure(
    audio_data: np.ndarray,
    sample_rate: int,
    hop_length: int = 2048,
    n_chroma: int = 12,
    min_segment_duration: float = 15.0,
    max_segment_duration: float = 60.0,
    similarity_threshold: float = 0.75
) -> Dict:
    """
    Complete analysis pipeline that extracts chroma, builds SSM, and detects repetitions.

    Args:
        audio_data: 1D numpy array of audio samples
        sample_rate: Sample rate of the audio
        hop_length: Number of samples between successive frames (default: 2048)
        n_chroma: Number of chroma bins (default: 12)
        min_segment_duration: Minimum segment duration in seconds (default: 15.0, raised for musical coherence)
        max_segment_duration: Maximum segment duration in seconds (default: 60.0, to filter false positives)
        similarity_threshold: Minimum similarity for a match (default: 0.75, raised for quality)

    Returns:
        Dict with keys:
            - chroma: 2D array of chroma features
            - ssm: 2D array of self-similarity matrix
            - repeated_segments: List of repeated segment dicts
    """
    # Extract chroma features
    chroma = extract_chroma_features(audio_data, sample_rate, hop_length, n_chroma)

    # Build self-similarity matrix
    ssm = build_self_similarity_matrix(chroma)

    # Detect repeated segments with higher threshold for musical coherence
    repeated_segments = detect_repeated_segments(
        ssm,
        sample_rate,
        hop_length,
        min_segment_duration,
        max_segment_duration,
        similarity_threshold
    )

    return {
        'chroma': chroma,
        'ssm': ssm,
        'repeated_segments': repeated_segments
    }
