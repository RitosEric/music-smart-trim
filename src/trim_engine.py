"""Trim engine — turns section-removal plans into renderable TrimStrategy objects.

The heavy lifting (which sections to remove, how to keep cuts un-fragmented and
section-aligned) lives in :mod:`src.section_planner`. This module is the thin
adapter that wraps each plan in the :class:`TrimStrategy` dataclass the renderer
and scorer consume, plus the ``generate_strategies`` router shared with the
extension engine.

The old engine's parametric search, section-boundary remediation, and
length-refinement loop (which fragmented cuts whenever it missed the target)
have been removed — the planner produces section-aligned cuts directly, so no
remediation is needed.
"""
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np

from src.section_planner import plan_trims, plan_extensions, snap_to_downbeat


@dataclass
class TrimStrategy:
    """A renderable edit plan shared by trim and extend modes.

    Attributes:
        name: Human-readable strategy name (e.g. "remove-bridge").
        cut_points: List of (start_time, end_time) regions to remove.
        loop_points: List of (start_time, end_time, repeat_count) regions to repeat.
        fade_regions: List of (fade_start, fade_end) crossfade markers (metadata).
        target_length: Requested output length in seconds.
    """
    name: str
    cut_points: List[Tuple[float, float]]
    loop_points: List[Tuple[float, float, int]]
    fade_regions: List[Tuple[float, float]]
    target_length: float

    def calculate_resulting_length(self, original_length: float) -> float:
        """Resulting length after applying this strategy's cuts and loops."""
        result = original_length
        for start, end in self.cut_points:
            result -= (end - start)
        for start, end, repeat_count in self.loop_points:
            result += (end - start) * (repeat_count - 1)
        return result


def generate_trim_strategies(
    original_length: float,
    target_length: float,
    sections: Optional[List[Dict]] = None,
    downbeats: Optional[np.ndarray] = None,
    regenerate_seed: Optional[int] = None,
    num_strategies: int = 5,
    protected_regions: Optional[List[Tuple[float, float]]] = None,
    protect_ends: bool = True,
    max_cuts: int = 2,
) -> List[TrimStrategy]:
    """Build section-aligned trim strategies.

    Delegates section selection to :func:`plan_trims`. Each returned plan
    already has cut endpoints on section boundaries snapped to downbeats and at
    most ``max_cuts`` cuts, so we simply wrap it as a :class:`TrimStrategy`.

    ``protected_regions`` (parsed (start, end) spans) and ``protect_ends`` (the
    auto-protect toggle) flow to the planner so user/auto protection is honored.
    ``max_cuts`` is raised by the strict-length escalation to admit closer but
    more-fragmented cuts when the target demands it.

    When no section data is available (structure detection failed), falls back
    to a single centered cut of the required duration so the pipeline still
    produces output.
    """
    if sections:
        plans = plan_trims(
            sections, original_length, target_length,
            downbeats=downbeats, seed=regenerate_seed,
            max_cuts=max_cuts, num_plans=num_strategies,
            protected_regions=protected_regions, protect_ends=protect_ends,
        )
        strategies = [
            TrimStrategy(
                name=plan.name,
                cut_points=plan.cut_points,
                loop_points=[],
                fade_regions=[],
                target_length=target_length,
            )
            for plan in plans
        ]
        if strategies:
            return strategies

    return [_fallback_trim(original_length, target_length, downbeats)]


def _fallback_trim(
    original_length: float,
    target_length: float,
    downbeats: Optional[np.ndarray] = None,
) -> TrimStrategy:
    """Single centered cut removing the deficit, used when no sections exist."""
    deficit = max(0.0, original_length - target_length)
    mid = original_length / 2.0
    cut_start = snap_to_downbeat(max(0.0, mid - deficit / 2.0), downbeats)
    cut_end = snap_to_downbeat(cut_start + deficit, downbeats)
    return TrimStrategy(
        name="fallback-center-cut",
        cut_points=[(cut_start, cut_end)],
        loop_points=[],
        fade_regions=[],
        target_length=target_length,
    )


def generate_strategies(
    mode: str,
    original_length: float,
    target_length: float,
    sections: Optional[List[Dict]] = None,
    downbeats: Optional[np.ndarray] = None,
    regenerate_seed: int = None,
    num_strategies: int = 5,
    min_segment_duration: float = 10.0,
    protected_regions: Optional[List[Tuple[float, float]]] = None,
    protect_ends: bool = True,
    max_cuts: int = 2,
    max_repeats: int = 4,
    all_repeat_counts: bool = False,
) -> List[TrimStrategy]:
    """Route to the trim or extend engine based on ``mode``.

    Protection (``protected_regions``, ``protect_ends``) and the strict-length
    escalation knobs (``max_cuts`` for trim; ``max_repeats`` / ``all_repeat_counts``
    for extend) are forwarded to the relevant engine.

    Raises:
        ValueError: if ``mode`` is not "trim" or "extend".
    """
    if mode == "trim":
        return generate_trim_strategies(
            original_length=original_length,
            target_length=target_length,
            sections=sections,
            downbeats=downbeats,
            regenerate_seed=regenerate_seed,
            num_strategies=num_strategies,
            protected_regions=protected_regions,
            protect_ends=protect_ends,
            max_cuts=max_cuts,
        )
    elif mode == "extend":
        from src.extension_engine import generate_extension_strategies
        return generate_extension_strategies(
            original_length=original_length,
            target_length=target_length,
            sections=sections,
            downbeats=downbeats,
            regenerate_seed=regenerate_seed,
            num_strategies=num_strategies,
            min_segment_duration=min_segment_duration,
            protected_regions=protected_regions,
            max_repeats=max_repeats,
            all_repeat_counts=all_repeat_counts,
        )
    else:
        raise ValueError(f"Invalid mode: {mode}. Must be 'trim' or 'extend'.")
