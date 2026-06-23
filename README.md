# Music Smart Trim

Intelligently trim or extend audio files to a target length while preserving musical quality. Uses advanced audio analysis and research-backed quality metrics to create natural-sounding edits.

## Features

- **Smart Trimming**: Automatically shorten audio while preserving choruses and musical structure
- **Smart Extension**: Intelligently lengthen audio by repeating suitable sections
- **Music-Aware**: Detects and respects song sections (intro, verse, chorus, bridge, outro)
- **Beat-Aligned**: All cuts aligned to beats for seamless transitions
- **Quality-Driven**: Research-backed metrics ensure high-quality output (3.2-3.9★ expected)

## Quick Start

### Requirements

- Python 3.8 or higher
- pip (Python package manager)

### Installation

```bash
# Clone the repository
git clone https://github.com/RitosEric/music-smart-trim.git
cd music-smart-trim

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Basic Usage

```bash
# Trim audio to 120 seconds
python -m src.cli --input song.mp3 --target 120

# Extend audio to 240 seconds
python -m src.cli --input song.mp3 --target 240
```

The program will generate 3 output files in the `output/` directory, ranked by quality.

## Usage Examples

### Trimming Audio

```bash
# Basic trim to 2 minutes
python -m src.cli --input song.mp3 --target 120

# Trim with better quality (slower, uses AI model)
python -m src.cli --input song.mp3 --target 120 --use-mert
```

### Extending Audio

```bash
# Extend to 4 minutes
python -m src.cli --input song.mp3 --target 240
```

### Protecting Regions

```bash
# Protect intro and outro from editing
python -m src.cli --input song.mp3 --target 120 --auto-protect

# Protect specific time ranges
python -m src.cli --input song.mp3 --target 120 --protect "0:00-0:30" "3:00-3:30"
```

## Command-Line Options

| Option                  | Description                              |
| ----------------------- | ---------------------------------------- |
| `--input PATH`          | Input audio file (required)              |
| `--target SECONDS`      | Target length in seconds (required)      |
| `--output-dir PATH`     | Output directory (default: `./output`)   |
| `--protect "START-END"` | Protect specific time ranges             |
| `--auto-protect`        | Automatically protect intro/outro        |
| `--use-mert`            | Use AI model for better quality (slower) |

## Output

The program generates 3 audio files ranked by quality:

```
output/
├── option_0_3.9stars.wav  # Best quality
├── option_1_3.7stars.wav  # Second best
└── option_2_3.5stars.wav  # Third best
```

Each file is rated on a 5-star scale based on:

- Musical coherence (beat alignment, section order)
- Transition smoothness (no audible cuts)
- Length accuracy (within ±15 seconds)

## How It Works

1. **Analysis**: Detects beats, tempo, and song structure
2. **Segment Detection**: Identifies repeated sections (verses, choruses)
3. **Strategy Generation**: Creates multiple editing strategies
4. **Quality Scoring**: Ranks strategies using research-backed metrics
5. **Rendering**: Applies edits with smooth crossfades

## Performance

- **Processing Time**: ~60-70 seconds for a 3-minute song
- **With --use-mert**: +20 seconds (first-time 360MB model download)
- **Quality**: 3.2-3.9★ typical output rating

## Troubleshooting

### "No module named 'src'"

Use `python -m src.cli` instead of `python src/cli.py`

### "File not found"

Provide full path to input file: `python -m src.cli --input /path/to/song.mp3 --target 120`

### Poor quality output

Try with `--use-mert` flag for better quality (requires download, slower)

## Supported Formats

**Input**: MP3, WAV, FLAC, M4A, OGG  
**Output**: WAV (high quality, uncompressed)

## Requirements

- Python 3.8+
- librosa >= 0.10.0
- pydub >= 0.25.0
- numpy >= 1.24.0
- scipy >= 1.10.0
- soundfile >= 0.12.0
- pyloudnorm >= 0.1.0

See `requirements.txt` for complete list.

## License

MIT License - see LICENSE file for details

## Acknowledgments

Built using research-backed audio analysis techniques:

- EBU R128 loudness standard
- MIREX beat tracking evaluation
- Self-similarity matrix analysis

Dependencies: librosa, pydub, numpy, scipy, soundfile, pyloudnorm
