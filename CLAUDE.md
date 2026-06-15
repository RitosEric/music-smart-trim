# Music Smart Trim - Developer Guide

## Project Overview

Music Smart Trim is an intelligent audio trimming system that shortens music files while preserving musical quality. The system analyzes audio structure using spectral analysis, detects repeated segments, and generates multiple trim strategies with quality ratings.

**Key capabilities:**
- Multi-format audio support (MP3, WAV, FLAC, M4A, OGG)
- Intelligent segment detection via chroma features and self-similarity matrices
- Protected regions to preserve intro/outro or key moments
- Three trim strategies per run (conservative, balanced, aggressive)
- Quality rating system (1-5 stars) based on transition smoothness, musical coherence, and length accuracy
- Automatic retry with different strategies until ≥4.5★ rating achieved
- Regeneration support for alternative trim options

## Development Commands

### Run Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test module
pytest tests/test_audio_loader.py -v
pytest tests/test_spectral_analyzer.py -v
pytest tests/test_segment_matcher.py -v
pytest tests/test_trim_engine.py -v
pytest tests/test_quality_scorer.py -v
pytest tests/test_output_generator.py -v
pytest tests/test_integration.py -v

# Run single test
pytest tests/test_audio_loader.py::test_load_audio_mp3 -v

# Run with coverage
pytest tests/ --cov=src --cov-report=term-missing
pytest tests/ --cov=src --cov-report=html  # Generates htmlcov/index.html

# Run with short traceback (easier to read)
pytest tests/ -v --tb=short
```

### Run CLI

```bash
# Basic usage
PYTHONPATH=. python src/cli.py --input song.mp3 --target 120

# With protected regions
PYTHONPATH=. python src/cli.py --input song.mp3 --target 120 --protect "0:00-0:30" "3:00-3:30"

# Custom output directory
PYTHONPATH=. python src/cli.py --input song.mp3 --target 120 --output-dir my_output
```

### Generate Test Audio Fixtures

```bash
# Generate test fixtures (run from project root)
PYTHONPATH=. python tests/generate_fixtures.py

# This creates fixtures in tests/fixtures/:
# - test_audio.wav (3-minute test audio with repeated segments)
# - test_short.wav (30-second audio)
# - test_sine_wave.wav (10-second pure sine wave)
```

## Architecture

The system uses a 6-stage pipeline with 7 core modules:

```
┌─────────────┐
│ audio_loader│  Stage 1: Load and validate audio
└──────┬──────┘
       │ audio_data, sample_rate
       ▼
┌──────────────────┐
│spectral_analyzer │  Stage 2: Extract chroma, build SSM, detect repetitions
└──────┬───────────┘
       │ repeated_segments
       ▼
┌─────────────────┐
│ segment_matcher │  Stage 3: Parse protected regions, cluster segments
└──────┬──────────┘
       │ clusters, protected_regions
       ▼
┌──────────────┐
│ trim_engine  │  Stage 4: Generate 3 strategies (conservative/balanced/aggressive)
└──────┬───────┘
       │ strategies
       ▼
┌────────────────┐
│quality_scorer  │  Stage 5: Score each strategy (transition/coherence/length)
└──────┬─────────┘
       │ scores
       ▼
┌──────────────────┐
│output_generator  │  Stage 6: Render audio, apply cuts/fades, save files
└──────────────────┘

