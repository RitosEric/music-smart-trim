# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Music Smart Trim intelligently shortens music to target length using spectral analysis, section-aware cutting with chorus preservation, and optional MERT embeddings for quality assessment (V7).

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
# Run (basic trim)
PYTHONPATH=. python src/cli.py --input song.mp3 --target 120

# Run (extend audio by repeating sections)
PYTHONPATH=. python src/cli.py --input song.mp3 --target 180

# Run (with MERT embeddings for better quality - recommended)
PYTHONPATH=. python src/cli.py --input song.mp3 --target 120 --use-mert

# Run (with protected regions)
PYTHONPATH=. python src/cli.py --input song.mp3 --target 120 --protect "0:00-0:30" "3:00-3:30"

# Run all tests
pytest tests/ -v

# Run single test file
pytest tests/test_audio_loader.py -v

# Test extension feature
python test_extension.py

# Clean output directories
rm -rf output* __pycache__ .pytest_cache
```

**Note:** CLI includes interactive regeneration loop - after generating top 3 options (from 10 candidates), prompts "Generate alternative options? (y/n)" to try different strategies with exclusion of previously shown options.

## Architecture (7-Stage Pipeline, 8 Modules)

```
Audio → audio_loader → spectral_analyzer → structure_analyzer
  → segment_matcher → trim_engine → quality_scorer → output_generator → CLI
