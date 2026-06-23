"""
Unified strategy generation using Dynamic Programming optimization.

This module provides the new API for generating music editing strategies
using the EditGraph and DP optimization. It replaces the separate greedy
approaches in trim_engine.py and extension_engine.py with a unified,
globally optimal solution.

Usage:
    # Generate strategies for trim mode
    strategies = generate_strategies_unified(
        mode="trim",
        segments=segments,
        target_length=60.0,
        original_length=80.0,
        num_strategies=5
    )

    # Generate strategies for extend mode
    strategies = generate_strategies_unified(
        mode="extend",
        segments=segments,
        target_length=100.0,
        original_length=80.0,
        num_strategies=5
    )
"""

from typing import List, Literal, Optional, Dict, Tuple
import numpy as np
from src.edit_operations import Segment, EditSequence
from src.edit_graph import EditGraph
from src.structure_analyzer import analyze_structure


def segments_from_structure(
    clusters: List[Dict],
    sections: List[Dict],
    downbeats: np.ndarray
) -> List[Segment]:
    """
    Convert structure analysis results to Segment objects.

    Args:
        clusters: Segment clusters from segment_matcher
        sections: Section labels from structure_analyzer
        downbeats: Beat positions from structure_analyzer

    Returns:
        List of Segment objects with metadata
    """
    segments = []

    # Create segments from section boundaries
    for section in sections:
        # Find matching cluster for similarity score
        similarity = 0.5  # Default
        for cluster in clusters:
            for seg_start, seg_end in cluster['segment_times']:
                # Check if this segment overlaps with section
                overlap_start = max(seg_start, section['start'])
                overlap_end = min(seg_end, section['end'])
                if overlap_end > overlap_start:
                    similarity = cluster.get('avg_similarity', 0.5)
                    break

        segment = Segment(
            start=section['start'],
            end=section['end'],
            label=section['label'],
            similarity=similarity,
            energy=section.get('avg_energy', 0.5)
        )
        segments.append(segment)

    return segments


def generate_strategies_unified(
    mode: Literal["trim", "extend"],
    clusters: List[Dict],
    original_length: float,
    target_length: float,
    sections: Optional[List[Dict]] = None,
    downbeats: Optional[np.ndarray] = None,
    num_strategies: int = 5,
    tolerance: float = 15.0,
    protected_regions: List[Tuple[float, float]] = None,
    max_repeats: int = 4
) -> List:
    """
    Generate editing strategies using unified DP optimization.

    This replaces both generate_trim_strategies() and generate_extension_strategies()
    with a single, unified approach that guarantees globally optimal solutions.

    Args:
        mode: "trim" or "extend"
        clusters: Segment clusters from segment_matcher
        original_length: Original audio length in seconds
        target_length: Target length in seconds
        sections: Section labels (from structure_analyzer)
        downbeats: Beat positions (from structure_analyzer)
        num_strategies: Number of diverse strategies to generate
        tolerance: Maximum length error (±seconds)
        protected_regions: Time ranges that cannot be edited
        max_repeats: Maximum repeat count for extension

    Returns:
        List of TrimStrategy objects (for backward compatibility)
    """
    sections = sections or []
    downbeats = downbeats if downbeats is not None else np.array([])
    protected_regions = protected_regions or []

    # Convert structure to segments
    segments = segments_from_structure(clusters, sections, downbeats)

    if not segments:
        # Fallback: create segments from downbeats
        segments = []
        for i in range(len(downbeats) - 1):
            seg = Segment(
                start=float(downbeats[i]),
                end=float(downbeats[i+1])
            )
            segments.append(seg)

    if not segments:
        raise ValueError("No segments available for optimization")

    # Build edit graph
    graph = EditGraph(segments, original_length, mode)
    graph.build_edges(protected_regions=protected_regions, max_repeats=max_repeats)

    # Generate diverse solutions using DP
    edit_sequences = graph.generate_diverse_solutions(
        target_length=target_length,
        num_solutions=num_strategies,
        tolerance=tolerance
    )

    # Convert to TrimStrategy format for backward compatibility
    trim_strategies = []
    for i, seq in enumerate(edit_sequences):
        strategy = seq.to_trim_strategy()
        # Update name to reflect it's from DP
        strategy.name = f"dp_{i+1}"
        trim_strategies.append(strategy)

    return trim_strategies


def compare_greedy_vs_dp(
    mode: Literal["trim", "extend"],
    clusters: List[Dict],
    original_length: float,
    target_length: float,
    sections: Optional[List[Dict]] = None,
    downbeats: Optional[np.ndarray] = None,
    audio_data: Optional[np.ndarray] = None,
    sr: int = 22050
) -> Dict:
    """
    Compare greedy (old) vs DP (new) approaches for research validation.

    Args:
        mode: "trim" or "extend"
        clusters: Segment clusters
        original_length: Original length
        target_length: Target length
        sections: Section labels
        downbeats: Beat positions
        audio_data: Audio data for quality scoring
        sr: Sample rate

    Returns:
        Dict with comparison results
    """
    from src.trim_engine import generate_trim_strategies
    from src.extension_engine import generate_extension_strategies
    from src.quality_scorer import score_strategy
    from src.output_generator import render_strategy

    # Generate strategies using old greedy approach
    if mode == "trim":
        greedy_strategies = generate_trim_strategies(
            clusters=clusters,
            original_length=original_length,
            target_length=target_length,
            sections=sections,
            downbeats=downbeats,
            num_strategies=5
        )
    else:
        greedy_strategies = generate_extension_strategies(
            clusters=clusters,
            original_length=original_length,
            target_length=target_length,
            sections=sections,
            downbeats=downbeats,
            num_strategies=5
        )

    # Generate strategies using new DP approach
    dp_strategies = generate_strategies_unified(
        mode=mode,
        clusters=clusters,
        original_length=original_length,
        target_length=target_length,
        sections=sections,
        downbeats=downbeats,
        num_strategies=5
    )

    # Compare quality if audio provided
    comparison = {
        "mode": mode,
        "greedy_count": len(greedy_strategies),
        "dp_count": len(dp_strategies),
        "greedy_scores": [],
        "dp_scores": []
    }

    if audio_data is not None:
        for strategy in greedy_strategies[:3]:
            rendered = render_strategy(strategy, audio_data, sr)
            score = score_strategy(strategy, audio_data, sr, original_length, rendered)
            comparison["greedy_scores"].append(score['star_rating'])

        for strategy in dp_strategies[:3]:
            rendered = render_strategy(strategy, audio_data, sr)
            score = score_strategy(strategy, audio_data, sr, original_length, rendered)
            comparison["dp_scores"].append(score['star_rating'])

        comparison["greedy_avg"] = np.mean(comparison["greedy_scores"])
        comparison["dp_avg"] = np.mean(comparison["dp_scores"])
        comparison["improvement"] = comparison["dp_avg"] - comparison["greedy_avg"]

    return comparison
