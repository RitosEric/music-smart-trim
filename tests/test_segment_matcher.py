"""Tests for segment matcher module."""

import pytest
from src.segment_matcher import (
    parse_protected_regions,
    merge_overlapping_regions,
    is_segment_protected,
    cluster_similar_segments,
    match_segments
)


class TestProtectedRegionsParsing:
    """Test protected regions parsing functionality."""

    def test_parse_single_protected_region(self):
        """Test parsing a single protected region."""
        result = parse_protected_regions(["1:30-2:45"])
        assert result == [(90.0, 165.0)]

    def test_parse_multiple_protected_regions(self):
        """Test parsing multiple protected regions."""
        result = parse_protected_regions(["0:30-1:00", "2:15-3:00"])
        assert result == [(30.0, 60.0), (135.0, 180.0)]

    def test_parse_empty_protected_regions(self):
        """Test parsing empty list of protected regions."""
        result = parse_protected_regions([])
        assert result == []


class TestMergeOverlappingRegions:
    """Test merging of overlapping protected regions."""

    def test_merge_overlapping_regions(self):
        """Test merging regions that overlap."""
        regions = [(30.0, 60.0), (50.0, 90.0), (100.0, 120.0)]
        result = merge_overlapping_regions(regions)
        assert result == [(30.0, 90.0), (100.0, 120.0)]

    def test_merge_non_overlapping_regions(self):
        """Test that non-overlapping regions remain separate."""
        regions = [(30.0, 60.0), (70.0, 90.0), (100.0, 120.0)]
        result = merge_overlapping_regions(regions)
        assert result == [(30.0, 60.0), (70.0, 90.0), (100.0, 120.0)]


class TestIsSegmentProtected:
    """Test checking if a segment is protected."""

    def test_segment_fully_inside_protected_region(self):
        """Test segment that is fully inside a protected region."""
        protected_regions = [(30.0, 90.0)]
        # Segment from 40s to 50s (fully inside 30-90)
        assert is_segment_protected(40.0, 50.0, protected_regions) is True

    def test_segment_partially_overlaps_protected_region(self):
        """Test segment that partially overlaps a protected region."""
        protected_regions = [(30.0, 90.0)]
        # Segment from 20s to 40s (partially overlaps 30-90)
        assert is_segment_protected(20.0, 40.0, protected_regions) is True

    def test_segment_no_overlap_with_protected_region(self):
        """Test segment with no overlap with protected regions."""
        protected_regions = [(30.0, 90.0)]
        # Segment from 100s to 110s (no overlap with 30-90)
        assert is_segment_protected(100.0, 110.0, protected_regions) is False


class TestClusterSimilarSegments:
    """Test clustering of similar segments."""

    def test_cluster_similar_segments(self):
        """Test clustering segments by proximity and similarity threshold."""
        repeated_segments = [
            {'start_time_1': 10.0, 'start_time_2': 50.0, 'duration': 5.0, 'similarity': 0.85},
            {'start_time_1': 10.5, 'start_time_2': 90.0, 'duration': 5.0, 'similarity': 0.82},
            {'start_time_1': 100.0, 'start_time_2': 150.0, 'duration': 4.0, 'similarity': 0.75},
        ]

        result = cluster_similar_segments(repeated_segments, similarity_threshold=0.8)

        # Should have 1 cluster (first two segments are close in time and above threshold)
        # Third segment is below threshold
        assert len(result) == 1
        cluster = result[0]
        assert len(cluster['segment_times']) == 3  # 10.0, 10.5, 50.0 (start_time_2 from first)
        assert cluster['avg_similarity'] == pytest.approx((0.85 + 0.82) / 2)
        assert cluster['duration'] == 5.0


class TestMatchSegments:
    """Test complete matching pipeline."""

    def test_match_segments_complete_pipeline(self):
        """Test the complete segment matching pipeline."""
        repeated_segments = [
            {'start_time_1': 10.0, 'start_time_2': 50.0, 'duration': 5.0, 'similarity': 0.85},
            {'start_time_1': 30.0, 'start_time_2': 70.0, 'duration': 4.0, 'similarity': 0.82},
            {'start_time_1': 110.0, 'start_time_2': 150.0, 'duration': 5.0, 'similarity': 0.88},
        ]
        protected_regions_str = ["0:25-0:35", "1:30-1:45"]  # 25-35s and 90-105s

        result = match_segments(
            repeated_segments,
            protected_regions_str,
            similarity_threshold=0.8
        )

        # Check that protected regions are parsed and merged
        assert result['protected_regions'] == [(25.0, 35.0), (90.0, 105.0)]

        # Check filtered segments (segment with start_time_1=30.0 should be filtered out)
        assert len(result['filtered_segments']) == 2

        # Check clusters
        assert len(result['clusters']) >= 1
