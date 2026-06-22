"""Tests for output generator module."""

import numpy as np
import pytest
import tempfile
import json
from pathlib import Path
from src.output_generator import apply_cuts, apply_loops, apply_crossfades, render_strategy, generate_outputs
from src.trim_engine import TrimStrategy


class TestApplyCuts:
    """Test apply_cuts function."""

    def test_apply_cuts_single_cut(self):
        """Test applying a single cut to audio."""
        # Create test audio: 10 seconds at 100 Hz (1000 samples)
        sr = 100
        audio = np.arange(1000, dtype=np.float32)  # [0, 1, 2, ..., 999]

        # Cut from 2s to 5s (remove samples 200-499)
        cut_points = [(2.0, 5.0)]

        result = apply_cuts(audio, sr, cut_points)

        # Result calculation with crossfades:
        # - First segment: 0-199 (200 samples) with fade-out applied
        # - Final segment: 500-999 (500 samples) with fade-in and fade-out applied
        # - Crossfade between segments: 50 samples overlap (500ms at 100 Hz)
        # Total: 200 + 500 - 50 = 650 samples
        assert len(result) == 650

        # Verify the cut was applied (samples 200-499 removed)
        # First part should start with original values (faded)
        assert result[0] < audio[0] + 1  # May be faded but close to original start

    def test_apply_cuts_multiple_cuts(self):
        """Test applying multiple cuts to audio."""
        sr = 100
        audio = np.arange(1000, dtype=np.float32)

        # Cut from 1s to 2s and 5s to 7s
        cut_points = [(1.0, 2.0), (5.0, 7.0)]

        result = apply_cuts(audio, sr, cut_points)

        # Result calculation with crossfades:
        # - First segment: 0-99 (100 samples) with fade-out applied
        # - Second segment: 200-499 (300 samples) with fade-out applied
        # - Final segment: 700-999 (300 samples) with fade-in and fade-out applied
        # - Two crossfades: 2 × 50 samples overlap = 100 samples
        # Total: 100 + 300 + 300 - 100 = 600 samples
        assert len(result) == 600

        # Verify cuts were applied (samples 100-199 and 500-699 removed)
        # Check that result is reasonable length
        assert len(result) < len(audio)

    def test_apply_cuts_no_cuts(self):
        """Test with no cuts - should return original audio."""
        sr = 100
        audio = np.arange(1000, dtype=np.float32)

        result = apply_cuts(audio, sr, [])

        assert len(result) == 1000
        assert np.array_equal(result, audio)

    def test_apply_cuts_final_segment_has_fade_out(self):
        """Test that final segment after last cut has both fade-in and fade-out applied."""
        # Create test audio: 10 seconds at 22050 Hz (constant amplitude for easy verification)
        sr = 22050
        audio = np.ones(sr * 10, dtype=np.float32)

        # Cut from 2s to 5s (final segment is 5s-10s = 5 seconds)
        cut_points = [(2.0, 5.0)]

        result = apply_cuts(audio, sr, cut_points)

        # Result contains: [0-2s with fade-out] + crossfade + [5s-10s with fade-in]
        # The final segment starts after the first segment ends
        # First segment: 0-2s = 44100 samples minus fade-out (500ms = 11025 samples)
        # After crossfade, final segment begins

        fade_samples = int(0.5 * sr)  # 500ms crossfade = 11025 samples
        first_segment_samples = int(2.0 * sr)  # 44100 samples

        # The end of the audio should have fade-out applied
        # Check that last samples are faded out (less than 1.0)
        assert result[-1] < 0.5, "Final segment should have fade-out at end"
        assert result[-(fade_samples // 2)] < 1.0, "Fade-out should be gradual"

        # Verify the fade-out actually reduces amplitude at the end
        # Last 100 samples should be very quiet
        assert np.mean(result[-100:]) < 0.3, "End of audio should be faded out"

    def test_apply_cuts_short_final_segment_fade_out(self):
        """Test that very short final segments still get fade-out without overlap."""
        sr = 22050
        audio = np.ones(sr * 10, dtype=np.float32)

        # Cut from 2s to 9.5s (final segment is only 0.5s = 500ms)
        cut_points = [(2.0, 9.5)]

        result = apply_cuts(audio, sr, cut_points)

        # Short segment: fade-in and fade-out should not overlap
        # Both should be limited to len(segment) // 2
        expected_max_fade = len(audio[int(9.5 * sr):]) // 2

        # Check that fade-out is applied (end samples should be reduced)
        assert result[-1] < 0.5, "Short final segment should still have fade-out"

        # Check that we don't crash or produce invalid audio
        assert len(result) > 0
        assert not np.any(np.isnan(result))
        assert not np.any(np.isinf(result))


class TestApplyLoops:
    """Test apply_loops function."""

    def test_apply_loops_single_loop(self):
        """Test applying a single loop to audio."""
        # Create test audio: 10 seconds at 100 Hz (1000 samples)
        sr = 100
        audio = np.arange(1000, dtype=np.float32)

        # Loop from 2s to 4s, repeat 3 times (2s segment × 3 = 6s total)
        loop_points = [(2.0, 4.0, 3)]

        result = apply_loops(audio, sr, loop_points)

        # Result: 0-199 (200) + [200-399 × 3 with 2 crossfades] (600-100) + 400-999 (600) = 1300 samples
        # 2 crossfades × 50 samples each (500ms at 100 Hz) = 100 samples total reduction
        assert len(result) == 1300
        assert np.array_equal(result[:200], audio[:200])
        # Check the loop repeats (with crossfades applied)
        # Note: exact values after loop start are affected by crossfades

    def test_apply_loops_multiple_loops(self):
        """Test applying multiple loops to audio."""
        sr = 100
        audio = np.arange(1000, dtype=np.float32)

        # Loop 1s-2s twice, and 5s-6s twice
        loop_points = [(1.0, 2.0, 2), (5.0, 6.0, 2)]

        result = apply_loops(audio, sr, loop_points)

        # Result: 0-99 (100) + [100-199 × 2 with 1 crossfade] (200-50) + 200-499 (300)
        #         + [500-599 × 2 with 1 crossfade] (200-50) + 600-999 (400) = 1100
        # 2 crossfades × 50 samples each (500ms at 100 Hz) = 100 samples total reduction
        assert len(result) == 1100

    def test_apply_loops_no_loops(self):
        """Test with no loops - should return original audio."""
        sr = 100
        audio = np.arange(1000, dtype=np.float32)

        result = apply_loops(audio, sr, [])

        assert len(result) == 1000
        assert np.array_equal(result, audio)

    def test_apply_loops_final_segment_has_fade_out(self):
        """Test that final segment after loops has fade-out applied (outro protection)."""
        # Create test audio: 10 seconds at 100 Hz (1000 samples)
        sr = 100
        audio = np.ones(1000, dtype=np.float32)  # Constant amplitude 1.0

        # Loop from 2s to 4s, repeat 2 times
        loop_points = [(2.0, 4.0, 2)]

        result = apply_loops(audio, sr, loop_points)

        # Final segment starts at sample 400 (after loop region)
        # With 50 samples crossfade (500ms at 100Hz), fade-out should be in last ~50 samples
        # Check that last samples are faded out (< 0.5 amplitude)
        assert result[-1] < 0.5, f"Expected fade-out at end, got {result[-1]}"
        assert result[-10] < 0.9, f"Expected fade-out gradient, got {result[-10]}"

        # Check that fade-out is gradual (values decrease toward end)
        last_20 = result[-20:]
        assert last_20[0] > last_20[-1], "Expected decreasing amplitude in fade-out"

    def test_apply_loops_short_final_segment_fade_out(self):
        """Test fade-out on very short final segment after loops."""
        # Create test audio with very short final segment
        sr = 100
        audio = np.ones(1000, dtype=np.float32)

        # Loop that leaves only 50 samples (0.5s) at end
        loop_points = [(2.0, 9.5, 2)]

        result = apply_loops(audio, sr, loop_points)

        # Should not crash and should have valid audio
        assert len(result) > 0
        assert not np.any(np.isnan(result))
        assert not np.any(np.isinf(result))

        # Final segment should have fade-out (even if short)
        assert result[-1] < 0.8, "Expected some fade-out even on short segment"


class TestApplyCrossfades:
    """Test apply_crossfades function."""

    def test_apply_crossfades_single_fade(self):
        """Test applying a single crossfade to audio."""
        # Create test audio: constant value 1.0 for 1000 samples
        sr = 100
        audio = np.ones(1000, dtype=np.float32)

        # Fade from 2s to 3s (samples 200-299)
        fade_regions = [(2.0, 3.0)]

        result = apply_crossfades(audio, sr, fade_regions)

        # Check that fade region has linear fade applied
        fade_start = 200
        fade_end = 300
        fade_length = fade_end - fade_start

        # Before fade should be unchanged
        assert np.allclose(result[:fade_start], 1.0)

        # Fade region should have linear fade (0 to 1)
        expected_fade = np.linspace(0, 1, fade_length)
        assert np.allclose(result[fade_start:fade_end], expected_fade)

        # After fade should be unchanged
        assert np.allclose(result[fade_end:], 1.0)

    def test_apply_crossfades_multiple_fades(self):
        """Test applying multiple crossfades to audio."""
        sr = 100
        audio = np.ones(1000, dtype=np.float32)

        # Two fade regions
        fade_regions = [(1.0, 2.0), (5.0, 6.0)]

        result = apply_crossfades(audio, sr, fade_regions)

        # Check first fade (100-199)
        assert np.allclose(result[100:200], np.linspace(0, 1, 100))

        # Check second fade (500-599)
        assert np.allclose(result[500:600], np.linspace(0, 1, 100))

    def test_apply_crossfades_no_fades(self):
        """Test with no fades - should return original audio."""
        sr = 100
        audio = np.ones(1000, dtype=np.float32)

        result = apply_crossfades(audio, sr, [])

        assert len(result) == 1000
        assert np.array_equal(result, audio)


class TestRenderStrategy:
    """Test render_strategy function."""

    def test_render_strategy_with_loops_cuts_fades(self):
        """Test rendering a complete strategy with loops, cuts, and fades."""
        # Create test audio: 10 seconds at 100 Hz (1000 samples)
        sr = 100
        audio = np.ones(1000, dtype=np.float32)

        # Strategy: loop 1s-2s twice, cut 5s-6s, fade 7s-8s
        strategy = TrimStrategy(
            name="test",
            cut_points=[(5.0, 6.0)],
            loop_points=[(1.0, 2.0, 2)],
            fade_regions=[(7.0, 8.0)],
            target_length=90.0
        )

        result = render_strategy(strategy, audio, sr)

        # Expected length: 1000 + 100 (loop) - 50 (loop crossfade) - 100 (cut) - 50 (cut crossfade) = 900 samples
        assert len(result) == 900

        # Check that result is not all ones (fade should have modified it)
        assert not np.allclose(result, 1.0)

    def test_render_strategy_loops_only(self):
        """Test rendering a strategy with only loops."""
        sr = 100
        audio = np.arange(1000, dtype=np.float32)

        strategy = TrimStrategy(
            name="test",
            cut_points=[],
            loop_points=[(2.0, 4.0, 3)],
            fade_regions=[],
            target_length=120.0
        )

        result = render_strategy(strategy, audio, sr)

        # Expected length: 1000 + 200*2 (loop adds 2 extra repeats) - 100 (2 crossfades × 50 samples) = 1300 samples
        assert len(result) == 1300

    def test_render_strategy_cuts_only(self):
        """Test rendering a strategy with only cuts."""
        sr = 100
        audio = np.arange(1000, dtype=np.float32)

        strategy = TrimStrategy(
            name="test",
            cut_points=[(3.0, 5.0)],
            loop_points=[],
            fade_regions=[],
            target_length=80.0
        )

        result = render_strategy(strategy, audio, sr)

        # Expected length: 1000 - 200 (cut) - 50 (cut crossfade) = 750 samples
        assert len(result) == 750


class TestGenerateOutputs:
    """Test generate_outputs function."""

    def test_generate_outputs_creates_files(self):
        """Test that generate_outputs creates all expected files."""
        # Create test audio and strategies
        sr = 22050
        audio = np.random.randn(sr * 5).astype(np.float32)  # 5 seconds

        strategies = [
            TrimStrategy(name="conservative", cut_points=[(1.0, 2.0)], loop_points=[],
                        fade_regions=[(0.9, 1.1)], target_length=4.0),
            TrimStrategy(name="balanced", cut_points=[(1.0, 2.5)], loop_points=[],
                        fade_regions=[(0.9, 1.1)], target_length=3.5),
            TrimStrategy(name="aggressive", cut_points=[(1.0, 3.0)], loop_points=[],
                        fade_regions=[(0.9, 1.1)], target_length=3.0),
        ]

        scores = [
            {'star_rating': 4.5, 'total_points': 85.0, 'breakdown': {}},
            {'star_rating': 3.5, 'total_points': 75.0, 'breakdown': {}},
            {'star_rating': 3.0, 'total_points': 70.0, 'breakdown': {}},
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            input_file = "test.wav"

            generate_outputs(
                audio=audio,
                sr=sr,
                strategies=strategies,
                scores=scores,
                output_dir=output_dir,
                input_file=input_file,
                target_length=4.0,
                protected_regions=[],
                processing_time=1.5
            )

            # Check that audio files were created
            assert (output_dir / "option_0_4.5stars.wav").exists()
            assert (output_dir / "option_1_3.5stars.wav").exists()
            assert (output_dir / "option_2_3.0stars.wav").exists()

            # Check that summary.json was created
            summary_json = output_dir / "summary.json"
            assert summary_json.exists()

            # Verify summary.json content
            with open(summary_json, 'r') as f:
                summary = json.load(f)

            assert summary['input_file'] == input_file
            assert summary['target_length'] == 4.0
            assert summary['protected_regions'] == []
            assert summary['processing_time'] == 1.5
            assert len(summary['options']) == 3
            assert summary['options'][0]['star_rating'] == 4.5

            # Check that summary.txt was created
            summary_txt = output_dir / "summary.txt"
            assert summary_txt.exists()

            # Verify summary.txt contains expected content
            with open(summary_txt, 'r') as f:
                txt_content = f.read()

            assert "Music Smart Trim - Summary" in txt_content
            assert "Input file: test.wav" in txt_content
            assert "Target length: 4.0s" in txt_content
            assert "option_0_4.5stars.wav" in txt_content
            assert "★★★★" in txt_content  # 4.5 stars

    def test_generate_outputs_star_formatting(self):
        """Test that star ratings are formatted correctly in filenames."""
        sr = 22050
        audio = np.random.randn(sr * 3).astype(np.float32)

        strategies = [
            TrimStrategy(name="test", cut_points=[], loop_points=[],
                        fade_regions=[], target_length=3.0),
        ]

        scores = [
            {'star_rating': 5.0, 'total_points': 90.0, 'breakdown': {}},
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)

            generate_outputs(
                audio=audio,
                sr=sr,
                strategies=strategies,
                scores=scores,
                output_dir=output_dir,
                input_file="test.mp3",
                target_length=3.0,
                protected_regions=[],
                processing_time=1.0
            )

            # Check filename format with 5.0 stars
            assert (output_dir / "option_0_5.0stars.wav").exists()
