# Task 12: Add fade-out to final audio segment

## Location
- File: `src/output_generator.py`
- Function: `apply_cuts()`
- Lines: 100-107

## Problem
After the last cut, the final segment gets fade-in (line 105) but no fade-out at the end. This causes an abrupt volume drop when the audio ends, especially noticeable in the last 10 seconds.

## Current Code (lines 99-107)
```python
# Add final segment after last cut
if last_end < len(audio):
    final_segment = audio[last_end:]
    
    # Apply fade-in to start of final segment (smooth entry after cut)
    fade_in_duration = min(crossfade_samples, len(final_segment) // 2)
    final_segment = apply_smooth_fade_in(final_segment, fade_in_duration)
    
    segments.append(final_segment)
```

## Requirements

1. **Add fade-out to final segment**
   - Apply fade-out to the END of final_segment (last 500ms or less)
   - Use similar logic to fade-in: `min(crossfade_samples, len(final_segment) // 2)`
   - Apply using existing fade utility function

2. **Handle edge cases**
   - Very short final segments (< 1 second)
   - Final segment that's exactly crossfade length
   - Ensure fade-in and fade-out don't overlap or conflict

3. **Consider outro protection**
   - This fixes the case when outro protection is disabled (`--no-auto-protect`)
   - Also helps when a cut happens near the end despite protection
   - Should complement, not replace, outro protection

4. **Use existing utilities**
   - Check for `apply_smooth_fade_out()` or equivalent
   - May need to create it if only fade-in exists
   - Follow same pattern as fade-in implementation

## Test Coverage
- Test final segment with fade-in and fade-out
- Test very short final segments
- Verify no volume drop at end
- Run existing output_generator tests

## Expected Impact
- Eliminates reported abrupt volume drop in last 10 seconds
- Smoother audio endings across all strategies
- Better listening experience

## Constraints
- Match fade-in duration logic (symmetric behavior)
- Use 500ms crossfade constant (DEFAULT_CROSSFADE_MS)
- Don't break existing fade-in behavior
- Maintain compatibility with crossfade application