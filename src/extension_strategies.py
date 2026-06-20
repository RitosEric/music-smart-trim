"""
Diverse extension strategy generation.

This module generates multiple truly different extension strategies by varying
section selection methods, not just random seeds.
"""

from typing import List, Dict, Optional, Tuple
import numpy as np
from src.trim_engine import (
    TrimStrategy, score_section_repeatability, find_nearest_downbeat,
    ms_to_fade_duration, CROSSFADE_BALANCED_MS
)


def generate_diverse_extension_strategies(
    original_length: float,
    target_length: float,
    sections: List[Dict],
    downbeats: np.ndarray,
    audio_data: np.ndarray,
    sample_rate: int,
    num_strategies: int = 5
) -> List[TrimStrategy]:
    """
    Generate truly diverse extension strategies using different selection methods.

    Strategy diversity methods:
    1. Best-first: Always pick highest-scoring sections
    2. Diversity-focused: Alternate between high/medium scoring sections
    3. Duration-balanced: Prefer sections of different lengths
    4. Position-varied: Pick sections from different song positions
    5. Energy-focused: Weight energy consistency higher

    Args:
        original_length: Original audio length in seconds
        target_length: Target length (must be > original)
        sections: List of section dicts
        downbeats: Array of downbeat times
        audio_data: Audio data
        sample_rate: Sample rate
        num_strategies: Number of diverse strategies to generate

    Returns:
        List of diverse TrimStrategy objects
    """
    if target_length <= original_length:
        raise ValueError(f"Extension requires target > original ({target_length} <= {original_length})")

    extension_needed = target_length - original_length
    fade_duration = ms_to_fade_duration(CROSSFADE_BALANCED_MS)

    # Score all sections
    section_scores = []
    for section in sections:
        score = score_section_repeatability(section, audio_data, sample_rate, sections)
        section_scores.append({
            'section': section,
            'score': score,
            'duration': section['end'] - section['start'],
            'position': section['start'] / original_length,
            'label': section.get('label', 'unknown')
        })

    if not section_scores:
        return []

    strategies = []

    # Strategy 1: Best-first (always pick highest scoring)
    strategy1 = _generate_best_first_strategy(
        section_scores, extension_needed, original_length, downbeats, fade_duration
    )
    if strategy1:
        strategy1.name = "extension_best"
        strategies.append(strategy1)

    # Strategy 2: Diversity-focused (alternate high/medium scoring)
    strategy2 = _generate_diversity_strategy(
        section_scores, extension_needed, original_length, downbeats, fade_duration
    )
    if strategy2 and not _is_identical(strategy2, strategies):
        strategy2.name = "extension_diverse"
        strategies.append(strategy2)

    # Strategy 3: Duration-balanced (prefer varied section lengths)
    strategy3 = _generate_duration_balanced_strategy(
        section_scores, extension_needed, original_length, downbeats, fade_duration
    )
    if strategy3 and not _is_identical(strategy3, strategies):
        strategy3.name = "extension_balanced"
        strategies.append(strategy3)

    # Strategy 4: Position-varied (pick from different positions)
    strategy4 = _generate_position_varied_strategy(
        section_scores, extension_needed, original_length, downbeats, fade_duration
    )
    if strategy4 and not _is_identical(strategy4, strategies):
        strategy4.name = "extension_varied"
        strategies.append(strategy4)

    # Strategy 5: Conservative (fewer, longer repeats)
    strategy5 = _generate_conservative_strategy(
        section_scores, extension_needed, original_length, downbeats, fade_duration
    )
    if strategy5 and not _is_identical(strategy5, strategies):
        strategy5.name = "extension_conservative"
        strategies.append(strategy5)

    return strategies[:num_strategies]


