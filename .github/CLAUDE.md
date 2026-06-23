# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Music Smart Trim intelligently trims or extends music to target length using spectral analysis, section-aware editing with chorus preservation, and optional MERT embeddings for quality assessment (V9). Supports both shortening (trim mode) and lengthening (extension mode) with 5 diverse strategies.

## Recent Version

**V6 (Current - 2026-06-23):** Research-backed quality scoring with LUFS loudness (EBU R128), tempo stability (beat interval variance), and updated weights (50/35/15). Expected +0.2-0.4★ quality improvement from perceptually-validated metrics.

**V9 (2026-06-22):** Audio extension feature - intelligently lengthens audio by repeating sections. Supports both trim (target < original) and extend (target > original) modes with 5 diverse strategies each. Automatic mode detection based on target length. See `V9_EXTENSION_FEATURE.md` for details.

## Setup

**Dependencies:**
```bash
# Install Python dependencies
pip install -r requirements.txt

# Or install as editable package (avoids PYTHONPATH prefix)
pip install -e .
```

**System Requirements:**
- Python 3.8+
- FFmpeg (required for audio processing): `brew install ffmpeg` on macOS

## Quick Commands

```bash
# Run (basic trim - target < original)
PYTHONPATH=. python src/cli.py --input song.mp3 --target 120

# Run (basic extension - target > original)
PYTHONPATH=. python src/cli.py --input song.mp3 --target 240

# Run (with MERT embeddings for better quality - recommended)
PYTHONPATH=. python src/cli.py --input song.mp3 --target 120 --use-mert

# Run (extension with MERT)
PYTHONPATH=. python src/cli.py --input song.mp3 --target 240 --use-mert

# Run (with protected regions)
PYTHONPATH=. python src/cli.py --input song.mp3 --target 120 --protect "0:00-0:30" "3:00-3:30"

# Run (enable auto intro/outro protection)
PYTHONPATH=. python src/cli.py --input song.mp3 --target 120 --auto-protect

# Run all tests
pytest tests/ -v

# Run single test file
pytest tests/test_audio_loader.py -v

# Clean output directories
rm -rf output* __pycache__ .pytest_cache
```

**Note:** Mode (trim vs extend) is automatically detected based on target length. CLI includes interactive regeneration loop - after generating top 3 options (from 5 candidates), prompts "Generate alternative options? (y/n)" to try different strategies with exclusion of previously shown options.

## Architecture (7-Stage Pipeline, 9 Modules)

```
Audio → audio_loader → spectral_analyzer → structure_analyzer
  → segment_matcher → [trim_engine | extension_engine] 
  → quality_scorer → output_generator → CLI
```

**Core Modules:**
- `audio_loader`: Load, normalize to 22050Hz mono
- `spectral_analyzer`: Detect repetitions (SSM, min 15s, threshold 0.75)
- `structure_analyzer`: Detect beats, tempo, label sections with repetition counts
- `segment_matcher`: Cluster and filter segments
- `trim_engine`: Generate 5 diverse trim strategies, select top 3 by quality
- `extension_engine`: Generate 5 diverse extension strategies, select top 3 by quality
- `quality_scorer`: V6 research-backed metrics (LUFS, tempo stability, spectral flux)
- `crossfade`: Constant-power crossfades (500ms)
- `output_generator`: Render with crossfades, save files

## Key Features (V9)

- **Dual-mode operation** (V9) - Automatic trim (target < original) or extend (target > original) mode selection
- **Audio extension** (V9) - Intelligently lengthens audio by repeating musically similar sections
- **5 diverse extension strategies** (V9) - best, diverse, varied, balanced, conservative with different repeat patterns
- **Intelligent section selection** (V9) - Prioritizes choruses, avoids intro/outro, aligns to beats
- **5 genuinely diverse trim strategies** (V8) - best, diverse, varied, balanced, conservative with different cut patterns
- **Intelligent chorus preservation** (V7) - keeps at least 1 chorus, prioritizes cutting verses > bridges > extra choruses
- **Enhanced crossfades** (V7) - 500ms constant-power crossfades for smoother melodic transitions
- **Section-aware priority system** (V7) - cuts extra verses first, protects first chorus occurrence
- **Top 3 selection by quality** (V8) - ensures variety, excludes previously shown options on regeneration
- **Strict ±15s length enforcement** (V5) - iterative refinement ensures compliance
- **Enhanced quality scoring** (V6) - research-backed metrics with academic justification
- **Optional MERT embeddings** (V5) - AI-powered transition quality assessment (`--use-mert`)
- **Normalized star ratings** (V5) - Full 0.0-5.0 scale with 0.1 increments (linear mapping: 100pts = 5.0★)
- **Section-aware editing** (V4) - aligns cuts/loops to section boundaries
- **Radio edit strategy** (V4) - back-to-back cuts forming continuous removal
- **Improved section boundary alignment** (2026-06-23) - limits over-expansion while preserving musical flow
- Auto intro/outro protection (first/last 10% or 15s) - **opt-in with --auto-protect flag**
- Beat-aligned editing at bar boundaries

