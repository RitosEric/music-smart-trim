"""Trim engine module for generating trim/extend strategies with section-aware cutting."""

from dataclasses import dataclass
from typing import List, Tuple, Dict, Optional
import numpy as np
from src.structure_analyzer import find_nearest_downbeat
from src.crossfade import (
    CROSSFADE_CONSERVATIVE_MS,
    CROSSFADE_BALANCED_MS,
    CROSSFADE_AGGRESSIVE_MS,
    ms_to_fade_duration
)


@dataclass
class TrimStrategy:
    """
    Represents a strategy for trimming/extending audio.

    Attributes:
        name: Name of the strategy (e.g., "conservative", "balanced", "aggressive")
        cut_points: List of (start_time, end_time) tuples for sections to remove
        loop_points: List of (start_time, end_time, repeat_count) tuples for sections to repeat
        fade_regions: List of (fade_start, fade_end) tuples for crossfade locations
        target_length: Target length in seconds
    """
    name: str
    cut_points: List[Tuple[float, float]]
    loop_points: List[Tuple[float, float, int]]
    fade_regions: List[Tuple[float, float]]
    target_length: float

    def calculate_resulting_length(self, original_length: float) -> float:
        """
        Calculate the resulting audio length after applying this strategy.

        Args:
            original_length: Original audio length in seconds

        Returns:
            Resulting length after cuts and loops
        """
        result = original_length

        # Subtract cut durations
        for start, end in self.cut_points:
            result -= (end - start)

        # Add loop durations × (repeat_count - 1)
        for start, end, repeat_count in self.loop_points:
            duration = end - start
            result += duration * (repeat_count - 1)

        return result


def align_to_section_boundaries(
    cut_start: float,
    cut_end: float,
    sections: List[Dict],
    downbeats: np.ndarray
) -> Tuple[float, float]:
    """
    Align cut points to section boundaries to avoid mid-section cuts.

    Strategy: Expand cut to encompass whole sections that overlap significantly.

    Args:
        cut_start: Proposed cut start time
        cut_end: Proposed cut end time
        sections: List of section dicts with start, end, label
        downbeats: Array of downbeat times for fine alignment

    Returns:
        Aligned (start, end) tuple
    """
    if not sections:
        # Fallback to downbeat alignment if no sections
        return align_to_downbeats(cut_start, cut_end, downbeats)

    # Find sections that overlap with the cut
    overlapping_sections = []
    for section in sections:
        # Check if section overlaps with proposed cut
        if not (section['end'] <= cut_start or section['start'] >= cut_end):
            overlapping_sections.append(section)

    if not overlapping_sections:
        # No overlap, use original cut points aligned to downbeats
        return align_to_downbeats(cut_start, cut_end, downbeats)

    # Strategy: Expand to encompass all overlapping sections
    # This ensures we cut whole verses/choruses, not partial ones
    aligned_start = min(s['start'] for s in overlapping_sections)
    aligned_end = max(s['end'] for s in overlapping_sections)

    # Fine-tune to nearest downbeats for clean cuts
    aligned_start = find_nearest_downbeat(aligned_start, downbeats)
    aligned_end = find_nearest_downbeat(aligned_end, downbeats)

    return (aligned_start, aligned_end)


def align_to_downbeats(
    cut_start: float,
    cut_end: float,
    downbeats: np.ndarray
) -> Tuple[float, float]:
    """
    Align cut points to nearest downbeats for beat-aligned editing.

    Args:
        cut_start: Proposed cut start time
        cut_end: Proposed cut end time
        downbeats: Array of downbeat times

    Returns:
        Aligned (start, end) tuple
    """
    if len(downbeats) == 0:
        return (cut_start, cut_end)

    aligned_start = find_nearest_downbeat(cut_start, downbeats)
    aligned_end = find_nearest_downbeat(cut_end, downbeats)

    return (aligned_start, aligned_end)


