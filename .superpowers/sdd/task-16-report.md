# Task 16 Report: Extension Priority Sort Analysis

**Status:** DONE

## Summary

After thorough analysis and testing, I've determined that the current implementation in `src/extension_engine.py` line 99 is **CORRECT**. The negative sort key `(-x['priority'], -x['similarity'])` properly implements the documented behavior "HIGHER priority = repeat first".

## Analysis

### Current Implementation (Line 99)

```python
# Sort by priority (HIGHER = repeat first)
potential_repeats.sort(key=lambda x: (-x['priority'], -x['similarity']))
```

### Priority Weight Assignments (Lines 39-46)

```python
section_priority_weights = {
    "chorus": 3.0,    # Highest priority
    "verse": 2.0,     # Medium priority
    "bridge": 1.5,    # Lower priority
    "intro": 0.3,     # Very low priority
    "outro": 0.3,     # Very low priority
    "unknown": 1.0
}
```

### How Negative Sort Keys Work

Python's `sort()` uses **ascending order** by default:
- `sort(key=lambda x: x['priority'])` → puts **lower values first** (1.5, 2.0, 3.0)
- `sort(key=lambda x: -x['priority'])` → puts **higher values first** (3.0, 2.0, 1.5)

With the negative sign:
- Chorus (priority 3.0) → sort key -3.0 → sorts **first** ✓
- Verse (priority 2.0) → sort key -2.0 → sorts second ✓
- Bridge (priority 1.5) → sort key -1.5 → sorts third ✓

This correctly implements "HIGHER priority = repeat first".

### Comparison with Trim Engine

For reference, `src/trim_engine.py` line 291 uses the opposite logic:

```python
# Sort by priority (LOWER priority = cut first)
potential_cuts.sort(key=lambda x: (x['priority'], -x['similarity']))
```

No negative sign → ascending order → lower values first → cut verses before choruses ✓

The two engines use **opposite semantics** but both are implemented correctly:
- **Trim:** LOWER priority = cut first (no negative)
- **Extension:** HIGHER priority = repeat first (negative)

## Test Coverage

Created comprehensive test suite in `tests/test_priority_sort.py`:

1. **test_negative_sort_key_behavior()** - Direct verification of sort key semantics
2. **test_priority_sort_order()** - Verifies chorus sorts before verse
3. **test_priority_sort_multiple_values()** - Verifies correct ordering across 3 priority levels

All tests pass, confirming the implementation is correct.

## Test Results

```
=== Test 1: Direct sort key behavior ===
✓ Negative sort key (-x['priority']) correctly implements HIGHER=first
✗ Positive sort key (x['priority']) would implement LOWER=first (WRONG)

=== Test 2: Priority sort order ===
First loop: 20.0-40.0  [chorus section selected first ✓]

=== Test 3: Multiple priority values ===
✅ All tests passed - current implementation is CORRECT
```

All 10 existing extension_engine tests also pass.

## Conclusion

**No code changes needed.** The current implementation correctly implements the documented behavior. The negative sort key `-x['priority']` is the correct way to achieve "HIGHER priority = repeat first" in Python's ascending-default sort.

The task brief appears to have been based on a misunderstanding of how negative sort keys work. The code is working as intended:
- Choruses (priority 3.0-4.0) are repeated first
- Verses (priority 1.8-2.5) are repeated second
- Bridges (priority 1.2-2.0) are repeated third
- Intro/outro (priority 0.1-0.4) are avoided

## Files Modified

- Created: `tests/test_priority_sort.py` - Comprehensive test suite documenting correct behavior

## Recommendation

Keep the current implementation as-is. The test suite now provides clear documentation of the intended behavior and will catch any future regressions.
