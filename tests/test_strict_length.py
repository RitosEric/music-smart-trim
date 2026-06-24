"""Unit tests for the strict-length filter and retry logic in src/cli.py.

These tests use stubs for the heavy audio + scoring stages so they run in
milliseconds without librosa, MERT, or any actual file I/O.
"""
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from src.cli import (
    MIN_ACCEPTABLE_QUALITY,
    STRICT_LENGTH_TOLERANCE,
    MAX_STRICT_RETRIES,
    MAX_QUALITY_RETRIES,
    _apply_strict_length_filter,
    _select_closest,
    retry_for_quality,
    retry_for_strict_length,
)


def _make_candidate(name, resulting_length, star_rating=3.0):
    """Build the dict shape that retry_for_quality / strict expects."""
    return {
        'strategy': SimpleNamespace(name=name),
        'score': {
            'resulting_length': resulting_length,
            'star_rating': star_rating,
            'total_points': star_rating * 10,
        },
        'rendered_audio': None,
    }


# ---------- _apply_strict_length_filter ----------

def test_filter_keeps_within_tolerance():
    target = 120.0
    items = [
        _make_candidate('a', 115.0),  # 5s off — keep
        _make_candidate('b', 140.0),  # 20s off — drop
        _make_candidate('c', 105.0),  # 15s off — keep (inclusive)
        _make_candidate('d', 100.0),  # 20s off — drop
    ]
    kept = _apply_strict_length_filter(items, target)
    assert [k['strategy'].name for k in kept] == ['a', 'c']


def test_filter_returns_empty_when_all_outside():
    target = 120.0
    items = [
        _make_candidate('a', 80.0),
        _make_candidate('b', 200.0),
    ]
    assert _apply_strict_length_filter(items, target) == []


def test_filter_boundary_is_inclusive():
    target = 60.0
    # Exactly at the tolerance edge — should pass with <=.
    edge_low = _make_candidate('low', target - STRICT_LENGTH_TOLERANCE)
    edge_high = _make_candidate('high', target + STRICT_LENGTH_TOLERANCE)
    just_over = _make_candidate('over', target + STRICT_LENGTH_TOLERANCE + 0.01)
    kept = _apply_strict_length_filter([edge_low, edge_high, just_over], target)
    assert {k['strategy'].name for k in kept} == {'low', 'high'}


# ---------- _select_closest ----------

def test_closest_sorts_by_distance_then_quality():
    target = 100.0
    items = [
        _make_candidate('far_good', 150.0, star_rating=5.0),   # 50s off
        _make_candidate('near_bad', 95.0, star_rating=1.0),    # 5s off
        _make_candidate('tie_low', 110.0, star_rating=2.0),    # 10s off, lower quality
        _make_candidate('tie_high', 90.0, star_rating=4.0),    # 10s off, higher quality
    ]
    result = _select_closest(items, target, count=3)
    # near_bad first (5s), then tie_high (10s, quality 4.0 > 2.0), then tie_low.
    assert [r['strategy'].name for r in result] == ['near_bad', 'tie_high', 'tie_low']


# ---------- retry_for_strict_length ----------

def _stub_pipeline_args():
    """Common args for retry_for_strict_length that don't matter for these tests."""
    return dict(
        clusters=[],
        original_length=240.0,
        target_length=120.0,
        structure={'sections': [], 'beat_info': {'downbeats': []}},
        audio_data=None,
        sample_rate=44100,
        use_mert=False,
        regenerate_seed=None,
        mode='trim',
        min_segment_duration=10.0,
    )


def test_retry_returns_compliant_without_regenerating():
    """If the initial batch has at least one compliant strategy, no retry fires."""
    initial = [
        _make_candidate('compliant', 115.0, star_rating=4.0),
        _make_candidate('off', 150.0, star_rating=5.0),
    ]
    with patch('src.cli.generate_strategies') as mock_gen:
        strategies, scores, met = retry_for_strict_length(
            initial, **_stub_pipeline_args(),
        )
    assert met is True
    assert [s.name for s in strategies] == ['compliant']
    assert mock_gen.call_count == 0


