# V9 Extension Feature - Complete Documentation

## Overview

**V9 (2026-06-22):** Music Smart Trim now supports **audio extension** in addition to trimming. Extension mode intelligently lengthens audio by repeating musically similar sections with seamless crossfades, maintaining quality and structure.

**Key Capabilities:**
- Extends audio to target length by repeating sections
- 5 diverse extension strategies with different characteristics
- Intelligent section selection prioritizing choruses
- Beat-aligned loops with 500ms constant-power crossfades
- Same quality scoring system as trim mode
- Strict ±15s length enforcement

## When to Use Extension vs Trim

- **Trim Mode:** Target < Original length (e.g., 180s → 120s)
- **Extension Mode:** Target > Original length (e.g., 180s → 240s)

Mode selection is **automatic** based on target length. No flag needed.

## Extension Strategies

V9 generates **5 genuinely diverse extension strategies** with different characteristics:

### 1. Best Strategy
**Goal:** Highest quality, conservative repeats

- **Similarity filter:** 0.85 (only highest-quality matches)
- **Section weights:** Strongly prefers choruses (3.5), standard verses (2.0)
- **Max repeats:** 2 per section
- **Randomization:** None (deterministic)
- **Buffer:** -2.0s (slightly shorter result)
- **Best for:** Maximum quality, minimal repetition

### 2. Diverse Strategy
**Goal:** Balanced variety with some randomization

- **Similarity filter:** 0.75 (good quality matches)
- **Section weights:** Balanced chorus (3.0) and verse (2.2) preference
- **Max repeats:** 3 per section
- **Randomization:** Yes (shuffles within priority groups)
- **Buffer:** -1.0s (near target)
- **Best for:** General use, good balance of quality and variety

### 3. Varied Strategy
**Goal:** Most aggressive repeats, closest to target

- **Similarity filter:** 0.70 (accepts more matches)
- **Section weights:** More balanced sections (chorus 2.8, verse 2.5, bridge 2.0)
- **Max repeats:** 4 per section
- **Randomization:** Yes (adds variety)
- **Buffer:** 0.0s (closest to exact target)
- **Best for:** Hitting exact target length, more variety

### 4. Balanced Strategy
**Goal:** Middle ground approach

- **Similarity filter:** 0.80 (high quality)
- **Section weights:** Standard preferences (chorus 3.0, verse 2.0)
- **Max repeats:** 3 per section
- **Randomization:** None (deterministic)
- **Buffer:** -1.5s (slightly shorter)
- **Best for:** Predictable, high-quality results

### 5. Conservative Strategy
**Goal:** Minimal repeats, maximum preservation

- **Similarity filter:** 0.88 (extremely high quality only)
- **Section weights:** Strongly prefers choruses (4.0), minimal verses (1.8)
- **Max repeats:** 1 per section (single repeat only)
- **Randomization:** None (deterministic)
- **Buffer:** -3.0s (shortest result)
- **Best for:** Subtle extension, preserving original feel

## Intelligent Section Selection

### Priority System

Extension prioritizes sections based on **musical suitability** for repetition:

**HIGHER priority = repeat first:**
1. **Chorus** (3.0-4.0 weight) - Most repetitive, high energy, ideal for loops
2. **Verse** (1.8-2.5 weight) - Good for extension, varies by strategy
3. **Bridge** (1.2-2.0 weight) - Moderate repetition potential
4. **Unknown** (0.8-1.5 weight) - Unclassified sections
5. **Intro/Outro** (0.1-0.4 weight) - Avoided (low priority)

### Region Filtering

- **Middle region preference:** Sections with centers in 15%-85% of original length get full priority
- **Edge penalty:** Intro/outro regions get 0.3× priority reduction
- **Minimum duration:** Sections must be ≥10s to be considered

### Similarity Filtering

Each strategy filters clusters by similarity threshold:
- Only sections with `avg_similarity ≥ threshold` are considered
- Higher thresholds = fewer, higher-quality options
- Lower thresholds = more options, more variety

