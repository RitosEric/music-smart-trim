"""Tests for the rewritten trim/extension engine wrappers.

These exercise the thin layer that turns section_planner output into
TrimStrategy objects, and the generate_strategies router. Pure logic over
section dicts — no audio.
"""
import pytest

from src.trim_engine import TrimStrategy, generate_trim_strategies, generate_strategies
from src.extension_engine import generate_extension_strategies


def _pop_song():
    specs = [
        (0.0, 10.0, 'intro'),
        (10.0, 40.0, 'verse'),
        (40.0, 60.0, 'chorus'),
        (60.0, 90.0, 'verse'),
        (90.0, 110.0, 'chorus'),
        (110.0, 130.0, 'bridge'),
        (130.0, 150.0, 'chorus'),
        (150.0, 160.0, 'outro'),
    ]
    return [{'start': s, 'end': e, 'label': lbl} for s, e, lbl in specs]


# ---------- trim ----------

def test_generate_trim_strategies_returns_section_aligned_cuts():
    strats = generate_trim_strategies(
        clusters=[], original_length=160.0, target_length=140.0,
        sections=_pop_song(), downbeats=None,
    )
    assert len(strats) >= 1
    best = strats[0]
    assert isinstance(best, TrimStrategy)
    assert best.loop_points == []
    assert best.target_length == 140.0
    # 20s deficit → isolate the bridge in a single clean cut.
    assert best.cut_points == [(110.0, 130.0)]


def test_generate_trim_strategies_are_distinct():
    strats = generate_trim_strategies(
        clusters=[], original_length=160.0, target_length=120.0,
        sections=_pop_song(),
    )
    signatures = {tuple(s.cut_points) for s in strats}
    assert len(signatures) == len(strats)


def test_generate_trim_strategies_falls_back_without_sections():
    strats = generate_trim_strategies(
        clusters=[], original_length=160.0, target_length=140.0, sections=None,
    )
    assert len(strats) >= 1
    removed = sum(e - s for s, e in strats[0].cut_points)
    assert removed == pytest.approx(20.0, abs=2.0)


# ---------- extend ----------

def test_generate_extension_strategies_returns_loops():
    strats = generate_extension_strategies(
        clusters=[], original_length=160.0, target_length=180.0,
        sections=_pop_song(),
    )
    assert len(strats) >= 1
    best = strats[0]
    assert isinstance(best, TrimStrategy)
    assert best.cut_points == []
    assert len(best.loop_points) >= 1
    _, _, count = best.loop_points[0]
    assert count >= 2
    assert best.target_length == 180.0


def test_generate_extension_strategies_falls_back_without_sections():
    strats = generate_extension_strategies(
        clusters=[], original_length=160.0, target_length=180.0, sections=None,
    )
    assert len(strats) >= 1
    assert len(strats[0].loop_points) >= 1


# ---------- router ----------

def test_router_routes_trim_and_extend():
    trims = generate_strategies(
        mode='trim', clusters=[], original_length=160.0, target_length=140.0,
        sections=_pop_song(),
    )
    assert all(s.loop_points == [] for s in trims)
    extends = generate_strategies(
        mode='extend', clusters=[], original_length=160.0, target_length=180.0,
        sections=_pop_song(),
    )
    assert all(s.cut_points == [] for s in extends)


def test_router_rejects_unknown_mode():
    with pytest.raises(ValueError):
        generate_strategies(
            mode='bogus', clusters=[], original_length=160.0, target_length=140.0,
        )


# ---------- protection threading ----------

def test_generate_trim_respects_protected_regions():
    strats = generate_trim_strategies(
        clusters=[], original_length=160.0, target_length=140.0,
        sections=_pop_song(), protected_regions=[(110.0, 130.0)],
    )
    for s in strats:
        for cs, ce in s.cut_points:
            assert min(ce, 130.0) - max(cs, 110.0) <= 0


def test_generate_trim_can_cut_intro_when_ends_unprotected():
    strats = generate_trim_strategies(
        clusters=[], original_length=160.0, target_length=150.0,
        sections=_pop_song(), protect_ends=False, num_strategies=20,
    )
    assert any(any(cs <= 0.1 and ce >= 9.9 for cs, ce in s.cut_points) for s in strats)


def test_router_forwards_protection_to_trim():
    strats = generate_strategies(
        mode='trim', clusters=[], original_length=160.0, target_length=140.0,
        sections=_pop_song(), protected_regions=[(110.0, 130.0)],
    )
    for s in strats:
        for cs, ce in s.cut_points:
            assert min(ce, 130.0) - max(cs, 110.0) <= 0
