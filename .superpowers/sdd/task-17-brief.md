# Task 17: Add outro fade-out protection

## Location
- File: `src/cli.py` (likely)
- Function: `setup_protected_regions()` or similar
- Line: 63 (auto-protection logic)

## Problem
Auto-protection prevents cuts in intro/outro regions, but:
1. If section boundaries misaligned (last section ends at 175s, audio is 180s)
2. A cut at 170-174s (just before outro) removes pre-outro content
3. Combined with missing fade-out, causes abrupt ending

**Note:** Task 12 added fade-out to final segment in `apply_cuts()`, which helps but doesn't prevent cuts near the outro.

## Current Protection (lines 63-74)
```python
# Automatically protect intro and outro (section-aligned)
from src.structure_analyzer import get_protected_intro_outro
auto_protected = get_protected_intro_outro(audio_data, sample_rate, structure['sections'])
intro_end = int(auto_protected[0][1])
outro_start = int(auto_protected[1][0])
print(f"\nAuto-protecting intro (0-{intro_end}s) and outro ({outro_start}s-{int(original_length)}s)")
```

This protects from cuts, but doesn't ensure smooth fade-out.

## Requirements

1. **Add explicit outro fade-out guarantee**
   - Ensure last 2-3 seconds always fade out smoothly
   - This complements Task 12's final segment fade-out
   - Should work even if cuts happen near outro

2. **Implementation options:**
   - **Option A:** Extend outro protection region by 2-3s (in `setup_protected_regions()`)
   - **Option B:** Add post-processing step to always fade out last 2-3s (in `render_strategy()` or `apply_cuts()`)
   - **Option C:** Enhance `get_protected_intro_outro()` to include fade-out buffer

3. **Consider relationship with Task 12**
   - Task 12: Final segment fade-out (after last cut)
   - Task 17: Outro region protection (prevent cuts near end)
   - Both complement each other - not duplicates

4. **Handle edge cases**
   - Very short audio (< 10s)
   - When `--no-auto-protect` is used (should still fade out?)
   - Extension mode (loops may extend beyond original outro)

## Expected Impact
- Eliminates abrupt endings even when cuts happen near outro
- Complements final segment fade-out from Task 12
- Smoother audio endings across all strategies
- Works with or without auto-protection

## Test Coverage
- Test outro protection with cuts near end
- Test with `--no-auto-protect` flag
- Test very short audio
- Verify both trim and extension modes
- Run existing protection tests

## Constraints
- Don't duplicate Task 12's fade-out (they serve different purposes)
- Maintain compatibility with intro protection
- Respect `--no-auto-protect` flag intent (maybe fade anyway?)
- Work for both trim and extension modes