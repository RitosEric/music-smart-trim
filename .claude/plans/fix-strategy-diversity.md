# Implementation Plan: Fix Strategy Diversity Bug

## Problem Analysis

The current implementation generates 10 strategies but they all produce **identical results**. Root causes:

1. **`generate_strategy()` ignores key parameters**: The `buffer` and `regenerate_seed` parameters are passed but never used effectively
2. **No diversity mechanisms**: All strategies call `select_middle_region_cuts()` with identical inputs
3. **Wrapper functions are redundant**: `generate_conservative_strategy_with_buffer()`, `generate_balanced_strategy_with_buffer()`, and `generate_aggressive_strategy_with_buffer()` are just thin wrappers that don't add value

## Proposed Solution

Rewrite the strategy generation to create **truly diverse strategies** with different approaches:

### New Strategy Types (5 diverse strategies)

1. **`best`** - Optimized for highest quality
   - Prioritize high-similarity cuts only (>0.8)
   - Align strictly to section boundaries
   - Conservative merging (max_gap: 3.0s)
   - Keep more content (buffer: 3.0s)

2. **`diverse`** - Balanced variety
   - Mix of similarity thresholds (0.75-0.85)
   - Section-aware alignment
   - Moderate merging (max_gap: 2.0s)
   - Target length precisely (buffer: 1.0s)

3. **`varied`** - Alternative cut patterns
   - Prioritize different section types (bridges before verses)
   - Use different random seeds for cut selection
   - Aggressive merging (max_gap: 1.0s)
   - Closer to target (buffer: 0.5s)

4. **`balanced`** - Middle ground
   - Standard similarity threshold (0.75)
   - Mix of section and downbeat alignment
   - Standard merging (max_gap: 2.0s)
   - Moderate buffer (buffer: 2.0s)

5. **`conservative`** - Preserve maximum structure
   - Only highest similarity cuts (>0.85)
   - Strict section boundary alignment
   - Maximum merging (max_gap: 4.0s)
   - Longest result (buffer: 4.0s)

### Implementation Changes

#### 1. **Rewrite `select_middle_region_cuts()` to accept diversity parameters**

Add parameters:
- `similarity_filter`: Filter cuts by similarity threshold
- `section_priority_weights`: Custom weights for section types
- `randomize_order`: Use seed to randomize selection within priority groups
- `max_cuts`: Limit number of cuts

#### 2. **Rewrite `generate_strategy()` to use diversity parameters**

Map each strategy type to specific parameter combinations:
```python
STRATEGY_CONFIGS = {
    "best": {
        "similarity_filter": 0.80,
        "section_weights": {"verse": 1, "bridge": 2, "chorus": 3},
        "max_gap": 3.0,
        "buffer": 3.0,
        "randomize": False
    },
    "diverse": {
        "similarity_filter": 0.75,
        "section_weights": {"verse": 1, "bridge": 2, "chorus": 3},
        "max_gap": 2.0,
        "buffer": 1.0,
        "randomize": True
    },
    # ... etc
}
```

#### 3. **Simplify `generate_trim_strategies()`**

Replace the 10-strategy generation with 5 truly diverse strategies:
```python
def generate_trim_strategies(..., num_strategies=5):
    strategy_types = ["best", "diverse", "varied", "balanced", "conservative"]
    strategies = []
    
    for i, strategy_type in enumerate(strategy_types[:num_strategies]):
        seed = (regenerate_seed or 0) + i
        strategy = generate_strategy(
            strategy_type, clusters, original_length, target_length,
            sections=sections, downbeats=downbeats, 
            regenerate_seed=seed
        )
        strategies.append(strategy)
    
    return strategies
```

#### 4. **Remove redundant wrapper functions**

Delete:
- `generate_conservative_strategy_with_buffer()`
- `generate_balanced_strategy_with_buffer()`
- `generate_aggressive_strategy_with_buffer()`

These are now handled by the unified `generate_strategy()` function.

#### 5. **Update CLI to show top 3 from 5 strategies**

Change `num_strategies=10` to `num_strategies=5` in `run_pipeline()`.

## Files to Modify

1. **`src/trim_engine.py`** (main changes)
   - Rewrite `select_middle_region_cuts()` with diversity parameters
   - Rewrite `generate_strategy()` to use parameter configs
   - Simplify `generate_trim_strategies()` to 5 strategies
   - Delete 3 wrapper functions (~40 lines removed)

2. **`src/cli.py`** (minor changes)
   - Change default `num_strategies=10` to `num_strategies=5`
   - Update display messages

## Expected Results

After implementation:
```
Generating 5 diverse trim strategies...
Strategy cut details:
  best: 2 cuts (45.2s removed): [60.5-85.3s, 120.1-140.4s]
  diverse: 3 cuts (52.8s removed): [55.2-72.1s, 98.3-115.7s, 135.6-152.3s]
  varied: 1 cut (48.3s removed): [80.2-128.5s]
  balanced: 2 cuts (50.1s removed): [62.4-88.9s, 125.3-148.9s]
  conservative: 1 cut (42.7s removed): [90.1-132.8s]

Scoring all strategies...
  best: 3.5★ (69.5 points, 134.8s)
  diverse: 3.8★ (75.2 points, 127.2s)
  varied: 4.3★ (86.6 points, 131.7s)
  balanced: 3.9★ (78.1 points, 129.9s)
  conservative: 3.7★ (73.5 points, 137.3s)
```

## Benefits

1. **Genuine diversity**: Each strategy produces different cut patterns and lengths
2. **Better names**: Clear, descriptive names (not "conservative_1", "conservative_2", etc.)
3. **Code cleanup**: Remove ~40 lines of redundant wrapper functions
4. **Predictable behavior**: Each strategy type behaves consistently
5. **Easier debugging**: Clear parameter mapping for each strategy type

## Testing Strategy

Test with example files:
1. `examples/One Direction - What Makes You Beautiful.mp3` (simple pop structure)
2. `examples/JAY-Z,Alicia Keys - Empire State Of Mind.mp3` (verse-heavy hip-hop)
3. Verify all 5 strategies produce different cut patterns
4. Verify quality scores vary appropriately (3.5-4.5★ range expected)
5. Verify length accuracy (all within ±15s of target)
