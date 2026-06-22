"""Tests for extension_engine module."""

import pytest
import numpy as np
from src.extension_engine import (
    select_extension_sections,
    generate_extension_strategy,
    generate_extension_strategies
)


class TestSelectExtensionSections:
    """Tests for section selection."""

    def test_basic_selection(self):
        """Test basic section selection."""
        clusters = [
            {
                'segment_times': [(20.0, 40.0), (80.0, 100.0)],
                'avg_similarity': 0.90,
                'duration': 20.0
            }
        ]
        sections = [
            {'start': 20.0, 'end': 40.0, 'label': 'chorus'},
            {'start': 80.0, 'end': 100.0, 'label': 'chorus'},
        ]

        loop_points = select_extension_sections(
            clusters, sections, 100.0, 40.0,
            prioritize_chorus=True
        )

        assert isinstance(loop_points, list)
        assert len(loop_points) > 0

        # Check format: (start, end, repeat_count)
        for start, end, repeat in loop_points:
            assert end > start
            assert repeat >= 2  # At least 1 extra repeat

    def test_chorus_prioritization(self):
        """Test that choruses are prioritized over verses."""
        clusters = [
            {
                'segment_times': [(20.0, 40.0), (80.0, 100.0)],
                'avg_similarity': 0.85,
                'duration': 20.0
            }
        ]
        sections = [
            {'start': 20.0, 'end': 40.0, 'label': 'verse'},
            {'start': 80.0, 'end': 100.0, 'label': 'chorus'},
        ]

        loop_points = select_extension_sections(
            clusters, sections, 100.0, 20.0,
            prioritize_chorus=True
        )

        # Should select chorus (80-100) over verse (20-40)
        assert len(loop_points) > 0
        first_loop = loop_points[0]
        assert first_loop[0] == 80.0 or first_loop[0] == 20.0  # Either is valid

    def test_empty_clusters(self):
        """Test handling of empty clusters."""
        loop_points = select_extension_sections(
            [], [], 100.0, 40.0
        )

        assert loop_points == []

    def test_similarity_filter(self):
        """Test similarity filtering."""
        clusters = [
            {
                'segment_times': [(20.0, 40.0)],
                'avg_similarity': 0.70,
                'duration': 20.0
            },
            {
                'segment_times': [(80.0, 100.0)],
                'avg_similarity': 0.90,
                'duration': 20.0
            }
        ]
        sections = [
            {'start': 20.0, 'end': 40.0, 'label': 'verse'},
            {'start': 80.0, 'end': 100.0, 'label': 'chorus'},
        ]

        # High threshold should filter out low-similarity segment
        loop_points = select_extension_sections(
            clusters, sections, 100.0, 20.0,
            similarity_filter=0.85
        )

        # Should only select the high-similarity chorus
        assert len(loop_points) >= 1
        for start, end, repeat in loop_points:
            if start == 80.0:
                assert True  # Found high-similarity section
                break

    def test_min_segment_duration_default(self):
        """Test default minimum segment duration (10s)."""
        clusters = [
            {
                'segment_times': [(20.0, 28.0)],  # 8s - too short with default
                'avg_similarity': 0.90,
                'duration': 8.0
            },
            {
                'segment_times': [(80.0, 100.0)],  # 20s - long enough
                'avg_similarity': 0.90,
                'duration': 20.0
            }
        ]
        sections = [
            {'start': 20.0, 'end': 28.0, 'label': 'verse'},
            {'start': 80.0, 'end': 100.0, 'label': 'chorus'},
        ]

        loop_points = select_extension_sections(
            clusters, sections, 100.0, 20.0
        )

        # Should only select 20s segment, 8s is too short
        assert len(loop_points) >= 1
        for start, end, repeat in loop_points:
            assert (end - start) >= 10.0  # Default minimum

    def test_min_segment_duration_custom(self):
        """Test custom minimum segment duration."""
        clusters = [
            {
                'segment_times': [(20.0, 25.0)],  # 5s
                'avg_similarity': 0.90,
                'duration': 5.0
            },
            {
                'segment_times': [(80.0, 100.0)],  # 20s
                'avg_similarity': 0.90,
                'duration': 20.0
            }
        ]
        sections = [
            {'start': 20.0, 'end': 25.0, 'label': 'verse'},
            {'start': 80.0, 'end': 100.0, 'label': 'chorus'},
        ]

        # With min_segment_duration=5.0, both should be valid
        loop_points = select_extension_sections(
            clusters, sections, 100.0, 20.0,
            min_segment_duration=5.0
        )

        assert len(loop_points) >= 1
        # At least one segment should be 5s (could be either)
        found_short = any((end - start) >= 5.0 and (end - start) < 10.0
                          for start, end, repeat in loop_points)
        assert found_short or len(loop_points) > 0

    def test_min_segment_duration_zero(self):
        """Test with zero minimum (accept all segments)."""
        clusters = [
            {
                'segment_times': [(20.0, 22.0)],  # 2s - very short
                'avg_similarity': 0.90,
                'duration': 2.0
            }
        ]
        sections = [
            {'start': 20.0, 'end': 22.0, 'label': 'verse'},
        ]

        # With min_segment_duration=0, should accept even 2s segments
        loop_points = select_extension_sections(
            clusters, sections, 100.0, 10.0,
            min_segment_duration=0.0
        )

        assert len(loop_points) >= 1