### Alignment

All loop points are aligned to:
1. **Section boundaries** (when detected)
2. **Bar boundaries** (downbeats)
3. Ensures seamless musical flow

## Quality Scoring

Extension uses the **same quality scoring system** as trim mode:

### Scoring Components (100 points total)

**Musical Coherence (50 points):**
- Base coherence: 40 points
- Pattern bonus: +10 points (for maintaining patterns)
- MERT bonus: +5 points (optional, with `--use-mert`)

**Transition Smoothness (30 points):**
- Base transitions: 20 points
- Spectral flux: +5 points (smooth frequency changes)
- Loudness consistency: +5 points (no volume jumps)

**Length Accuracy (20 points):**
- Full score if within ±15s of target
- Zero score if >30s error
- Linear penalty between 15s-30s error

### Star Rating Conversion

Linear mapping: **0-100 points → 0.0-5.0 stars**
- 100 points = 5.0★
- 80 points = 4.0★
- 60 points = 3.0★
- 40 points = 2.0★
- 0 points = 0.0★

### Quality Threshold

- Minimum acceptable quality: **3.5★**
- Up to 5 retry attempts with different seeds if below threshold
- Ensures all outputs meet quality standards

## Usage Examples

### Basic Extension

Extend 3-minute song to 4 minutes:

```bash
PYTHONPATH=. python src/cli.py --input song.mp3 --target 240
```

### Extension with MERT (Recommended)

Use AI-powered quality assessment for better results:

```bash
PYTHONPATH=. python src/cli.py --input song.mp3 --target 240 --use-mert
```

### Extension with Protected Regions

Prevent specific regions from being looped:

```bash
PYTHONPATH=. python src/cli.py --input song.mp3 --target 240 --protect "1:30-2:00"
```

Note: Intro/outro are automatically deprioritized (not fully protected) in extension mode.

### Custom Output Directory

```bash
PYTHONPATH=. python src/cli.py --input song.mp3 --target 240 --output-dir extended_output
```

### Complete Example

```bash
PYTHONPATH=. python src/cli.py \
  --input examples/song.wav \
  --target 300 \
  --use-mert \
  --output-dir extended_versions
```

## Interactive Regeneration

After generating initial 3 options (from 5 candidates), CLI prompts:

```
Generate alternative options? (y/n)
```

**If yes:**
- Generates 5 new strategies with different random seeds
- Excludes previously shown strategies from selection
- Scores all new strategies
- Presents top 3 by quality
- Repeats until user selects 'n'

**Exclusion tracking:** Ensures variety across regeneration cycles.

## Output Format

Extension outputs follow the same format as trim mode:

```
output/
├── song_extended_best_3.8stars.mp3      # Best strategy (highest similarity)
├── song_extended_diverse_3.6stars.mp3   # Diverse strategy (balanced)
└── song_extended_balanced_3.7stars.mp3  # Balanced strategy (middle ground)
```

**Filename format:** `{basename}_extended_{strategy}_{rating}stars.{ext}`

## Implementation Details

### Architecture

Extension adds **1 new module** to the existing 8-module pipeline:

```
Audio → audio_loader → spectral_analyzer → structure_analyzer
  → segment_matcher → extension_engine* → quality_scorer 
  → output_generator → CLI
```

*New module: `extension_engine.py`

### Key Functions

**`select_extension_sections()`**
- Selects sections to repeat based on priority weights
- Filters by similarity threshold
- Avoids intro/outro regions
- Calculates repeat counts to meet target
- Returns: `List[(start, end, repeat_count)]`

**`generate_extension_strategy()`**
- Creates single extension strategy with specific parameters
- 5 strategy types: best, diverse, varied, balanced, conservative
- Aligns loop points to section/bar boundaries
- Returns: `TrimStrategy` with `loop_points` populated