┌─────┐
│ cli │  Orchestrates pipeline, handles regeneration loop
└─────┘
```

### Module Descriptions

1. **audio_loader**: Multi-format audio loading with librosa backend, format validation, mono conversion, sample rate normalization (22050 Hz)

2. **spectral_analyzer**: Extracts 12-bin chroma features using CQT, builds self-similarity matrix (cosine similarity), detects repeated segments via diagonal scanning with configurable min duration and similarity threshold

3. **segment_matcher**: Parses MM:SS timestamp format, merges overlapping protected regions, clusters similar segments by proximity (2s window), filters segments that overlap protected regions

4. **trim_engine**: Generates 3 trim strategies with different aggressiveness levels (conservative: 5s buffer + 300ms fades, balanced: 3s buffer + 150ms fades, aggressive: 1s buffer + 75ms fades), enforces ±15s constraint with fade-out fallback

5. **quality_scorer**: Scores strategies on 100-point scale (40 pts transition smoothness: phase alignment + zero-crossing + fade quality, 40 pts musical coherence: beat alignment + harmonic continuity + section order, 20 pts length accuracy), converts to 0.5-5.0 star rating

6. **output_generator**: Renders strategies by applying loops → cuts → crossfades, saves WAV files with star ratings in filename, generates summary.json (machine-readable) and summary.txt (human-readable)

7. **cli**: Orchestrates full pipeline, implements auto-retry loop (up to 5 times) until ≥4.5★ achieved, handles regeneration with different seeds for variety, displays results with star symbols

## Data Flow

```
Input: audio_path, target_length, protected_regions
  ↓
audio_loader.load_audio()
  → audio_data: np.ndarray (mono, 22050 Hz)
  → sample_rate: int
  ↓
spectral_analyzer.analyze_audio_structure()
  → chroma: np.ndarray (12 × n_frames)
  → ssm: np.ndarray (n_frames × n_frames)
  → repeated_segments: List[Dict]
      - start_time_1, start_time_2, duration, similarity
  ↓
segment_matcher.match_segments()
  → clusters: List[Dict]
      - segment_times: List[(start, end)]
      - avg_similarity: float
      - duration: float
  → protected_regions: List[(start, end)]
  ↓
trim_engine.generate_trim_strategies()
  → strategies: List[TrimStrategy]
      - name: str (conservative/balanced/aggressive)
      - cut_points: List[(start, end)]
      - loop_points: List[(start, end, repeat_count)]
      - fade_regions: List[(fade_start, fade_end)]
      - target_length: float
  ↓
quality_scorer.score_strategy()
  → scores: List[Dict]
      - total_points: float (0-100)
      - star_rating: float (0.5-5.0)
      - breakdown: Dict
          - transition_smoothness: float (0-40)
          - musical_coherence: float (0-40)
          - length_accuracy: float (0-20)
  ↓
output_generator.generate_outputs()
  → Files:
      - option_0_{stars}stars.wav
      - option_1_{stars}stars.wav
      - option_2_{stars}stars.wav
      - summary.json
      - summary.txt
```

## Key Design Principles

### DRY (Don't Repeat Yourself)
- Each module has a single responsibility
- Shared utilities are centralized (timestamp parsing, numpy serialization)
- Strategy generation uses configurable parameters (buffers, fade durations)

### YAGNI (You Aren't Gonna Need It)
- No premature optimization (simple diagonal scanning for SSM)
- No unused abstractions (TrimStrategy is a dataclass, not a class hierarchy)
- No feature creep (protected regions use simple time ranges, no complex rule engines)

### TDD (Test-Driven Development)
- All modules have comprehensive unit tests (7 test files, 40+ tests)
- Integration tests verify end-to-end pipeline
- Fixtures generated programmatically for reproducibility

### Web-Ready Architecture
- Modular design allows easy API wrapping
- No global state or file system dependencies in core modules
- Pipeline function accepts all inputs as parameters
- Outputs can be streamed instead of saved to disk

## Key Constraints

### Length Tolerance: ±15 seconds
All strategies enforce this constraint via fade-out fallback. If a strategy exceeds ±15s error after applying cuts, trim_engine adds a final cut from target_length to end of audio.

### Quality Guarantee: ≥4.5 stars
CLI automatically retries with different seeds (up to 5 times) if initial run produces no options ≥4.5★. Retry changes cluster ordering and segment selection for variety.

### Processing Time: ~30-60 seconds for 3-minute audio
- Chroma extraction: ~10s (CQT is expensive)
- SSM computation: ~5s (O(n²) but n is small after downsampling)
- Segment detection: ~2s
- Strategy generation + scoring: ~3s
- Audio rendering: ~5s per option (15s total)
- Total: ~35s typical, ~60s worst case

### File Size Limit: 15MB normalized
Audio is resampled to 22050 Hz and converted to mono during load. This keeps memory usage predictable. Original high-quality audio can exceed 15MB, but normalized version won't.

### Protected Regions
Segments overlapping protected regions are filtered before clustering. Protected regions are merged if overlapping. CLI accepts "MM:SS-MM:SS" format.

## Module Interfaces

### audio_loader

```python
def load_audio(audio_path: Path, target_sr: int = 22050) -> Tuple[np.ndarray, int]:
    """
    Load audio file and normalize to target sample rate and mono.
    
    Args:
        audio_path: Path to audio file
        target_sr: Target sample rate (default: 22050 Hz)
    
    Returns:
        Tuple of (audio_data, sample_rate)
    
    Raises:
        AudioLoadError: If file not found or unsupported format
    """

