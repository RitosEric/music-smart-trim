# Task 15: Fix trim strategy priority weights inversion

## Location
- File: `src/trim_engine.py`
- Line: 360 (STRATEGY_CONFIGS dict)

## Problem
In trim mode, LOWER priority = cut first. The strategy configs have inverted semantics:
- 'best' has verse=0.8 (low priority = cuts aggressively)
- 'conservative' has verse=1.5 (higher priority = preserves more)

This is backwards. 'best' should preserve more structure for higher quality, not cut more aggressively.

## Current Weights (approximate from line 360+)
```python
STRATEGY_CONFIGS = {
    "best": verse=0.8, chorus=3.0,
    "diverse": verse=1.0, chorus=2.5,
    "varied": verse=0.7, chorus=2.8,
    "balanced": verse=1.0, chorus=3.0,
    "conservative": verse=1.5, chorus=4.0
}
```

## Requirements

1. **Understand the semantics**
   - In trim mode: LOWER priority = cut first, HIGHER priority = keep
   - Verse priority 0.8 sorts before chorus priority 3.0
   - Verse at 0.8 gets cut before verse at 1.5
   - Goal: 'best' should cut LESS (preserve more), 'conservative' should cut LESS (preserve most)

2. **Invert the weights appropriately**
   - 'best': Should have HIGH verse weight (preserve structure) - maybe 1.5
   - 'conservative': Should have HIGHEST verse weight (maximum preservation) - maybe 2.0
   - 'varied': Can have LOW verse weight (more aggressive) - keep at 0.7
   - Maintain chorus weights (they should always be higher than verse)

3. **Ensure consistent strategy ordering**
   - conservative = most preservation (highest verse weight)
   - best = high quality preservation
   - balanced = middle ground
   - diverse = varied approach
   - varied = most aggressive (lowest verse weight)

4. **Consider the complete picture**
   - Also check bridge weights, section_priority_weights
   - Ensure buffers align with strategy intent
   - Verify max_cuts makes sense

## Test Coverage
- Test that 'best' strategy preserves more sections than 'varied'
- Test that 'conservative' preserves most sections
- Run existing trim_engine tests
- Verify quality scores align with names

## Constraints
- Chorus weights should remain higher than verse weights (choruses always preserved better)
- Don't change the strategy names
- Maintain ±15s length tolerance
- Keep 5 diverse strategies