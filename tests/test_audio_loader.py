"""Tests for audio loader module."""

import pytest
import numpy as np
from pathlib import Path

from src.audio_loader import load_audio, check_normalized_size, AudioLoadError


class TestLoadAudio:
    """Tests for load_audio function."""

    def test_load_audio_basic(self):
        """Test basic audio loading with WAV file."""
        # This will use a fixture we create later
        audio_path = Path(__file__).parent / "fixtures" / "sample_30s.wav"

        audio_data, sample_rate = load_audio(audio_path)

        # Verify output type and shape
        assert isinstance(audio_data, np.ndarray)
        assert audio_data.ndim == 1  # mono audio
        assert sample_rate == 22050

        # Verify duration (30 seconds at 22050 Hz)
        expected_samples = 30 * 22050
        assert len(audio_data) == expected_samples


class TestCheckNormalizedSize:
    """Tests for check_normalized_size function."""

    def test_check_normalized_size_within_limit(self):
        """Test that audio within 15MB limit passes validation."""
        # Create audio data that's under 15MB
        # 15MB / 4 bytes per sample = 3,932,160 samples
        # Use 3 million samples to be safely under
        audio_data = np.random.randn(3_000_000).astype(np.float32)

        # Should not raise exception
        check_normalized_size(audio_data)

    def test_check_normalized_size_exceeds_limit(self):
        """Test that audio exceeding 15MB limit raises ValueError."""
        # Create audio data that exceeds 15MB
        # 15MB / 4 bytes per sample = 3,932,160 samples
        # Use 4 million samples to exceed limit
        audio_data = np.random.randn(4_000_000).astype(np.float32)

        # Should raise ValueError
        with pytest.raises(ValueError, match="exceeds 15.0MB"):
            check_normalized_size(audio_data)


class TestAudioLoadError:
    """Tests for AudioLoadError exception handling."""

    def test_load_audio_file_not_found(self):
        """Test that missing file raises AudioLoadError."""
        audio_path = Path("/nonexistent/path/to/audio.wav")

        with pytest.raises(AudioLoadError, match="File not found"):
            load_audio(audio_path)

    def test_load_audio_unsupported_format(self):
        """Test that unsupported format raises AudioLoadError."""
        # Create a temporary text file with unsupported extension
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
            tmp.write(b"not an audio file")
            tmp_path = Path(tmp.name)

        try:
            with pytest.raises(AudioLoadError, match="Unsupported format"):
                load_audio(tmp_path)
        finally:
            tmp_path.unlink()

