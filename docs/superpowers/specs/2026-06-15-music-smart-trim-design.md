# Music Smart Trim - Design Specification

**Date:** 2026-06-15  
**Version:** 1.0  
**Status:** Approved

## Overview

Music Smart Trim is a Python-based tool that intelligently adjusts background music to a target length by detecting and manipulating repeated melodic sections. The system can both shorten music by removing repetitions and lengthen it by looping similar sections, while maintaining musical coherence and audio quality.

## Goals

- Process 3-minute songs in approximately 1 minute
- Generate 3 alternative trim options with quality ratings
- Ensure at least one option scores ≥4.5★ (out of 5★)
- All outputs within ±15 seconds of target length
- Support multiple audio formats (MP3, WAV, FLAC, M4A, OGG)
- Allow users to protect specific sections from modification
- Provide regeneration capability for different alternatives

## System Architecture

### Design Principle: Web-Ready Architecture

The system is designed with clean module separation to support future web deployment without refactoring core logic:

- **Core modules** (`audio_loader`, `spectral_analyzer`, `segment_matcher`, `trim_engine`, `quality_scorer`, `output_generator`) contain pure processing logic with no CLI dependencies
- **CLI wrapper** (`cli.py`) handles only command-line interaction and orchestration
- **Clean interfaces:** Each module accepts standard Python types (arrays, dicts) and returns structured data, not CLI-specific formats
- **State management:** Processing state can be serialized (for web sessions) via the metadata outputs
- **Future web backend** can import and use the same core modules, replacing only the CLI wrapper with HTTP endpoints

This architecture ensures the engine can be deployed as a web service by adding a Flask/FastAPI wrapper without touching the core processing pipeline.

### Pipeline Flow

```
Input Audio (MP3/WAV/FLAC/M4A/OGG)
    ↓
Audio Loader (normalize to 22050 Hz, check file size)
    ↓
Spectral Analyzer (CQT chroma features, self-similarity matrix)
    ↓
Segment Matcher (cosine similarity + DTW, find repeated patterns)
    ↓
Trim Engine (generate 3 strategies: conservative, balanced, aggressive)
    ↓
Quality Scorer (rate 0-100 → stars, ensure ≥1 option at 4.5★)
    ↓
Output Generator (3 audio files + metadata)
    ↓
User Review → Optional Regeneration
```

### Module Structure

The system is divided into focused modules to maintain code clarity and testability:

#### 1. `audio_loader.py`
**Responsibility:** Load and normalize audio files

- Load MP3, WAV, FLAC, M4A, OGG formats using `librosa` and `pydub`
- Normalize to 22050 Hz sample rate (optimal for melodic analysis)
- Convert to mono channel for spectral analysis
- File size validation: if normalized audio exceeds 15MB, apply compression or warn user
- Return: NumPy array of audio samples + sample rate

#### 2. `spectral_analyzer.py`
**Responsibility:** Extract melodic features and identify structure

**Method:** CQT-based chroma analysis with self-similarity matrix
- Extract CENS (Chroma Energy Normalized Statistics) features
- Build self-similarity matrix (SSM) using cosine distance between chroma vectors
- Apply diagonal smoothing to detect repeated melodic segments
- Extract diagonal lines in SSM indicating repetitions

**Parameters:**
- `hop_length=2048` (balance speed vs resolution)
- `n_chroma=12` (standard semitone resolution)
- `frame_size=4096` (frequency resolution)
- Minimum segment duration: 4-8 seconds (avoid transients)

**Return:** Timestamped feature vectors + list of repeated segment pairs

**Rationale:** Based on music information retrieval (MIR) research, CQT chroma features capture harmonic/melodic content while being invariant to timbre changes. Self-similarity matrix approach is proven in structure analysis tasks with 85-90% accuracy.

#### 3. `segment_matcher.py`
**Responsibility:** Match similar melodic patterns across the track

- Use cosine similarity (threshold 0.7-0.85) for initial matching
- Apply constrained Dynamic Time Warping (DTW) for tempo-flexible alignment
- Cluster similar segments using agglomerative clustering
- Identify musical sections (intro, verse, chorus, bridge, outro)
- Track user-specified protected regions
- Use `librosa.segment` for recurrence matrix and structure detection

**Return:** Segment map with similarity scores, section labels, protected flags

#### 4. `trim_engine.py`
**Responsibility:** Generate trim/extend strategies

**Three strategy types per generation:**

1. **Conservative:** Minimal cuts only at clear section boundaries
   - Remove only highly similar repeated sections
   - Prefer longer segments with clean boundaries
   - Use gentle crossfades (200-500ms)

