"""Extension engine module for generating audio extension strategies."""

from dataclasses import dataclass
from typing import List, Tuple, Dict, Optional
import numpy as np
from src.structure_analyzer import find_nearest_downbeat
from src.trim_engine import TrimStrategy, align_to_section_boundaries


def select_extension_sections(
    clusters: List[Dict],
    sections: List[Dict],
    original_length: float,
    target_addition: float,
    prioritize_chorus: bool = True,
    similarity_filter: float = 0.0,
    section_priority_weights: Optional[Dict[str, float]] = None,
    randomize_order: bool = False,
    random_seed: Optional[int] = None,
    max_repeats: Optional[int] = None
) -> List[Tuple[float, float, int]]:
    """
    Select sections to repeat for audio extension.

    Strategy:
    - Prioritize chorus sections (higher energy, more repetitive)
    - Use repeated segments from clusters (already similar)
    - Repeat sections in middle region (avoid intro/outro)
    - Align to section boundaries for seamless loops

    Returns:
        List of (start, end, repeat_count) tuples
    """
    if randomize_order and random_seed is not None:
        np.random.seed(random_seed)

    # Default weights: HIGHER priority = repeat first
    if section_priority_weights is None:
        section_priority_weights = {
            "chorus": 3.0,
            "verse": 2.0,
            "bridge": 1.5,
            "intro": 0.3,
            "outro": 0.3,
            "unknown": 1.0
        }

    # Collect potential sections to repeat
    potential_repeats = []

    for cluster in clusters:
        if cluster['avg_similarity'] < similarity_filter:
            continue

        segment_times = cluster['segment_times']
        if len(segment_times) < 1:
            continue

        for seg_start, seg_end in segment_times:
            duration = seg_end - seg_start

            if duration < 10.0:  # Skip short segments
                continue

            # Find section label
            section_label = "unknown"
            for section in sections:
                overlap_start = max(seg_start, section['start'])
                overlap_end = min(seg_end, section['end'])
                overlap = overlap_end - overlap_start

                if overlap > duration * 0.5:
                    section_label = section['label']
                    break

            priority = section_priority_weights.get(section_label, 1.0)

            # Avoid intro/outro regions
            middle_start = original_length * 0.15
            middle_end = original_length * 0.85
            seg_center = (seg_start + seg_end) / 2

            if seg_center < middle_start or seg_center > middle_end:
                priority *= 0.3

            potential_repeats.append({
                'start': seg_start,
                'end': seg_end,
                'duration': duration,
                'similarity': cluster['avg_similarity'],
                'section_label': section_label,
                'priority': priority
            })

    if not potential_repeats:
        return []

    # Sort by priority (HIGHER = repeat first)
    potential_repeats.sort(key=lambda x: (-x['priority'], -x['similarity']))

    # Apply randomization
    if randomize_order:
        from itertools import groupby
        grouped = []
        for priority, group in groupby(potential_repeats, key=lambda x: round(x['priority'] * 2) / 2):
            group_list = list(group)
            np.random.shuffle(group_list)
            grouped.extend(group_list)
        potential_repeats = grouped

    # Select sections and calculate repeat counts
    selected_loops = []
    total_added = 0.0

    for section in potential_repeats:
        if total_added >= target_addition:
            break

        duration = section['duration']
        remaining = target_addition - total_added
        repeat_count = max(1, int(np.ceil(remaining / duration)))

        if max_repeats is not None:
            repeat_count = min(repeat_count, max_repeats)

        selected_loops.append((section['start'], section['end'], repeat_count + 1))
        total_added += duration * repeat_count

    return selected_loops