def test_retry_picks_highest_quality_among_compliant():
    initial = [
        _make_candidate('compliant_low', 118.0, star_rating=2.0),
        _make_candidate('compliant_high', 122.0, star_rating=4.5),
        _make_candidate('off', 80.0, star_rating=5.0),
    ]
    with patch('src.cli.generate_strategies') as mock_gen:
        strategies, scores, met = retry_for_strict_length(
            initial, **_stub_pipeline_args(),
        )
    assert met is True
    # Top-by-quality first, then the other compliant one.
    assert [s.name for s in strategies] == ['compliant_high', 'compliant_low']
    assert mock_gen.call_count == 0


def test_retry_loops_up_to_max_when_all_fail():
    """All retries return non-compliant strategies — should hit MAX and return closest."""
    initial = [_make_candidate('init', 200.0, star_rating=5.0)]  # 80s off

    def make_retry_strategy(name, length):
        return SimpleNamespace(name=name, _length=length)

    # Each retry call returns one non-compliant strategy.
    retry_strategies = [
        [make_retry_strategy(f'r{i}', 200.0 - i)]  # 80s, 79s, ... still way off
        for i in range(1, MAX_STRICT_RETRIES + 1)
    ]

    def fake_render(strategy, audio, sr):
        return None

    def fake_score(strategy, audio, sr, original_length, rendered, use_mert=False):
        # SimpleNamespace inputs carry _length so we can vary results per strategy.
        length = getattr(strategy, '_length', 200.0)
        return {
            'resulting_length': length,
            'star_rating': 2.0,
            'total_points': 20.0,
        }

    with patch('src.cli.generate_strategies', side_effect=retry_strategies) as mock_gen, \
         patch('src.output_generator.render_strategy', side_effect=fake_render), \
         patch('src.cli.score_strategy', side_effect=fake_score):
        strategies, scores, met = retry_for_strict_length(
            initial, **_stub_pipeline_args(),
        )

    assert met is False
    assert mock_gen.call_count == MAX_STRICT_RETRIES
    # Returned strategies should be sorted by closeness to target (120s).
    # init=200 (80 off), retry strategies 200..196 → init is also 80 off, r5=195 (75 off) closest.
    # Lowest |length - 120| should come first.
    distances = [abs(s.score['resulting_length'] - 120.0) if hasattr(s, 'score') else None for s in strategies]
    # `strategies` are SimpleNamespace objects without .score; check via lengths attribute.
    lengths = [getattr(s, '_length', 200.0) for s in strategies]
    sorted_lengths = sorted(lengths, key=lambda L: abs(L - 120.0))
    assert lengths == sorted_lengths


def test_retry_succeeds_mid_loop_returns_compliant():
    """First retry returns non-compliant, second returns compliant — stop at second."""
    initial = [_make_candidate('init', 200.0, star_rating=5.0)]

    retry_round_1 = [SimpleNamespace(name='r1', _length=199.0)]  # still off
    retry_round_2 = [SimpleNamespace(name='r2_good', _length=121.0)]  # compliant

    def fake_score(strategy, audio, sr, original_length, rendered, use_mert=False):
        length = getattr(strategy, '_length', 200.0)
        return {
            'resulting_length': length,
            'star_rating': 3.0,
            'total_points': 30.0,
        }

    with patch('src.cli.generate_strategies', side_effect=[retry_round_1, retry_round_2]) as mock_gen, \
         patch('src.output_generator.render_strategy', return_value=None), \
         patch('src.cli.score_strategy', side_effect=fake_score):
        strategies, scores, met = retry_for_strict_length(
            initial, **_stub_pipeline_args(),
        )

    assert met is True
    assert mock_gen.call_count == 2  # stopped after second retry succeeded
    assert [s.name for s in strategies] == ['r2_good']


