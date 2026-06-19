"""Tests for quality scorer module."""

import pytest
import numpy as np
from src.quality_scorer import (
    points_to_stars,
    score_transition_smoothness,
    score_musical_coherence,
    score_length_accuracy,
    score_strategy
)
from src.trim_engine import TrimStrategy


class TestStarConversion:
    """Test points to stars conversion."""

    def test_points_to_stars_conversion(self):
        """Test that points are correctly converted to star ratings (V5 linear mapping)."""
        # Linear mapping: 100 points = 5.0 stars, 20 points = 1 star
        assert points_to_stars(100) == 5.0  # Perfect
        assert points_to_stars(90) == 4.5   # Excellent
        assert points_to_stars(80) == 4.0   # Very good
        assert points_to_stars(70) == 3.5   # Good
        assert points_to_stars(60) == 3.0   # Acceptable
        assert points_to_stars(50) == 2.5   # Fair
        assert points_to_stars(40) == 2.0   # Poor
        assert points_to_stars(20) == 1.0   # Very poor
        assert points_to_stars(0) == 0.0    # Failed

        # Test rounding to 0.1 increments
        assert points_to_stars(76.3) == 3.8  # 76.3 * 5 / 100 = 3.815 → 3.8
        assert points_to_stars(68.4) == 3.4  # 68.4 * 5 / 100 = 3.42 → 3.4

        # Test edge cases
        assert points_to_stars(95) == 4.8   # 95 * 5 / 100 = 4.75 → 4.8
        assert points_to_stars(110) == 5.0  # Clamped to max
        assert points_to_stars(-10) == 0.0  # Clamped to min

    def test_points_to_stars_range(self):
        """Test that star ratings stay within valid range."""
        assert 0.0 <= points_to_stars(0) <= 5.0
        assert 0.0 <= points_to_stars(50) <= 5.0
        assert 0.0 <= points_to_stars(100) <= 5.0
        assert 0.0 <= points_to_stars(200) <= 5.0  # Over-maximum
        assert 0.0 <= points_to_stars(-50) <= 5.0  # Negative


class TestLengthAccuracy:
    """Test length accuracy scoring."""

    def test_perfect_length(self):
        """Test scoring for perfect length match."""
        score = score_length_accuracy(120.0, 120.0)
        assert score == 20.0

    def test_small_error(self):
        """Test scoring for small length error."""
        score = score_length_accuracy(120.0, 123.0)  # 3s error
        assert score == 20.0

    def test_medium_error(self):
        """Test scoring for medium length error."""
        score = score_length_accuracy(120.0, 130.0)  # 10s error
        assert 5.0 <= score <= 15.0

    def test_large_error(self):
        """Test scoring for large length error."""
        score = score_length_accuracy(120.0, 145.0)  # 25s error
        assert 0.0 <= score <= 5.0

    def test_excessive_error(self):
        """Test scoring for excessive length error."""
        score = score_length_accuracy(120.0, 160.0)  # 40s error
        assert score == 0.0


class TestTransitionSmoothness:
    """Test transition smoothness scoring."""

    def test_no_cuts(self):
        """Test scoring with no cuts."""
        audio = np.random.randn(22050 * 10)  # 10 seconds
        score = score_transition_smoothness(audio, 22050, [], [])
        assert score > 0.0

    def test_single_cut(self):
        """Test scoring with a single cut."""
        audio = np.random.randn(22050 * 10)
        cut_points = [(3.0, 5.0)]
        fade_regions = [(3.0, 3.5)]
        score = score_transition_smoothness(audio, 22050, cut_points, fade_regions)
        assert 0.0 <= score <= 40.0


class TestMusicalCoherence:
    """Test musical coherence scoring."""

    def test_no_cuts(self):
        """Test scoring with no cuts (perfect coherence)."""
        audio = np.random.randn(22050 * 10)
        score = score_musical_coherence(audio, 22050, [], 10.0)
        assert score == 50.0

    def test_with_cuts(self):
        """Test scoring with cuts."""
        audio = np.random.randn(22050 * 10)
        cut_points = [(3.0, 5.0), (7.0, 8.0)]
        score = score_musical_coherence(audio, 22050, cut_points, 10.0)
        assert 0.0 <= score <= 50.0


class TestCompleteStrategy:
    """Test complete strategy scoring."""

    def test_strategy_scoring(self):
        """Test scoring a complete strategy."""
        # Create a simple strategy
        strategy = TrimStrategy(
            name="test",
            cut_points=[(30.0, 60.0)],
            loop_points=[],
            fade_regions=[(30.0, 30.5)],
            target_length=120.0
        )

        # Create test audio (3 minutes)
        audio = np.random.randn(22050 * 180)
        sr = 22050

        # Score the strategy
        score = score_strategy(strategy, audio, sr, 180.0)

        # Verify structure
        assert 'total_points' in score
        assert 'star_rating' in score
        assert 'breakdown' in score
        assert 'resulting_length' in score

        # Verify ranges
        assert 0.0 <= score['total_points'] <= 100.0
        assert 0.0 <= score['star_rating'] <= 5.0
        assert 0.0 <= score['breakdown']['musical_coherence'] <= 50.0
        assert 0.0 <= score['breakdown']['transition_smoothness'] <= 30.0
        assert 0.0 <= score['breakdown']['length_accuracy'] <= 20.0
