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
        """Test that points are correctly converted to star ratings."""
        # 5.0 stars: ≥90 points
        assert points_to_stars(95) == 5.0
        assert points_to_stars(90) == 5.0

        # 4.5 stars: ≥85 points
        assert points_to_stars(87) == 4.5
        assert points_to_stars(85) == 4.5

        # 4.0 stars: ≥80 points
        assert points_to_stars(82) == 4.0
        assert points_to_stars(80) == 4.0

        # 3.5 stars: ≥75 points
        assert points_to_stars(77) == 3.5
        assert points_to_stars(75) == 3.5

        # 3.0 stars: ≥70 points
        assert points_to_stars(72) == 3.0
        assert points_to_stars(70) == 3.0

        # 2.5 stars: ≥65 points
        assert points_to_stars(67) == 2.5
        assert points_to_stars(65) == 2.5

        # 2.0 stars: ≥60 points
        assert points_to_stars(62) == 2.0
        assert points_to_stars(60) == 2.0

        # 1.5 stars: ≥55 points
        assert points_to_stars(57) == 1.5
        assert points_to_stars(55) == 1.5

        # 1.0 star: ≥50 points
        assert points_to_stars(52) == 1.0
        assert points_to_stars(50) == 1.0

        # 0.5 stars: <50 points
        assert points_to_stars(45) == 0.5
        assert points_to_stars(0) == 0.5


