# Music Smart Trim

Intelligently shorten audio files while preserving musical quality and structure. Music Smart Trim analyzes audio, detects repeated segments, and generates multiple trim options with quality ratings, using **beat-aligned cutting**, **section-aware editing**, and **constant-power crossfading** for professional results.

## Features

- **Intelligent Analysis**: Detects repeated segments using spectral analysis (15s+ phrases, 0.75 similarity)
- **Section-Aware Cutting**: Aligns cuts to song sections (intro/verse/chorus/bridge/outro) and bar boundaries
- **Strict Length Control**: ±15s accuracy through iterative refinement (V5)
- **Enhanced Quality Scoring**: Spectral flux, loudness consistency, and optional MERT embeddings (V5)
- **Beat-Aligned Editing**: All cuts aligned to bar boundaries, maintains rhythmic flow
- **Constant-Power Crossfading**: Professional DJ-quality seamless transitions (500ms)
- **Multiple Strategies**: Generates 3 trim options (conservative, balanced, aggressive)
- **Quality Ratings**: Each option rated 0.0-5.0 stars (0.1 increments) based on coherence, transitions, and length
- **Protected Regions**: Automatically protects intro/outro, supports custom protection
- **Interactive Regeneration**: Generate alternative options with different trim strategies

## What's New in V5 (Enhanced Quality & Strict Length Control)

✨ **Strict ±15s Length Enforcement** - Iterative refinement ensures all outputs within target ±15s  
✨ **Enhanced Quality Scoring** - Spectral flux and loudness consistency analysis  
✨ **Optional MERT Embeddings** - AI-powered transition quality assessment (`--use-mert`)  
✨ **Normalized Star Ratings** - Full 0.0-5.0 scale with 0.1 increments  
✨ **Realistic Quality Thresholds** - Adjusted for real-world music complexity

See `V5_IMPLEMENTATION_COMPLETE.md` for technical details.

## Requirements

- Python 3.8 or higher
- FFmpeg (for audio file support)

### Install FFmpeg

**macOS:**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt-get install ffmpeg
```

**Windows:**
Download from [ffmpeg.org](https://ffmpeg.org/download.html)

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/music-smart-trim.git
cd music-smart-trim

# Install dependencies
pip install -r requirements.txt

# Optional: Install as editable package (avoids PYTHONPATH prefix)
pip install -e .
```

## Usage

### Basic Usage

Trim audio to target length:

```bash
PYTHONPATH=. python src/cli.py --input song.mp3 --target 120
```

### With MERT Embeddings (Better Quality)

Use AI-powered quality assessment for superior results:

```bash
PYTHONPATH=. python src/cli.py --input song.mp3 --target 120 --use-mert
```

**Note:** First run downloads MERT-95M model (~360MB). Adds ~10-20s processing time but improves quality by +0.2-0.4★.

### With Protected Regions

Preserve specific time ranges (in addition to auto-protected intro/outro):

```bash
PYTHONPATH=. python src/cli.py --input song.mp3 --target 120 --protect "0:00-0:30" "3:00-3:30"
```

### Custom Output Directory

```bash
PYTHONPATH=. python src/cli.py --input song.mp3 --target 120 --output-dir my_output
```

### Complete Example

```bash
PYTHONPATH=. python src/cli.py \
  --input examples/song.wav \
  --target 90 \
  --protect "0:00-0:15" "2:45-3:00" \
  --output-dir output/song_trimmed \
  --use-mert
```

The tool will:
1. Analyze the audio structure and detect sections
2. Generate 3 trim strategies with different aggressiveness
3. Score each option (0.0-5.0 stars) using enhanced heuristics
4. Save output files with quality ratings
5. Prompt for regeneration if you want alternatives

## Output Files

Each run creates 5 files in the output directory:

- `option_0_X.Xstars.wav` - Conservative trim (fewer cuts, preserves more structure)
- `option_1_X.Xstars.wav` - Balanced trim (moderate cuts)
- `option_2_X.Xstars.wav` - Aggressive trim (more cuts, closer to target)
- `summary.json` - Detailed results in JSON format
- `summary.txt` - Human-readable summary

### Example Output

```
output/
├── option_0_3.8stars.wav    # 107.8s, 2 cuts
├── option_1_3.3stars.wav    # 107.8s, 1 cut
├── option_2_3.3stars.wav    # 107.8s, 1 cut
├── summary.json
└── summary.txt
```

## How It Works

Music Smart Trim uses a 7-stage pipeline with research-backed music editing techniques:

1. **Audio Loading**: Load and validate input file (mono conversion, 22050Hz, size check)
2. **Spectral Analysis**: Extract chroma features and build self-similarity matrix to detect repetitions (min 15s segments, 0.75 similarity)
3. **Structure Detection**: Detect tempo, beats, bars, and label sections (intro/verse/chorus/bridge/outro)
4. **Segment Matching**: Cluster repeated segments, filter protected regions (auto-protects intro/outro)
5. **Strategy Generation**: Create 3 section-aware, beat-aligned trim strategies with iterative refinement (V5)
6. **Quality Scoring**: Rate each strategy on coherence (50%), transitions (30%), length (20%) with optional MERT embeddings
7. **Output Generation**: Render audio with constant-power crossfades (500ms), apply smooth intro/outro fades, save files

### Key Technical Features

- **Section-Aware Cutting** (V5): Aligns cuts to section boundaries (whole verses/choruses, not partial)
- **Iterative Length Refinement** (V5): Automatically adjusts cuts to meet ±15s target
- **Beat-Aligned Cutting**: Uses librosa beat tracker to align all cuts to downbeats (bar boundaries)
- **Constant-Power Crossfading**: Equal-power law (fade_out² + fade_in² = 1) maintains perceived loudness
- **Automatic Protection**: First/last 10% or 15s (whichever shorter) preserved as intro/outro
- **Enhanced Quality Heuristics** (V5): Spectral flux, loudness consistency, optional MERT embeddings
- **Normalized Star Ratings** (V5): Full 0.0-5.0 scale with 0.1 increment precision

