"""Tests for CLI module retry_for_quality function."""

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from src.cli import retry_for_quality
from src.trim_engine import TrimStrategy


class TestRetryForQuality:
    """Tests for retry_for_quality function."""

    @pytest.fixture
    def mock_audio_data(self):
        """Create mock audio data."""
        return np.random.randn(44100 * 10)  # 10 seconds at 44100Hz

    @pytest.fixture
    def mock_structure(self):
        """Create mock structure data."""
        return {
            'sections': [
                {'start': 0.0, 'end': 5.0, 'label': 'intro'},
                {'start': 5.0, 'end': 10.0, 'label': 'verse'}
            ],
            'beat_info': {
                'downbeats': [0.0, 2.0, 4.0, 6.0, 8.0, 10.0],
                'tempo': 120.0
            }
        }

    @pytest.fixture
    def mock_clusters(self):
        """Create mock clusters."""
        return [
            {
                'segment_times': [(2.0, 4.0), (6.0, 8.0)],
                'avg_similarity': 0.85,
                'duration': 2.0
            }
        ]

    def test_retry_accepts_quality_above_threshold(self, mock_audio_data, mock_structure, mock_clusters):
        """Test that retry accepts strategies with quality >= 3.5 stars."""
        # Create a high-quality strategy
        strategy = TrimStrategy(
            name="test_strategy",
            cut_points=[(2.0, 4.0)],
            loop_points=[],
            fade_regions=[(1.85, 2.15)],
            target_length=8.0
        )

        scored_strategies = [{
            'strategy': strategy,
            'score': {
                'star_rating': 4.0,
                'total_points': 80.0,
                'resulting_length': 8.0
            },
            'rendered_audio': mock_audio_data[:8*22050]
        }]

        strategies, scores = retry_for_quality(
            scored_strategies=scored_strategies,
            clusters=mock_clusters,
            original_length=10.0,
            target_length=8.0,
            structure=mock_structure,
            audio_data=mock_audio_data,
            sample_rate=22050,
            use_mert=False,
            regenerate_seed=None,
            mode="trim"
        )

        assert len(strategies) == 1
        assert len(scores) == 1
        assert scores[0]['star_rating'] == 4.0

    @patch('src.cli.generate_strategies')
    @patch('src.output_generator.render_strategy')
    @patch('src.cli.score_strategy')
    def test_retry_uses_trim_mode_for_trim(
        self, mock_score, mock_render, mock_generate,
        mock_audio_data, mock_structure, mock_clusters
    ):
        """Test that retry uses trim mode when target < original (trim mode)."""
        # Create a low-quality strategy to trigger retry
        strategy = TrimStrategy(
            name="low_quality",
            cut_points=[(2.0, 4.0)],
            loop_points=[],
            fade_regions=[(1.85, 2.15)],
            target_length=8.0
        )

        scored_strategies = [{
            'strategy': strategy,
            'score': {
                'star_rating': 2.5,  # Below 3.5 threshold
                'total_points': 50.0,
                'resulting_length': 8.0
            },
            'rendered_audio': mock_audio_data[:8*22050]
        }]

        # Mock the retry generation to return a better strategy
        better_strategy = TrimStrategy(
            name="retry_strategy",
            cut_points=[(2.0, 3.0)],
            loop_points=[],
            fade_regions=[(1.85, 2.15)],
            target_length=8.0
        )
        mock_generate.return_value = [better_strategy]
        mock_render.return_value = mock_audio_data[:8*22050]
        mock_score.return_value = {
            'star_rating': 3.8,
            'total_points': 76.0,
            'resulting_length': 8.0
        }

        # Run retry with trim mode (target < original)
        strategies, scores = retry_for_quality(
            scored_strategies=scored_strategies,
            clusters=mock_clusters,
            original_length=10.0,  # original > target = trim mode
            target_length=8.0,
            structure=mock_structure,
            audio_data=mock_audio_data,
            sample_rate=22050,
            use_mert=False,
            regenerate_seed=None,
            mode="trim"
        )

        # Verify generate_strategies was called with mode="trim"
        assert mock_generate.called
        call_args = mock_generate.call_args
        assert call_args[1]['mode'] == 'trim'

    @patch('src.cli.generate_strategies')
    @patch('src.output_generator.render_strategy')
    @patch('src.cli.score_strategy')
    def test_retry_uses_extend_mode_for_extension(
        self, mock_score, mock_render, mock_generate,
        mock_audio_data, mock_structure, mock_clusters
    ):
        """Test that retry uses extend mode when target > original (extend mode)."""
        # Create a low-quality extension strategy to trigger retry
        strategy = TrimStrategy(
            name="low_quality_extension",
            cut_points=[],
            loop_points=[(2.0, 4.0, 2)],
            fade_regions=[],
            target_length=12.0
        )

        scored_strategies = [{
            'strategy': strategy,
            'score': {
                'star_rating': 2.5,  # Below 3.5 threshold
                'total_points': 50.0,
                'resulting_length': 12.0
            },
            'rendered_audio': mock_audio_data
        }]

        # Mock the retry generation to return a better strategy
        better_strategy = TrimStrategy(
            name="retry_extension",
            cut_points=[],
            loop_points=[(3.0, 5.0, 2)],
            fade_regions=[],
            target_length=12.0
        )
        mock_generate.return_value = [better_strategy]
        mock_render.return_value = mock_audio_data
        mock_score.return_value = {
            'star_rating': 3.8,
            'total_points': 76.0,
            'resulting_length': 12.0
        }

        # Run retry with extend mode (target > original)
        strategies, scores = retry_for_quality(
            scored_strategies=scored_strategies,
            clusters=mock_clusters,
            original_length=10.0,  # original < target = extend mode
            target_length=12.0,
            structure=mock_structure,
            audio_data=mock_audio_data,
            sample_rate=22050,
            use_mert=False,
            regenerate_seed=None,
            mode="extend"
        )

        # Verify generate_strategies was called with mode="extend"
        assert mock_generate.called
        call_args = mock_generate.call_args
        assert call_args[1]['mode'] == 'extend'

    def test_retry_skips_when_regenerate_seed_provided(
        self, mock_audio_data, mock_structure, mock_clusters
    ):
        """Test that retry is skipped when regenerate_seed is provided (manual regeneration)."""
        # Create a low-quality strategy
        strategy = TrimStrategy(
            name="low_quality",
            cut_points=[(2.0, 4.0)],
            loop_points=[],
            fade_regions=[(1.85, 2.15)],
            target_length=8.0
        )

        scored_strategies = [{
            'strategy': strategy,
            'score': {
                'star_rating': 2.5,  # Below threshold but should not retry
                'total_points': 50.0,
                'resulting_length': 8.0
            },
            'rendered_audio': mock_audio_data[:8*22050]
        }]

        # Run with regenerate_seed (should skip retry)
        strategies, scores = retry_for_quality(
            scored_strategies=scored_strategies,
            clusters=mock_clusters,
            original_length=10.0,
            target_length=8.0,
            structure=mock_structure,
            audio_data=mock_audio_data,
            sample_rate=22050,
            use_mert=False,
            regenerate_seed=1,  # Manual regeneration - skip retry
            mode="trim"
        )

        # Should return the low-quality strategy without retry
        assert len(strategies) == 1
        assert scores[0]['star_rating'] == 2.5

    @patch('src.cli.generate_strategies')
    @patch('src.output_generator.render_strategy')
    @patch('src.cli.score_strategy')
    def test_retry_stops_when_acceptable_quality_found(
        self, mock_score, mock_render, mock_generate,
        mock_audio_data, mock_structure, mock_clusters
    ):
        """Test that retry stops as soon as acceptable quality is found."""
        # Create a low-quality strategy to trigger retry
        strategy = TrimStrategy(
            name="low_quality",
            cut_points=[(2.0, 4.0)],
            loop_points=[],
            fade_regions=[(1.85, 2.15)],
            target_length=8.0
        )

        scored_strategies = [{
            'strategy': strategy,
            'score': {
                'star_rating': 2.5,
                'total_points': 50.0,
                'resulting_length': 8.0
            },
            'rendered_audio': mock_audio_data[:8*22050]
        }]

        # Mock to return acceptable quality on first retry
        better_strategy = TrimStrategy(
            name="acceptable",
            cut_points=[(2.0, 3.0)],
            loop_points=[],
            fade_regions=[(1.85, 2.15)],
            target_length=8.0
        )
        mock_generate.return_value = [better_strategy]
        mock_render.return_value = mock_audio_data[:8*22050]
        mock_score.return_value = {
            'star_rating': 3.6,  # Above threshold
            'total_points': 72.0,
            'resulting_length': 8.0
        }

        strategies, scores = retry_for_quality(
            scored_strategies=scored_strategies,
            clusters=mock_clusters,
            original_length=10.0,
            target_length=8.0,
            structure=mock_structure,
            audio_data=mock_audio_data,
            sample_rate=22050,
            use_mert=False,
            regenerate_seed=None,
            mode="trim"
        )

        # Should have called generate_strategies only once (first retry succeeded)
        assert mock_generate.call_count == 1
        assert scores[0]['star_rating'] == 3.6