def generate_extension_strategy(
    strategy_type: str,
    clusters: List[Dict],
    original_length: float,
    target_length: float,
    sections: Optional[List[Dict]] = None,
    downbeats: Optional[np.ndarray] = None,
    regenerate_seed: Optional[int] = None
) -> TrimStrategy:
    """
    Generate single extension strategy with specific parameters.

    5 distinct approaches:
    - best: High-quality sections, conservative repeats
    - diverse: Balanced with randomization
    - varied: More aggressive repeats
    - balanced: Middle ground
    - conservative: Minimal repeats

    Returns:
        TrimStrategy with loop_points populated, cut_points empty
    """
    # Validate: extension requires target > original
    if target_length <= original_length:
        raise ValueError(
            f"Extension requires target > original (got target={target_length:.1f}s, original={original_length:.1f}s)"
        )

    STRATEGY_CONFIGS = {
        "best": {
            "similarity_filter": 0.85,
            "section_weights": {"chorus": 3.5, "verse": 2.0, "bridge": 1.5, "intro": 0.2, "outro": 0.2, "unknown": 1.0},
            "max_repeats": 2,
            "randomize": False,
            "buffer": -2.0
        },
        "diverse": {
            "similarity_filter": 0.75,
            "section_weights": {"chorus": 3.0, "verse": 2.2, "bridge": 1.8, "intro": 0.3, "outro": 0.3, "unknown": 1.2},
            "max_repeats": 3,
            "randomize": True,
            "buffer": -1.0
        },
        "varied": {
            "similarity_filter": 0.70,
            "section_weights": {"chorus": 2.8, "verse": 2.5, "bridge": 2.0, "intro": 0.4, "outro": 0.4, "unknown": 1.5},
            "max_repeats": 4,
            "randomize": True,
            "buffer": 0.0
        },
        "balanced": {
            "similarity_filter": 0.80,
            "section_weights": {"chorus": 3.0, "verse": 2.0, "bridge": 1.5, "intro": 0.3, "outro": 0.3, "unknown": 1.0},
            "max_repeats": 3,
            "randomize": False,
            "buffer": -1.5
        },
        "conservative": {
            "similarity_filter": 0.88,
            "section_weights": {"chorus": 4.0, "verse": 1.8, "bridge": 1.2, "intro": 0.1, "outro": 0.1, "unknown": 0.8},
            "max_repeats": 1,
            "randomize": False,
            "buffer": -3.0
        },
    }

    if strategy_type not in STRATEGY_CONFIGS:
        raise ValueError(f"Unknown strategy_type: {strategy_type}")

    config = STRATEGY_CONFIGS[strategy_type]

    if downbeats is None:
        downbeats = np.array([])
    if sections is None:
        sections = []

    amount_to_add = max(0, target_length - original_length + config["buffer"])

    loop_points = select_extension_sections(
        clusters, sections, original_length, amount_to_add,
        prioritize_chorus=True,
        similarity_filter=config["similarity_filter"],
        section_priority_weights=config["section_weights"],
        randomize_order=config["randomize"],
        random_seed=regenerate_seed,
        max_repeats=config["max_repeats"]
    )

    # Align loop points to section boundaries
    aligned_loops = []
    for loop_start, loop_end, repeat_count in loop_points:
        if sections:
            aligned_start, aligned_end = align_to_section_boundaries(
                loop_start, loop_end, sections, downbeats
            )
        else:
            aligned_start = find_nearest_downbeat(loop_start, downbeats) if len(downbeats) > 0 else loop_start
            aligned_end = find_nearest_downbeat(loop_end, downbeats) if len(downbeats) > 0 else loop_end

        aligned_loops.append((aligned_start, aligned_end, repeat_count))

    # Note: Fade regions will be calculated during rendering (Task 3: apply_loops)
    # Crossfades are applied at actual loop boundaries when audio is rendered
    fade_regions = []

    return TrimStrategy(
        name=strategy_type,
        cut_points=[],
        loop_points=aligned_loops,
        fade_regions=fade_regions,
        target_length=target_length
    )


def generate_extension_strategies(
    clusters: List[Dict],
    original_length: float,
    target_length: float,
    sections: Optional[List[Dict]] = None,
    downbeats: Optional[np.ndarray] = None,
    regenerate_seed: int = None,
    num_strategies: int = 5
) -> List[TrimStrategy]:
    """
    Generate multiple diverse extension strategies.

    Returns:
        List of TrimStrategy objects with loop_points populated
    """
    strategy_types = ["best", "diverse", "varied", "balanced", "conservative"]
    strategies = []
    base_seed = regenerate_seed if regenerate_seed is not None else 0

    for i, strategy_type in enumerate(strategy_types[:num_strategies]):
        strategy_seed = base_seed + i

        strategy = generate_extension_strategy(
            strategy_type, clusters, original_length, target_length,
            sections=sections, downbeats=downbeats, regenerate_seed=strategy_seed
        )
        strategies.append(strategy)

    # Refine for ±15s constraint
    for strategy in strategies:
        refine_extension_for_length(
            strategy, original_length, target_length,
            clusters, sections, downbeats, tolerance=15.0
        )

    return strategies


def refine_extension_for_length(
    strategy: TrimStrategy,
    original_length: float,
    target_length: float,
    clusters: List[Dict],
    sections: Optional[List[Dict]],
    downbeats: Optional[np.ndarray],
    tolerance: float = 15.0,
    max_iterations: int = 3
) -> None:
    """
    Iteratively adjust extension strategy to meet length constraint.

    Modifies strategy in-place by adjusting repeat counts.
    """
    if downbeats is None:
        downbeats = np.array([])
    if sections is None:
        sections = []

    for iteration in range(max_iterations):
        result_length = strategy.calculate_resulting_length(original_length)
        error = result_length - target_length

        if abs(error) <= tolerance:
            break

        if error < 0:  # Too short
            if strategy.loop_points:
                shortest_idx = min(
                    range(len(strategy.loop_points)),
                    key=lambda i: strategy.loop_points[i][1] - strategy.loop_points[i][0]
                )
                start, end, count = strategy.loop_points[shortest_idx]
                strategy.loop_points[shortest_idx] = (start, end, count + 1)

        else:  # Too long
            if strategy.loop_points:
                max_repeat_idx = max(
                    range(len(strategy.loop_points)),
                    key=lambda i: strategy.loop_points[i][2]
                )
                start, end, count = strategy.loop_points[max_repeat_idx]
                if count > 2:
                    strategy.loop_points[max_repeat_idx] = (start, end, count - 1)
                else:
                    # Don't pop if it would create empty strategy
                    if len(strategy.loop_points) > 1:
                        strategy.loop_points.pop(max_repeat_idx)
