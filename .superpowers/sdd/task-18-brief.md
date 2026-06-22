# Task 18: Make extension minimum segment duration configurable

## Location
- File: `src/extension_engine.py`
- Function: `select_extension_sections()`
- Line: 61

## Problem
Hardcoded 10s minimum for segment selection (`if duration < 10.0: continue`) limits extension of short audio clips. This contributes to the "minimum extension ~15s" limitation.

## Current Code (lines 59-62)
```python
duration = seg_end - seg_start

if duration < 10.0:  # Skip short segments
    continue
```

## Requirements

1. **Make minimum configurable in select_extension_sections()**
   - Add parameter: `min_segment_duration: float = 10.0`
   - Use parameter instead of hardcoded 10.0
   - Update docstring

2. **Thread parameter through call chain**
   - `generate_extension_strategy()` should accept `min_segment_duration`
   - `generate_extension_strategies()` should accept it
   - Pass default of 10.0 to maintain backward compatibility

3. **Optional CLI flag (stretch goal)**
   - Add `--min-segment-duration` flag to CLI
   - Default: 10.0s (current behavior)
   - Range: 5.0-30.0s (reasonable bounds)
   - Only affects extension mode

4. **Update CLAUDE.md documentation**
   - Document the new configurability
   - Note that lower values allow shorter extensions
   - Mention quality tradeoff (very short segments may not loop well)

## Expected Impact
- Allows extension of shorter audio clips (e.g., 30s → 45s)
- User control over quality vs flexibility tradeoff
- Reduces "minimum extension ~15s" limitation to ~8-10s
- Default behavior unchanged (backward compatible)

## Test Coverage
- Test with min_segment_duration=5.0, 10.0, 15.0
- Verify short segments are included/excluded correctly
- Test that default value maintains current behavior
- Run existing extension tests

## Constraints
- Default value: 10.0s (no breaking change)
- Reasonable range: 5.0-30.0s
- Don't affect trim mode (different min_segment_duration in spectral_analyzer)
- Maintain quality - warn if value too low (<5s)