## Parameters

**Segment Detection:**
- Min: 15.0s, Max: 60.0s, Threshold: 0.75

**Quality Scoring (V6 - Research-Backed):**
- Musical coherence: 50 points (includes 10pt pattern bonus + optional 5pt MERT)
- Transition smoothness: 35 points (15pt base + 10pt spectral flux + 8pt LUFS loudness + 7pt tempo stability)
- Length accuracy: 15 points (strict: 0 points if >30s error)
- **Star conversion:** Linear 0-100pts → 0.0-5.0★ (100pts=5.0★, 80pts=4.0★, 60pts=3.0★)
- **Research-backed metrics:**
  * Spectral flux: Standard in MIR (Foote 2000, onset detection)
  * LUFS loudness: EBU R128 broadcast standard (perceptually validated)
  * Tempo stability: Beat tracking evaluation metrics (MIREX)
  * Weights based on perceptual importance studies

**Cut Strategy Generation (V8 - Trim Mode):**
- Generate 5 truly diverse strategies with different parameters:
  * **best**: High-quality cuts, 2 cuts max, +3s buffer (longer result)
  * **diverse**: Balanced with randomization for variety
  * **varied**: Alternative patterns, no cut limit, +0.5s buffer (closest to target)
  * **balanced**: Middle ground, 3 cuts max, +2s buffer
  * **conservative**: Maximum preservation, 1 cut max, +4.5s buffer (longest result)
- Score all 5 strategies using quality scorer
- Select top 3 by quality for output generation
- Exclude previously shown strategies on regeneration
- Each strategy: section-aware with chorus preservation (V7)
- Iterative refinement to ±15s (max 3 iterations per strategy)

**Extension Strategy Generation (V9 - Extension Mode):**
- Generate 5 truly diverse extension strategies with different parameters:
  * **best**: High-quality sections (0.85 similarity), 2 repeats max, -2.0s buffer
  * **diverse**: Balanced with randomization (0.75 similarity), 3 repeats max
  * **varied**: More aggressive (0.70 similarity), 4 repeats max, 0.0s buffer (closest to target)
  * **balanced**: Middle ground (0.80 similarity), 3 repeats max, -1.5s buffer
  * **conservative**: Minimal repeats (0.88 similarity), 1 repeat max, -3.0s buffer
- Prioritize chorus sections (3.0-4.0 weight) over verses (1.8-2.5) and bridges (1.2-2.0)
- Avoid intro/outro regions (0.1-0.4 weight)
- Score all 5 strategies using quality scorer
- Select top 3 by quality for output generation
- Iterative refinement to ±15s (max 3 iterations per strategy)

**MERT Embeddings (V5 - Optional):**
- Model: MERT-95M (360MB, first-time download)
- Processing: ~20s per 3-min song on CPU
- Quality boost: +0.2-0.4★ typical
- Enable with: `--use-mert` flag

## Common Tasks

### Adjust Min Segment Duration
`spectral_analyzer.py:63` - `min_segment_duration` parameter (default: 15.0s)

### Change Similarity Threshold
`spectral_analyzer.py:65` - `similarity_threshold` parameter (default: 0.75)

### Modify Quality Weights
`quality_scorer.py:688` - `score_strategy()` function (50pts coherence, 35pts transitions, 15pts length) - V6 research-backed weights

### Change Star Rating Conversion
`quality_scorer.py:685` - `points_to_stars()` function (currently linear 0-100 → 0.0-5.0)

### Tune Length Tolerance
`trim_engine.py:492` - `refine_strategy_for_length()` tolerance parameter (default: 15.0s)
`extension_engine.py:291` - `refine_extension_for_length()` tolerance parameter (default: 15.0s)

### Change Quality Threshold
`cli.py:18` - `MIN_ACCEPTABLE_QUALITY` constant (default: 3.5★)

### Toggle Auto Protection
`cli.py` - Use `--auto-protect` flag to enable automatic intro/outro protection (disabled by default)

### Adjust Extension Priority Weights
`extension_engine.py:39` - `section_priority_weights` dict (chorus=3.0, verse=2.0, bridge=1.5, intro/outro=0.3)

### Modify Extension Strategy Configs
`extension_engine.py:160` - `STRATEGY_CONFIGS` dict with similarity filters, section weights, max repeats, buffers

## Constraints (V7/V9)

- **Length tolerance: ±15s (STRICT)** - enforced via iterative refinement in both trim and extension modes
- **Min quality: ≥3.5★** (retries up to 5 times with different seeds)
- **Chorus preservation: ≥1 chorus** (V7) - first chorus always protected (when detected) in trim mode
- **Chorus prioritization** (V9) - choruses repeated first in extension mode
- **Crossfade duration: 500ms** (V7) - longer crossfades for smoother transitions
- **Fade-out duration: 5s** - extended to prevent abrupt drops at track end
- Processing: ~60s for 3-min song (without MERT), ~70s (with MERT) for trim; ~60-70s (without MERT), ~80-90s (with MERT) for extension
- File size limit: 15MB after normalization
- Star ratings: 0.0-5.0 scale, 0.1 increments, rounded