def merge_adjacent_cuts(
    cut_points: List[Tuple[float, float]],
    max_gap: float = 2.0
) -> List[Tuple[float, float]]:
    """
    Merge cut points that are close together or overlapping to create continuous removals.

    This implements the "back-to-back cuts" strategy for natural radio edit feel.

    Args:
        cut_points: List of (start, end) cut tuples
        max_gap: Maximum gap between cuts to merge (default: 2.0s)

    Returns:
        List of merged cut tuples
    """
    if not cut_points:
        return []

    # Sort by start time
    sorted_cuts = sorted(cut_points, key=lambda x: x[0])

    merged = [sorted_cuts[0]]

    for cut_start, cut_end in sorted_cuts[1:]:
        last_start, last_end = merged[-1]

        # Merge if overlapping OR close together
        if cut_start <= last_end + max_gap:
            merged[-1] = (last_start, max(cut_end, last_end))
        else:
            merged.append((cut_start, cut_end))

    return merged


def select_middle_region_cuts(
    clusters: List[Dict],
    sections: List[Dict],
    original_length: float,
    target_removal: float,
    prioritize_chorus_preservation: bool = True,
    similarity_filter: float = 0.0,
    section_priority_weights: Optional[Dict[str, float]] = None,
    randomize_order: bool = False,
    random_seed: Optional[int] = None,
    max_cuts: Optional[int] = None
) -> List[Tuple[float, float]]:
    """
    Select cuts prioritizing chorus preservation and smooth transitions.

    NEW V7 LOGIC:
    - Keep at least 1 chorus (preferably first occurrence)
    - Remove extra verses first
    - Remove extra choruses (2nd, 3rd occurrences) if needed
    - Never remove ALL choruses
    - Ensure smooth transitions with proper crossfades

    NEW DIVERSITY PARAMETERS:
    - similarity_filter: Minimum similarity threshold for considering cuts (applied to cluster avg)
    - section_priority_weights: Custom weights for section types (LOWER = cut first, HIGHER = keep)
    - randomize_order: Randomize selection within priority groups
    - random_seed: Seed for randomization
    - max_cuts: Maximum number of cuts to select

    Args:
        clusters: List of cluster dicts with segment_times, avg_similarity
        sections: List of section dicts with start, end, label
        original_length: Original audio length
        target_removal: How much time to remove
        prioritize_chorus_preservation: If True, keep at least 1 chorus
        similarity_filter: Only consider clusters with avg_similarity >= this threshold
        section_priority_weights: Custom priority weights (LOWER = cut first, HIGHER = keep)
        randomize_order: If True, randomize selection within same priority level
        random_seed: Random seed for reproducible randomization
        max_cuts: Maximum number of cuts to return (None = unlimited)

    Returns:
        List of (start, end) cut tuples prioritized by section importance
    """
    # Set random seed if randomization is enabled
    if randomize_order and random_seed is not None:
        np.random.seed(random_seed)

    # Default section weights (LOWER priority = cut first, HIGHER priority = keep)
    if section_priority_weights is None:
        section_priority_weights = {
            "verse": 1.0,
            "bridge": 2.0,
            "chorus": 3.0,
            "intro": 0.5,
            "outro": 0.5,
            "unknown": 1.5
        }

    # Collect all potential cuts with their section labels
    potential_cuts = []

    for cluster in clusters:
        # Apply similarity filter at cluster level
        if cluster['avg_similarity'] < similarity_filter:
            continue

        segment_times = cluster['segment_times']
        if len(segment_times) < 2:
            continue

        # Sort by start time
        sorted_segments = sorted(segment_times, key=lambda s: s[0])

        # Consider removing 2nd and later occurrences
        for i in range(1, len(sorted_segments)):
            cut_start, cut_end = sorted_segments[i]
            duration = cut_end - cut_start

            # Find which section this cut belongs to
            section_label = "unknown"
            section_index = -1
            for idx, section in enumerate(sections):
                # Check if cut overlaps significantly with this section
                overlap_start = max(cut_start, section['start'])
                overlap_end = min(cut_end, section['end'])
                overlap = overlap_end - overlap_start

                if overlap > duration * 0.5:  # >50% overlap
                    section_label = section['label']
                    section_index = idx
                    break

            # Get priority from section weights (LOWER = cut first)
            priority = section_priority_weights.get(section_label, 1.5)

            potential_cuts.append({
                'start': cut_start,
                'end': cut_end,
                'duration': duration,
                'similarity': cluster['avg_similarity'],
                'section_label': section_label,
                'section_index': section_index,
                'occurrence_index': i,  # 1st repeat, 2nd repeat, etc.
                'priority': priority
            })

    if not potential_cuts:
        return []

    # CHORUS PROTECTION: Count how many chorus cuts we have
    chorus_cuts = [c for c in potential_cuts if c['section_label'] == 'chorus']

    if prioritize_chorus_preservation and len(chorus_cuts) > 0:
        # Keep at least 1 chorus - mark first chorus occurrence as protected
        chorus_cuts_sorted = sorted(chorus_cuts, key=lambda x: x['start'])
        first_chorus = chorus_cuts_sorted[0]

        # Remove first chorus from potential cuts (protect it)
        potential_cuts = [c for c in potential_cuts if not (
            c['section_label'] == 'chorus' and
            c['start'] == first_chorus['start']
        )]

    # Sort by priority (LOWER priority = cut first)
    # Within same priority, prefer cuts with higher similarity
    potential_cuts.sort(key=lambda x: (x['priority'], -x['similarity']))

    # Apply randomization within priority groups if requested
    if randomize_order:
        # Group by priority level (rounded to 0.5)
        from itertools import groupby
        grouped = []
        for priority, group in groupby(potential_cuts, key=lambda x: round(x['priority'] * 2) / 2):
            group_list = list(group)
            np.random.shuffle(group_list)
            grouped.extend(group_list)
        potential_cuts = grouped

    # Select cuts until we reach target removal or max_cuts
    selected_cuts = []
    total_removed = 0.0

    for cut in potential_cuts:
        if total_removed >= target_removal:
            break
        if max_cuts is not None and len(selected_cuts) >= max_cuts:
            break

        selected_cuts.append((cut['start'], cut['end']))
        total_removed += cut['duration']

    return selected_cuts