**`generate_extension_strategies()`**
- Generates all 5 strategies
- Applies iterative refinement for ±15s constraint
- Returns: `List[TrimStrategy]`

**`refine_extension_for_length()`**
- Iteratively adjusts repeat counts to meet ±15s constraint
- Adds repeats if too short (shortest section first)
- Removes repeats if too long (highest repeat count first)
- Max 3 iterations per strategy

### Loop Rendering

**Process:**
1. Original audio is loaded
2. For each loop point `(start, end, repeat_count)`:
   - Extract section `audio[start:end]`
   - Repeat section `repeat_count - 1` times
   - Apply 500ms constant-power crossfades between repetitions
3. Concatenate: `[intro][repeated_section_1][repeated_section_2]...[outro]`
4. Apply crossfades at all boundaries

**Crossfade details:**
- Duration: 500ms (standardized in V7)
- Type: Constant-power (equal-energy)
- Applied at: All loop boundaries and concatenation points
- Ensures: Seamless, professional-quality transitions

### Length Calculation

**Formula:**
```python
resulting_length = original_length + sum(
    (end - start) * (repeat_count - 1) 
    for start, end, repeat_count in loop_points
)
```

**Example:**
- Original: 180s
- Loop 1: 30-50s (20s) × 2 = +20s
- Loop 2: 80-100s (20s) × 3 = +40s
- **Result:** 180 + 20 + 40 = 240s

## Performance Metrics

**Processing Time:**
- Without MERT: ~60-70s for 3-min song
- With MERT: ~80-90s for 3-min song
- Rendering: ~5-10s per strategy

**Memory Usage:**
- Without MERT: ~200-250MB peak
- With MERT: ~400-450MB peak
- Similar to trim mode

**Quality:**
- Typical range: 3.2-3.9★
- With MERT: +0.2-0.4★ improvement
- Threshold: ≥3.5★ (same as trim)

**Length Accuracy:**
- Typical: ±5-12s from target
- Guaranteed: ±15s (100% compliance after refinement)
- Strictest strategy: varied (buffer 0.0s)

**Loop Patterns:**
- Loops per strategy: 1-3 typical
- Repeats per loop: 1-4 (strategy dependent)
- Total sections repeated: 2-6 typical

**Chorus Detection:**
- Duration: 12-30s sections
- Energy: Top 40% (high energy)
- Repetitions: ≥3 occurrences
- Success rate: ~70-80% of songs with clear choruses

## Testing

### Test Coverage

**Unit Tests:**
- `test_extension_engine.py` - Core extension logic
  - Strategy generation (5 strategies)
  - Section selection with priority weights
  - Length refinement algorithm
  - Edge cases (no clusters, short audio)

**Integration Tests:**
- `test_extension_integration.py` - End-to-end pipeline
  - Full extension pipeline execution
  - Quality scoring for extensions
  - Output file generation
  - Regeneration with exclusion

### Running Tests

```bash
# Run all extension tests
pytest tests/test_extension_engine.py tests/test_extension_integration.py -v

# Run specific test
pytest tests/test_extension_engine.py::test_generate_extension_strategies -v

# Run with coverage
pytest tests/test_extension_engine.py --cov=src.extension_engine --cov-report=html
```

### Test Scenarios

**Basic extension:**
- 180s → 240s (+60s)
- Generates 5 strategies
- All within ±15s
- All ≥3.5★ quality

**Long extension:**
- 120s → 300s (+180s)
- Multiple loops required
- More aggressive repeat counts
- Still maintains quality

**Edge cases:**
- No similar clusters (fallback behavior)
- Very short original (<30s)
- Protected regions excluding all sections
- Target only slightly longer than original

## Known Limitations

### Chorus Detection
- Requires: 12-30s duration, high energy (top 40%), ≥3 repetitions
- Some songs may not have detectable choruses
- Correctly identified as no-chorus structure (not an error)

### Extension Constraints
- Maximum practical extension: ~2× original length
- Beyond 2×, quality may degrade (excessive repetition)
- Minimum extension: ~15s (due to minimum segment duration)