```

**Modules:**
- `audio_loader`: Load, normalize to 22050Hz mono
- `spectral_analyzer`: Detect repetitions (SSM, min 15s, threshold 0.75)
- `structure_analyzer`: Detect beats, tempo, label sections (intro/verse/chorus/bridge/outro) with repetition counts (V7)
- `segment_matcher`: Cluster and filter segments
- `trim_engine`: Generate 10 diverse strategies, select top 3 by quality (V6); section-aware with chorus preservation (V7)
- `quality_scorer`: Enhanced heuristics + optional MERT embeddings (V5)
- `crossfade`: Constant-power crossfades (500ms in V7)
- `output_generator`: Render with crossfades, save files

## Key Features (V7)

- **Intelligent chorus preservation** (V7) - keeps at least 1 chorus, prioritizes cutting verses > bridges > extra choruses
- **Enhanced crossfades** (V7) - 500ms constant-power crossfades for smoother melodic transitions
- **Section-aware priority system** (V7) - cuts extra verses first, protects first chorus occurrence
- **10 strategies generated, top 3 shown** (V6) - ensures variety, excludes previously shown options on regeneration
- **Strict ±15s length enforcement** (V5) - iterative refinement ensures compliance
- **Enhanced quality scoring** (V5) - spectral flux, loudness consistency, tempo stability
- **Optional MERT embeddings** (V5) - AI-powered transition quality assessment (`--use-mert`)
- **Normalized star ratings** (V5) - Full 0.0-5.0 scale with 0.1 increments (linear mapping: 100pts = 5.0★)
- **Section-aware cutting** (V4) - aligns cuts to section boundaries
- **Radio edit strategy** (V4) - back-to-back cuts forming continuous removal
- Auto intro/outro protection (first/last 10% or 15s)
- Beat-aligned cutting at bar boundaries

## Parameters

**Segment Detection:**
- Min: 15.0s, Max: 60.0s, Threshold: 0.75

**Quality Scoring (V5):**
- Musical coherence: 50 points (includes 10pt pattern bonus + optional 5pt MERT)
- Transition smoothness: 30 points (20pt base + 5pt spectral flux + 5pt loudness)
- Length accuracy: 20 points (strict: 0 points if >30s error)
- **Star conversion:** Linear 0-100pts → 0.0-5.0★ (100pts=5.0★, 80pts=4.0★, 60pts=3.0★)

**Cut Strategy Generation (V6/V7):**
- Generate 10 diverse strategies with different aggressiveness levels
- Score all 10 strategies using quality scorer
- Select top 3 by quality for output generation
- Exclude previously shown strategies on regeneration
- Each strategy: section-aware with chorus preservation (V7)
- Iterative refinement to ±15s (max 3 iterations per strategy)

**MERT Embeddings (V5 - Optional):**
- Model: MERT-95M (360MB, first-time download)
- Processing: ~20s per 3-min song on CPU
- Quality boost: +0.2-0.4★ typical
- Enable with: `--use-mert` flag

## Common Tasks

### Adjust Min Segment Duration
`spectral_analyzer.py:64` - `min_segment_duration` parameter (default: 15.0s)

### Change Similarity Threshold
`spectral_analyzer.py:66` - `similarity_threshold` parameter (default: 0.75)

### Modify Quality Weights
`quality_scorer.py:531-624` - `score_strategy()` function weights

### Change Star Rating Conversion
`quality_scorer.py:685-710` - `points_to_stars()` function (currently linear 0-100 → 0.0-5.0)

### Tune Length Tolerance
`trim_engine.py:540-641` - `refine_strategy_for_length()` tolerance parameter (default: 15.0s)

### Adjust Initial Buffers
`trim_engine.py:274,343,432` - Buffer zones for conservative/balanced/aggressive

### Change Quality Threshold
`cli.py:142` - Quality threshold check (default: 3.5★)

## Constraints (V7)

- **Length tolerance: ±15s (STRICT)** - enforced via iterative refinement
- **Min quality: ≥3.5★** (retries up to 5 times with different seeds)
- **Chorus preservation: ≥1 chorus** (V7) - first chorus always protected (when detected)
- **Crossfade duration: 500ms** (V7) - longer crossfades for smoother transitions
- Processing: ~60s for 3-min song (without MERT), ~70s (with MERT)
- File size limit: 15MB after normalization
- Star ratings: 0.0-5.0 scale, 0.1 increments, rounded

## Documentation

- `README.md`: User documentation
- `CLAUDE.md`: This file - development guide
- `V7_COMPLETE_REPORT.md`: V7 chorus preservation & smooth transitions implementation
- `V7_IMPLEMENTATION_PROGRESS.md`: V7 progress tracking and test results
- `RESEARCH_FINDINGS.md`: Research on advanced music editing & quality assessment
- `TESTING_GUIDE.md`: Test scenarios

## Performance (V7)

- Processing: ~60-70s for 3-min song (60s without MERT, 70s with MERT)
- Memory: ~200MB peak (without MERT), ~400MB (with MERT)
- Quality: 3.0-3.8★ typical (3.5★ without MERT, 3.8★ with MERT)
- Length: ±5-12s typical (100% within ±15s)
- Cut pattern: 1-2 continuous blocks (radio edit style)
- Chorus detection: Identifies repeated, high-energy, 12-30s sections (≥3 repetitions)

## Version History

- **V7** (Current): Intelligent chorus preservation + 500ms crossfades + section-aware priority system
- **V6**: Generate 10 strategies, show top 3 by quality + regeneration with exclusion
- **V5**: Enhanced quality scoring + strict ±15s + MERT embeddings + normalized 0.0-5.0★ scale + 3.5★ threshold
- **V4**: Section-aware cutting + back-to-back cuts + radio edit strategy
- **V3**: Beat-aligned cutting + constant-power crossfades
- **V2**: Quality scoring improvements
- **V1**: Initial release

## Recent Changes (V7)

**V8 Features (Extension Mode):**
- ✅ Audio extension by repeating sections (target > original length)
- ✅ Section repeatability scoring (chorus > verse > bridge, energy consistency)
- ✅ Loop quality scoring (naturalness, transition smoothness, over-repetition penalty)
- ✅ Automatic mode detection (trim vs extend based on target length)
- ✅ MERT-based loop transition scoring (optional)
- ✅ Multiple extension strategies (conservative/balanced/aggressive: 2x/3x/5x max repeats)
- ✅ See `test_extension.py` for usage examples

**V7 Features:**
- ✅ Chorus detection with repetition counting (integrated with spectral analyzer)
- ✅ Chorus preservation logic (first chorus protected, verses cut first)
- ✅ Section-aware priority system (verses=1, bridges=2, choruses=3)
- ✅ Enhanced crossfades (standardized at 500ms) for smoother melodic transitions
- ✅ Triple-layer smoothing: section-aligned + beat-aligned + 500ms crossfades

**V6 Features:**
- ✅ Generate 10 diverse strategies, select top 3 by quality
- ✅ Regeneration excludes previously shown strategies
- ✅ Improved output variety

**Code Cleanup (2026-06-19):**
- ✅ Consolidated 6 strategy functions into 1 unified `generate_strategy()` function (-227 lines)
- ✅ Standardized crossfade durations at 500ms across all modules
- ✅ Fixed bug: output rendering was using 1000ms instead of 500ms crossfades
- ✅ Refactored `run_pipeline()` with helper functions for better modularity
- ✅ Added crossfade constants module with conversion utilities
- ✅ Implemented `--no-auto-protect` CLI flag to toggle intro/outro protection
- ✅ Eliminated 200+ lines of duplicate code
- ✅ See `CODE_CLEANUP_SUMMARY.md` for details

**Known Limitations:**
- Chorus detection requires: 12-30s duration, high energy (top 40%), ≥3 repetitions
- Some songs may not have detectable choruses (correctly identified as no-chorus structure)