def check_normalized_size(audio_data: np.ndarray, max_mb: float = 15.0) -> None:
    """
    Check if normalized audio data exceeds maximum size limit.
    
    Raises:
        ValueError: If audio data exceeds the size limit
    """

SUPPORTED_FORMATS = {'.mp3', '.wav', '.flac', '.m4a', '.ogg'}
```

### spectral_analyzer

```python
def extract_chroma_features(
    audio_data: np.ndarray,
    sample_rate: int,
    hop_length: int = 2048,
    n_chroma: int = 12
) -> np.ndarray:
    """
    Extract chroma features from audio using Constant-Q Transform.
    
    Returns:
        2D numpy array of shape (n_chroma, n_frames)
    """

def build_self_similarity_matrix(chroma: np.ndarray) -> np.ndarray:
    """
    Build self-similarity matrix using cosine similarity.
    
    Returns:
        2D numpy array of shape (n_frames, n_frames), values 0-1
    """

def detect_repeated_segments(
    ssm: np.ndarray,
    sample_rate: int = 22050,
    hop_length: int = 2048,
    min_segment_duration: float = 4.0,
    similarity_threshold: float = 0.8
) -> List[Dict]:
    """
    Detect repeated segments by scanning SSM for diagonal lines.
    
    Returns:
        List of dicts with keys: start_time_1, start_time_2, duration, similarity
    """

def analyze_audio_structure(
    audio_data: np.ndarray,
    sample_rate: int,
    hop_length: int = 2048,
    n_chroma: int = 12,
    min_segment_duration: float = 4.0,
    similarity_threshold: float = 0.8
) -> Dict:
    """
    Complete analysis pipeline: chroma → SSM → segment detection.
    
    Returns:
        Dict with keys: chroma, ssm, repeated_segments
    """
```

### segment_matcher

```python
def parse_protected_regions(protected_regions_str: List[str]) -> List[Tuple[float, float]]:
    """
    Parse protected regions from "MM:SS-MM:SS" format to (start_sec, end_sec) tuples.
    """

