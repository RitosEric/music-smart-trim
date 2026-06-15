# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Music Smart Trim intelligently adjusts background music to target length by detecting and manipulating repeated melodic sections using spectral analysis.

## Development Commands

### Run Tests
```bash
pytest tests/ -v                              # All tests
pytest tests/test_audio_loader.py -v          # Specific module
pytest tests/ --cov=src --cov-report=term     # With coverage
```

### Run CLI
```bash
python src/cli.py --input song.mp3 --target 120
python src/cli.py --input song.mp3 --target 120 --protect "0:30-1:15"
```

### Generate Test Fixtures
```bash
# 30-second test file
python -c "
import numpy as np, soundfile as sf
sr = 22050; t = np.linspace(0, 30, sr * 30)
audio = np.concatenate([np.sin(2*np.pi*440*t[:sr*10]), np.sin(2*np.pi*523*t[:sr*10]), np.sin(2*np.pi*440*t[:sr*10])])
sf.write('tests/fixtures/sample_30s.wav', audio * 0.3, sr)
"

# 3-minute test file
python -c "
import numpy as np, soundfile as sf
sr = 22050; t = np.linspace(0, 30, sr * 30)
melody = np.concatenate([np.sin(2*np.pi*440*t), np.sin(2*np.pi*523*t), np.sin(2*np.pi*440*t), 
                         np.sin(2*np.pi*523*t), np.sin(2*np.pi*587*t), np.sin(2*np.pi*440*t)])
sf.write('tests/fixtures/sample_3min.wav', melody * 0.3, sr)
"
```

## Architecture

**6-stage pipeline with 7 modules:**

```
Audio (MP3/WAV/FLAC/M4A/OGG)
  ↓ audio_loader: Load, normalize to 22050Hz mono, validate size
  ↓ spectral_analyzer: Extract chroma, build SSM, detect repetitions
  ↓ segment_matcher: Parse protected regions, filter, cluster
  ↓ trim_engine: Generate 3 strategies (conservative/balanced/aggressive)
  ↓ quality_scorer: Rate on 100pt scale (40% transition, 40% coherence, 20% length)
  ↓ output_generator: Render audio, save with metadata
  ↓ cli: Orchestrate pipeline, ensure ≥4.5★, handle regeneration
```

## Module Interfaces

**audio_loader.py**
- `load_audio(file_path, target_sr=22050) -> (audio_data, sr)`
- `check_normalized_size(audio_data, sr, max_mb=15.0) -> (is_valid, size_mb)`

**spectral_analyzer.py**
- `extract_chroma_features(audio_data, sr, hop_length=2048) -> chroma`
- `build_self_similarity_matrix(chroma) -> ssm`
- `detect_repeated_segments(ssm, sr, hop_length, min_duration=4.0, threshold=0.8) -> List[Dict]`
- `analyze_audio_structure(audio_data, sr) -> Dict[chroma, ssm, repeated_segments]`

**segment_matcher.py**
- `parse_protected_regions(regions_str) -> List[Tuple[float, float]]`
- `is_segment_protected(start, end, protected) -> bool`
- `cluster_similar_segments(segments, threshold=0.8) -> List[Dict]`
- `match_segments(repeated_segments, protected_str) -> Dict[clusters, protected_regions, filtered_segments]`

**trim_engine.py**
- `TrimStrategy` dataclass: name, cut_points, loop_points, fade_regions, target_length
- `generate_trim_strategies(clusters, original_length, target_length, protected) -> List[TrimStrategy]`

**quality_scorer.py**
- `points_to_stars(points) -> float` (≥90→5.0, ≥85→4.5, ≥80→4.0, etc.)
- `score_strategy(strategy, audio_data, sr, chroma, original_length) -> Dict[total_points, star_rating, breakdown]`

**output_generator.py**
- `render_strategy(audio_data, sr, strategy) -> np.ndarray`
- `generate_outputs(audio_data, sr, strategies, scores, output_dir, ...) -> Dict[audio_files, summary_json, summary_txt]`

