"""Unit tests for the rewritten src/quality_scorer.py.

The new scorer is one unified 100-point system shared by trim and extend:

    beat alignment      30   boundaries land on downbeats
    harmonic continuity 25   chroma matches across each join
    structural position 20   boundaries sit on section edges
    energy continuity   15   no loudness jump across a join
    length accuracy     10   close to the requested duration
                       ----
                        100  × cut-count multiplier (anti-fragmentation)

The numeric components are pure and tested directly here. The audio components
use short synthetic tones so they stay fast and deterministic.
"""
import numpy as np
import pytest

from src.quality_scorer import (
    score_length_accuracy,
    cut_count_multiplier,
    score_beat_alignment,
    score_structural_position,
    score_harmonic_continuity,
    score_energy_continuity,
    points_to_stars,
    score_strategy,
)
from src.trim_engine import TrimStrategy


# ---------- score_length_accuracy (0..10) ----------

def test_length_accuracy_exact_is_full():
    assert score_length_accuracy(100.0, 100.0) == pytest.approx(10.0)


def test_length_accuracy_within_5pct_is_full():
    # 3% off still counts as on-target — aesthetics over the last few seconds.
    assert score_length_accuracy(100.0, 103.0) == pytest.approx(10.0)


def test_length_accuracy_zero_beyond_25pct():
    assert score_length_accuracy(100.0, 130.0) == pytest.approx(0.0)
    assert score_length_accuracy(100.0, 70.0) == pytest.approx(0.0)  # symmetric


def test_length_accuracy_linear_midpoint():
    # 15% off is halfway between the 5% (=10) and 25% (=0) knees → 5.0.
    assert score_length_accuracy(100.0, 115.0) == pytest.approx(5.0, abs=0.01)


# ---------- cut_count_multiplier ----------

def test_multiplier_one_cut_is_unpenalized():
    assert cut_count_multiplier(0) == 1.0
    assert cut_count_multiplier(1) == 1.0


def test_multiplier_penalizes_fragmentation_progressively():
    assert cut_count_multiplier(2) == pytest.approx(0.85)
    assert cut_count_multiplier(3) == pytest.approx(0.65)
    assert cut_count_multiplier(4) == pytest.approx(0.40)
    assert cut_count_multiplier(7) == pytest.approx(0.40)  # floor


# ---------- score_beat_alignment (0..30) ----------

def test_beat_alignment_full_when_no_boundaries():
    assert score_beat_alignment([], [10.0, 20.0]) == pytest.approx(30.0)


def test_beat_alignment_full_when_all_on_downbeats():
    assert score_beat_alignment([40.0, 60.0], [0.0, 40.0, 60.0, 80.0]) == pytest.approx(30.0)


def test_beat_alignment_half_when_half_aligned():
    # 40.0 lands on a downbeat; 61.0 is 1s off (outside the 70ms tolerance).
    score = score_beat_alignment([40.0, 61.0], [40.0, 60.0])
    assert score == pytest.approx(15.0)


def test_beat_alignment_neutral_when_no_downbeats():
    # No downbeat data → don't reward or punish; return the neutral midpoint.
    assert score_beat_alignment([40.0], []) == pytest.approx(15.0)


# ---------- score_structural_position (0..20) ----------

def _pop_sections():
    return [
        {'start': 0.0, 'end': 10.0, 'label': 'intro'},
        {'start': 10.0, 'end': 40.0, 'label': 'verse'},
        {'start': 40.0, 'end': 60.0, 'label': 'chorus'},
        {'start': 60.0, 'end': 90.0, 'label': 'verse'},
        {'start': 90.0, 'end': 110.0, 'label': 'chorus'},
    ]


def test_structural_position_full_on_section_edges():
    # 40 and 60 are both section boundaries.
    assert score_structural_position([40.0, 60.0], _pop_sections()) == pytest.approx(20.0)


def test_structural_position_zero_mid_section():
    # 25.0 is deep inside the first verse — no section edge nearby.
    assert score_structural_position([25.0], _pop_sections()) == pytest.approx(0.0)


def test_structural_position_full_when_no_boundaries():
    assert score_structural_position([], _pop_sections()) == pytest.approx(20.0)


# ---------- audio-based components (synthetic tones) ----------

def _tone(freq, dur, sr=22050, amp=0.5):
    t = np.arange(int(dur * sr)) / sr
    return (amp * np.sin(2 * np.pi * freq * t)).astype(np.float32)


