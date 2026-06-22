# Task 14: Fix quality retry to support extension mode

## Location
- File: `src/cli.py`
- Function: `retry_for_quality()`
- Line: 122 (hardcoded mode='trim')

## Problem
The `retry_for_quality()` function hardcodes `mode='trim'` when calling `generate_strategies()`, so extension mode never gets quality retries. When extension strategies score < 3.5★, they're used as-is instead of retrying with different seeds.

## Current Code (line 121-130)
```python
all_strategies = generate_strategies(
    mode="trim",  # ← HARDCODED
    clusters=clusters,
    original_length=original_length,
    target_length=target_length,
    sections=structure['sections'],
    downbeats=structure['beat_info']['downbeats'],
    regenerate_seed=retry_seed,
    num_strategies=10
)
```

## Requirements

1. **Add mode parameter to retry_for_quality() function signature**
   - Current: `retry_for_quality(scored_strategies, clusters, original_length, target_length, structure, audio_data, sample_rate, use_mert, regenerate_seed)`
   - New: Add `mode` parameter

2. **Pass mode to generate_strategies() call**
   - Line 122: Change `mode="trim"` to `mode=mode`

3. **Update all callers of retry_for_quality()**
   - Find where it's called in cli.py
   - Pass the actual mode parameter

4. **Expected behavior**
   - Both trim and extension modes now retry up to 5 times for quality < 3.5★
   - Extension strategies get the same quality retry treatment as trim

## Test Coverage
- Test retry_for_quality with mode='trim'
- Test retry_for_quality with mode='extend'
- Verify retry seeds work correctly for both modes
- Run existing CLI tests

## Constraints
- Maintain backward compatibility
- Don't change retry threshold (3.5★) or max retries (5)
- Ensure regenerate_seed is handled correctly for both modes