"""Tests for spectral analyzer module."""

import pytest
import numpy as np

from src.spectral_analyzer import (
    extract_chroma_features,
    build_self_similarity_matrix,
    detect_repeated_segments,
    analyze_audio_structure
)


class TestExtractChromaFeatures:
    """Tests for extract_chroma_features function."""

    def test_extract_chroma_features_shape(self):
        """Test that chroma extraction returns shape (12, n_frames)."""
        # Create synthetic audio data (5 seconds at 22050 Hz)
        sample_rate = 22050
        duration = 5.0
        audio_data = np.random.randn(int(sample_rate * duration)).astype(np.float32)

        # Extract chroma features
        chroma = extract_chroma_features(audio_data, sample_rate)

        # Verify output shape
        assert chroma.shape[0] == 12  # 12 chroma bins
        assert chroma.ndim == 2  # 2D array (chroma_bins, time_frames)
        assert chroma.shape[1] > 0  # At least some frames


class TestBuildSelfSimilarityMatrix:
    """Tests for build_self_similarity_matrix function."""

    def test_build_self_similarity_matrix_properties(self):
        """Test that SSM returns symmetric square matrix with diagonal ≈1."""
        # Create synthetic chroma features (12 chroma bins, 100 frames)
        chroma = np.random.randn(12, 100).astype(np.float32)

        # Build self-similarity matrix
        ssm = build_self_similarity_matrix(chroma)

        # Verify output shape (square matrix)
        assert ssm.shape[0] == ssm.shape[1]
        assert ssm.shape[0] == chroma.shape[1]  # n_frames x n_frames

        # Verify symmetric
        assert np.allclose(ssm, ssm.T, atol=1e-6)

        # Verify diagonal is approximately 1 (each frame maximally similar to itself)
        diagonal_values = np.diag(ssm)
        assert np.allclose(diagonal_values, 1.0, atol=0.01)


class TestDetectRepeatedSegments:
    """Tests for detect_repeated_segments function."""

    def test_detect_repeated_segments_with_clear_repetition(self):
        """Test that repeated segment detection finds segments with clear repetition pattern."""
        # Create SSM with a clear repetition pattern
        # 100 frames total, with a 20-frame segment repeated at frame 0 and frame 50
        n_frames = 100
        ssm = np.random.rand(n_frames, n_frames) * 0.3  # Low background similarity

        # Add diagonal of 1s (self-similarity)
        np.fill_diagonal(ssm, 1.0)

        # Add a clear repetition: frames 0-19 are similar to frames 50-69
        for i in range(20):
            for j in range(20):
                ssm[i, 50 + j] = 0.9
                ssm[50 + j, i] = 0.9  # Ensure symmetry

        # Detect repeated segments
        # With hop_length=2048 and sr=22050, each frame is ~0.093s
        # 20 frames = ~1.86s, which is less than min_segment_duration=4.0s default
        # So use min_segment_duration=1.0s for this test
        segments = detect_repeated_segments(
            ssm,
            sample_rate=22050,
            hop_length=2048,
            min_segment_duration=1.0,
            similarity_threshold=0.8
        )

        # Verify that at least one repeated segment was detected
        assert len(segments) > 0

        # Verify segment structure
        segment = segments[0]
        assert 'start_time_1' in segment
        assert 'start_time_2' in segment
        assert 'duration' in segment
        assert 'similarity' in segment

        # Verify reasonable values
        assert segment['start_time_1'] >= 0
        assert segment['start_time_2'] > segment['start_time_1']
        assert segment['duration'] > 0
        assert 0 <= segment['similarity'] <= 1


class TestAnalyzeAudioStructure:
    """Tests for analyze_audio_structure function."""

    def test_analyze_audio_structure_returns_complete_dict(self):
        """Test that complete analysis pipeline returns dict with chroma, ssm, repeated_segments."""
        # Create synthetic audio data (5 seconds at 22050 Hz)
        sample_rate = 22050
        duration = 5.0
        audio_data = np.random.randn(int(sample_rate * duration)).astype(np.float32)

        # Run complete analysis pipeline
        result = analyze_audio_structure(audio_data, sample_rate)

        # Verify result is a dictionary
        assert isinstance(result, dict)

        # Verify all required keys are present
        assert 'chroma' in result
        assert 'ssm' in result
        assert 'repeated_segments' in result

        # Verify chroma features
        assert result['chroma'].shape[0] == 12
        assert result['chroma'].ndim == 2

        # Verify SSM
        n_frames = result['chroma'].shape[1]
        assert result['ssm'].shape == (n_frames, n_frames)

        # Verify repeated_segments is a list
        assert isinstance(result['repeated_segments'], list)
