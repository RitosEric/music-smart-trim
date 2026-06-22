"""Tests for trim engine module."""

import pytest
from src.trim_engine import (
    TrimStrategy,
    generate_strategy,
    generate_trim_strategies,
    generate_strategies
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


class TestBestStrategy:
    """Tests for best strategy generation."""

    def test_generate_best_strategy(self):
        """Test best strategy generation with high-quality cuts."""
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

        strategy = generate_strategy("best", clusters, original_length, target_length)

        # Verify strategy properties
        assert strategy.name == "best"
        assert strategy.target_length == 180.0

        # Should have some cuts
        assert len(strategy.cut_points) > 0

        # Should have fade regions matching cuts
        assert len(strategy.fade_regions) == len(strategy.cut_points)

        # Verify resulting length is reasonable (with buffer)
        result_length = strategy.calculate_resulting_length(original_length)
        assert result_length >= target_length  # Best strategy has +3s buffer


class TestBalancedStrategy:
    """Tests for balanced strategy generation."""

    def test_generate_balanced_strategy(self):
        """Test balanced strategy generation."""
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

        strategy = generate_strategy("balanced", clusters, original_length, target_length)

        # Verify strategy properties
        assert strategy.name == "balanced"
        assert strategy.target_length == 180.0

        # Should have some cuts
        assert len(strategy.cut_points) > 0

        # Should have fade regions matching cuts
        assert len(strategy.fade_regions) == len(strategy.cut_points)

        # Verify resulting length is reasonable
        result_length = strategy.calculate_resulting_length(original_length)
        assert abs(result_length - target_length) < 70.0


class TestVariedStrategy:
    """Tests for varied strategy generation."""

    def test_generate_varied_strategy(self):
        """Test varied strategy generation with alternative patterns."""
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

        strategy = generate_strategy("varied", clusters, original_length, target_length)

        # Verify strategy properties
        assert strategy.name == "varied"
        assert strategy.target_length == 180.0

        # Should have some cuts
        assert len(strategy.cut_points) > 0

        # Should have fade regions matching cuts
        assert len(strategy.fade_regions) == len(strategy.cut_points)

        # Verify resulting length is close to target (small buffer)
        result_length = strategy.calculate_resulting_length(original_length)
        assert abs(result_length - target_length) < 70.0


class TestCompleteTrimEngine:
    """Tests for complete trim engine with all strategies."""

    def test_generate_trim_strategies(self):
        """Test complete engine generates 5 diverse strategies within ±15s constraint."""
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

        # Should return 5 strategies (new in V8)
        assert len(strategies) == 5

        # Verify strategy names
        strategy_names = [s.name for s in strategies]
        assert "best" in strategy_names
        assert "diverse" in strategy_names
        assert "varied" in strategy_names
        assert "balanced" in strategy_names
        assert "conservative" in strategy_names

        # Verify all strategies are within ±15s of target
        for strategy in strategies:
            result_length = strategy.calculate_resulting_length(original_length)
            error = abs(result_length - target_length)
            assert error <= 15.0, f"{strategy.name} strategy error {error}s exceeds ±15s constraint"

        # Verify each strategy has appropriate characteristics
        best = next(s for s in strategies if s.name == "best")
        conservative = next(s for s in strategies if s.name == "conservative")
        varied = next(s for s in strategies if s.name == "varied")

        # All strategies should have cuts
        assert len(best.cut_points) > 0
        assert len(conservative.cut_points) > 0
        assert len(varied.cut_points) > 0

        # All strategies should have matching fade regions
        assert len(best.fade_regions) == len(best.cut_points)
        assert len(conservative.fade_regions) == len(conservative.cut_points)
        assert len(varied.fade_regions) == len(varied.cut_points)


class TestGenerateStrategies:
    """Tests for unified generate_strategies() interface."""

    def test_trim_mode_generates_strategies_with_cuts(self):
        """Test trim mode generates 5 strategies with cuts and no loops."""
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
            }
        ]

        original_length = 240.0
        target_length = 180.0

        strategies = generate_strategies(
            mode="trim",
            clusters=clusters,
            original_length=original_length,
            target_length=target_length
        )

        # Should return 5 strategies
        assert len(strategies) == 5

        # All strategies should have cuts
        for strategy in strategies:
            assert len(strategy.cut_points) > 0, f"{strategy.name} has no cuts"

        # No strategy should have loops (trim mode)
        for strategy in strategies:
            assert len(strategy.loop_points) == 0, f"{strategy.name} has loops in trim mode"

        # All strategies should be within ±15s of target
        for strategy in strategies:
            result_length = strategy.calculate_resulting_length(original_length)
            error = abs(result_length - target_length)
            assert error <= 15.0, f"{strategy.name} error {error}s exceeds ±15s"

    def test_extend_mode_generates_strategies_with_loops(self):
        """Test extend mode generates 5 strategies with loops and no cuts."""
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

        original_length = 180.0
        target_length = 240.0  # Extend by 60s

        strategies = generate_strategies(
            mode="extend",
            clusters=clusters,
            original_length=original_length,
            target_length=target_length
        )

        # Should return 5 strategies
        assert len(strategies) == 5

        # All strategies should have loops
        for strategy in strategies:
            assert len(strategy.loop_points) > 0, f"{strategy.name} has no loops"

        # No strategy should have cuts (extend mode)
        for strategy in strategies:
            assert len(strategy.cut_points) == 0, f"{strategy.name} has cuts in extend mode"

        # All strategies should be within ±15s of target
        for strategy in strategies:
            result_length = strategy.calculate_resulting_length(original_length)
            error = abs(result_length - target_length)
            assert error <= 15.0, f"{strategy.name} error {error}s exceeds ±15s"

    def test_invalid_mode_raises_error(self):
        """Test that invalid mode raises ValueError."""
        clusters = [
            {
                'segment_times': [(10.0, 20.0)],
                'avg_similarity': 0.95,
                'duration': 10.0
            }
        ]

        with pytest.raises(ValueError, match="Invalid mode: invalid"):
            generate_strategies(
                mode="invalid",
                clusters=clusters,
                original_length=240.0,
                target_length=180.0
            )

    def test_trim_mode_with_custom_num_strategies(self):
        """Test trim mode respects custom num_strategies parameter."""
        clusters = [
            {
                'segment_times': [(10.0, 20.0), (50.0, 60.0), (100.0, 110.0)],
                'avg_similarity': 0.95,
                'duration': 10.0
            }
        ]

        original_length = 240.0
        target_length = 180.0

        # Generate 3 strategies instead of default 5
        strategies = generate_strategies(
            mode="trim",
            clusters=clusters,
            original_length=original_length,
            target_length=target_length,
            num_strategies=3
        )

        assert len(strategies) == 3

    def test_extend_mode_with_custom_num_strategies(self):
        """Test extend mode respects custom num_strategies parameter."""
        clusters = [
            {
                'segment_times': [(10.0, 20.0), (50.0, 60.0)],
                'avg_similarity': 0.95,
                'duration': 10.0
            }
        ]

        original_length = 180.0
        target_length = 240.0

        # Generate 3 strategies instead of default 5
        strategies = generate_strategies(
            mode="extend",
            clusters=clusters,
            original_length=original_length,
            target_length=target_length,
            num_strategies=3
        )

        assert len(strategies) == 3

    def test_trim_mode_with_regenerate_seed(self):
        """Test trim mode with reproducible randomization."""
        clusters = [
            {
                'segment_times': [(10.0, 20.0), (50.0, 60.0), (100.0, 110.0)],
                'avg_similarity': 0.95,
                'duration': 10.0
            }
        ]

        original_length = 240.0
        target_length = 180.0

        # Generate with seed
        strategies1 = generate_strategies(
            mode="trim",
            clusters=clusters,
            original_length=original_length,
            target_length=target_length,
            regenerate_seed=42
        )

        # Generate with same seed
        strategies2 = generate_strategies(
            mode="trim",
            clusters=clusters,
            original_length=original_length,
            target_length=target_length,
            regenerate_seed=42
        )

        # Should produce identical results
        assert len(strategies1) == len(strategies2)
        for s1, s2 in zip(strategies1, strategies2):
            assert s1.name == s2.name
            assert s1.cut_points == s2.cut_points

    def test_extend_mode_with_regenerate_seed(self):
        """Test extend mode with reproducible randomization."""
        clusters = [
            {
                'segment_times': [(10.0, 20.0), (50.0, 60.0)],
                'avg_similarity': 0.95,
                'duration': 10.0
            }
        ]

        original_length = 180.0
        target_length = 240.0

        # Generate with seed
        strategies1 = generate_strategies(
            mode="extend",
            clusters=clusters,
            original_length=original_length,
            target_length=target_length,
            regenerate_seed=42
        )

        # Generate with same seed
        strategies2 = generate_strategies(
            mode="extend",
            clusters=clusters,
            original_length=original_length,
            target_length=target_length,
            regenerate_seed=42
        )

        # Should produce identical results
        assert len(strategies1) == len(strategies2)
        for s1, s2 in zip(strategies1, strategies2):
            assert s1.name == s2.name
            assert s1.loop_points == s2.loop_points