def generate_strategy(
    strategy_type: str,
    clusters: List[Dict],
    original_length: float,
    target_length: float,
    sections: Optional[List[Dict]] = None,
    downbeats: Optional[np.ndarray] = None,
    regenerate_seed: Optional[int] = None
) -> TrimStrategy:
    """
    Unified strategy generation with truly diverse parameter configurations.

    Creates genuinely different strategies by varying:
    - Similarity filtering thresholds
    - Section priority weights
    - Cut merging aggressiveness
    - Length buffers
    - Alignment modes
    - Randomization

    Args:
        strategy_type: One of "best", "diverse", "varied", "balanced", "conservative"
        clusters: List of cluster dicts with segment_times, avg_similarity, duration
        original_length: Original audio length in seconds
        target_length: Target length in seconds
        sections: List of section dicts (for boundary alignment)
        downbeats: Array of downbeat times (for beat alignment)
        regenerate_seed: Optional seed for randomization

    Returns:
        TrimStrategy with specified approach

    Raises:
        ValueError: If strategy_type is not recognized
    """
    # Strategy-specific configurations with DIVERSE parameters
    # Note: In trim mode, LOWER priority weight = cut first, HIGHER = preserve
    # Expected order: conservative > best > balanced > diverse > varied
    STRATEGY_CONFIGS = {
        "best": {
            "similarity_filter": 0.80,  # High-quality cuts only
            "section_weights": {"verse": 1.3, "bridge": 2.5, "chorus": 3.0, "intro": 0.3, "outro": 0.3, "unknown": 1.8},
            "max_gap": 3.0,
            "buffer": 3.0,  # Stay 3s away from target (longer result)
            "alignment": "section",
            "randomize": False,
            "max_cuts": 2  # Fewer cuts for cleaner result
        },
        "diverse": {
            "similarity_filter": 0.72,  # Lower threshold for more options
            "section_weights": {"verse": 0.9, "bridge": 1.8, "chorus": 3.2, "intro": 0.4, "outro": 0.4, "unknown": 1.3},
            "max_gap": 2.5,
            "buffer": 1.5,  # Moderate distance from target
            "alignment": "section",
            "randomize": True,  # Add randomization
            "max_cuts": None
        },
        "varied": {
            "similarity_filter": 0.65,  # Lowest threshold = most cut options
            "section_weights": {"verse": 0.7, "bridge": 1.2, "chorus": 2.8, "intro": 0.35, "outro": 0.35, "unknown": 1.0},
            "max_gap": 1.0,  # Aggressive merging
            "buffer": 0.5,  # Very close to target
            "alignment": "downbeat",  # Different alignment mode
            "randomize": True,
            "max_cuts": None  # Allow more cuts
        },
        "balanced": {
            "similarity_filter": 0.75,
            "section_weights": {"verse": 1.1, "bridge": 2.1, "chorus": 3.0, "intro": 0.5, "outro": 0.5, "unknown": 1.6},
            "max_gap": 2.0,
            "buffer": 2.0,  # Moderate buffer
            "alignment": "section",
            "randomize": False,
            "max_cuts": 3  # Moderate number of cuts
        },
        "conservative": {
            "similarity_filter": 0.85,  # Very high quality only
            "section_weights": {"verse": 1.5, "bridge": 2.8, "chorus": 4.0, "intro": 0.2, "outro": 0.2, "unknown": 2.0},
            "max_gap": 4.0,  # Maximum merging
            "buffer": 4.5,  # Stay well away from target (longest result)
            "alignment": "section",
            "randomize": False,
            "max_cuts": 1  # Fewest cuts - single long removal
        },
    }

    if strategy_type not in STRATEGY_CONFIGS:
        raise ValueError(f"Unknown strategy_type: {strategy_type}. Must be one of {list(STRATEGY_CONFIGS.keys())}")

    config = STRATEGY_CONFIGS[strategy_type]

    # Common initialization
    if downbeats is None:
        downbeats = np.array([])
    if sections is None:
        sections = []

    # Calculate amount to remove with buffer
    amount_to_remove = max(0, original_length - target_length - config["buffer"])

    # Select cuts with strategy-specific parameters
    raw_cuts = select_middle_region_cuts(
        clusters, sections, original_length, amount_to_remove,
        prioritize_chorus_preservation=True,
        similarity_filter=config["similarity_filter"],
        section_priority_weights=config["section_weights"],
        randomize_order=config["randomize"],
        random_seed=regenerate_seed,
        max_cuts=config["max_cuts"]
    )

    # Align cuts based on strategy
    aligned_cuts = []
    for cut_start, cut_end in raw_cuts:
        if config["alignment"] == "section":
            aligned = align_to_section_boundaries(cut_start, cut_end, sections, downbeats)
        else:  # downbeat
            aligned = align_to_downbeats(cut_start, cut_end, downbeats)
        aligned_cuts.append(aligned)

    # Merge adjacent cuts
    merged_cuts = merge_adjacent_cuts(aligned_cuts, max_gap=config["max_gap"])

    # Create fade regions (use standard 500ms fade)
    fade_duration = ms_to_fade_duration(500)  # Standard 500ms crossfade
    fade_regions = [
        (cut_start - fade_duration, cut_start + fade_duration)
        for cut_start, _ in merged_cuts
    ]

    return TrimStrategy(
        name=strategy_type,
        cut_points=merged_cuts,
        loop_points=[],
        fade_regions=fade_regions,
        target_length=target_length
    )




