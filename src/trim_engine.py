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
    prioritize_chorus_preservation: bool = True
) -> List[Tuple[float, float]]:
    """
    Select cuts prioritizing chorus preservation and smooth transitions.

    NEW V7 LOGIC:
    - Keep at least 1 chorus (preferably first occurrence)
    - Remove extra verses first
    - Remove extra choruses (2nd, 3rd occurrences) if needed
    - Never remove ALL choruses
    - Ensure smooth transitions with proper crossfades

    Args:
        clusters: List of cluster dicts with segment_times, avg_similarity
        sections: List of section dicts with start, end, label
        original_length: Original audio length
        target_removal: How much time to remove
        prioritize_chorus_preservation: If True, keep at least 1 chorus

    Returns:
        List of (start, end) cut tuples prioritized by section importance
    """
    # Collect all potential cuts with their section labels
    potential_cuts = []

    for cluster in clusters:
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

            # Assign priority based on section label
            if prioritize_chorus_preservation:
                if section_label == "chorus":
                    priority = 3  # Lower priority = cut later (keep choruses)
                elif section_label == "verse":
                    priority = 1  # Higher priority = cut first
                elif section_label == "bridge":
                    priority = 2  # Medium priority
                else:  # intro, outro, unknown
                    priority = 0  # Very low priority = don't cut unless necessary
            else:
                # Original behavior: prioritize middle region
                cut_center = (cut_start + cut_end) / 2
                middle_start = original_length * 0.2
                middle_end = original_length * 0.8

                if cut_center < middle_start or cut_center > middle_end:
                    priority = 0
                else:
                    center = original_length * 0.5
                    priority = 1.0 - abs(cut_center - center) / (center * 0.6)

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

    # Sort by priority (higher priority = cut first)
    # Within same priority, prefer cuts with higher similarity
    potential_cuts.sort(key=lambda x: (-x['priority'], -x['similarity']))

    # Select cuts until we reach target removal
    selected_cuts = []
    total_removed = 0.0

    for cut in potential_cuts:
        if total_removed >= target_removal:
            break

        selected_cuts.append((cut['start'], cut['end']))
        total_removed += cut['duration']

    return selected_cuts