def _generate_best_first_strategy(
    section_scores: List[Dict],
    extension_needed: float,
    original_length: float,
    downbeats: np.ndarray,
    fade_duration: float
) -> Optional[TrimStrategy]:
    """Generate strategy by always picking highest-scoring sections."""
    sorted_sections = sorted(section_scores, key=lambda x: x['score'], reverse=True)

    loop_points = []
    total_extension = 0.0
    used_sections = {}  # Track usage count

    MAX_REPEATS = 3

    for candidate in sorted_sections:
        section = candidate['section']
        section_id = f"{section['start']}-{section['end']}"

        # Keep adding this section until we hit max repeats or fill extension
        while total_extension < extension_needed:
            if used_sections.get(section_id, 0) >= MAX_REPEATS:
                break

            duration = candidate['duration']
            if duration > (extension_needed - total_extension) * 1.3:
                break

            # Add loop
            loop_start = _align_to_downbeat(section['start'], downbeats)
            loop_end = _align_to_downbeat(section['end'], downbeats)
            loop_points.append((loop_start, loop_end, 2))

            total_extension += (loop_end - loop_start)
            used_sections[section_id] = used_sections.get(section_id, 0) + 1

        if total_extension >= extension_needed * 0.9:  # Within 90% is good enough
            break

    if not loop_points:
        return None

    fade_regions = [(start - fade_duration, start + fade_duration) for start, _, _ in loop_points]
    return TrimStrategy(
        name="extension_best",
        cut_points=[],
        loop_points=loop_points,
        fade_regions=fade_regions,
        target_length=original_length + total_extension
    )


