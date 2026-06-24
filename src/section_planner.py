"""Section-enumeration planner for the rewritten trim/extend engine.

The previous engine searched a parameter space (similarity thresholds, max-cut
counts) and then tried to *remediate* the resulting cuts toward section
boundaries. That inverted the priorities: it decided how aggressively to cut
before deciding where a cut belonged musically, and its refinement loop added
fragmented micro-cuts whenever the length target was missed.

This module inverts the design. A musical edit is modelled as *adding or
removing whole sections*:

  - Trim  = remove one or more contiguous runs of interior sections. Each run
            is a single cut whose endpoints are section boundaries (snapped to
            the nearest downbeat). Removing a contiguous run never leaves a
            seam inside a section.
  - Extend = repeat a whole section (chorus first, then verse). The loop seam
            sits on section boundaries, which are bar-aligned by construction.

Both directions share the same principles, drawn from the MIR literature on
music structure analysis and summarization:

  1. Cut/loop only at section boundaries, snapped to downbeats.
  2. Prefer the fewest edits — one clean splice beats four fragmented ones,
     even at the cost of some length accuracy.
  3. Protect the song's anchors: keep the intro, the outro, and at least one
     chorus. Bridges and repeated verses are the safe things to remove; the
     chorus is the safe thing to repeat.

Everything here is pure logic over section dicts and downbeat arrays, so it is
exhaustively unit-tested without touching audio.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple


# --- Aesthetic priorities ---------------------------------------------------
# Lower removal_cost => safer to remove (cut first). These encode the perceptual
# salience ordering from the structure-analysis literature: bridges are designed
# as one-off contrast and are the most disposable; repeated verses go next; a
# lone verse is more costly; a surplus chorus is the last resort.
_REMOVAL_COST = {
    'bridge': 1.0,
    'verse_repeat': 1.5,   # 2nd+ occurrence of a verse
    'unknown': 2.0,
    'end': 2.5,            # intro/outro, only removable when ends are unprotected
    'verse': 3.0,          # first/only verse
    'chorus_repeat': 5.0,  # surplus chorus (only if >1 chorus exists)
}

# Higher loop_priority => better to repeat first. Chorus is built for
# repetition; verse works once; everything else is unsafe to loop.
_LOOP_PRIORITY = {
    'chorus': 3.0,
    'verse': 2.0,
    'prechorus': 1.0,
    'pre-chorus': 1.0,
}
_NEVER_LOOP = {'intro', 'outro', 'bridge'}


@dataclass
class TrimPlan:
    """One trim option: a set of (start, end) cuts at section boundaries."""
    cut_points: List[Tuple[float, float]]
    name: str
    labels_removed: List[str] = field(default_factory=list)


@dataclass
class ExtendPlan:
    """One extend option: a set of (start, end, repeat_count) loops."""
    loop_points: List[Tuple[float, float, int]]
    name: str
    labels_repeated: List[str] = field(default_factory=list)


def snap_to_downbeat(
    time: float,
    downbeats: Optional[Sequence[float]],
    tolerance: float = 2.0,
) -> float:
    """Move ``time`` to the nearest downbeat, if one is within ``tolerance``.

    Section boundaries from spectral clustering rarely land exactly on a bar
    line. Snapping the cut/loop endpoint to the closest downbeat is the single
    highest-impact step for making an edit sound deliberate. When no downbeat
    is close enough (or none exist), the original section boundary is kept.
    """
    if downbeats is None or len(downbeats) == 0:
        return time
    nearest = min(downbeats, key=lambda db: abs(db - time))
    if abs(nearest - time) <= tolerance:
        return float(nearest)
    return time


def classify_sections(
    sections: List[Dict],
    protected_regions: Optional[List[Tuple[float, float]]] = None,
    protect_ends: bool = True,
) -> List[Dict]:
    """Annotate each section with removability for trim planning.

    Returns a new list of dicts, each carrying the original
    ``start``/``end``/``label`` plus:
      - ``removable``: bool — may this section be cut?
      - ``removal_cost``: float — lower is safer to remove (sort key).
      - ``index``: position in the song.

    Protection rules, in priority order:
      1. A section overlapping any ``protected_regions`` span (user-marked or
         auto intro/outro) is never removable.
      2. When ``protect_ends`` is True (the auto-protect toggle), the intro
         (first section) and outro (last section) are protected. When False,
         they become cuttable — the engine may drop the opening or ending.
      3. The earliest chorus is always kept so the hook survives, regardless of
         the toggle.
    """
    protected_regions = protected_regions or []
    n = len(sections)
    chorus_indices = [i for i, s in enumerate(sections) if s.get('label') == 'chorus']
    protected_chorus = chorus_indices[0] if chorus_indices else None

    # Track how many times each verse label has appeared so 2nd+ verses are
    # cheaper to remove than the first.
    verse_seen = 0

    classified = []
    for i, s in enumerate(sections):
        label = s.get('label', 'unknown')
        removable = True
        cost = _REMOVAL_COST['unknown']

        is_intro = (i == 0) or label == 'intro'
        is_outro = (i == n - 1) or label == 'outro'

        if label == 'verse':
            verse_seen += 1

        if _overlaps_any(s, protected_regions):
            removable = False                       # rule 1: explicit protection
        elif protect_ends and (is_intro or is_outro):
            removable = False                       # rule 2: anchor the ends
        elif label == 'chorus' and (i == protected_chorus or len(chorus_indices) <= 1):
            removable = False                       # rule 3: keep one chorus
        elif label == 'chorus':
            cost = _REMOVAL_COST['chorus_repeat']
        elif label == 'bridge':
            cost = _REMOVAL_COST['bridge']
        elif label == 'verse':
            cost = _REMOVAL_COST['verse_repeat'] if verse_seen > 1 else _REMOVAL_COST['verse']
        elif label in ('intro', 'outro'):
            cost = _REMOVAL_COST['end']             # removable only when protect_ends is False
        else:
            cost = _REMOVAL_COST.get(label, _REMOVAL_COST['unknown'])

        out = dict(s)
        out['index'] = i
        out['removable'] = removable
        out['removal_cost'] = cost if removable else float('inf')
        classified.append(out)

    return classified


def _overlaps_any(section: Dict, regions: List[Tuple[float, float]]) -> bool:
    """True if the section overlaps any (start, end) protected span."""
    s_start, s_end = section['start'], section['end']
    for r_start, r_end in regions:
        if not (s_end <= r_start or s_start >= r_end):
            return True
    return False


def plan_trims(
    sections: List[Dict],
    original_length: float,
    target_length: float,
    downbeats: Optional[Sequence[float]] = None,
    seed: Optional[int] = None,
    max_cuts: int = 2,
    num_plans: int = 5,
    protected_regions: Optional[List[Tuple[float, float]]] = None,
    protect_ends: bool = True,
) -> List[TrimPlan]:
    """Enumerate distinct trim options that remove whole sections.

    A trim plan is any subset of removable sections. Sections that are adjacent
    *in the song* merge into a single cut, so the plan's cut count is the number
    of disjoint runs the subset spans — and a subset can isolate one interior
    section (e.g. just the bridge) even when it sits between protected choruses.

    Plans are ranked by, in order:
      1. whether the removed duration lands within an aesthetic tolerance band
         of the deficit (everything inside the band is treated as equally good
         on length, so we don't fragment a clean cut chasing the last second),
      2. fewest cuts — one clean splice beats several scattered ones,
      3. closeness to the deficit,
      4. lowest total removal cost (bridge before verse before surplus chorus).

    Subsets producing more than ``max_cuts`` disjoint cuts are discarded
    outright, which is the structural guarantee against fragmentation.

    ``seed`` shifts which slice of the ranked options is returned so the web
    UI's "regenerate" surfaces fresh alternatives instead of the same list.
    """
    from itertools import combinations

    deficit = original_length - target_length
    if deficit <= 0:
        return []

    classified = classify_sections(sections, protected_regions, protect_ends)
    removable = [c for c in classified if c['removable']]
    if not removable:
        return []

    tolerance = max(5.0, 0.05 * target_length)  # ±5s or 5% of target, whichever larger
    max_subset = min(len(removable), 8)  # bound the enumeration; songs rarely exceed this

    ranked = []
    for r in range(1, max_subset + 1):
        for combo in combinations(removable, r):
            intervals = _merge_adjacent_sections(combo, downbeats)
            if len(intervals) > max_cuts:
                continue  # too fragmented — reject
            removed = sum(e - s for s, e in intervals)
            cost = sum(c['removal_cost'] for c in combo)
            labels = [c['label'] for c in combo]
            miss = abs(removed - deficit)
            n_cuts = len(intervals)
            if miss <= tolerance:
                # Inside the tolerance band every option is "close enough" on
                # length, so aesthetics decide: fewest cuts, then cheapest
                # (safest) sections, with sub-second length only as a tiebreak.
                key = (0, n_cuts, cost, round(miss, 3))
            else:
                # Outside the band, get as close as possible first.
                key = (1, n_cuts, round(miss, 3), cost)
            plan = TrimPlan(
                cut_points=intervals,
                name="remove-" + "+".join(labels),
                labels_removed=labels,
            )
            ranked.append((key, plan))

    ranked.sort(key=lambda item: item[0])

    # De-duplicate by cut signature, preserving rank order.
    distinct: List[TrimPlan] = []
    seen = set()
    for _, plan in ranked:
        sig = tuple(round(c, 2) for cp in plan.cut_points for c in cp)
        if sig in seen:
            continue
        seen.add(sig)
        distinct.append(plan)

    return _seed_window(distinct, seed, num_plans)


def plan_extensions(
    sections: List[Dict],
    original_length: float,
    target_length: float,
    downbeats: Optional[Sequence[float]] = None,
    min_segment_duration: float = 10.0,
    seed: Optional[int] = None,
    max_repeats: int = 4,
    num_plans: int = 5,
    protected_regions: Optional[List[Tuple[float, float]]] = None,
    all_repeat_counts: bool = False,
) -> List[ExtendPlan]:
    """Enumerate distinct extension options that repeat whole sections.

    A loopable section (chorus first, then verse) is repeated enough times to
    cover the surplus, capped at ``max_repeats`` so the song never turns into a
    monotonous loop. The loop endpoints are section boundaries snapped to
    downbeats, so each seam is bar-aligned.

    Normally one repeat count is chosen per section — the one that best covers
    the surplus. When ``all_repeat_counts`` is set (strict-length escalation),
    every count from 2..``max_repeats`` is emitted per section, giving the
    caller a finer ladder of reachable lengths; plans are then ordered by how
    close their added duration lands to the surplus.
    """
    surplus = target_length - original_length
    if surplus <= 0:
        return []

    loopable = _loopable_sections(sections, min_segment_duration, protected_regions)
    if not loopable:
        return []

    candidates = []  # (miss, ExtendPlan)
    seen = set()
    for s in loopable:
        start = snap_to_downbeat(s['start'], downbeats)
        end = snap_to_downbeat(s['end'], downbeats)
        duration = end - start
        if duration <= 0:
            continue

        if all_repeat_counts:
            counts = range(2, max_repeats + 1)
        else:
            # The single count whose extra plays best cover the surplus.
            extra_needed = max(1, round(surplus / duration))
            counts = [min(max_repeats, 1 + extra_needed)]

        for repeat_count in counts:
            sig = (round(start, 2), round(end, 2), repeat_count)
            if sig in seen:
                continue
            seen.add(sig)
            added = duration * (repeat_count - 1)
            candidates.append((abs(added - surplus), ExtendPlan(
                loop_points=[(start, end, repeat_count)],
                name=f"repeat-{s['label']}-x{repeat_count}",
                labels_repeated=[s['label']],
            )))

    # Best-first by closeness when laddering; otherwise preserve loop priority.
    if all_repeat_counts:
        candidates.sort(key=lambda c: c[0])
    plans = [plan for _, plan in candidates]
    return plans[:num_plans]


# --- internal helpers -------------------------------------------------------

def _merge_adjacent_sections(combo, downbeats) -> List[Tuple[float, float]]:
    """Collapse a subset of sections into cut intervals.

    Sections whose song positions are consecutive (index n, n+1, ...) belong to
    one uninterrupted stretch of audio and so become a single cut spanning their
    outer boundaries. A protected section sitting between two selected ones has
    a non-consecutive index, so it breaks the run — the result is two separate
    cuts that leave the protected section intact. Endpoints snap to downbeats.
    """
    ordered = sorted(combo, key=lambda s: s['index'])
    intervals: List[Tuple[float, float]] = []
    run_start = ordered[0]['start']
    run_end = ordered[0]['end']
    prev_index = ordered[0]['index']

    for s in ordered[1:]:
        if s['index'] == prev_index + 1:
            run_end = s['end']  # extend the current contiguous run
        else:
            intervals.append((run_start, run_end))
            run_start, run_end = s['start'], s['end']
        prev_index = s['index']
    intervals.append((run_start, run_end))

    return [
        (snap_to_downbeat(s, downbeats), snap_to_downbeat(e, downbeats))
        for s, e in intervals
    ]


def _seed_window(items: list, seed: Optional[int], count: int) -> list:
    """Return ``count`` items starting at a seed-derived offset, wrapping around.

    With no seed the best options come first. Each regenerate seed rotates the
    window so the user sees fresh alternatives without losing determinism.
    """
    if not items:
        return []
    if seed is None:
        return items[:count]
    offset = (seed * count) % len(items)
    rotated = items[offset:] + items[:offset]
    return rotated[:count]


def _loopable_sections(
    sections: List[Dict],
    min_segment_duration: float,
    protected_regions: Optional[List[Tuple[float, float]]] = None,
) -> List[Dict]:
    """Return loop-eligible sections ordered best-first (chorus, then verse)."""
    protected_regions = protected_regions or []
    eligible = []
    for s in sections:
        label = s.get('label', 'unknown')
        if label in _NEVER_LOOP:
            continue
        priority = _LOOP_PRIORITY.get(label)
        if priority is None:
            continue
        if (s['end'] - s['start']) < min_segment_duration:
            continue
        if _overlaps_any(s, protected_regions):
            continue  # don't repeat a protected section
        eligible.append((priority, s))
    # Highest priority first; ties keep chronological order (stable sort).
    eligible.sort(key=lambda p: -p[0])
    return [s for _, s in eligible]