**cli.py**
- `run_pipeline(input_file, target_length, protected_regions, output_dir) -> Dict[strategies, scores, output_files, processing_time]`

## Key Constraints

- All outputs within ±15 seconds of target length
- At least one option ≥4.5★ (85+ points)
- Processing time: ~60 seconds for 3-minute song
- File size limit: 15MB after normalization (warning if exceeded)
- Protected regions never modified

## Key Design Principles

- **DRY**: Single responsibility per module, no code duplication
- **YAGNI**: Only features from spec, no premature optimization
- **TDD**: All modules have comprehensive tests (63 tests total)
- **Web-Ready**: Core modules accept standard Python types, no CLI dependencies

## Common Development Tasks

### Add New Strategy Type
1. Add function to `src/trim_engine.py`: `generate_experimental_strategy()`
2. Update `generate_trim_strategies()` to include new strategy
3. Add tests in `tests/test_trim_engine.py`

### Modify Quality Scoring
1. Change component max points in `src/quality_scorer.py` (must sum to 100)
2. Adjust star thresholds in `points_to_stars()`
3. Update tests to match new thresholds

### Support New Audio Format
1. Check librosa supports the format
2. Add to `SUPPORTED_FORMATS` in `src/audio_loader.py`
3. Add test fixture and test

### Adjust Constraint Thresholds
- **Length tolerance (±15s)**: Edit `generate_trim_strategies()` in `trim_engine.py`
- **Quality guarantee (≥4.5★)**: Edit `run_pipeline()` in `cli.py`
- **Processing time**: Increase `hop_length` in `spectral_analyzer.py` (2048 → 4096)
- **File size limit (15MB)**: Edit `check_normalized_size()` in `audio_loader.py`

## Testing Strategy

- **Unit tests**: Each module has dedicated test file (7 test files)
- **Integration tests**: End-to-end pipeline in `test_integration.py`
- **Test fixtures**: `sample_30s.wav` (unit), `sample_3min.wav` (integration)
- **Coverage goal**: >80% for core modules (currently 86%)

## Future Web Deployment

Core modules are web-ready. Example FastAPI endpoint:

```python
from fastapi import FastAPI, UploadFile
from src.audio_loader import load_audio
from src.spectral_analyzer import analyze_audio_structure
from src.segment_matcher import match_segments
from src.trim_engine import generate_trim_strategies
from src.quality_scorer import score_strategy
from src.output_generator import render_strategy

app = FastAPI()

@app.post("/api/trim")
async def trim_audio(file: UploadFile, target_length: float = 120):
    # Save uploaded file temporarily
    audio_data, sr = load_audio(file.file)
    
    # Run pipeline
    analysis = analyze_audio_structure(audio_data, sr)
    match_result = match_segments(analysis['repeated_segments'], "")
    strategies = generate_trim_strategies(match_result['clusters'], len(audio_data)/sr, target_length, [])
    scores = [score_strategy(s, audio_data, sr, analysis['chroma'], len(audio_data)/sr) for s in strategies]
    
    # Render best strategy
    best_idx = max(range(len(scores)), key=lambda i: scores[i]['star_rating'])
    rendered = render_strategy(audio_data, sr, strategies[best_idx])
    
    return {
        'audio': rendered.tobytes(),
        'rating': scores[best_idx]['star_rating'],
        'length': strategies[best_idx].calculate_resulting_length(len(audio_data)/sr)
    }
```

No refactoring required - modules already accept standard Python types and return structured data.

## Troubleshooting

**ImportError when running CLI**: Use `PYTHONPATH=. python src/cli.py ...`

**Tests fail on fresh clone**: Generate test fixtures first (see commands above)

**Low quality scores (<4.5★)**: Check if audio has sufficient repeated segments. Short or highly varied audio may not have detectable repetitions.

**Processing too slow**: Increase `hop_length` in spectral analyzer (trades accuracy for speed)

**Memory issues with large files**: Check file size after normalization with `check_normalized_size()`. Consider downsampling or compression for files >15MB.