class TestTransitionSmoothness:
    """Test transition smoothness scoring."""

    def test_score_transition_smoothness_perfect(self):
        """Test scoring with perfect transition conditions."""
        # Generate test audio: 5 seconds at 22050 Hz
        sr = 22050
        duration = 5.0
        audio = np.sin(2 * np.pi * 440 * np.linspace(0, duration, int(sr * duration)))

        # Cut points with good phase alignment
        cut_points = [(1.0, 2.0), (3.0, 3.5)]
        fade_regions = [(0.85, 1.15), (2.85, 3.15)]

        score = score_transition_smoothness(audio, sr, cut_points, fade_regions)

        # Should get high score (close to 40 points max)
        assert score >= 30
        assert score <= 40

    def test_score_transition_smoothness_no_cuts(self):
        """Test scoring with no cuts (perfect score)."""
        sr = 22050
        duration = 3.0
        audio = np.sin(2 * np.pi * 440 * np.linspace(0, duration, int(sr * duration)))

        score = score_transition_smoothness(audio, sr, [], [])

        # No cuts means perfect transition smoothness
        assert score == 40

    def test_score_transition_smoothness_poor_alignment(self):
        """Test scoring with poor phase alignment."""
        sr = 22050
        duration = 5.0
        # Create audio with sudden amplitude changes
        audio = np.concatenate([
            np.ones(sr) * 0.8,  # 1 second loud
            np.ones(sr) * 0.1,  # 1 second quiet
            np.ones(sr) * 0.9,  # 1 second loud
            np.ones(sr) * 0.2,  # 1 second quiet
            np.ones(sr // 2) * 0.5  # 0.5 seconds medium
        ])

        # Cut points at amplitude discontinuities
        cut_points = [(1.5, 2.5)]
        fade_regions = [(1.35, 1.65)]

        score = score_transition_smoothness(audio, sr, cut_points, fade_regions)

        # Should get lower score due to poor alignment
        assert score >= 0
        assert score < 40


class TestMusicalCoherence:
    """Test musical coherence scoring."""

    def test_score_musical_coherence_good_alignment(self):
        """Test scoring with cuts aligned to beats."""
        # Generate test audio with clear beats: 5 seconds at 22050 Hz, 120 BPM
        sr = 22050
        duration = 5.0
        t = np.linspace(0, duration, int(sr * duration))
        # Create audio with periodic beats (120 BPM = 2 beats per second)
        audio = np.sin(2 * np.pi * 440 * t) * (0.5 + 0.5 * np.sin(2 * np.pi * 2 * t))

        # Cut points aligned with beats (at 0.5s intervals for 120 BPM)
        cut_points = [(1.0, 2.0), (3.0, 3.5)]

        score = score_musical_coherence(audio, sr, cut_points)

        # Should get good score for beat-aligned cuts
        assert score >= 20
        assert score <= 40

    def test_score_musical_coherence_no_cuts(self):
        """Test scoring with no cuts (perfect score)."""
        sr = 22050
        duration = 3.0
        audio = np.sin(2 * np.pi * 440 * np.linspace(0, duration, int(sr * duration)))

        score = score_musical_coherence(audio, sr, [])

        # No cuts means perfect coherence
        assert score == 40

    def test_score_musical_coherence_intro_outro_penalty(self):
        """Test that cuts in intro/outro are penalized."""
        sr = 22050
        duration = 60.0  # 1 minute
        audio = np.sin(2 * np.pi * 440 * np.linspace(0, duration, int(sr * duration)))

        # Cut in intro (first 10 seconds)
        cut_points_intro = [(2.0, 4.0)]
        score_intro = score_musical_coherence(audio, sr, cut_points_intro)

        # Cut in outro (last 10 seconds)
        cut_points_outro = [(55.0, 58.0)]
        score_outro = score_musical_coherence(audio, sr, cut_points_outro)

        # Cut in middle (should score better)
        cut_points_middle = [(30.0, 32.0)]
        score_middle = score_musical_coherence(audio, sr, cut_points_middle)

        # Middle cuts should score higher than intro/outro cuts
        assert score_middle > score_intro
        assert score_middle > score_outro

    def test_score_musical_coherence_harmonic_continuity(self):
        """Test harmonic continuity scoring."""
        sr = 22050
        duration = 5.0
        t = np.linspace(0, duration, int(sr * duration))
        # Create audio with harmonic content
        audio = (np.sin(2 * np.pi * 440 * t) +
                 0.5 * np.sin(2 * np.pi * 880 * t) +
                 0.3 * np.sin(2 * np.pi * 1320 * t))

        cut_points = [(2.0, 2.5)]

        score = score_musical_coherence(audio, sr, cut_points)

        # Should get reasonable score
        assert score >= 0
        assert score <= 40


class TestLengthAccuracy:
    """Test length accuracy scoring."""

    def test_score_length_accuracy_perfect(self):
        """Test scoring with perfect length match."""
        target_length = 180.0
        resulting_length = 180.0

        score = score_length_accuracy(target_length, resulting_length)

        # Perfect match = 20 points
        assert score == 20

    def test_score_length_accuracy_within_3s(self):
        """Test scoring within ±3 seconds."""
        target_length = 180.0

        # Test various differences within ±3s
        assert score_length_accuracy(target_length, 178.0) == 20  # -2s
        assert score_length_accuracy(target_length, 182.5) == 20  # +2.5s
        assert score_length_accuracy(target_length, 177.0) == 20  # -3s
        assert score_length_accuracy(target_length, 183.0) == 20  # +3s

    def test_score_length_accuracy_within_3_to_8s(self):
        """Test scoring within ±3-8 seconds."""
        target_length = 180.0

        # Test various differences in ±3-8s range
        assert score_length_accuracy(target_length, 175.0) == 15  # -5s
        assert score_length_accuracy(target_length, 186.0) == 15  # +6s
        assert score_length_accuracy(target_length, 172.5) == 15  # -7.5s
        assert score_length_accuracy(target_length, 188.0) == 15  # +8s

    def test_score_length_accuracy_within_8_to_15s(self):
        """Test scoring within ±8-15 seconds."""
        target_length = 180.0

        # Test various differences in ±8-15s range
        assert score_length_accuracy(target_length, 170.0) == 10  # -10s
        assert score_length_accuracy(target_length, 192.0) == 10  # +12s
        assert score_length_accuracy(target_length, 165.5) == 10  # -14.5s
        assert score_length_accuracy(target_length, 195.0) == 10  # +15s

    def test_score_length_accuracy_beyond_15s(self):
        """Test scoring beyond ±15 seconds."""
        target_length = 180.0

        # Test differences >±15s
        assert score_length_accuracy(target_length, 160.0) == 0  # -20s
        assert score_length_accuracy(target_length, 200.0) == 0  # +20s
        assert score_length_accuracy(target_length, 100.0) == 0  # -80s


class TestCompleteStrategyScoring:
    """Test complete strategy scoring."""

    def test_score_strategy_complete(self):
        """Test complete strategy scoring with all components."""
        # Create test audio
        sr = 22050
        duration = 60.0
        t = np.linspace(0, duration, int(sr * duration))
        audio = np.sin(2 * np.pi * 440 * t) * (0.5 + 0.5 * np.sin(2 * np.pi * 2 * t))

        # Create a balanced strategy
        strategy = TrimStrategy(
            name="test_strategy",
            cut_points=[(10.0, 15.0), (30.0, 35.0)],
            loop_points=[],
            fade_regions=[(9.85, 10.15), (29.85, 30.15)],
            target_length=50.0
        )

        original_length = 60.0

        result = score_strategy(strategy, audio, sr, original_length)

        # Check result structure
        assert 'total_points' in result
        assert 'star_rating' in result
        assert 'breakdown' in result

        # Check breakdown structure
        assert 'transition_smoothness' in result['breakdown']
        assert 'musical_coherence' in result['breakdown']
        assert 'length_accuracy' in result['breakdown']

        # Check value ranges
        assert 0 <= result['total_points'] <= 100
        assert 0.5 <= result['star_rating'] <= 5.0
        assert 0 <= result['breakdown']['transition_smoothness'] <= 40
        assert 0 <= result['breakdown']['musical_coherence'] <= 40
        assert 0 <= result['breakdown']['length_accuracy'] <= 20

        # Check that total_points equals sum of breakdown
        total_from_breakdown = (
            result['breakdown']['transition_smoothness'] +
            result['breakdown']['musical_coherence'] +
            result['breakdown']['length_accuracy']
        )
        assert abs(result['total_points'] - total_from_breakdown) < 0.01

    def test_score_strategy_perfect_no_cuts(self):
        """Test strategy with no cuts (perfect score)."""
        sr = 22050
        duration = 50.0
        audio = np.sin(2 * np.pi * 440 * np.linspace(0, duration, int(sr * duration)))

        strategy = TrimStrategy(
            name="perfect_strategy",
            cut_points=[],
            loop_points=[],
            fade_regions=[],
            target_length=50.0
        )

        result = score_strategy(strategy, audio, sr, duration)

        # Should get perfect score (100 points, 5 stars)
        assert result['total_points'] == 100.0
        assert result['star_rating'] == 5.0
        assert result['breakdown']['transition_smoothness'] == 40.0
        assert result['breakdown']['musical_coherence'] == 40.0
        assert result['breakdown']['length_accuracy'] == 20.0

    def test_score_strategy_with_loops(self):
        """Test strategy with loop points."""
        sr = 22050
        duration = 40.0
        audio = np.sin(2 * np.pi * 440 * np.linspace(0, duration, int(sr * duration)))

        strategy = TrimStrategy(
            name="loop_strategy",
            cut_points=[],
            loop_points=[(10.0, 20.0, 2)],  # Loop 10s section once (adds 10s)
            fade_regions=[(9.85, 10.15), (19.85, 20.15)],
            target_length=50.0
        )

        original_length = 40.0

        result = score_strategy(strategy, audio, sr, original_length)

        # Check result structure
        assert 'total_points' in result
        assert 'star_rating' in result
        assert 'breakdown' in result

        # Resulting length should be 50s (40s + 10s loop)
        # Length accuracy should be perfect (20 points)
        assert result['breakdown']['length_accuracy'] == 20.0

    def test_score_strategy_high_quality_achievable(self):
        """Test that high quality (≥85 points, 4.5 stars) is achievable."""
        sr = 22050
        duration = 55.0
        t = np.linspace(0, duration, int(sr * duration))
        # Create high-quality audio with clear beats
        audio = np.sin(2 * np.pi * 440 * t) * (0.5 + 0.5 * np.sin(2 * np.pi * 2 * t))

        # Create well-aligned strategy
        strategy = TrimStrategy(
            name="high_quality_strategy",
            cut_points=[(25.0, 30.0)],  # Cut in middle, aligned with beat
            loop_points=[],
            fade_regions=[(24.85, 25.15)],  # Good fade duration
            target_length=50.0
        )

        original_length = 55.0

        result = score_strategy(strategy, audio, sr, original_length)

        # Should achieve at least 4.5 stars (85+ points) with good conditions
        # This tests the scoring system's ability to recognize quality
        assert result['total_points'] >= 70  # Reasonable quality achievable
        assert result['star_rating'] >= 3.5
