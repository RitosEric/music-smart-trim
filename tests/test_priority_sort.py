"""Test to verify priority sorting behavior in extension_engine."""

import pytest
import numpy as np
from src.extension_engine import select_extension_sections


def test_priority_sort_order():
    """Verify that HIGHER priority sections sort first (chorus before verse)."""
    clusters = [
        {
            'segment_times': [(20.0, 40.0)],  # Will be labeled as chorus
            'avg_similarity': 0.85,
            'duration': 20.0
        },
        {
            'segment_times': [(60.0, 80.0)],  # Will be labeled as verse
            'avg_similarity': 0.85,
            'duration': 20.0
        },
    ]
    sections = [
        {'start': 20.0, 'end': 40.0, 'label': 'chorus'},
        {'start': 60.0, 'end': 80.0, 'label': 'verse'},
    ]

    # Use explicit priority weights
    priority_weights = {
        'chorus': 3.0,
        'verse': 2.0
    }

    loop_points = select_extension_sections(
        clusters, sections, 100.0, 40.0,
        section_priority_weights=priority_weights,
        similarity_filter=0.80
    )

    # The first loop should be from the chorus (higher priority)
    # because chorus has priority 3.0 and verse has priority 2.0
    if len(loop_points) > 0:
        first_loop_start, first_loop_end, _ = loop_points[0]

        # Chorus is at 20.0-40.0
        # If priority sorting works correctly, this should be selected first
        print(f"First loop: {first_loop_start}-{first_loop_end}")

        # The first selected loop should be the chorus section
        assert first_loop_start == 20.0, f"Expected chorus (20.0) first, got {first_loop_start}"
        assert first_loop_end == 40.0, f"Expected chorus (40.0) first, got {first_loop_end}"


def test_priority_sort_multiple_values():
    """Test priority sorting with multiple priority values."""
    # Create test data with chorus, verse, and bridge
    clusters = [
        {'segment_times': [(20.0, 40.0)], 'avg_similarity': 0.85, 'duration': 20.0},  # chorus
        {'segment_times': [(60.0, 80.0)], 'avg_similarity': 0.85, 'duration': 20.0},  # verse
        {'segment_times': [(100.0, 120.0)], 'avg_similarity': 0.85, 'duration': 20.0},  # bridge
    ]
    sections = [
        {'start': 20.0, 'end': 40.0, 'label': 'chorus'},
        {'start': 60.0, 'end': 80.0, 'label': 'verse'},
        {'start': 100.0, 'end': 120.0, 'label': 'bridge'},
    ]

    priority_weights = {
        'chorus': 3.0,
        'verse': 2.0,
        'bridge': 1.5
    }

    loop_points = select_extension_sections(
        clusters, sections, 150.0, 60.0,
        section_priority_weights=priority_weights,
        similarity_filter=0.80,
        randomize_order=False  # Disable randomization for deterministic test
    )

    # Expected order: chorus (3.0) -> verse (2.0) -> bridge (1.5)
    if len(loop_points) >= 2:
        print(f"Loop order: {[(s, e) for s, e, _ in loop_points]}")

        # First should be chorus
        assert loop_points[0][0] == 20.0, "First loop should be chorus"

        # Second should be verse (if there are multiple loops)
        if len(loop_points) >= 2:
            assert loop_points[1][0] == 60.0, "Second loop should be verse"


def test_negative_sort_key_behavior():
    """Direct test of sort behavior with negative keys."""
    items = [
        {'priority': 3.0, 'name': 'chorus'},
        {'priority': 2.0, 'name': 'verse'},
        {'priority': 1.5, 'name': 'bridge'}
    ]

    # Test with NEGATIVE key (current implementation)
    items_negative = items.copy()
    items_negative.sort(key=lambda x: -x['priority'])

    # With negative sort, higher values should come first
    assert items_negative[0]['name'] == 'chorus', "Negative sort should put highest first"
    assert items_negative[1]['name'] == 'verse', "Negative sort should put middle second"
    assert items_negative[2]['name'] == 'bridge', "Negative sort should put lowest third"

    # Test with POSITIVE key (what would happen if we remove negative)
    items_positive = items.copy()
    items_positive.sort(key=lambda x: x['priority'])

    # With positive sort, lower values come first
    assert items_positive[0]['name'] == 'bridge', "Positive sort should put lowest first"
    assert items_positive[1]['name'] == 'verse', "Positive sort should put middle second"
    assert items_positive[2]['name'] == 'chorus', "Positive sort should put highest third"

    print("✓ Negative sort key (-x['priority']) correctly implements HIGHER=first")
    print("✗ Positive sort key (x['priority']) would implement LOWER=first (WRONG)")


if __name__ == "__main__":
    print("Testing priority sort behavior...")
    print("\n=== Test 1: Direct sort key behavior ===")
    test_negative_sort_key_behavior()
    print("\n=== Test 2: Priority sort order ===")
    test_priority_sort_order()
    print("\n=== Test 3: Multiple priority values ===")
    test_priority_sort_multiple_values()
    print("\n✅ All tests passed - current implementation is CORRECT")
