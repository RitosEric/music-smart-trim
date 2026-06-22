# Task 13: Lower chorus detection threshold from ≥3 to ≥2 repetitions

## Location
- File: `src/structure_analyzer.py`
- Line: 201

## Problem
Primary chorus detection requires `repetition_count >= 3`, which misses songs with 2-repeat choruses (common in pop music). A fallback exists at line 204 with `>= 2` but has looser duration constraints (≤35.0s vs ≤30.0s).

## Current Code (lines 201-206)
```python
elif (repetition_count >= 3 and is_high_energy and is_bright and
      12.0 <= section_duration <= 30.0):
    label = "chorus"  # High repetition + high energy + short = chorus
elif (repetition_count >= 2 and is_high_energy and
      12.0 <= section_duration <= 35.0):
    label = "chorus"  # Medium-high repetition + high energy + shortish = likely chorus
```

## Requirements

1. **Change primary rule from ≥3 to ≥2 repetitions**
   - Line 201: Change `repetition_count >= 3` to `repetition_count >= 2`
   - Keep all other conditions (high energy, bright, 12-30s duration)

2. **Adjust or remove the fallback rule**
   - The fallback at line 204 now duplicates the primary rule
   - Either remove it entirely, or adjust it for `repetition_count >= 1` with stricter energy requirements

3. **Expected impact**
   - Improves chorus detection accuracy by ~20-30%
   - More songs will have choruses correctly identified
   - Better trim preservation (protects choruses)
   - Better extension quality (prioritizes choruses for repetition)

## Test Coverage
- Run existing structure analyzer tests
- Verify chorus detection still works correctly
- Check that verse/bridge detection isn't affected
- Test with audio that has 2-repeat vs 3-repeat choruses

## Constraints
- Maintain backward compatibility with existing detection logic
- Don't reduce detection quality for 3+ repeat choruses
- Ensure energy and brightness thresholds remain effective