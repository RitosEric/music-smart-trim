"""Trim engine module for generating trim/extend strategies."""

from dataclasses import dataclass
from typing import List, Tuple, Dict
import numpy as np


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


def generate_conservative_strategy(
    clusters: List[Dict],
    original_length: float,
    target_length: float,
    regenerate_seed: int = None
) -> TrimStrategy:
    """
    Generate conservative strategy with minimal cuts and gentle crossfades.

    Strategy:
    - Sort clusters by similarity (highest first)
    - Remove 2nd occurrence of each cluster
    - Use 5s buffer to stay conservative
    - Use gentle crossfades: 300ms (±0.15s)

    Args:
        clusters: List of cluster dicts with segment_times, avg_similarity, duration
        original_length: Original audio length in seconds
        target_length: Target length in seconds
        regenerate_seed: Optional seed for randomization

    Returns:
        TrimStrategy with conservative approach
    """
    if regenerate_seed is not None:
        np.random.seed(regenerate_seed)

    # Sort clusters by similarity (highest first) for conservative approach
    sorted_clusters = sorted(clusters, key=lambda c: c['avg_similarity'], reverse=True)

    cut_points = []
    fade_regions = []
    fade_duration = 0.15  # ±0.15s = 300ms total

    # Calculate how much to remove (with 5s buffer)
    amount_to_remove = original_length - target_length - 5.0

    total_removed = 0.0

    for cluster in sorted_clusters:
        if total_removed >= amount_to_remove:
            break

        segment_times = cluster['segment_times']
        if len(segment_times) < 2:
            continue

        # Sort segment times by start time
        sorted_segments = sorted(segment_times, key=lambda s: s[0])

        # Remove 2nd occurrence (conservative)
        if len(sorted_segments) >= 2:
            cut_start, cut_end = sorted_segments[1]
            cut_points.append((cut_start, cut_end))

            # Add fade region: ±0.15s around cut point
            fade_regions.append((cut_start - fade_duration, cut_start + fade_duration))

            total_removed += (cut_end - cut_start)

    return TrimStrategy(
        name="conservative",
        cut_points=cut_points,
        loop_points=[],
        fade_regions=fade_regions,
        target_length=target_length
    )


def generate_balanced_strategy(
    clusters: List[Dict],
    original_length: float,
    target_length: float,
    regenerate_seed: int = None
) -> TrimStrategy:
    """
    Generate balanced strategy with moderate cuts and standard crossfades.

    Strategy:
    - Remove multiple occurrences from clusters
    - Use 3s buffer for moderate approach
    - Use standard crossfades: 150ms (±0.075s)

    Args:
        clusters: List of cluster dicts with segment_times, avg_similarity, duration
        original_length: Original audio length in seconds
        target_length: Target length in seconds
        regenerate_seed: Optional seed for randomization

    Returns:
        TrimStrategy with balanced approach
    """
    if regenerate_seed is not None:
        np.random.seed(regenerate_seed)

    # Sort clusters by similarity (highest first)
    sorted_clusters = sorted(clusters, key=lambda c: c['avg_similarity'], reverse=True)

    cut_points = []
    fade_regions = []
    fade_duration = 0.075  # ±0.075s = 150ms total

    # Calculate how much to remove (with 3s buffer)
    amount_to_remove = original_length - target_length - 3.0

    total_removed = 0.0

    for cluster in sorted_clusters:
        if total_removed >= amount_to_remove:
            break

        segment_times = cluster['segment_times']
        if len(segment_times) < 2:
            continue

        # Sort segment times by start time
        sorted_segments = sorted(segment_times, key=lambda s: s[0])

        # Remove multiple occurrences (all but first)
        for i in range(1, len(sorted_segments)):
            if total_removed >= amount_to_remove:
                break

            cut_start, cut_end = sorted_segments[i]
            cut_points.append((cut_start, cut_end))

            # Add fade region: ±0.075s around cut point
            fade_regions.append((cut_start - fade_duration, cut_start + fade_duration))

            total_removed += (cut_end - cut_start)

    return TrimStrategy(
        name="balanced",
        cut_points=cut_points,
        loop_points=[],
        fade_regions=fade_regions,
        target_length=target_length
    )