2. **Balanced:** Moderate repetition removal with smart fades
   - Balance between length accuracy and musical flow
   - Mix cuts and crossfades
   - Standard fade duration (100-200ms)

3. **Aggressive:** Maximum trimming with short crossfades
   - Remove more repeated content
   - Tighter cuts with shorter crossfades (50-100ms)
   - May sacrifice some musical flow for length accuracy

**Constraints:**
- All 3 options must be within ±15 seconds of target length
- Never modify protected regions
- Fallback: if error exceeds 15 seconds, apply fade-out to reach target
- Each strategy tracks: cut points, loop points, fade regions, protected regions

**Return:** 3 strategy objects with detailed edit instructions

#### 5. `quality_scorer.py`
**Responsibility:** Rate each trim option

**Scoring system (0-100 points → star rating):**

**Star conversion:**
- 5★ = 90-100 points
- 4.5★ = 85-89 points
- 4★ = 80-84 points
- 3.5★ = 75-79 points
- 3★ = 70-74 points
- <3★ = <70 points

**Component scoring (weighted):**

**Transition Smoothness (40 points max):**
- Phase alignment at cut/loop points (15 pts): cross-correlation to align waveforms
- Zero-crossing detection at splice points (10 pts): avoid audible clicks
- Fade quality for unnatural cuts (15 pts): check fade curve smoothness

**Musical Coherence (40 points max):**
- Cuts at measure/phrase boundaries (20 pts): align with beat grid from `librosa.beat.beat_track`
- Maintains harmonic progression (10 pts): check chroma feature continuity across cuts
- Section order makes sense (10 pts): preserve intro→verse→chorus flow

**Length Accuracy (20 points max):**
- ±0-3 seconds: 20 pts
- ±3-8 seconds: 15 pts
- ±8-15 seconds: 10 pts
- >15 seconds: 0 pts (should not occur due to constraint)

**Quality guarantee:** If no option reaches 4.5★ (85+ points), regenerate with alternative strategies. After 5 attempts, return best 3 options with warning.

**Return:** Score breakdown + final star rating for each option

#### 6. `output_generator.py`
**Responsibility:** Render final audio files and metadata

- Apply edit instructions (cuts, loops, fades) from each strategy
- Export 3 trimmed audio files in original format
- Filename format: `option_{N}_{rating}stars.{ext}`
- Generate `summary.json`: detailed metadata (cut points, loop regions, score breakdown)
- Generate `summary.txt`: human-readable report
- Include: star rating, strategy type, actual length, number of cuts/loops

**Return:** List of output file paths

#### 7. `cli.py`
**Responsibility:** Command-line interface and orchestration

- Parse command-line arguments
- Orchestrate pipeline: loader → analyzer → matcher → engine → scorer → generator
- Display results with ratings
- Handle regeneration requests interactively
- Manage error handling and user feedback

## Command-Line Interface

### Basic Usage

```bash
python cli.py --input song.mp3 --target 120 --protect "0:30-1:15,2:00-2:30"
```

### Arguments

**Required:**
- `--input`: Path to audio file (MP3/WAV/FLAC/M4A/OGG)
- `--target`: Target length in seconds

**Optional:**
- `--protect`: Comma-separated timestamp ranges to preserve (format: `MM:SS-MM:SS`)
- `--output-dir`: Directory for output files (default: `./output`)

### Workflow

**1. Initial Run**
Script analyzes audio and generates 3 options with ratings

**2. Results Display**
```
Processing complete! (58.3 seconds)

Option 1: ★★★★★ 4.5 (strategy: balanced, length: 2:02, cuts: 3, loops: 1)
Option 2: ★★★★☆ 4.0 (strategy: conservative, length: 2:05, cuts: 2, loops: 0)
Option 3: ★★★½☆ 3.5 (strategy: aggressive, length: 1:58, cuts: 4, loops: 2)

Files saved to: ./output/
- option_1_4.5stars.mp3
- option_2_4.0stars.mp3
- option_3_3.5stars.mp3
- summary.json
- summary.txt

Regenerate for 3 new options? (y/n):
```

**3. Regeneration**
User types `y` to generate 3 new alternatives with different strategies. Each regeneration uses different combinations of cut points, fade durations, and segment selections.

### Output Files

**Audio files:**
- 3 trimmed versions with star rating in filename
- Same format as input file
- Preserved metadata (artist, album, etc.) where possible