def merge_overlapping_regions(regions: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
    """
    Merge overlapping protected regions.
    """

def is_segment_protected(
    start_time: float,
    end_time: float,
    protected_regions: List[Tuple[float, float]]
) -> bool:
    """
    Check if a segment overlaps with any protected region.
    """

def cluster_similar_segments(
    repeated_segments: List[Dict],
    similarity_threshold: float = 0.8
) -> List[Dict]:
    """
    Cluster similar segments by proximity (2s window).
    
    Returns:
        List of cluster dicts with keys: segment_times, avg_similarity, duration
    """

def match_segments(
    repeated_segments: List[Dict],
    protected_regions_str: List[str],
    similarity_threshold: float = 0.8
) -> Dict:
    """
    Complete matching pipeline: parse → filter → cluster.
    
    Returns:
        Dict with keys: clusters, protected_regions, filtered_segments
    """
```

### trim_engine

```python
@dataclass
class TrimStrategy:
    name: str
    cut_points: List[Tuple[float, float]]
    loop_points: List[Tuple[float, float, int]]
    fade_regions: List[Tuple[float, float]]
    target_length: float
    
    def calculate_resulting_length(self, original_length: float) -> float:
        """Calculate resulting audio length after applying strategy."""

def generate_conservative_strategy(
    clusters: List[Dict],
    original_length: float,
    target_length: float,
    regenerate_seed: int = None
) -> TrimStrategy:
    """
    Conservative strategy: 5s buffer, 300ms fades, remove 2nd occurrence only.
    """

def generate_balanced_strategy(
    clusters: List[Dict],
    original_length: float,
    target_length: float,
    regenerate_seed: int = None
) -> TrimStrategy:
    """
    Balanced strategy: 3s buffer, 150ms fades, remove multiple occurrences.
    """

def generate_aggressive_strategy(
    clusters: List[Dict],
    original_length: float,
    target_length: float,
    regenerate_seed: int = None
) -> TrimStrategy:
    """
    Aggressive strategy: 1s buffer, 75ms fades, remove all but first occurrence.
    """

def generate_trim_strategies(
    clusters: List[Dict],
    original_length: float,
    target_length: float,
    regenerate_seed: int = None
) -> List[TrimStrategy]:
    """
    Generate all three strategies and enforce ±15s constraint.
    
    Returns:
        List of 3 TrimStrategy objects (conservative, balanced, aggressive)
    """
```

### quality_scorer

```python
def score_transition_smoothness(
    audio: np.ndarray,
    sr: int,
    cut_points: List[Tuple[float, float]],
    fade_regions: List[Tuple[float, float]]
) -> float:
    """
    Score transition smoothness (max 40 points).
    Components: phase alignment (15), zero-crossing (10), fade quality (15).
    """

def score_musical_coherence(
    audio: np.ndarray,
    sr: int,
    cut_points: List[Tuple[float, float]]
) -> float:
    """
    Score musical coherence (max 40 points).
    Components: beat alignment (20), harmonic continuity (10), section order (10).
    """

def score_length_accuracy(target_length: float, resulting_length: float) -> float:
    """
    Score length accuracy (max 20 points).
    Thresholds: ±0-3s → 20pts, ±3-8s → 15pts, ±8-15s → 10pts, >±15s → 0pts.
    """

def score_strategy(
    strategy: TrimStrategy,
    audio: np.ndarray,
    sr: int,
    original_length: float
) -> Dict:
    """
    Score a complete trim strategy.
    
    Returns:
        Dict with keys: total_points (0-100), star_rating (0.5-5.0), breakdown
    """

def points_to_stars(points: float) -> float:
    """
    Convert points (0-100) to star rating (0.5-5.0).
    Thresholds: ≥90→5.0★, ≥85→4.5★, ≥80→4.0★, ≥75→3.5★, ≥70→3.0★, etc.
    """
```

### output_generator

```python
def apply_cuts(audio: np.ndarray, sr: int, cut_points: List[Tuple[float, float]]) -> np.ndarray:
    """Apply cuts to audio by removing specified regions."""

def apply_loops(audio: np.ndarray, sr: int, loop_points: List[Tuple[float, float, int]]) -> np.ndarray:
    """Apply loops to audio by repeating specified segments."""

def apply_crossfades(audio: np.ndarray, sr: int, fade_regions: List[Tuple[float, float]]) -> np.ndarray:
    """Apply crossfades to audio using linear fade curves."""

def render_strategy(strategy: TrimStrategy, audio: np.ndarray, sr: int) -> np.ndarray:
    """
    Render a complete trim strategy by applying loops → cuts → fades.
    """

def generate_outputs(
    audio: np.ndarray,
    sr: int,
    strategies: List[TrimStrategy],
    scores: List[Dict],
    output_dir: Path,
    input_file: str,
    target_length: float,
    protected_regions: List[Tuple[float, float]],
    processing_time: float
) -> None:
    """
    Generate output files for all strategies with metadata.
    Creates: option_{i}_{stars}stars.wav, summary.json, summary.txt
    """
```

### cli

```python
def run_pipeline(
    audio_path: Path,
    target_length: float,
    protected_regions: List[str],
    output_dir: Path,
    regenerate_seed: Optional[int] = None
) -> Dict:
    """
    Run complete pipeline from audio loading to output generation.
    Automatically retries up to 5 times if no option scores ≥4.5★.
    
    Returns:
        Dict with keys: strategies, scores, output_files, processing_time, original_length
    """

def main():
    """
    Main CLI entry point with regeneration loop.
    Prompts user for regeneration after each run.
    """
```

## Testing Strategy

### Unit Tests
Each module has isolated unit tests with mocked dependencies:
- `test_audio_loader.py`: Format validation, error handling, mono conversion
- `test_spectral_analyzer.py`: Chroma extraction, SSM computation, segment detection
- `test_segment_matcher.py`: Timestamp parsing, region merging, clustering, filtering
- `test_trim_engine.py`: Strategy generation, length calculation, constraint enforcement
- `test_quality_scorer.py`: Component scoring, star conversion, edge cases
- `test_output_generator.py`: Audio rendering, cut/loop/fade application, file generation

### Integration Tests
`test_integration.py` tests the complete pipeline with real audio fixtures:
- End-to-end pipeline execution
- Multi-format audio support
- Protected regions handling
- Regeneration with different seeds
- Quality guarantee (≥4.5★ retry loop)

### Fixtures
Test fixtures are generated programmatically in `tests/generate_fixtures.py`:
- `test_audio.wav`: 3-minute audio with repeated segments (for segment detection tests)
- `test_short.wav`: 30-second audio (for edge case tests)
- `test_sine_wave.wav`: 10-second pure sine wave (for algorithm validation)

### Coverage Goals
- Line coverage: >80% for core modules
- Branch coverage: >70% for core logic
- Critical paths: 100% (audio loading, strategy generation, scoring)

### Running Tests Locally
```bash
# Quick validation (no coverage)
pytest tests/ -v --tb=short

# Full validation with coverage
pytest tests/ --cov=src --cov-report=term-missing --cov-report=html

# Continuous testing during development
pytest tests/ -v --tb=short -x  # Stop on first failure
```

## Common Development Tasks

### Adding a New Strategy Type

1. Add strategy function to `src/trim_engine.py`:
```python
def generate_experimental_strategy(
    clusters: List[Dict],
    original_length: float,
    target_length: float,
    regenerate_seed: int = None
) -> TrimStrategy:
    # Your strategy logic here
    return TrimStrategy(
        name="experimental",
        cut_points=cut_points,
        loop_points=loop_points,
        fade_regions=fade_regions,
        target_length=target_length
    )
```

2. Update `generate_trim_strategies()` to include new strategy:
```python
experimental = generate_experimental_strategy(
    clusters, original_length, target_length,
    regenerate_seed=(regenerate_seed + 3) if regenerate_seed is not None else None
)
strategies = [conservative, balanced, aggressive, experimental]
```

3. Add tests in `tests/test_trim_engine.py`:
```python
def test_generate_experimental_strategy():
    # Test your strategy
    pass
```

### Modifying Scoring Weights

Edit `src/quality_scorer.py`:

1. Change component max points (must sum to 100):
```python
def score_strategy(...):
    # Current: 40% transition, 40% coherence, 20% length
    # To change: modify score_transition_smoothness() max (40 pts)
    #            modify score_musical_coherence() max (40 pts)
    #            modify score_length_accuracy() max (20 pts)
```

2. Adjust star conversion thresholds in `points_to_stars()`:
```python
def points_to_stars(points: float) -> float:
    if points >= 95:  # Stricter 5-star threshold
        return 5.0
    elif points >= 88:  # Stricter 4.5-star threshold
        return 4.5
    # ...
```

3. Update tests to match new thresholds:
```python
def test_points_to_stars():
    assert points_to_stars(95) == 5.0
    assert points_to_stars(88) == 4.5
```

### Supporting a New Audio Format

1. Check if librosa supports the format (likely yes for common formats)

2. Add format to `SUPPORTED_FORMATS` in `src/audio_loader.py`:
```python
SUPPORTED_FORMATS = {'.mp3', '.wav', '.flac', '.m4a', '.ogg', '.aac'}
```

3. Add test fixture and test in `tests/test_audio_loader.py`:
```python
def test_load_audio_aac(tmp_path):
    # Create test AAC file
    # Test loading
    pass
```

### Adjusting Constraint Thresholds

**Length tolerance (±15s):**
- Edit `generate_trim_strategies()` in `src/trim_engine.py`:
```python
if error > 15.0:  # Change threshold here
```

**Quality guarantee (≥4.5★):**
- Edit `run_pipeline()` in `src/cli.py`:
```python
if max_rating < 4.5:  # Change threshold here
```

**Processing time optimization:**
- Reduce chroma hop_length (faster but less accurate):
```python
# In spectral_analyzer.py
chroma = librosa.feature.chroma_cqt(
    y=audio_data,
    sr=sample_rate,
    hop_length=4096,  # Default: 2048, larger = faster
    n_chroma=12
)
```

**File size limit (15MB):**
- Edit `check_normalized_size()` in `src/audio_loader.py`:
```python
def check_normalized_size(audio_data: np.ndarray, max_mb: float = 20.0):  # Increase limit
```

### Debugging Strategies

**View detailed scoring breakdown:**
```python
# Add to cli.py after scoring:
for strategy, score in zip(strategies, scores):
    print(f"\n{strategy.name}:")
    print(f"  Transition: {score['breakdown']['transition_smoothness']:.1f}/40")
    print(f"  Coherence: {score['breakdown']['musical_coherence']:.1f}/40")
    print(f"  Length: {score['breakdown']['length_accuracy']:.1f}/20")
```

**Visualize self-similarity matrix:**
```python
import matplotlib.pyplot as plt

# After spectral analysis:
plt.figure(figsize=(10, 10))
plt.imshow(ssm, cmap='hot', origin='lower')
plt.colorbar()
plt.title('Self-Similarity Matrix')
plt.savefig('ssm.png')
```

**Inspect detected segments:**
```python
# After segment detection:
for i, seg in enumerate(repeated_segments):
    print(f"Segment {i}:")
    print(f"  Time 1: {seg['start_time_1']:.2f}s - {seg['start_time_1'] + seg['duration']:.2f}s")
    print(f"  Time 2: {seg['start_time_2']:.2f}s - {seg['start_time_2'] + seg['duration']:.2f}s")
    print(f"  Similarity: {seg['similarity']:.3f}")
```

## Future Web Deployment Example

The modular architecture allows easy web API wrapping:

```python
from fastapi import FastAPI, UploadFile, File
from pathlib import Path
import tempfile
import shutil

from src.audio_loader import load_audio
from src.spectral_analyzer import analyze_audio_structure
from src.segment_matcher import match_segments
from src.trim_engine import generate_trim_strategies
from src.quality_scorer import score_strategy
from src.output_generator import render_strategy

app = FastAPI()

@app.post("/api/trim")
async def trim_audio(
    file: UploadFile = File(...),
    target_length: float = 120,
    protected_regions: List[str] = []
):
    # Save uploaded file to temp location
    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = Path(tmp.name)
    
    try:
        # Run pipeline (same as CLI, but without file I/O at the end)
        audio_data, sample_rate = load_audio(tmp_path)
        original_length = len(audio_data) / sample_rate
        
        analysis_result = analyze_audio_structure(audio_data, sample_rate)
        match_result = match_segments(analysis_result['repeated_segments'], protected_regions)
        strategies = generate_trim_strategies(
            match_result['clusters'],
            original_length,
            target_length
        )
        
        scores = [score_strategy(s, audio_data, sample_rate, original_length) for s in strategies]
        
        # Render best strategy
        best_idx = max(range(len(scores)), key=lambda i: scores[i]['star_rating'])
        rendered_audio = render_strategy(strategies[best_idx], audio_data, sample_rate)
        
        # Convert to bytes for streaming (using soundfile)
        import io
        import soundfile as sf
        buffer = io.BytesIO()
        sf.write(buffer, rendered_audio, sample_rate, format='WAV')
        buffer.seek(0)
        
        return {
            'audio': buffer.read(),  # Return as base64 or stream
            'star_rating': scores[best_idx]['star_rating'],
            'resulting_length': strategies[best_idx].calculate_resulting_length(original_length)
        }
    
    finally:
        tmp_path.unlink()  # Clean up temp file
```

This example shows:
- No changes to core modules required
- Pipeline can be run entirely in memory
- Output can be streamed instead of saved to disk
- API can expose selected strategies rather than all 3
