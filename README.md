# Music Smart Trim

Intelligently shorten audio files while preserving musical quality. Music Smart Trim analyzes audio structure, detects repeated segments, and generates multiple trim options with quality ratings.

## Features

- **Intelligent Analysis**: Detects repeated segments using spectral analysis
- **Multiple Strategies**: Generates 3 trim options (conservative, balanced, aggressive)
- **Quality Ratings**: Each option rated 1-5 stars based on transition smoothness, musical coherence, and length accuracy
- **Protected Regions**: Preserve specific time ranges (intro, outro, key moments)
- **Regeneration**: Generate alternative options with different trim strategies
- **Automatic Crossfades**: Smooth transitions at cut points

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
```

## Usage

### Basic Usage

Trim audio to target length:

```bash
PYTHONPATH=. python src/cli.py --input song.mp3 --target 120
```

### With Protected Regions

Preserve intro and outro:

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
  --output-dir output/song_trimmed
```

The tool will:
1. Analyze the audio structure
2. Generate 3 trim strategies
3. Score each option (1-5 stars)
4. Save output files
5. Prompt for regeneration if you want alternatives

## Output Files

Each run creates 5 files in the output directory:

- `option_0_X.Xstars.wav` - Conservative trim (fewer cuts)
- `option_1_X.Xstars.wav` - Balanced trim (moderate cuts)
- `option_2_X.Xstars.wav` - Aggressive trim (more cuts)
- `summary.json` - Detailed results in JSON format
- `summary.txt` - Human-readable summary

### Example Output

```
output/
├── option_0_4.5stars.wav    # 118.2s, 2 cuts
├── option_1_4.0stars.wav    # 121.5s, 3 cuts
├── option_2_3.5stars.wav    # 119.8s, 4 cuts
├── summary.json
└── summary.txt
```

## How It Works

Music Smart Trim uses a 6-stage pipeline:

1. **Audio Loading**: Load and validate input file (mono conversion, size check)
2. **Spectral Analysis**: Extract chroma features and build self-similarity matrix
3. **Segment Matching**: Cluster repeated segments, filter protected regions
4. **Strategy Generation**: Create 3 trim strategies (conservative/balanced/aggressive)
5. **Quality Scoring**: Rate each strategy on transition smoothness, musical coherence, and length accuracy
6. **Output Generation**: Render audio with cuts/loops, apply crossfades, save files

## Quality Rating System

Each option receives a 1-5 star rating based on:

### Scoring Factors

- **Transition Smoothness (40 points)**: Zero-crossing alignment at cut points
- **Musical Coherence (40 points)**: Harmonic continuity, beat alignment, intro/outro preservation
- **Length Accuracy (20 points)**: How close to target length

### Star Conversion

- 5.0★: 95-100 points (excellent)
- 4.5★: 90-94 points (very good)
- 4.0★: 80-89 points (good)
- 3.5★: 70-79 points (acceptable)
- 3.0★: 60-69 points (fair)
- 2.5★: 50-59 points (poor)
- 2.0★: 40-49 points (very poor)
- 1.5★: 30-39 points (bad)
- 1.0★: 0-29 points (very bad)

The system automatically retries with different strategies if no option achieves 4.5+ stars.

## Constraints

- **Length Tolerance**: Results within ±15 seconds of target
- **Processing Time**: ~30-60 seconds for 3-minute audio
- **File Size Limit**: Input files normalized to 15MB (resampled if needed)
- **Quality Guarantee**: At least one option with ≥4.5★ rating (system retries up to 5 times)

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
│   ├── audio_loader.py       # Audio loading and validation
│   ├── spectral_analyzer.py  # Chroma features and self-similarity
│   ├── segment_matcher.py    # Segment clustering and filtering
│   ├── trim_engine.py        # Strategy generation
│   ├── quality_scorer.py     # Quality rating calculation
│   ├── output_generator.py   # Audio rendering and file output
│   └── cli.py               # Command-line interface
├── tests/                   # Comprehensive test suite
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

## License

MIT License - see LICENSE file for details

## Contributing

Contributions welcome. Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## Troubleshooting

**FFmpeg not found:**
- Install FFmpeg using package manager (see Requirements section)
- Ensure `ffmpeg` is in your PATH

**Import errors:**
- Always use `PYTHONPATH=.` when running the CLI
- Or install as package: `pip install -e .`

**Poor quality ratings:**
- Try increasing target length (less aggressive trimming)
- Use protected regions to preserve critical sections
- Use regeneration to get alternative trim strategies

**Processing too slow:**
- Processing time scales with audio length (~20s per minute of audio)
- Consider using shorter input files or more powerful hardware