## Quality Rating System

Each option receives a 0.0-5.0 star rating (0.1 increments) based on:

### Scoring Factors

- **Musical Coherence (50 points)**: Harmonic continuity, beat alignment, section preservation, cut patterns
- **Transition Smoothness (30 points)**: Zero-crossing alignment, crossfade quality, spectral flux, loudness consistency
- **Length Accuracy (20 points)**: How close to target length (strict ±15s enforcement)

### Star Conversion (V5 - Normalized)

Linear mapping: **100 points = 5.0 stars**, **20 points = 1 star**

- 5.0★: 100 points (perfect)
- 4.0★: 80 points (excellent)
- 3.5★: 70 points (good - realistic threshold)
- 3.0★: 60 points (acceptable)
- 2.0★: 40 points (fair)
- 1.0★: 20 points (poor)
- 0.0★: 0 points (failed)

The system automatically retries with different strategies if no option achieves 3.5+ stars (up to 5 retries).

## Constraints

- **Length Tolerance**: ±15s (strict enforcement via iterative refinement)
- **Processing Time**: ~60s for 3-minute audio without MERT, ~70s with MERT
- **File Size Limit**: Input files normalized to 15MB (resampled if needed)
- **Quality Threshold**: At least one option with ≥3.5★ rating (system retries up to 5 times)
- **Automatic Protection**: Intro (first 10%/15s) and outro (last 10%/15s) always preserved
- **Beat Alignment**: All cuts aligned to bar boundaries (4/4 time signature)

## Development

### Run Tests

Run full test suite:
```bash
pytest tests/ -v
```

Run specific test file:
```bash
pytest tests/test_audio_loader.py -v
```

Run with coverage:
```bash
pytest tests/ --cov=src --cov-report=html
```

### Project Structure

```
music-smart-trim/
├── src/
│   ├── audio_loader.py           # Audio loading and validation
│   ├── spectral_analyzer.py      # Chroma features and self-similarity
│   ├── structure_analyzer.py     # Beat detection and section labeling
│   ├── segment_matcher.py        # Segment clustering and filtering
│   ├── trim_engine.py            # Section-aware strategy generation with iterative refinement
│   ├── quality_scorer.py         # Enhanced quality rating with optional MERT embeddings
│   ├── crossfade.py              # Constant-power crossfading
│   ├── output_generator.py       # Audio rendering with crossfades
│   └── cli.py                    # Command-line interface with regeneration
├── tests/                        # Comprehensive test suite
├── examples/                     # Example audio files for testing
├── requirements.txt              # Python dependencies
├── README.md                     # This file
├── CLAUDE.md                     # Development guide for Claude Code
├── TESTING_GUIDE.md              # Test scenarios and procedures
└── V5_IMPLEMENTATION_COMPLETE.md # V5 technical documentation
```

## Performance (V5)

### Without MERT (Default)
- **Processing time:** ~60s for 3-min song (0.33x realtime)
- **Memory:** ~200MB peak
- **Quality:** 3.0-3.8★ typical
- **Length accuracy:** ±5-12s typical (100% within ±15s)

### With MERT (`--use-mert`)
- **Processing time:** ~70s for 3-min song (0.39x realtime)
- **Memory:** ~400MB peak (includes model)
- **Quality:** 3.2-4.0★ typical (+0.2-0.4★ improvement)
- **Length accuracy:** ±5-12s typical (100% within ±15s)
- **First-time setup:** 360MB model download

## Troubleshooting

**FFmpeg not found:**
- Install FFmpeg using package manager (see Requirements section)
- Ensure `ffmpeg` is in your PATH

**Import errors:**
- Always use `PYTHONPATH=.` when running the CLI
- Or install as package: `pip install -e .`

**Quality ratings below 3.5★:**
- Try increasing target length (less aggressive trimming)
- Use `--use-mert` for better quality assessment
- Use `--protect` to preserve critical sections
- Note: Complex songs may require ±10-15s deviation to maintain quality

**Length not meeting target:**
- V5 enforces ±15s strict tolerance (100% compliance in testing)
- If you need tighter tolerance, consider time-stretching (future feature)
- Song structure may limit how much can be removed while preserving quality

**MERT model download issues:**
- Requires internet connection for first-time download
- ~360MB download from Hugging Face
- Set `HF_TOKEN` environment variable for faster downloads
- Model cached in `~/.cache/huggingface/` for future use

**Processing too slow:**
- Use default mode (without `--use-mert`) for 15% faster processing
- Processing time scales with audio length (~20s per minute)
- Consider using shorter input files or more powerful hardware

**Non-interactive mode:**
- Tool detects piped stdin and exits after generating initial options
- Use `yes n | python src/cli.py ...` to auto-decline regeneration

## Version History

- **V5** (Current): Enhanced quality scoring + strict ±15s length enforcement + MERT embeddings + normalized 0.0-5.0 star scale
- **V4**: Section-aware cutting + back-to-back cuts + radio edit strategy
- **V3**: Beat-aligned cutting + constant-power crossfades
- **V2**: Quality scoring improvements
- **V1**: Initial release

## License

MIT License - see LICENSE file for details

## Contributing

Contributions welcome. Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass (`pytest tests/ -v`)
5. Submit a pull request

## Citation

If you use this tool in research or production, please cite:

```
Music Smart Trim: Section-Aware Audio Trimming with Beat Alignment and AI Quality Assessment
```