def generate_trim_strategies(
    clusters: List[Dict],
    original_length: float,
    target_length: float,
    sections: Optional[List[Dict]] = None,
    downbeats: Optional[np.ndarray] = None,
    regenerate_seed: int = None,
    num_strategies: int = 5
) -> List[TrimStrategy]:
    """
    Generate multiple diverse trim strategies with truly different approaches.

    NEW IN V8 (BUG FIX):
    - Generate 5 TRULY diverse strategies (not 10 identical ones)
    - Each strategy uses different parameter configurations:
      * best: High-quality cuts, conservative merging, longer result
      * diverse: Balanced with randomization for variety
      * varied: Alternative patterns, aggressive merging, closer to target
      * balanced: Middle ground approach
      * conservative: Maximum structure preservation, fewest cuts
    - Different similarity filters, section weights, merging strategies
    - Real diversity in cut patterns and output lengths

    V7 FEATURES:
    - Section boundary alignment (no mid-verse/chorus cuts)
    - Chorus preservation (keep at least 1 chorus)
    - Back-to-back cut merging (continuous removal from middle)
    - Beat-aligned cutting on downbeats
    - Iterative refinement to ±15s

    Args:
        clusters: List of cluster dicts with segment_times, avg_similarity, duration
        original_length: Original audio length in seconds
        target_length: Target length in seconds
        sections: List of section dicts with start, end, label (from structure_analyzer)
        downbeats: Array of downbeat times (from structure_analyzer)
        regenerate_seed: Optional seed for randomization
        num_strategies: Number of strategies to generate (default: 5)

    Returns:
        List of TrimStrategy objects with genuinely different approaches
    """
    # Define strategy types with descriptive names
    strategy_types = ["best", "diverse", "varied", "balanced", "conservative"]

    strategies = []
    base_seed = regenerate_seed if regenerate_seed is not None else 0

    # Generate strategies with truly different configurations
    for i, strategy_type in enumerate(strategy_types[:num_strategies]):
        strategy_seed = base_seed + i

        strategy = generate_strategy(
            strategy_type,
            clusters,
            original_length,
            target_length,
            sections=sections,
            downbeats=downbeats,
            regenerate_seed=strategy_seed
        )

        strategies.append(strategy)

    # Iteratively refine all strategies to meet ±15s constraint
    for strategy in strategies:
        refine_strategy_for_length(strategy, original_length, target_length,
                                   clusters, sections, downbeats, tolerance=15.0)

    return strategies


