# Music Smart Trim

A simple tool to intelligently trim or extend audio files while preserving musical quality.

## Features

- **Smart Trimming**: Automatically shorten audio while preserving choruses
- **Smart Extension**: Intelligently lengthen audio by repeating suitable sections
- **Music-Aware**: Detects song sections (intro, verse, chorus, bridge, outro)
- **Beat-Aligned**: All cuts aligned to beats for seamless transitions

## Installation

```bash
git clone https://github.com/RitosEric/music-smart-trim.git
cd music-smart-trim

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Usage

```bash
# Trim audio to 120 seconds
python -m src.cli --input song.mp3 --target 120

# Extend audio to 240 seconds
python -m src.cli --input song.mp3 --target 240

# With better quality (slower)
python -m src.cli --input song.mp3 --target 120 --use-mert
```

## Options

| Option | Description |
|--------|-------------|
| `--input PATH` | Input audio file (required) |
| `--target SECONDS` | Target length in seconds (required) |
| `--output-dir PATH` | Output directory (default: `./output`) |
| `--protect "START-END"` | Protect specific time ranges |
| `--auto-protect` | Automatically protect intro/outro |
| `--use-mert` | Use AI model for better quality |

## Output

The program generates 3 audio files ranked by quality in the `output/` directory.

## Requirements

- Python 3.8+
- See `requirements.txt` for dependencies

## License

MIT License - see LICENSE file

---

*A fun demo project for intelligent audio editing*
