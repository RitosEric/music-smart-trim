# Task 11: Fix extension quality scoring - restore loop-specific metrics

## Location
- File: `src/quality_scorer.py`
- Function: `score_strategy()`
- Line: 576

## Problem
Extension strategies are scored using trim-only logic (cut_points), completely ignoring loop_points. This results in:
1. Artificially high coherence scores (~45-50pts) since no boundaries are penalized
2. Missing loop-specific quality metrics
3. All 5 extension strategies get similar scores, defeating diversity purpose

Extension strategies need specialized scoring for:
- **Boundary energy consistency** - smooth loop points
- **Over-repetition penalties** - same section repeated 4+ times
- **Section quality** - avoid intro/outro in loops
- **Loop naturalness** - how well the loop sounds

## Current Code (lines 576-580)
```python
# Score musical coherence (50 points max) - MOST IMPORTANT
# Use ORIGINAL audio with cut_points to score the strategy design
coherence_score = score_musical_coherence(
    original_audio, sr, strategy.cut_points, original_length
)
```

This only uses `cut_points`, which are empty for extension strategies.

## Requirements

1. **Detect extension mode**
   - Add logic to detect if strategy is extension (has loop_points, empty cut_points)
   - Route to appropriate scoring path

2. **Implement loop-specific coherence scoring** (~50 points)
   - **Loop diversity** (20 pts): Penalize repeating the same section too many times
   - **Section quality** (15 pts): Prefer choruses, penalize intro/outro
   - **Over-repetition penalty** (15 pts): Limit total repetitions across all loops

3. **Implement loop-specific transition scoring** (~30 points)
   - **Boundary energy consistency** (10 pts): RMS energy at loop start/end boundaries
   - **Zero-crossing consistency** (10 pts): Smooth zero-crossing alignment
   - **Spectral similarity** (10 pts): Audio similarity at boundaries (optional MERT)

4. **Reuse existing heuristics where possible**
   - Use `score_spectral_flux()` for boundary smoothness
   - Use `score_loudness_consistency()` for overall loudness
   - Create new functions for loop-specific checks

5. **Length accuracy unchanged** (20 points)
   - Extension strategies already calculate length correctly
   - Keep existing `score_length_accuracy()` logic

## Suggested Implementation Approach

**Option A: Restore deleted functions**
- The git diff shows ~220 lines of loop scoring were deleted
- Functions: `score_loop_naturalness()`, `score_loop_transitions()`, `score_mert_loop_transitions()`
- Could restore from git history and adapt

**Option B: Create new unified scorer**
- Single `score_musical_coherence()` that handles both cuts and loops
- Pass both cut_points and loop_points
- Detect which to use based on which is populated

**Option C: Separate scoring functions**
- Keep `score_musical_coherence()` for cuts only
- Create `score_loop_coherence()` for loops only
- Main `score_strategy()` routes based on mode

## Test Coverage
- Test extension strategy scoring produces reasonable scores (not all 45-50pts)
- Test that different extension strategies get different scores
- Test loop boundary analysis
- Test over-repetition detection
- Run existing quality_scorer tests

## Constraints
- Maintain 100-point scale (50 coherence + 30 transitions + 20 length)
- Don't break trim mode scoring
- Extension scores should be comparable to trim scores (both use 0-5★ scale)
- Optional MERT support for loop transitions