def refine_strategy_for_length(
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
    Iteratively adjust strategy to meet length constraint within tolerance.

    Modifies strategy in-place by adding/removing cuts until within ±tolerance.

    Args:
        strategy: TrimStrategy to refine
        original_length: Original audio length
        target_length: Target length in seconds
        clusters: Available segment clusters for additional cuts
        sections: Section information for alignment
        downbeats: Downbeat times for alignment
        tolerance: Maximum acceptable error (default: 15.0s)
        max_iterations: Maximum refinement iterations
    """
    if downbeats is None:
        downbeats = np.array([])
    if sections is None:
        sections = []

    for iteration in range(max_iterations):
        result_length = strategy.calculate_resulting_length(original_length)
        error = result_length - target_length

        if abs(error) <= tolerance:
            break  # Within tolerance, done

        if error > 0:  # Too long, need more cuts
            # Find segments not yet cut
            existing_cuts = set(strategy.cut_points)

            # Get all potential segments from clusters
            potential_cuts = []
            for cluster in clusters:
                for seg_start, seg_end in cluster['segment_times']:
                    # Skip if this segment overlaps with existing cuts
                    overlaps = any(
                        not (seg_end <= cut_start or seg_start >= cut_end)
                        for cut_start, cut_end in existing_cuts
                    )
                    if not overlaps:
                        duration = seg_end - seg_start
                        potential_cuts.append((seg_start, seg_end, duration, cluster['avg_similarity']))

            if not potential_cuts:
                break  # No more cuts available

            # Sort by similarity (best candidates first), then by size (prefer cuts close to error)
            potential_cuts.sort(key=lambda x: (-x[3], abs(x[2] - error)))

            # Add best cut
            best_cut = potential_cuts[0]
            cut_start, cut_end = best_cut[0], best_cut[1]

            # Align to sections/downbeats
            if sections:
                cut_start, cut_end = align_to_section_boundaries(cut_start, cut_end, sections, downbeats)
            else:
                cut_start, cut_end = align_to_downbeats(cut_start, cut_end, downbeats)

            strategy.cut_points.append((cut_start, cut_end))

            # Add fade region
            fade_duration = 0.075  # Standard fade
            strategy.fade_regions.append((cut_start - fade_duration, cut_start + fade_duration))

        else:  # Too short, reduce cuts
            if not strategy.cut_points:
                break  # No cuts to remove

            # Remove smallest cut
            smallest_idx = min(range(len(strategy.cut_points)),
                             key=lambda i: strategy.cut_points[i][1] - strategy.cut_points[i][0])

            strategy.cut_points.pop(smallest_idx)
            if smallest_idx < len(strategy.fade_regions):
                strategy.fade_regions.pop(smallest_idx)

    # Final check: if still > tolerance, force trim to exact length
    result_length = strategy.calculate_resulting_length(original_length)
    error = result_length - target_length

    if error > tolerance:
        # Last resort: add small trim at end (before outro protection)
        # Find a safe spot in middle region to trim excess
        middle_start = original_length * 0.4
        middle_end = original_length * 0.6

        # Add a small cut in middle to hit target exactly
        trim_start = middle_start
        trim_end = middle_start + (error - tolerance + 2.0)  # Remove excess + small buffer

        if sections:
            trim_start, trim_end = align_to_section_boundaries(trim_start, trim_end, sections, downbeats)

        strategy.cut_points.append((trim_start, trim_end))
        strategy.fade_regions.append((trim_start - 0.05, trim_start + 0.05))


def generate_strategies(
    mode: str,
    clusters: List[Dict],
    original_length: float,
    target_length: float,
    sections: Optional[List[Dict]] = None,
    downbeats: Optional[np.ndarray] = None,
    regenerate_seed: int = None,
    num_strategies: int = 5
) -> List[TrimStrategy]:
    """
    Unified interface for generating trim or extension strategies.

    Routes to the appropriate implementation based on mode.

    Args:
        mode: "trim" for trimming strategies, "extend" for extension strategies
        clusters: List of segment cluster dicts
        original_length: Original audio length in seconds
        target_length: Target audio length in seconds
        sections: Optional list of section dicts with start, end, label
        downbeats: Optional array of downbeat times
        regenerate_seed: Optional seed for reproducible randomization
        num_strategies: Number of strategies to generate (default: 5)

    Returns:
        List of TrimStrategy objects

    Raises:
        ValueError: If mode is not "trim" or "extend"
    """
    if mode == "trim":
        return generate_trim_strategies(
            clusters=clusters,
            original_length=original_length,
            target_length=target_length,
            sections=sections,
            downbeats=downbeats,
            regenerate_seed=regenerate_seed,
            num_strategies=num_strategies
        )
    elif mode == "extend":
        from src.extension_engine import generate_extension_strategies
        return generate_extension_strategies(
            clusters=clusters,
            original_length=original_length,
            target_length=target_length,
            sections=sections,
            downbeats=downbeats,
            regenerate_seed=regenerate_seed,
            num_strategies=num_strategies
        )
    else:
        raise ValueError(f"Invalid mode: {mode}. Must be 'trim' or 'extend'.")


