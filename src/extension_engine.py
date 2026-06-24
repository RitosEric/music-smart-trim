"""Extension engine — turns section-repeat plans into TrimStrategy objects.

Mirror image of :mod:`src.trim_engine`. Section selection (which section to
repeat, how many times, capped to avoid monotony) lives in
:func:`src.section_planner.plan_extensions`; this module wraps each plan as a
:class:`TrimStrategy` with ``loop_points`` populated.

The old engine's per-strategy parameter sweep and length-refinement loop have
been removed in favour of the planner's direct, section-aligned choices.
"""
from typing import Dict, List, Optional, Tuple

import numpy as np

from src.trim_engine import TrimStrategy
from src.section_planner import plan_extensions, snap_to_downbeat


def generate_extension_strategies(
    clusters: List[Dict],
    original_length: float,
    target_length: float,
    sections: Optional[List[Dict]] = None,
    downbeats: Optional[np.ndarray] = None,
    regenerate_seed: int = None,
    num_strategies: int = 5,
    min_segment_duration: float = 10.0,
    protected_regions: Optional[List[Tuple[float, float]]] = None,
    max_repeats: int = 4,
    all_repeat_counts: bool = False,
) -> List[TrimStrategy]:
    """Build section-aligned extension strategies.

    Each plan from :func:`plan_extensions` repeats a single loop-eligible
    section (chorus first, then verse) enough times to cover the surplus,
    capped so the song never degenerates into an endless loop. Falls back to
    repeating a centered chunk when no section data is available.

    ``protected_regions`` keeps the planner from repeating a protected section.
    ``max_repeats`` is raised by strict-length escalation to reach tight targets.
    ``clusters`` is accepted for signature compatibility; section structure now
    drives the decision.
    """
    if sections:
        plans = plan_extensions(
            sections, original_length, target_length,
            downbeats=downbeats, min_segment_duration=min_segment_duration,
            seed=regenerate_seed, num_plans=num_strategies,
            protected_regions=protected_regions, max_repeats=max_repeats,
            all_repeat_counts=all_repeat_counts,
        )
        strategies = [
            TrimStrategy(
                name=plan.name,
                cut_points=[],
                loop_points=plan.loop_points,
                fade_regions=[],
                target_length=target_length,
            )
            for plan in plans
        ]
        if strategies:
            return strategies

    return [_fallback_extension(original_length, target_length, downbeats)]


def _fallback_extension(
    original_length: float,
    target_length: float,
    downbeats: Optional[np.ndarray] = None,
) -> TrimStrategy:
    """Repeat a centered chunk, used when no sections are available."""
    surplus = max(0.0, target_length - original_length)
    # Repeat a central quarter of the track enough times to cover the surplus.
    seg_start = snap_to_downbeat(original_length * 0.375, downbeats)
    seg_end = snap_to_downbeat(original_length * 0.625, downbeats)
    seg_duration = max(1.0, seg_end - seg_start)
    repeat_count = min(4, 1 + max(1, round(surplus / seg_duration)))
    return TrimStrategy(
        name="fallback-center-loop",
        cut_points=[],
        loop_points=[(seg_start, seg_end, repeat_count)],
        fade_regions=[],
        target_length=target_length,
    )