def generate_aggressive_strategy(
    clusters: List[Dict],
    original_length: float,
    target_length: float,
    regenerate_seed: int = None
) -> TrimStrategy:
    """
    Generate aggressive strategy with maximum cuts and short crossfades.

    Strategy:
    - Remove all but first occurrence from each cluster
    - Use 1s buffer for aggressive approach
    - Use short crossfades: 75ms (±0.0375s)

    Args:
        clusters: List of cluster dicts with segment_times, avg_similarity, duration
        original_length: Original audio length in seconds
        target_length: Target length in seconds
        regenerate_seed: Optional seed for randomization

    Returns:
        TrimStrategy with aggressive approach
    """
    if regenerate_seed is not None:
        np.random.seed(regenerate_seed)

    # Sort clusters by similarity (highest first)
    sorted_clusters = sorted(clusters, key=lambda c: c['avg_similarity'], reverse=True)

    cut_points = []
    fade_regions = []
    fade_duration = 0.0375  # ±0.0375s = 75ms total

    # Calculate how much to remove (with 1s buffer)
    amount_to_remove = original_length - target_length - 1.0

    total_removed = 0.0

    for cluster in sorted_clusters:
        if total_removed >= amount_to_remove:
            break

        segment_times = cluster['segment_times']
        if len(segment_times) < 2:
            continue

        # Sort segment times by start time
        sorted_segments = sorted(segment_times, key=lambda s: s[0])

        # Remove all but first occurrence (aggressive)
        for i in range(1, len(sorted_segments)):
            if total_removed >= amount_to_remove:
                break

            cut_start, cut_end = sorted_segments[i]
            cut_points.append((cut_start, cut_end))

            # Add fade region: ±0.0375s around cut point
            fade_regions.append((cut_start - fade_duration, cut_start + fade_duration))

            total_removed += (cut_end - cut_start)

    return TrimStrategy(
        name="aggressive",
        cut_points=cut_points,
        loop_points=[],
        fade_regions=fade_regions,
        target_length=target_length
    )


def generate_trim_strategies(
    clusters: List[Dict],
    original_length: float,
    target_length: float,
    regenerate_seed: int = None
) -> List[TrimStrategy]:
    """
    Generate all three trim strategies and enforce ±15s constraint.

    Generates conservative, balanced, and aggressive strategies.
    If any strategy exceeds ±15s error, adds fade-out cut from target_length to original_length.
    Uses regenerate_seed for variety in cluster shuffling.

    Args:
        clusters: List of cluster dicts with segment_times, avg_similarity, duration
        original_length: Original audio length in seconds
        target_length: Target length in seconds
        regenerate_seed: Optional seed for randomization to create variety

    Returns:
        List of 3 TrimStrategy objects (conservative, balanced, aggressive)
    """
    strategies = []

    # Generate all three strategies with different seeds for variety
    conservative = generate_conservative_strategy(
        clusters, original_length, target_length,
        regenerate_seed=regenerate_seed if regenerate_seed is not None else None
    )
    balanced = generate_balanced_strategy(
        clusters, original_length, target_length,
        regenerate_seed=(regenerate_seed + 1) if regenerate_seed is not None else None
    )
    aggressive = generate_aggressive_strategy(
        clusters, original_length, target_length,
        regenerate_seed=(regenerate_seed + 2) if regenerate_seed is not None else None
    )

    strategies = [conservative, balanced, aggressive]

    # Enforce ±15s constraint with fade-out fallback
    for strategy in strategies:
        result_length = strategy.calculate_resulting_length(original_length)
        error = abs(result_length - target_length)

        if error > 15.0:
            # Add fade-out cut from target_length to original_length
            # This ensures we hit the target exactly
            additional_cut_needed = result_length - target_length

            if additional_cut_needed > 0:
                # Need to remove more - add fade-out at end
                fade_start = target_length
                fade_end = target_length + additional_cut_needed
                strategy.cut_points.append((fade_start, fade_end))
                # Add a small fade region for the fade-out
                strategy.fade_regions.append((fade_start - 0.1, fade_start + 0.1))

    return strategies