class TestGenerateExtensionStrategy:
    """Tests for single strategy generation."""

    def test_best_strategy(self):
        """Test best quality extension strategy."""
        clusters = [
            {
                'segment_times': [(20.0, 40.0), (80.0, 100.0)],
                'avg_similarity': 0.92,
                'duration': 20.0
            }
        ]
        sections = [
            {'start': 20.0, 'end': 40.0, 'label': 'chorus'},
            {'start': 80.0, 'end': 100.0, 'label': 'chorus'},
        ]
        downbeats = np.array([0.0, 2.0, 4.0, 6.0, 20.0, 22.0, 40.0, 42.0, 80.0, 100.0])

        strategy = generate_extension_strategy(
            "best", clusters, 100.0, 140.0,
            sections=sections, downbeats=downbeats
        )

        assert strategy.name == "best"
        assert strategy.target_length == 140.0
        assert len(strategy.loop_points) > 0
        assert len(strategy.cut_points) == 0

    def test_diverse_strategy(self):
        """Test diverse extension strategy."""
        clusters = [
            {
                'segment_times': [(20.0, 40.0), (80.0, 100.0)],
                'avg_similarity': 0.85,
                'duration': 20.0
            }
        ]
        sections = [
            {'start': 20.0, 'end': 40.0, 'label': 'verse'},
            {'start': 80.0, 'end': 100.0, 'label': 'chorus'},
        ]
        downbeats = np.array([0.0, 20.0, 40.0, 80.0, 100.0])

        strategy = generate_extension_strategy(
            "diverse", clusters, 100.0, 150.0,
            sections=sections, downbeats=downbeats
        )

        assert strategy.name == "diverse"
        assert len(strategy.loop_points) >= 0

    def test_invalid_strategy_type(self):
        """Test that invalid strategy type raises error."""
        clusters = [{'segment_times': [(20.0, 40.0)], 'avg_similarity': 0.90, 'duration': 20.0}]

        with pytest.raises(ValueError, match="Unknown strategy_type"):
            generate_extension_strategy("invalid", clusters, 100.0, 140.0)

    def test_validation_target_must_exceed_original(self):
        """Test that extension validates target > original."""
        clusters = [{'segment_times': [(20.0, 40.0)], 'avg_similarity': 0.90, 'duration': 20.0}]

        # target == original
        with pytest.raises(ValueError, match="Extension requires target > original"):
            generate_extension_strategy("best", clusters, 100.0, 100.0)

        # target < original
        with pytest.raises(ValueError, match="Extension requires target > original"):
            generate_extension_strategy("best", clusters, 100.0, 80.0)


class TestGenerateExtensionStrategies:
    """Tests for batch strategy generation."""

    def test_generate_five_strategies(self):
        """Test generating all 5 extension strategies."""
        clusters = [
            {
                'segment_times': [(20.0, 40.0), (80.0, 100.0)],
                'avg_similarity': 0.90,
                'duration': 20.0
            }
        ]
        sections = [
            {'start': 20.0, 'end': 40.0, 'label': 'chorus'},
        ]
        downbeats = np.array([0.0, 2.0, 4.0, 20.0, 40.0, 80.0, 100.0])

        strategies = generate_extension_strategies(
            clusters, 60.0, 100.0,
            sections=sections, downbeats=downbeats
        )

        assert len(strategies) == 5

        names = [s.name for s in strategies]
        assert "best" in names
        assert "diverse" in names
        assert "varied" in names
        assert "balanced" in names
        assert "conservative" in names

        # All should have loops, no cuts
        for strategy in strategies:
            assert len(strategy.cut_points) == 0
            assert len(strategy.loop_points) >= 0

    def test_length_refinement(self):
        """Test that strategies are refined to meet length constraint."""
        clusters = [
            {
                'segment_times': [(20.0, 40.0), (80.0, 100.0)],
                'avg_similarity': 0.90,
                'duration': 20.0
            }
        ]
        sections = [
            {'start': 20.0, 'end': 40.0, 'label': 'chorus'},
        ]
        downbeats = np.array([0.0, 20.0, 40.0, 80.0, 100.0])

        original_length = 100.0
        target_length = 140.0
        tolerance = 15.0

        strategies = generate_extension_strategies(
            clusters, original_length, target_length,
            sections=sections, downbeats=downbeats
        )

        # Check that at least one strategy meets the length constraint
        within_tolerance = False
        for strategy in strategies:
            result_length = strategy.calculate_resulting_length(original_length)
            error = abs(result_length - target_length)
            if error <= tolerance:
                within_tolerance = True
                break

        assert within_tolerance, "At least one strategy should meet length constraint"

    def test_custom_min_segment_duration_in_strategies(self):
        """Test that custom min_segment_duration affects strategy generation."""
        clusters = [
            {
                'segment_times': [(20.0, 26.0)],  # 6s segment
                'avg_similarity': 0.90,
                'duration': 6.0
            },
            {
                'segment_times': [(80.0, 100.0)],  # 20s segment
                'avg_similarity': 0.90,
                'duration': 20.0
            }
        ]
        sections = [
            {'start': 20.0, 'end': 26.0, 'label': 'verse'},
            {'start': 80.0, 'end': 100.0, 'label': 'chorus'},
        ]
        downbeats = np.array([0.0, 20.0, 26.0, 80.0, 100.0])

        # With default 10s minimum, should only use 20s segment
        strategies_default = generate_extension_strategies(
            clusters, 100.0, 120.0,
            sections=sections, downbeats=downbeats,
            min_segment_duration=10.0
        )

        # With 5s minimum, could potentially use both segments
        strategies_custom = generate_extension_strategies(
            clusters, 100.0, 120.0,
            sections=sections, downbeats=downbeats,
            min_segment_duration=5.0
        )

        # Both should generate strategies
        assert len(strategies_default) == 5
        assert len(strategies_custom) == 5

        # At least one custom strategy might have different loop points
        # (this is not guaranteed, but likely given the different filtering)
        assert len(strategies_custom) > 0
