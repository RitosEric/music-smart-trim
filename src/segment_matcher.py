"""Protected-region parsing for trim/extend.

Reduced to timestamp parsing and overlap merging. The old similarity-based
segment clustering (and its scipy dependency) was removed: the planner decides
edits from section structure and does its own protected-region overlap check,
so the cluster output was never consumed.
"""
from typing import List, Tuple


def _parse_timestamp(timestamp: str) -> float:
    """Parse a "MM:SS" timestamp into seconds."""
    minutes, seconds = timestamp.split(':')
    return int(minutes) * 60.0 + int(seconds)


def parse_protected_regions(protected_regions_str: List[str]) -> List[Tuple[float, float]]:
    """Parse "MM:SS-MM:SS" strings into (start_sec, end_sec) tuples."""
    if not protected_regions_str:
        return []

    result = []
    for region_str in protected_regions_str:
        start_str, end_str = region_str.split('-')
        result.append((_parse_timestamp(start_str), _parse_timestamp(end_str)))
    return result


def merge_overlapping_regions(regions: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
    """Merge overlapping protected regions into a minimal non-overlapping set."""
    if not regions:
        return []

    sorted_regions = sorted(regions, key=lambda x: x[0])
    merged = [sorted_regions[0]]
    for current_start, current_end in sorted_regions[1:]:
        last_start, last_end = merged[-1]
        if current_start <= last_end:
            merged[-1] = (last_start, max(last_end, current_end))
        else:
            merged.append((current_start, current_end))
    return merged