class TestStrategyPriorityWeights:
    """Tests for strategy priority weight ordering."""

    def test_trim_strategy_weight_ordering(self):
        """Test that trim strategies have correct priority weight ordering.

        In trim mode, LOWER priority = cut first, HIGHER priority = preserve.
        Expected preservation order: conservative > best > balanced > diverse > varied
        """
        from src.trim_engine import generate_strategy
        import inspect
        import re

        # Extract STRATEGY_CONFIGS from source
        source = inspect.getsource(generate_strategy)

        # Find STRATEGY_CONFIGS dictionary
        configs = {}
        strategy_names = ["best", "diverse", "varied", "balanced", "conservative"]

        for strategy_name in strategy_names:
            # Find the strategy block
            pattern = f'"{strategy_name}"\\s*:\\s*{{[^}}]*"verse":\\s*([\\d.]+)'
            match = re.search(pattern, source)
            if match:
                verse_weight = float(match.group(1))
                configs[strategy_name] = {"verse": verse_weight}

        # Verify all weights extracted
        assert len(configs) == 5, f"Should extract 5 strategy configs, got {len(configs)}: {list(configs.keys())}"

        # Print current weights for debugging
        print("\nCurrent verse weights:")
        for name in strategy_names:
            print(f"  {name}: {configs[name]['verse']}")

        # Verify ordering: conservative > best > balanced > diverse > varied
        # (HIGHER weight = preserve more in trim mode)
        assert configs["conservative"]["verse"] > configs["best"]["verse"], \
            f"conservative verse weight ({configs['conservative']['verse']}) should be > best ({configs['best']['verse']})"

        assert configs["best"]["verse"] > configs["balanced"]["verse"], \
            f"best verse weight ({configs['best']['verse']}) should be > balanced ({configs['balanced']['verse']})"

        assert configs["balanced"]["verse"] > configs["diverse"]["verse"], \
            f"balanced verse weight ({configs['balanced']['verse']}) should be > diverse ({configs['diverse']['verse']})"

        assert configs["diverse"]["verse"] > configs["varied"]["verse"], \
            f"diverse verse weight ({configs['diverse']['verse']}) should be > varied ({configs['varied']['verse']})"

        # Additional check: conservative should have highest, varied should have lowest
        all_verse_weights = [configs[s]["verse"] for s in configs]
        assert configs["conservative"]["verse"] == max(all_verse_weights), \
            "conservative should have highest verse weight (most preservation)"

        assert configs["varied"]["verse"] == min(all_verse_weights), \
            "varied should have lowest verse weight (most aggressive cutting)"