## Documentation

- `README.md`: User documentation
- `CLAUDE.md`: This file - development guide
- `V9_EXTENSION_FEATURE.md`: V9 audio extension feature - complete documentation
- `V8_STRATEGY_DIVERSITY_FIX.md`: V8 bug fix - genuine strategy diversity
- `V7_COMPLETE_REPORT.md`: V7 chorus preservation & smooth transitions implementation
- `V7_IMPLEMENTATION_PROGRESS.md`: V7 progress tracking and test results
- `RESEARCH_FINDINGS.md`: Research on advanced music editing & quality assessment
- `TESTING_GUIDE.md`: Test scenarios

## Performance (V7/V9)

**Trim Mode:**
- Processing: ~60-70s for 3-min song (60s without MERT, 70s with MERT)
- Memory: ~200MB peak (without MERT), ~400MB (with MERT)
- Quality: 3.0-3.8★ typical (3.5★ without MERT, 3.8★ with MERT)
- Length: ±5-12s typical (100% within ±15s)
- Cut pattern: 1-2 continuous blocks (radio edit style)

**Extension Mode:**
- Processing: ~60-70s for 3-min song (60s without MERT, 80-90s with MERT)
- Memory: ~200-250MB peak (without MERT), ~400-450MB (with MERT)
- Quality: 3.2-3.9★ typical (3.5★ without MERT, 3.9★ with MERT)
- Length: ±5-12s typical (100% within ±15s)
- Loop pattern: 1-3 loops with 1-4 repeats each

**Common (Both Modes):**
- Chorus detection: Identifies repeated, high-energy, 12-30s sections (≥3 repetitions)

## Version History

- **V9** (Current - 2026-06-22): Audio extension feature - intelligently lengthens audio by repeating sections with 5 diverse strategies
- **V8** (2026-06-21): Fixed strategy diversity bug - 5 genuinely diverse strategies
- **V7**: Intelligent chorus preservation + 500ms crossfades + section-aware priority system
- **V6**: Generate 10 strategies, show top 3 by quality + regeneration with exclusion (bug: all identical)
- **V5**: Enhanced quality scoring + strict ±15s + MERT embeddings + normalized 0.0-5.0★ scale + 3.5★ threshold
- **V4**: Section-aware cutting + back-to-back cuts + radio edit strategy
- **V3**: Beat-aligned cutting + constant-power crossfades
- **V2**: Quality scoring improvements
- **V1**: Initial release

## Recent Changes (V9)

**V6 Research-Backed Quality Scoring (2026-06-23):**
- **Improved LUFS loudness metric** - Now uses EBU R128 standard (pyloudnorm) instead of RMS
- **Improved tempo stability metric** - Now uses beat interval variance instead of simple tempo detection
- **Updated scoring weights** - Based on perceptual importance research:
  * Musical coherence: 50% (unchanged)
  * Transition smoothness: 35% (increased from 30%)
  * Length accuracy: 15% (decreased from 20%)
- **Added tempo stability to scoring** - 7 points, measures rhythm consistency
- **Spectral flux weight increased** - Now 10 points (was 5)
- **LUFS loudness weight increased** - Now 8 points (was 5)
- All three metrics (spectral flux, LUFS, tempo) are research-backed with academic citations
- See `RESEARCH_RECOMMENDATIONS.md` for academic justification and future improvements

**Post-V9 Refinements (2026-06-23):**
- **Changed default intro/outro protection to opt-in** - users must now use `--auto-protect` flag to enable
- **Improved section boundary alignment** - prevents mid-melody cuts while limiting over-expansion:
  - If cut is >60% within one section: expand to that section only
  - Small cuts (<5s) spanning boundaries: pick section with more overlap
  - Downbeat alignment now stays within section boundaries (inward preference)
  - Prevents 9-18x expansions, typical expansion now 1.0-3.5x
- Experimented with volume consistency penalty for quiet endings (reverted)
- Enhanced fade-out handling to prevent abrupt drops (extended to 5 seconds)
- Fixed double fade-out issue on naturally fading audio
- Deleted volume-specific test files after penalty removal

**V9 Audio Extension Feature (2026-06-22):**
- Added extension_engine.py for intelligent audio lengthening
- 5 diverse extension strategies with section-aware repetition
- Automatic mode detection (trim vs extend) based on target length
- Performance: 60-90s for 3-min song, quality 3.2-3.9★
- See `V9_EXTENSION_FEATURE.md` for complete details

**V8 Critical Bug Fix (2026-06-21):**
- Fixed bug where all strategies generated identical results
- New strategy names: best, diverse, varied, balanced, conservative
- See `V8_STRATEGY_DIVERSITY_FIX.md` for details

**Known Limitations:**
- Chorus detection requires: 12-30s duration, high energy (top 40%), ≥3 repetitions
- Some songs may not have detectable choruses (correctly identified as no-chorus structure)
- Extension mode: Maximum practical extension ~2× original length for quality maintenance
- Extension mode: Minimum extension ~15s (due to minimum segment duration)