def generate_strategy(
    strategy_type: str,
    clusters: List[Dict],
    original_length: float,
    target_length: float,
    buffer: float = 0.0,
    sections: Optional[List[Dict]] = None,
    downbeats: Optional[np.ndarray] = None,
    regenerate_seed: Optional[int] = None
) -> TrimStrategy:
    """
    Unified strategy generation with configurable parameters.

    Consolidates conservative/balanced/aggressive strategy generation into a single
    parameterized function to eliminate code duplication.

    Args:
        strategy_type: Type of strategy - "conservative", "balanced", or "aggressive"
        clusters: List of cluster dicts with segment_times, avg_similarity, duration
        original_length: Original audio length in seconds
        target_length: Target length in seconds
        buffer: Buffer in seconds to stay away from target (default: 0.0)
        sections: List of section dicts (for boundary alignment)
        downbeats: Array of downbeat times (for beat alignment)
        regenerate_seed: Optional seed for randomization

    Returns:
        TrimStrategy with specified approach

    Raises:
        ValueError: If strategy_type is not recognized
    """
    # Strategy-specific parameters: (max_gap, fade_duration, alignment_mode)
    STRATEGY_PARAMS = {
        "conservative": {
            "max_gap": 3.0,
            "fade_duration": ms_to_fade_duration(CROSSFADE_CONSERVATIVE_MS),
            "alignment": "section",  # Align to section boundaries
        },
        "balanced": {
            "max_gap": 2.0,
            "fade_duration": ms_to_fade_duration(CROSSFADE_BALANCED_MS),
            "alignment": "section",  # Align to section boundaries
        },
        "aggressive": {
            "max_gap": 1.0,
            "fade_duration": ms_to_fade_duration(CROSSFADE_AGGRESSIVE_MS),
            "alignment": "downbeat",  # Align to downbeats only (less conservative)
        },
    }

    if strategy_type not in STRATEGY_PARAMS:
        raise ValueError(f"Unknown strategy_type: {strategy_type}. Must be one of {list(STRATEGY_PARAMS.keys())}")

    params = STRATEGY_PARAMS[strategy_type]

    # Common initialization
    if regenerate_seed is not None:
        np.random.seed(regenerate_seed)

    if downbeats is None:
        downbeats = np.array([])
    if sections is None:
        sections = []

    # Calculate amount to remove with buffer
    amount_to_remove = max(0, original_length - target_length - buffer)

    # Select cuts from middle region with chorus preservation
    raw_cuts = select_middle_region_cuts(
        clusters, sections, original_length, amount_to_remove,
        prioritize_chorus_preservation=True
    )

    # Align cuts based on strategy
    aligned_cuts = []
    for cut_start, cut_end in raw_cuts:
        if params["alignment"] == "section":
            aligned = align_to_section_boundaries(cut_start, cut_end, sections, downbeats)
        else:  # downbeat
            aligned = align_to_downbeats(cut_start, cut_end, downbeats)
        aligned_cuts.append(aligned)

    # Merge adjacent cuts
    merged_cuts = merge_adjacent_cuts(aligned_cuts, max_gap=params["max_gap"])

    # Create fade regions
    fade_regions = [
        (cut_start - params["fade_duration"], cut_start + params["fade_duration"])
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
    num_strategies: int = 10
) -> List[TrimStrategy]:
    """
    Generate multiple diverse trim strategies with section-aware, back-to-back cutting.

    NEW IN V6:
    - Generate 10 diverse strategies (not just 3)
    - Varied aggressiveness levels (buffers from 0s to 4.5s)
    - Different random seeds for each strategy to ensure diversity
    - Mix of conservative, balanced, and aggressive approaches

    V5 FEATURES:
    - Section boundary alignment (no mid-verse/chorus cuts)
    - Back-to-back cut merging (continuous removal from middle)
    - Middle-region prioritization (radio edit feel)
    - Beat-aligned cutting on downbeats
    - Iterative refinement to ±15s

    Args:
        clusters: List of cluster dicts with segment_times, avg_similarity, duration
        original_length: Original audio length in seconds
        target_length: Target length in seconds
        sections: List of section dicts with start, end, label (from structure_analyzer)
        downbeats: Array of downbeat times (from structure_analyzer)
        regenerate_seed: Optional seed for randomization
        num_strategies: Number of strategies to generate (default: 10)

    Returns:
        List of TrimStrategy objects (default: 10 strategies with varied approaches)
    """
    strategies = []
    base_seed = regenerate_seed if regenerate_seed is not None else 0

    # Generate 10 diverse strategies with different parameters
    strategy_configs = [
        # Conservative variants (buffers: 3.0-4.5s)
        ("conservative", 0, 3.0),
        ("conservative", 1, 3.5),
        ("conservative", 2, 4.0),
        ("conservative", 3, 4.5),
        # Balanced variants (buffers: 1.5-2.5s)
        ("balanced", 4, 1.5),
        ("balanced", 5, 2.0),
        ("balanced", 6, 2.5),
        # Aggressive variants (buffers: 0.0-1.0s)
        ("aggressive", 7, 0.0),
        ("aggressive", 8, 0.5),
        ("aggressive", 9, 1.0),
    ]

    for strategy_type, seed_offset, buffer in strategy_configs:
        strategy_seed = base_seed + seed_offset

        if strategy_type == "conservative":
            # Manually adjust the buffer in conservative strategy
            strategy = generate_conservative_strategy_with_buffer(
                clusters, original_length, target_length,
                buffer=buffer,
                sections=sections,
                downbeats=downbeats,
                regenerate_seed=strategy_seed
            )
            strategy.name = f"conservative_{seed_offset+1}"
        elif strategy_type == "balanced":
            strategy = generate_balanced_strategy_with_buffer(
                clusters, original_length, target_length,
                buffer=buffer,
                sections=sections,
                downbeats=downbeats,
                regenerate_seed=strategy_seed
            )
            strategy.name = f"balanced_{seed_offset-3}"
        else:  # aggressive
            strategy = generate_aggressive_strategy_with_buffer(
                clusters, original_length, target_length,
                buffer=buffer,
                sections=sections,
                downbeats=downbeats,
                regenerate_seed=strategy_seed
            )
            strategy.name = f"aggressive_{seed_offset-6}"

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


def generate_conservative_strategy_with_buffer(
    clusters: List[Dict],
    original_length: float,
    target_length: float,
    buffer: float,
    sections: Optional[List[Dict]] = None,
    downbeats: Optional[np.ndarray] = None,
    regenerate_seed: int = None
) -> TrimStrategy:
    """Generate conservative strategy with custom buffer (delegates to generate_strategy)."""
    return generate_strategy(
        "conservative", clusters, original_length, target_length,
        buffer, sections, downbeats, regenerate_seed
    )


def generate_balanced_strategy_with_buffer(
    clusters: List[Dict],
    original_length: float,
    target_length: float,
    buffer: float,
    sections: Optional[List[Dict]] = None,
    downbeats: Optional[np.ndarray] = None,
    regenerate_seed: int = None
) -> TrimStrategy:
    """Generate balanced strategy with custom buffer (delegates to generate_strategy)."""
    return generate_strategy(
        "balanced", clusters, original_length, target_length,
        buffer, sections, downbeats, regenerate_seed
    )


def generate_aggressive_strategy_with_buffer(
    clusters: List[Dict],
    original_length: float,
    target_length: float,
    buffer: float,
    sections: Optional[List[Dict]] = None,
    downbeats: Optional[np.ndarray] = None,
    regenerate_seed: int = None
) -> TrimStrategy:
    """Generate aggressive strategy with custom buffer (delegates to generate_strategy)."""
    return generate_strategy(
        "aggressive", clusters, original_length, target_length,
        buffer, sections, downbeats, regenerate_seed
    )