def _generate_diversity_strategy(
    section_scores: List[Dict],
    extension_needed: float,
    original_length: float,
    downbeats: np.ndarray,
    fade_duration: float
) -> Optional[TrimStrategy]:
    """Generate strategy by alternating between high and medium-scoring sections."""
    sorted_sections = sorted(section_scores, key=lambda x: x['score'], reverse=True)

    if len(sorted_sections) < 2:
        return None

    # Split into tiers
    top_tier = sorted_sections[:max(1, len(sorted_sections) // 3)]
    mid_tier = sorted_sections[len(sorted_sections) // 3:]

    loop_points = []
    total_extension = 0.0
    use_top = True

    while total_extension < extension_needed:
        tier = top_tier if use_top else mid_tier
        if not tier:
            tier = top_tier if not use_top else mid_tier

        candidate = tier[0]
        duration = candidate['duration']

        if duration > (extension_needed - total_extension) * 1.3:
            break

        section = candidate['section']
        loop_start = _align_to_downbeat(section['start'], downbeats)
        loop_end = _align_to_downbeat(section['end'], downbeats)
        loop_points.append((loop_start, loop_end, 2))

        total_extension += (loop_end - loop_start)
        use_top = not use_top  # Alternate

        if total_extension >= extension_needed * 0.9:
            break

    if not loop_points:
        return None

    fade_regions = [(start - fade_duration, start + fade_duration) for start, _, _ in loop_points]
    return TrimStrategy(
        name="extension_diverse",
        cut_points=[],
        loop_points=loop_points,
        fade_regions=fade_regions,
        target_length=original_length + total_extension
    )


def _generate_duration_balanced_strategy(
    section_scores: List[Dict],
    extension_needed: float,
    original_length: float,
    downbeats: np.ndarray,
    fade_duration: float
) -> Optional[TrimStrategy]:
    """Generate strategy preferring sections of varied durations."""
    # Sort by score, but prefer varied durations
    sorted_sections = sorted(section_scores, key=lambda x: x['score'], reverse=True)

    loop_points = []
    total_extension = 0.0
    last_duration = None

    for candidate in sorted_sections:
        if total_extension >= extension_needed:
            break

        duration = candidate['duration']

        # Skip if too similar to last duration (within 3 seconds)
        if last_duration and abs(duration - last_duration) < 3.0:
            continue

        if duration > (extension_needed - total_extension) * 1.3:
            continue

        section = candidate['section']
        loop_start = _align_to_downbeat(section['start'], downbeats)
        loop_end = _align_to_downbeat(section['end'], downbeats)
        loop_points.append((loop_start, loop_end, 2))

        total_extension += (loop_end - loop_start)
        last_duration = duration

    if not loop_points:
        return None

    fade_regions = [(start - fade_duration, start + fade_duration) for start, _, _ in loop_points]
    return TrimStrategy(
        name="extension_balanced",
        cut_points=[],
        loop_points=loop_points,
        fade_regions=fade_regions,
        target_length=original_length + total_extension
    )


def _generate_position_varied_strategy(
    section_scores: List[Dict],
    extension_needed: float,
    original_length: float,
    downbeats: np.ndarray,
    fade_duration: float
) -> Optional[TrimStrategy]:
    """Generate strategy picking sections from different song positions."""
    # Sort by position, then by score
    sorted_sections = sorted(section_scores, key=lambda x: (x['position'], -x['score']))

    loop_points = []
    total_extension = 0.0
    used_positions = []

    for candidate in sorted_sections:
        if total_extension >= extension_needed:
            break

        position = candidate['position']

        # Skip if position too close to already used positions (within 20%)
        if any(abs(position - used_pos) < 0.2 for used_pos in used_positions):
            continue

        duration = candidate['duration']
        if duration > (extension_needed - total_extension) * 1.3:
            continue

        section = candidate['section']
        loop_start = _align_to_downbeat(section['start'], downbeats)
        loop_end = _align_to_downbeat(section['end'], downbeats)
        loop_points.append((loop_start, loop_end, 2))

        total_extension += (loop_end - loop_start)
        used_positions.append(position)

    if not loop_points:
        return None

    fade_regions = [(start - fade_duration, start + fade_duration) for start, _, _ in loop_points]
    return TrimStrategy(
        name="extension_varied",
        cut_points=[],
        loop_points=loop_points,
        fade_regions=fade_regions,
        target_length=original_length + total_extension
    )


def _generate_conservative_strategy(
    section_scores: List[Dict],
    extension_needed: float,
    original_length: float,
    downbeats: np.ndarray,
    fade_duration: float
) -> Optional[TrimStrategy]:
    """Generate conservative strategy with fewer, higher-quality loops."""
    # Only use top-scoring sections
    sorted_sections = sorted(section_scores, key=lambda x: x['score'], reverse=True)
    top_sections = sorted_sections[:max(1, len(sorted_sections) // 4)]

    loop_points = []
    total_extension = 0.0

    MAX_LOOPS = 2  # Conservative: only 2 loops total

    for candidate in top_sections:
        if len(loop_points) >= MAX_LOOPS:
            break

        if total_extension >= extension_needed:
            break

        duration = candidate['duration']
        if duration > (extension_needed - total_extension) * 1.3:
            continue

        section = candidate['section']
        loop_start = _align_to_downbeat(section['start'], downbeats)
        loop_end = _align_to_downbeat(section['end'], downbeats)

        # Conservative: repeat more times per loop (3x instead of 2x)
        loop_points.append((loop_start, loop_end, 3))

        total_extension += (loop_end - loop_start) * 2  # 3x means 2 extra copies

    if not loop_points:
        return None

    fade_regions = [(start - fade_duration, start + fade_duration) for start, _, _ in loop_points]
    return TrimStrategy(
        name="extension_conservative",
        cut_points=[],
        loop_points=loop_points,
        fade_regions=fade_regions,
        target_length=original_length + total_extension
    )


def _align_to_downbeat(time: float, downbeats: np.ndarray) -> float:
    """Align time to nearest downbeat."""
    if len(downbeats) == 0:
        return time
    return find_nearest_downbeat(time, downbeats)


def _is_identical(strategy: TrimStrategy, existing_strategies: List[TrimStrategy]) -> bool:
    """Check if strategy is identical to any existing strategy."""
    for existing in existing_strategies:
        if set(strategy.loop_points) == set(existing.loop_points):
            return True
    return False
