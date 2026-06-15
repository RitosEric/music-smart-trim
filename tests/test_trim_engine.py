"""Tests for trim engine module."""

import pytest
from src.trim_engine import (
    TrimStrategy,
    generate_conservative_strategy,
    generate_balanced_strategy,
    generate_aggressive_strategy,
    generate_trim_strategies
)


class TestTrimStrategy:
    """Tests for TrimStrategy dataclass."""

    def test_trim_strategy_creation(self):
        """Test creating a TrimStrategy with all fields."""
        strategy = TrimStrategy(
            name="test_strategy",
            cut_points=[(10.0, 20.0), (30.0, 40.0)],
            loop_points=[(50.0, 60.0, 2)],
            fade_regions=[(9.85, 10.15), (29.85, 30.15)],
            target_length=180.0
        )

        assert strategy.name == "test_strategy"
        assert strategy.cut_points == [(10.0, 20.0), (30.0, 40.0)]
        assert strategy.loop_points == [(50.0, 60.0, 2)]
        assert strategy.fade_regions == [(9.85, 10.15), (29.85, 30.15)]
        assert strategy.target_length == 180.0

    def test_calculate_resulting_length(self):
        """Test calculating resulting length after cuts and loops."""
        # Original length: 240s
        # Cut: (10, 20) = -10s, (30, 40) = -10s => -20s total
        # Loop: (50, 60, 2) = 10s * (2-1) = +10s
        # Result: 240 - 20 + 10 = 230s
        strategy = TrimStrategy(
            name="test",
            cut_points=[(10.0, 20.0), (30.0, 40.0)],
            loop_points=[(50.0, 60.0, 2)],
            fade_regions=[],
            target_length=180.0
        )

        original_length = 240.0
        result = strategy.calculate_resulting_length(original_length)

        assert result == 230.0


class TestConservativeStrategy:
    """Tests for conservative strategy generation."""

    def test_generate_conservative_strategy(self):
        """Test conservative strategy generation with gentle fades."""
        # Mock clusters data
        clusters = [
            {
                'segment_times': [(10.0, 20.0), (50.0, 60.0), (100.0, 110.0)],
                'avg_similarity': 0.95,
                'duration': 10.0
            },
            {
                'segment_times': [(30.0, 40.0), (80.0, 90.0)],
                'avg_similarity': 0.85,
                'duration': 10.0
            }
        ]

        original_length = 240.0
        target_length = 180.0

        strategy = generate_conservative_strategy(clusters, original_length, target_length)

        # Verify strategy properties
        assert strategy.name == "conservative"
        assert strategy.target_length == 180.0

        # Conservative removes 2nd occurrence (highest similarity first)
        assert len(strategy.cut_points) > 0

        # Gentle crossfades: 300ms = ±0.15s
        # Each cut should have corresponding fade regions
        for cut_start, cut_end in strategy.cut_points:
            # Find matching fade region (should be within ±0.15s)
            matching_fades = [
                (fade_start, fade_end)
                for fade_start, fade_end in strategy.fade_regions
                if abs(fade_start - (cut_start - 0.15)) < 0.01 and
                   abs(fade_end - (cut_start + 0.15)) < 0.01
            ]
            assert len(matching_fades) > 0, f"No fade region found for cut at {cut_start}"

        # Verify resulting length is reasonable
        result_length = strategy.calculate_resulting_length(original_length)
        # Should be closer to target with 5s buffer
        assert abs(result_length - target_length) < 70.0  # Generous margin for conservative


class TestBalancedStrategy:
    """Tests for balanced strategy generation."""

    def test_generate_balanced_strategy(self):
        """Test balanced strategy generation with standard fades."""
        # Mock clusters data
        clusters = [
            {
                'segment_times': [(10.0, 20.0), (50.0, 60.0), (100.0, 110.0)],
                'avg_similarity': 0.95,
                'duration': 10.0
            },
            {
                'segment_times': [(30.0, 40.0), (80.0, 90.0)],
                'avg_similarity': 0.85,
                'duration': 10.0
            }
        ]

        original_length = 240.0
        target_length = 180.0

        strategy = generate_balanced_strategy(clusters, original_length, target_length)

        # Verify strategy properties
        assert strategy.name == "balanced"
        assert strategy.target_length == 180.0

        # Balanced removes multiple occurrences
        assert len(strategy.cut_points) > 0

        # Standard crossfades: 150ms = ±0.075s
        # Each cut should have corresponding fade regions
        for cut_start, cut_end in strategy.cut_points:
            # Find matching fade region (should be within ±0.075s)
            matching_fades = [
                (fade_start, fade_end)
                for fade_start, fade_end in strategy.fade_regions
                if abs(fade_start - (cut_start - 0.075)) < 0.01 and
                   abs(fade_end - (cut_start + 0.075)) < 0.01
            ]
            assert len(matching_fades) > 0, f"No fade region found for cut at {cut_start}"

        # Verify resulting length is reasonable
        result_length = strategy.calculate_resulting_length(original_length)
        # Should be closer to target with 3s buffer
        assert abs(result_length - target_length) < 50.0  # Moderate margin for balanced