# ---------- progress_callback regression tests ----------
# Without these, retry_for_quality could regress to its original
# silent-print behavior and the UI would freeze on "Analyzing audio
# structure..." through the entire reseed loop again.

def test_strict_retry_fires_progress_callback_per_retry():
    """retry_for_strict_length must emit a progress message on every retry."""
    initial = [_make_candidate('init', 200.0, star_rating=5.0)]  # 80s off, will retry
    retry_strategies = [
        [SimpleNamespace(name=f'r{i}', _length=200.0)]
        for i in range(1, MAX_STRICT_RETRIES + 1)
    ]
    captured = []

    def fake_score(strategy, audio, sr, original_length, rendered, use_mert=False):
        return {
            'resulting_length': getattr(strategy, '_length', 200.0),
            'star_rating': 2.0,
            'total_points': 20.0,
        }

    with patch('src.cli.generate_strategies', side_effect=retry_strategies), \
         patch('src.output_generator.render_strategy', return_value=None), \
         patch('src.cli.score_strategy', side_effect=fake_score):
        retry_for_strict_length(
            initial,
            **_stub_pipeline_args(),
            progress_callback=lambda msg, pct: captured.append((msg, pct)),
        )

    # 1 intro message + 5 per-retry messages = 6 callbacks.
    assert len(captured) == MAX_STRICT_RETRIES + 1
    # Per-retry percents should be monotonically increasing and stay <= 75
    # (the post-pipeline "Generating outputs..." milestone is at 90).
    retry_percents = [pct for _, pct in captured[1:]]
    assert retry_percents == sorted(retry_percents)
    assert max(retry_percents) <= 75


def test_quality_retry_fires_progress_callback_per_retry():
    """retry_for_quality must emit a progress message on every retry — the
    bug the user reported was that this loop reseeded silently and the UI
    sat frozen on 'Analyzing audio structure...' for the whole duration."""
    # First batch is below MIN_ACCEPTABLE_QUALITY so the loop fires.
    initial = [_make_candidate(f's{i}', 120.0, star_rating=MIN_ACCEPTABLE_QUALITY - 1.0)
               for i in range(3)]
    # Every retry returns the same low-quality batch so we exhaust MAX_QUALITY_RETRIES.
    retry_strategies = [
        [SimpleNamespace(name=f'q{r}_{i}', _length=120.0) for i in range(3)]
        for r in range(MAX_QUALITY_RETRIES)
    ]
    captured = []

    def fake_score(strategy, audio, sr, original_length, rendered, use_mert=False):
        return {
            'resulting_length': 120.0,
            'star_rating': MIN_ACCEPTABLE_QUALITY - 1.0,
            'total_points': 20.0,
        }

    with patch('src.cli.generate_strategies', side_effect=retry_strategies), \
         patch('src.output_generator.render_strategy', return_value=None), \
         patch('src.cli.score_strategy', side_effect=fake_score):
        retry_for_quality(
            initial,
            **_stub_pipeline_args(),
            progress_callback=lambda msg, pct: captured.append((msg, pct)),
        )

    # 1 intro + MAX_QUALITY_RETRIES per-retry messages.
    assert len(captured) == MAX_QUALITY_RETRIES + 1
    retry_percents = [pct for _, pct in captured[1:]]
    assert retry_percents == sorted(retry_percents)
    assert max(retry_percents) <= 75


def test_quality_retry_no_callback_when_first_batch_passes():
    """No reseed → no progress messages, matching today's UX for happy-path runs."""
    initial = [_make_candidate('good', 120.0, star_rating=4.5)]
    captured = []

    with patch('src.cli.generate_strategies') as mock_gen:
        retry_for_quality(
            initial,
            **_stub_pipeline_args(),
            progress_callback=lambda msg, pct: captured.append((msg, pct)),
        )

    assert captured == []
    assert mock_gen.call_count == 0
