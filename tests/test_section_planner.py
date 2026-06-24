"""Unit tests for src/section_planner.py — the section-enumeration core of the
rewritten trim/extend engine.

The planner works purely on section dicts ({'start', 'end', 'label'}) and
downbeat arrays. No audio, no librosa — so these run in milliseconds and pin
down the musical logic exactly.
"""
import pytest

from src.section_planner import (
    snap_to_downbeat,
    classify_sections,
    plan_trims,
    plan_extensions,
)


def _sections(*specs):
    """Build a section list from (start, end, label) tuples."""
    return [{'start': s, 'end': e, 'label': lbl} for s, e, lbl in specs]


# A canonical pop structure: intro/verse/chorus/verse/chorus/bridge/chorus/outro
def _pop_song():
    return _sections(
        (0.0, 10.0, 'intro'),
        (10.0, 40.0, 'verse'),
        (40.0, 60.0, 'chorus'),
        (60.0, 90.0, 'verse'),
        (90.0, 110.0, 'chorus'),
        (110.0, 130.0, 'bridge'),
        (130.0, 150.0, 'chorus'),
        (150.0, 160.0, 'outro'),
    )


# ---------- snap_to_downbeat ----------

def test_snap_returns_original_when_no_downbeats():
    assert snap_to_downbeat(40.0, [], tolerance=2.0) == 40.0
    assert snap_to_downbeat(40.0, None, tolerance=2.0) == 40.0


def test_snap_moves_to_nearest_downbeat_within_tolerance():
    downbeats = [0.0, 2.0, 4.0, 39.1, 41.5]
    # 40.0 is closest to 39.1 (0.9s) — within 2.0 tolerance.
    assert snap_to_downbeat(40.0, downbeats, tolerance=2.0) == 39.1


def test_snap_keeps_original_when_nearest_downbeat_too_far():
    downbeats = [0.0, 10.0, 20.0]
    # 40.0 nearest is 20.0 (20s away) — outside tolerance, keep original.
    assert snap_to_downbeat(40.0, downbeats, tolerance=2.0) == 40.0


def test_snap_picks_closest_of_several_candidates():
    downbeats = [38.0, 39.5, 41.0, 42.0]
    # 40.0: distances 2.0, 0.5, 1.0, 2.0 → 39.5 wins.
    assert snap_to_downbeat(40.0, downbeats, tolerance=3.0) == 39.5


# ---------- classify_sections ----------

def test_classify_protects_intro_and_outro():
    classified = classify_sections(_pop_song())
    assert classified[0]['removable'] is False   # intro (first)
    assert classified[-1]['removable'] is False   # outro (last)


def test_classify_protects_at_least_one_chorus():
    classified = classify_sections(_pop_song())
    chorus = [c for c in classified if c['label'] == 'chorus']
    protected = [c for c in chorus if not c['removable']]
    # The first chorus must stay protected so the hook survives.
    assert len(protected) >= 1
    assert protected[0]['start'] == 40.0  # earliest chorus


def test_classify_makes_bridge_and_later_verse_removable():
    classified = classify_sections(_pop_song())
    bridge = next(c for c in classified if c['label'] == 'bridge')
    verses = [c for c in classified if c['label'] == 'verse']
    assert bridge['removable'] is True
    # Both verses are interior → removable.
    assert all(v['removable'] for v in verses)


def test_classify_bridge_cheaper_to_remove_than_verse():
    classified = classify_sections(_pop_song())
    bridge = next(c for c in classified if c['label'] == 'bridge')
    first_verse = next(c for c in classified if c['label'] == 'verse')
    # Lower cost = removed first. Bridge is the safest interior removal.
    assert bridge['removal_cost'] < first_verse['removal_cost']


# ---------- classify_sections: protected regions + protect_ends ----------

def test_classify_protects_sections_overlapping_a_protected_region():
    # A user/auto protected span over the second verse (60-90) makes it uncuttable.
    classified = classify_sections(_pop_song(), protected_regions=[(65.0, 95.0)])
    verse2 = next(c for c in classified if c['start'] == 60.0)
    assert verse2['removable'] is False


def test_classify_protect_ends_false_makes_intro_and_outro_removable():
    classified = classify_sections(_pop_song(), protect_ends=False)
    assert classified[0]['removable'] is True    # intro now cuttable
    assert classified[-1]['removable'] is True   # outro now cuttable


def test_classify_protect_ends_true_is_the_default():
    classified = classify_sections(_pop_song())
    assert classified[0]['removable'] is False
    assert classified[-1]['removable'] is False


def test_classify_keeps_one_chorus_even_when_ends_unprotected():
    classified = classify_sections(_pop_song(), protect_ends=False)
    chorus = [c for c in classified if c['label'] == 'chorus']
    assert any(not c['removable'] for c in chorus)


# ---------- plan_trims: protection wiring ----------

def test_plan_trims_never_cuts_a_protected_region():
    # Protect the bridge (110-130); no plan may touch it even though it's the
    # cheapest interior removal.
    plans = plan_trims(_pop_song(), 160.0, 140.0, protected_regions=[(110.0, 130.0)])
    for plan in plans:
        for cs, ce in plan.cut_points:
            overlap = min(ce, 130.0) - max(cs, 110.0)
            assert overlap <= 0, f"{plan.name} cut ({cs},{ce}) hits protected bridge"