**Metadata files:**
- `summary.json`: machine-readable with full details
  ```json
  {
    "input_file": "song.mp3",
    "target_length": 120,
    "protected_regions": [[30, 75], [120, 150]],
    "processing_time": 58.3,
    "options": [
      {
        "number": 1,
        "rating_stars": 4.5,
        "rating_points": 87,
        "strategy": "balanced",
        "actual_length": 122,
        "cuts": [...],
        "loops": [...],
        "fades": [...]
      }
    ]
  }
  ```
- `summary.txt`: human-readable report with recommendations

## Error Handling & Edge Cases

### File Validation
- **Unsupported format:** Clear error message listing supported formats
- **Corrupted audio:** Catch `librosa`/`pydub` exceptions, report specific issue
- **File size >15MB after normalization:** Apply additional compression or warn user

### Target Length Constraints
- **Target longer than achievable:** Warn "cannot extend beyond X seconds with current repeats"
- **Target shorter than protected regions:** Error "protected regions total Y seconds, cannot trim to X seconds"
- **No repeated sections found:** Fall back to simple fade-out strategy, warn user about limited options

### Protected Regions
- **Invalid timestamp format:** Parse error with example format
- **Overlapping protected regions:** Merge automatically and notify user
- **Protected region outside audio duration:** Warn and ignore invalid region

### Quality Requirements
- **Cannot generate ≥4.5★ after 5 attempts:** Return best 3 options available with warning message
- **Processing timeout (>90 seconds):** Abort gracefully, return partial results if available

### Audio Processing Issues
- **Phase misalignment causing clicks:** Automatically increase crossfade duration
- **Beat detection fails:** Fall back to fixed-interval segmentation (4-second windows)
- **Insufficient memory for large files:** Process in chunks or request user to provide smaller file

## Technical Dependencies

### Required Python Libraries
- `librosa>=0.10.0` - Audio analysis and feature extraction
- `pydub>=0.25.0` - Multi-format audio loading
- `numpy>=1.24.0` - Numerical operations
- `scipy>=1.10.0` - Signal processing and DTW
- `soundfile>=0.12.0` - Audio I/O

### Optional (for format support)
- `ffmpeg` - Required by pydub for MP3, M4A, OGG
- `audioread` - Alternative audio backend

### Python Version
- Python 3.8+ (for librosa compatibility)

## Performance Targets

- **3-minute song:** ~60 seconds processing time
- **Memory usage:** <500MB peak for typical files
- **File size limit:** 15MB after normalization
- **Concurrent processing:** Single-threaded (sufficient for CLI tool)

## Testing Strategy

### Unit Tests (per module)
- `test_audio_loader.py`: Format support, normalization, file size checks
- `test_spectral_analyzer.py`: Chroma extraction, SSM generation, segment detection
- `test_segment_matcher.py`: Similarity matching, clustering, protected regions
- `test_trim_engine.py`: Strategy generation, constraint enforcement
- `test_quality_scorer.py`: Scoring components, star conversion
- `test_output_generator.py`: File rendering, metadata generation

### Integration Tests
- End-to-end pipeline with sample audio files
- Verify all 3 options within ±15 seconds
- Verify at least one option ≥4.5★
- Protected regions properly honored
- Regeneration produces different results

### Test Audio Files
- Short (30s), medium (3min), long (10min) tracks
- Different genres (pop, classical, electronic)
- Various formats (MP3, WAV, FLAC)
- Edge cases: no repetition, highly repetitive, complex structure

## Future Enhancements (Out of Scope for v1)

- Web interface for visual waveform annotation
- Real-time preview during generation
- Batch processing multiple files
- Advanced options (quality vs speed trade-off)
- Custom strategy configuration
- Export to video editing software formats
- AI-based quality prediction before rendering

## Success Criteria

1. ✅ Process 3-minute songs in ~60 seconds
2. ✅ Generate 3 options, at least 1 with ≥4.5★ rating
3. ✅ All outputs within ±15 seconds of target
4. ✅ Support MP3, WAV, FLAC, M4A, OGG formats
5. ✅ Respect user-protected regions
6. ✅ Enable regeneration for alternative options
7. ✅ Modular codebase (no 5000-line scripts)
8. ✅ CLI-based interaction for testing

## References

### Music Information Retrieval Research
- Müller & Ewert (2011): "Chroma Toolbox: MATLAB implementations for extracting variants of chroma-based audio features"
- Foote (1999): "Visualizing music and audio using self-similarity"
- Nieto & Bello (2016): "Systematic exploration of computational music structure research"
- McFee et al. (2015): "librosa: Audio and music signal analysis in Python"

### Key Techniques
- CQT-based chroma features for melodic analysis
- Self-similarity matrix for structure detection
- Dynamic Time Warping for tempo-flexible matching
- Beat tracking for musically-aware segmentation