class TestAggressiveStrategy:
    """Tests for aggressive strategy generation."""

    def test_generate_aggressive_strategy(self):
        """Test aggressive strategy generation with short fades."""
        # Mock clusters data
        clusters = [
            {
                'segment_times': [(10.0, 20.0), (50.0, 60.0), (100.0, 110.0)],
                'avg_similarity': 0.95,
                'duration': 10.0
            },
            {
                'segment_times': [(30.0, 40.0), (80.0, 90.0)],
                'avg_similarity': 0.85,
                'duration': 10.0
            }
        ]

        original_length = 240.0
        target_length = 180.0

        strategy = generate_aggressive_strategy(clusters, original_length, target_length)

        # Verify strategy properties
        assert strategy.name == "aggressive"
        assert strategy.target_length == 180.0

        # Aggressive removes all but first occurrence - should be more cuts
        assert len(strategy.cut_points) > 0

        # Short crossfades: 75ms = ±0.0375s
        # Each cut should have corresponding fade regions
        for cut_start, cut_end in strategy.cut_points:
            # Find matching fade region (should be within ±0.0375s)
            matching_fades = [
                (fade_start, fade_end)
                for fade_start, fade_end in strategy.fade_regions
                if abs(fade_start - (cut_start - 0.0375)) < 0.01 and
                   abs(fade_end - (cut_start + 0.0375)) < 0.01
            ]
            assert len(matching_fades) > 0, f"No fade region found for cut at {cut_start}"

        # Verify resulting length is close to target
        result_length = strategy.calculate_resulting_length(original_length)
        # Should be very close to target with 1s buffer
        assert abs(result_length - target_length) <= 30.0  # Tight margin for aggressive


class TestCompleteTrimEngine:
    """Tests for complete trim engine with all strategies."""

    def test_generate_trim_strategies(self):
        """Test complete engine generates all 3 strategies within ±15s constraint."""
        # Mock clusters data
        clusters = [
            {
                'segment_times': [(10.0, 20.0), (50.0, 60.0), (100.0, 110.0)],
                'avg_similarity': 0.95,
                'duration': 10.0
            },
            {
                'segment_times': [(30.0, 40.0), (80.0, 90.0), (120.0, 130.0)],
                'avg_similarity': 0.85,
                'duration': 10.0
            },
            {
                'segment_times': [(70.0, 75.0), (140.0, 145.0)],
                'avg_similarity': 0.80,
                'duration': 5.0
            }
        ]

        original_length = 240.0
        target_length = 180.0

        strategies = generate_trim_strategies(clusters, original_length, target_length)

        # Should return 3 strategies
        assert len(strategies) == 3

        # Verify strategy names
        strategy_names = [s.name for s in strategies]
        assert "conservative" in strategy_names
        assert "balanced" in strategy_names
        assert "aggressive" in strategy_names

        # Verify all strategies are within ±15s of target
        for strategy in strategies:
            result_length = strategy.calculate_resulting_length(original_length)
            error = abs(result_length - target_length)
            assert error <= 15.0, f"{strategy.name} strategy error {error}s exceeds ±15s constraint"

        # Verify each strategy has appropriate characteristics
        conservative = next(s for s in strategies if s.name == "conservative")
        balanced = next(s for s in strategies if s.name == "balanced")
        aggressive = next(s for s in strategies if s.name == "aggressive")

        # Conservative should have fewer cuts than aggressive
        assert len(conservative.cut_points) <= len(aggressive.cut_points)

        # Fade durations should be different
        # Conservative: ±0.15s, Balanced: ±0.075s, Aggressive: ±0.0375s
        if conservative.fade_regions:
            cons_fade_width = conservative.fade_regions[0][1] - conservative.fade_regions[0][0]
            assert abs(cons_fade_width - 0.30) < 0.01  # 2 * 0.15

        if balanced.fade_regions:
            bal_fade_width = balanced.fade_regions[0][1] - balanced.fade_regions[0][0]
            assert abs(bal_fade_width - 0.15) < 0.01  # 2 * 0.075

        if aggressive.fade_regions:
            agg_fade_width = aggressive.fade_regions[0][1] - aggressive.fade_regions[0][0]
            assert abs(agg_fade_width - 0.075) < 0.01  # 2 * 0.0375