def test_plan_trims_can_cut_intro_when_ends_unprotected():
    # 10s deficit; with ends unprotected, removing the 10s intro is a valid option.
    plans = plan_trims(_pop_song(), 160.0, 150.0, protect_ends=False, num_plans=20)
    cuts_intro = any(
        any(cs <= 0.1 and ce >= 9.9 for cs, ce in plan.cut_points) for plan in plans
    )
    assert cuts_intro


# ---------- plan_trims ----------

def test_plan_trims_empty_when_no_deficit():
    # Target longer than original is an extend, not a trim.
    assert plan_trims(_pop_song(), original_length=160.0, target_length=200.0) == []


def test_plan_trims_isolates_the_bridge_for_an_exact_single_cut():
    # 160s song, want 140s → remove 20s. The bridge (110-130) is exactly 20s and
    # is the safest single interior section to remove. The best plan must be a
    # single cut isolating just the bridge — even though it sits between two
    # choruses.
    plans = plan_trims(_pop_song(), original_length=160.0, target_length=140.0)
    best = plans[0]
    assert best.cut_points == [(110.0, 130.0)]
    assert best.labels_removed == ['bridge']


def test_plan_trims_prefers_fewest_cuts():
    plans = plan_trims(_pop_song(), original_length=160.0, target_length=140.0)
    # The deficit is reachable with one cut, so the top plan must use one cut.
    assert len(plans[0].cut_points) == 1


def test_plan_trims_never_touches_intro_outro_or_first_chorus():
    plans = plan_trims(_pop_song(), original_length=160.0, target_length=80.0)
    protected_spans = [(0.0, 10.0), (40.0, 60.0), (150.0, 160.0)]  # intro, 1st chorus, outro
    for plan in plans:
        for cut_start, cut_end in plan.cut_points:
            for p_start, p_end in protected_spans:
                overlap = min(cut_end, p_end) - max(cut_start, p_start)
                assert overlap <= 0, (
                    f"plan {plan.name} cut ({cut_start},{cut_end}) "
                    f"overlaps protected ({p_start},{p_end})"
                )


def test_plan_trims_large_deficit_uses_one_contiguous_block():
    # Want to drop 90s (160→70). idx3..idx6 (60-150) is a contiguous removable
    # block of exactly 90s → one clean cut beats several scattered ones.
    plans = plan_trims(_pop_song(), original_length=160.0, target_length=70.0)
    best = plans[0]
    assert len(best.cut_points) == 1
    removed = sum(e - s for s, e in best.cut_points)
    assert removed == pytest.approx(90.0, abs=1.0)


def test_plan_trims_snaps_cut_endpoints_to_downbeats():
    downbeats = [0.0, 109.6, 130.3]
    plans = plan_trims(
        _pop_song(), original_length=160.0, target_length=140.0, downbeats=downbeats,
    )
    assert plans[0].cut_points == [(109.6, 130.3)]


def test_plan_trims_returns_distinct_options():
    plans = plan_trims(_pop_song(), original_length=160.0, target_length=120.0)
    assert len(plans) >= 2
    signatures = {tuple(p.cut_points) for p in plans}
    assert len(signatures) == len(plans)  # all distinct


# ---------- plan_extensions ----------

def test_plan_extensions_empty_when_no_surplus():
    assert plan_extensions(_pop_song(), original_length=160.0, target_length=120.0) == []


def test_plan_extensions_prefers_chorus():
    plans = plan_extensions(_pop_song(), original_length=160.0, target_length=180.0)
    assert plans[0].labels_repeated == ['chorus']


def test_plan_extensions_repeat_count_covers_surplus():
    # Surplus 20s, chorus is 20s → play it twice (one extra pass).
    plans = plan_extensions(_pop_song(), original_length=160.0, target_length=180.0)
    start, end, count = plans[0].loop_points[0]
    assert count == 2


def test_plan_extensions_caps_repeat_count():
    # Absurd surplus must not produce an endless loop.
    plans = plan_extensions(_pop_song(), original_length=160.0, target_length=600.0)
    _, _, count = plans[0].loop_points[0]
    assert count <= 4


def test_plan_extensions_respects_min_segment_duration():
    # Choruses are 20s; raising the floor to 25s forces verse repeats instead.
    plans = plan_extensions(
        _pop_song(), original_length=160.0, target_length=200.0,
        min_segment_duration=25.0,
    )
    assert all(lbl == 'verse' for p in plans for lbl in p.labels_repeated)


def test_plan_extensions_never_loops_bridge_intro_or_outro():
    plans = plan_extensions(_pop_song(), original_length=160.0, target_length=260.0)
    banned = {'bridge', 'intro', 'outro'}
    for plan in plans:
        assert not (set(plan.labels_repeated) & banned)


def test_plan_extensions_snaps_loop_endpoints_to_downbeats():
    downbeats = [40.4, 59.7]
    plans = plan_extensions(
        _pop_song(), original_length=160.0, target_length=180.0, downbeats=downbeats,
    )
    start, end, _ = plans[0].loop_points[0]
    assert (start, end) == (40.4, 59.7)


def test_plan_extensions_all_repeat_counts_offers_multiple_lengths():
    # Strict mode needs finer length granularity: emit every repeat count per
    # section (k=2..max_repeats) instead of only the single best-fit count.
    plans = plan_extensions(
        _pop_song(), original_length=160.0, target_length=240.0,
        all_repeat_counts=True, max_repeats=4, num_plans=30,
    )
    chorus_ks = {p.loop_points[0][2] for p in plans if p.labels_repeated == ['chorus']}
    assert {2, 3, 4}.issubset(chorus_ks)
