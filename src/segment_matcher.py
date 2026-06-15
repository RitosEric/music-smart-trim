"""Segment matcher module for matching similar segments and handling protected regions."""

from typing import List, Tuple, Dict
from scipy.cluster.hierarchy import linkage, fcluster
from scipy.spatial.distance import pdist
import numpy as np


def _parse_timestamp(timestamp: str) -> float:
    """
    Parse a timestamp in MM:SS format to seconds.

    Args:
        timestamp: String in "MM:SS" format

    Returns:
        Time in seconds as float
    """
    parts = timestamp.split(':')
    minutes = int(parts[0])
    seconds = int(parts[1])
    return minutes * 60.0 + seconds


def parse_protected_regions(protected_regions_str: List[str]) -> List[Tuple[float, float]]:
    """
    Parse protected regions from "MM:SS-MM:SS" format to list of (start_sec, end_sec) tuples.

    Args:
        protected_regions_str: List of strings in "MM:SS-MM:SS" format

    Returns:
        List of tuples (start_time, end_time) in seconds
    """
    if not protected_regions_str:
        return []

    result = []
    for region_str in protected_regions_str:
        start_str, end_str = region_str.split('-')
        start_sec = _parse_timestamp(start_str)
        end_sec = _parse_timestamp(end_str)
        result.append((start_sec, end_sec))

    return result


def merge_overlapping_regions(regions: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
    """
    Merge overlapping protected regions.

    Args:
        regions: List of (start_time, end_time) tuples

    Returns:
        List of merged (start_time, end_time) tuples with no overlaps
    """
    if not regions:
        return []

    # Sort by start time
    sorted_regions = sorted(regions, key=lambda x: x[0])

    merged = [sorted_regions[0]]

    for current_start, current_end in sorted_regions[1:]:
        last_start, last_end = merged[-1]

        # Check if current region overlaps with last merged region
        if current_start <= last_end:
            # Merge by extending the end time
            merged[-1] = (last_start, max(last_end, current_end))
        else:
            # No overlap, add as new region
            merged.append((current_start, current_end))

    return merged


def is_segment_protected(
    start_time: float,
    end_time: float,
    protected_regions: List[Tuple[float, float]]
) -> bool:
    """
    Check if a segment overlaps with any protected region.

    Args:
        start_time: Segment start time in seconds
        end_time: Segment end time in seconds
        protected_regions: List of (start_time, end_time) protected region tuples

    Returns:
        True if segment overlaps any protected region, False otherwise
    """
    for prot_start, prot_end in protected_regions:
        # Check for overlap: segment overlaps if NOT (segment ends before region starts OR segment starts after region ends)
        if not (end_time <= prot_start or start_time >= prot_end):
            return True
    return False


def cluster_similar_segments(
    repeated_segments: List[Dict],
    similarity_threshold: float = 0.8
) -> List[Dict]:
    """
    Cluster similar segments by filtering on similarity threshold and grouping by proximity.

    Args:
        repeated_segments: List of segment dicts with keys: start_time_1, start_time_2, duration, similarity
        similarity_threshold: Minimum similarity for clustering (default: 0.8)

    Returns:
        List of cluster dicts with keys:
            - segment_times: List of (start, end) tuples for each occurrence
            - avg_similarity: Average similarity of segments in cluster
            - duration: Duration of the segment
    """
    # Filter segments by similarity threshold
    filtered_segments = [
        seg for seg in repeated_segments
        if seg['similarity'] >= similarity_threshold
    ]

    if not filtered_segments:
        return []

    # Group segments by proximity (simple proximity-based grouping)
    clusters = []

    for segment in filtered_segments:
        start_time_1 = segment['start_time_1']
        start_time_2 = segment['start_time_2']
        duration = segment['duration']
        similarity = segment['similarity']

        # Try to find an existing cluster within proximity (< 2.0s)
        found_cluster = False
        for cluster in clusters:
            # Check if start_time_1 is close to any existing segment_times in the cluster
            for seg_start, seg_end in cluster['segment_times']:
                if abs(start_time_1 - seg_start) < 2.0:
                    # Add only the occurrences that are not already close to existing ones
                    # Check if start_time_1 is already represented
                    if not any(abs(start_time_1 - s) < 2.0 for s, e in cluster['segment_times']):
                        cluster['segment_times'].append((start_time_1, start_time_1 + duration))
                    # Check if start_time_2 is already represented
                    if not any(abs(start_time_2 - s) < 2.0 for s, e in cluster['segment_times']):
                        cluster['segment_times'].append((start_time_2, start_time_2 + duration))
                    cluster['similarities'].append(similarity)
                    found_cluster = True
                    break
            if found_cluster:
                break

        if not found_cluster:
            # Create new cluster
            clusters.append({
                'segment_times': [
                    (start_time_1, start_time_1 + duration),
                    (start_time_2, start_time_2 + duration)
                ],
                'similarities': [similarity],
                'duration': duration
            })

    # Calculate average similarities and format output
    result = []
    for cluster in clusters:
        result.append({
            'segment_times': cluster['segment_times'],
            'avg_similarity': sum(cluster['similarities']) / len(cluster['similarities']),
            'duration': cluster['duration']
        })

    return result


def match_segments(
    repeated_segments: List[Dict],
    protected_regions_str: List[str],
    similarity_threshold: float = 0.8
) -> Dict:
    """
    Complete matching pipeline: parse protected regions, filter segments, and cluster.

    Args:
        repeated_segments: List of segment dicts with keys: start_time_1, start_time_2, duration, similarity
        protected_regions_str: List of strings in "MM:SS-MM:SS" format
        similarity_threshold: Minimum similarity for clustering (default: 0.8)

    Returns:
        Dict with keys:
            - clusters: List of cluster dicts
            - protected_regions: List of merged protected region tuples
            - filtered_segments: List of segments after filtering protected ones
    """
    # Parse and merge protected regions
    protected_regions = parse_protected_regions(protected_regions_str)
    protected_regions = merge_overlapping_regions(protected_regions)

    # Filter out segments that overlap with protected regions
    filtered_segments = []
    for segment in repeated_segments:
        start_time_1 = segment['start_time_1']
        end_time_1 = start_time_1 + segment['duration']
        start_time_2 = segment['start_time_2']
        end_time_2 = start_time_2 + segment['duration']

        # Check if either occurrence overlaps with protected regions
        if (not is_segment_protected(start_time_1, end_time_1, protected_regions) and
            not is_segment_protected(start_time_2, end_time_2, protected_regions)):
            filtered_segments.append(segment)

    # Cluster the filtered segments
    clusters = cluster_similar_segments(filtered_segments, similarity_threshold)

    return {
        'clusters': clusters,
        'protected_regions': protected_regions,
        'filtered_segments': filtered_segments
    }