def test_harmonic_continuity_higher_for_matching_pitch():
    sr = 22050
    matched = _tone(440.0, 3.0, sr)                                   # A everywhere
    mismatched = np.concatenate([_tone(440.0, 1.5, sr), _tone(261.63, 1.5, sr)])  # A → C
    join = [(1.5, 1.5)]  # compare the window ending at 1.5 with the one starting at 1.5
    s_match = score_harmonic_continuity(matched, sr, join)
    s_mismatch = score_harmonic_continuity(mismatched, sr, join)
    assert s_match > s_mismatch
    assert s_match > 20.0  # near-identical chroma → near-full marks


def test_harmonic_continuity_full_when_no_joins():
    assert score_harmonic_continuity(_tone(440.0, 1.0), 22050, []) == pytest.approx(25.0)


def test_energy_continuity_full_when_levels_match():
    sr = 22050
    audio = _tone(440.0, 3.0, sr, amp=0.5)  # constant level
    assert score_energy_continuity(audio, sr, [(1.5, 1.5)]) == pytest.approx(15.0)


def test_energy_continuity_penalizes_loudness_jump():
    sr = 22050
    audio = np.concatenate([_tone(440.0, 1.5, sr, amp=0.5), _tone(440.0, 1.5, sr, amp=0.05)])  # ~20 dB drop
    assert score_energy_continuity(audio, sr, [(1.5, 1.5)]) < 5.0


# ---------- score_strategy integration ----------

_BREAKDOWN_KEYS = {
    'beat_alignment', 'harmonic_continuity', 'structural_position',
    'energy_continuity', 'length_accuracy', 'cut_count_multiplier',
}


def test_score_strategy_trim_clean_cut_scores_high():
    sr = 22050
    audio = _tone(440.0, 5.0, sr)
    strat = TrimStrategy(
        name='clean', cut_points=[(2.0, 3.0)], loop_points=[],
        fade_regions=[], target_length=4.0,
    )
    rendered = np.concatenate([audio[:int(2.0 * sr)], audio[int(3.0 * sr):]])  # ~4s
    sections = [
        {'start': 0.0, 'end': 2.0, 'label': 'verse'},
        {'start': 2.0, 'end': 3.0, 'label': 'bridge'},
        {'start': 3.0, 'end': 5.0, 'label': 'chorus'},
    ]
    score = score_strategy(
        strat, audio, sr, 5.0, rendered_audio=rendered,
        downbeats=[2.0, 3.0], sections=sections,
    )
    assert set(score['breakdown']) == _BREAKDOWN_KEYS
    assert score['breakdown']['beat_alignment'] == pytest.approx(30.0)
    assert score['breakdown']['structural_position'] == pytest.approx(20.0)
    assert score['breakdown']['length_accuracy'] == pytest.approx(10.0)
    assert score['breakdown']['cut_count_multiplier'] == 1.0
    assert score['star_rating'] == pytest.approx(points_to_stars(score['total_points']))


def test_score_strategy_extension_uses_same_rubric():
    sr = 22050
    audio = _tone(440.0, 5.0, sr)
    strat = TrimStrategy(
        name='loopit', cut_points=[], loop_points=[(2.0, 3.0, 2)],
        fade_regions=[], target_length=6.0,
    )
    sections = [
        {'start': 0.0, 'end': 2.0, 'label': 'verse'},
        {'start': 2.0, 'end': 3.0, 'label': 'chorus'},
        {'start': 3.0, 'end': 5.0, 'label': 'outro'},
    ]
    score = score_strategy(
        strat, audio, sr, 5.0, rendered_audio=None,
        downbeats=[2.0, 3.0], sections=sections,
    )
    # Same rubric, same keys, same single-edit multiplier as the trim case.
    assert set(score['breakdown']) == _BREAKDOWN_KEYS
    assert score['breakdown']['cut_count_multiplier'] == 1.0
    assert score['breakdown']['beat_alignment'] == pytest.approx(30.0)
    assert score['resulting_length'] == pytest.approx(6.0)


def test_score_strategy_fragmentation_multiplier_applied():
    sr = 22050
    audio = _tone(440.0, 10.0, sr)
    strat = TrimStrategy(
        name='frag', cut_points=[(2.0, 3.0), (4.0, 5.0), (6.0, 7.0)],
        loop_points=[], fade_regions=[], target_length=7.0,
    )
    score = score_strategy(strat, audio, sr, 10.0, rendered_audio=None)
    assert score['breakdown']['cut_count_multiplier'] == pytest.approx(0.65)  # 3 cuts