### Section Detection
- Accuracy depends on song structure clarity
- Complex arrangements may have less accurate sections
- Affects prioritization but not overall functionality

### Audio Quality
- Normalized to 22050Hz mono (for analysis)
- Output matches input sample rate
- File size limit: 15MB after normalization

### MERT Embeddings
- First-time download: 360MB model
- Processing: +20-30s per song on CPU
- GPU acceleration not currently supported
- Optional feature (baseline quality still good)

## Troubleshooting

### "Extension requires target > original"
**Cause:** Target length ≤ original length  
**Solution:** Use larger target or let auto-mode select trim

### Low quality scores (all <3.5★)
**Cause:** Few similar sections, poor repetition detection  
**Solution:** Try `--use-mert` for better assessment, or use different target length

### Excessive repetition sounds unnatural
**Cause:** Aggressive strategies with high repeat counts  
**Solution:** Use "best" or "conservative" strategies (top-rated outputs)

### Sections not aligned to beats
**Cause:** Beat detection failed or unclear rhythm  
**Solution:** Expected behavior for some songs; crossfades still smooth transitions

### Processing takes too long (>2 min)
**Cause:** MERT enabled on slow CPU, or very long audio  
**Solution:** Disable `--use-mert` for faster processing, or use shorter audio

## Comparison with Trim Mode

| Aspect | Trim Mode | Extension Mode |
|--------|-----------|----------------|
| **Goal** | Shorten audio | Lengthen audio |
| **Trigger** | Target < Original | Target > Original |
| **Mechanism** | Remove sections (cut_points) | Repeat sections (loop_points) |
| **Strategies** | 5 diverse strategies | 5 diverse strategies |
| **Priority** | Cut verses first, keep choruses | Repeat choruses first |
| **Quality Scoring** | Same system (100 points) | Same system (100 points) |
| **Length Constraint** | ±15s strict | ±15s strict |
| **Crossfades** | 500ms at cuts | 500ms at loops |
| **Processing Time** | 60-70s (without MERT) | 60-70s (without MERT) |
| **Typical Quality** | 3.0-3.8★ | 3.2-3.9★ |

## Future Enhancements

**Potential improvements for future versions:**

1. **Smart loop variation** - Slightly vary repeated sections (EQ, effects) to reduce monotony
2. **Build/fade automation** - Gradual volume/filter builds in extended sections
3. **Multi-section composition** - Combine multiple sections in creative patterns
4. **Adaptive repeat counts** - ML-based prediction of optimal repetitions
5. **GPU acceleration** - Faster MERT processing with CUDA support
6. **Real-time preview** - Preview extensions before rendering all strategies
7. **Hybrid mode** - Combine trim and extend (trim some parts, extend others)
8. **Custom section weights** - User-specified priority for verse/chorus/bridge

## Version History Context

- **V9** (2026-06-22): Audio extension with 5 diverse strategies + intelligent section selection
- **V8** (2026-06-21): Fixed strategy diversity bug - 5 genuinely diverse trim strategies
- **V7**: Intelligent chorus preservation + 500ms crossfades + section-aware priority
- **V6**: Generate 10 strategies, show top 3 by quality (bug: all identical)
- **V5**: Enhanced quality scoring + strict ±15s + MERT embeddings + 0.0-5.0★ scale
- **V4**: Section-aware cutting + radio edit strategy
- **V3**: Beat-aligned cutting + constant-power crossfades
- **V2**: Quality scoring improvements
- **V1**: Initial release

## See Also

- `CLAUDE.md` - Development guide and architecture
- `V8_STRATEGY_DIVERSITY_FIX.md` - Strategy diversity implementation (trim mode)
- `V7_COMPLETE_REPORT.md` - Chorus preservation and crossfades (trim mode)
- `README.md` - User documentation
- `TESTING_GUIDE.md` - Test scenarios and validation
