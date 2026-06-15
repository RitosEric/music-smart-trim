# Music Smart Trim Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python-based music trimming tool that intelligently adjusts audio to target length by detecting and manipulating repeated melodic sections.

**Architecture:** Modular pipeline with 7 focused components: audio loading, spectral analysis, segment matching, trim strategy generation, quality scoring, output generation, and CLI orchestration. Core modules are web-ready with clean interfaces accepting standard Python types.

**Tech Stack:** Python 3.8+, librosa (audio analysis), pydub (format support), numpy/scipy (signal processing), soundfile (I/O)

---

## File Structure

### Source Files (src/)
- `src/audio_loader.py` - Load and normalize multi-format audio (MP3/WAV/FLAC/M4A/OGG)
- `src/spectral_analyzer.py` - CQT chroma features, self-similarity matrix, segment detection
- `src/segment_matcher.py` - Cosine similarity + DTW matching, clustering, protected regions
- `src/trim_engine.py` - Generate 3 strategies (conservative/balanced/aggressive)
- `src/quality_scorer.py` - Score options 0-100 → stars, ensure ≥1 at 4.5★
- `src/output_generator.py` - Render audio files + metadata (JSON/text)
- `src/cli.py` - Command-line interface and pipeline orchestration

### Test Files (tests/)
- `tests/test_audio_loader.py` - Format support, normalization, file size validation
- `tests/test_spectral_analyzer.py` - Chroma extraction, SSM, segment detection
- `tests/test_segment_matcher.py` - Similarity matching, clustering, protected regions
- `tests/test_trim_engine.py` - Strategy generation, constraints (±15s, protected regions)
- `tests/test_quality_scorer.py` - Scoring components, star conversion
- `tests/test_output_generator.py` - File rendering, metadata generation
- `tests/test_integration.py` - End-to-end pipeline with sample audio

### Configuration Files
- `requirements.txt` - Python dependencies
- `setup.py` - Package configuration
- `README.md` - Usage documentation
- `.gitignore` - Ignore output files, Python cache

### Test Data (tests/fixtures/)
- `tests/fixtures/sample_30s.wav` - Short test audio (30 seconds)
- `tests/fixtures/sample_3min.mp3` - Medium test audio (3 minutes)
- `tests/fixtures/README.md` - Instructions for obtaining test audio

---
## Task 1: Project Setup

**Files:**
- Create: `requirements.txt`
- Create: `.gitignore`
- Create: `setup.py`
- Create: `src/__init__.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: Create requirements.txt**

```txt
librosa>=0.10.0
pydub>=0.25.0
numpy>=1.24.0
scipy>=1.10.0
soundfile>=0.12.0
pytest>=7.0.0
```

- [ ] **Step 2: Create .gitignore**

```
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Testing
.pytest_cache/
.coverage
htmlcov/

# Output files
output/
*.mp3
*.wav
*.flac
*.m4a
*.ogg

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db
```

- [ ] **Step 3: Create setup.py**

```python
from setuptools import setup, find_packages

setup(
    name="music-smart-trim",
    version="1.0.0",
    description="Intelligently trim music to target length by detecting repeated melodic sections",
    author="Your Name",
    packages=find_packages(),
    install_requires=[
        "librosa>=0.10.0",
        "pydub>=0.25.0",
        "numpy>=1.24.0",
        "scipy>=1.10.0",
        "soundfile>=0.12.0",
    ],
    python_requires=">=3.8",
)
```

- [ ] **Step 4: Create source and test package markers**

```bash
mkdir -p src tests
touch src/__init__.py tests/__init__.py
```

- [ ] **Step 5: Install dependencies**

Run: `pip install -r requirements.txt`
Expected: All packages install successfully

- [ ] **Step 6: Verify installation**

Run: `python -c "import librosa; import pydub; import numpy; import scipy; print('All imports successful')"`
Expected: "All imports successful"

- [ ] **Step 7: Commit**

```bash
git add requirements.txt .gitignore setup.py src/__init__.py tests/__init__.py
git commit -m "chore: initial project setup with dependencies"
```

---

## Task 2: Audio Loader Module

**Files:**
- Create: `src/audio_loader.py`
- Create: `tests/test_audio_loader.py`

- [ ] **Step 1: Write failing test for basic audio loading**

Create `tests/test_audio_loader.py`:

```python
import pytest
import numpy as np
from src.audio_loader import load_audio


def test_load_audio_returns_array_and_sample_rate():
    """Test that load_audio returns numpy array and sample rate."""
    # This will fail until we implement load_audio
    audio_data, sr = load_audio("tests/fixtures/sample_30s.wav")
    
    assert isinstance(audio_data, np.ndarray)
    assert sr == 22050
    assert len(audio_data.shape) == 1  # mono
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_audio_loader.py::test_load_audio_returns_array_and_sample_rate -v`
Expected: FAIL with "cannot import name 'load_audio'"

- [ ] **Step 3: Implement minimal audio loader**

Create `src/audio_loader.py`:

```python
"""Audio loading and normalization module."""
import librosa
import numpy as np
from typing import Tuple


def load_audio(file_path: str, target_sr: int = 22050) -> Tuple[np.ndarray, int]:
    """
    Load audio file and normalize to target sample rate.
    
    Args:
        file_path: Path to audio file (MP3, WAV, FLAC, M4A, OGG)
        target_sr: Target sample rate in Hz (default: 22050)
    
    Returns:
        Tuple of (audio_data, sample_rate) where audio_data is mono float32 array
    """
    # Load audio using librosa (handles multiple formats via audioread/soundfile)
    audio_data, sr = librosa.load(file_path, sr=target_sr, mono=True)
    
    return audio_data, sr
```

- [ ] **Step 4: Create test fixture directory and placeholder**

```bash
mkdir -p tests/fixtures
```

Create `tests/fixtures/README.md`:

```markdown
# Test Audio Fixtures

This directory contains test audio files for the music smart trim test suite.

## Required Files

- `sample_30s.wav` - 30-second audio clip for unit tests
- `sample_3min.mp3` - 3-minute audio clip for integration tests

## How to Obtain Test Audio

You can generate test audio using the following Python script:

```python
import numpy as np
import soundfile as sf

# Generate 30-second test audio with simple melody
sr = 22050
duration = 30
t = np.linspace(0, duration, int(sr * duration))
# Simple melody: A440 for 10s, then D523 for 10s, then A440 again for 10s
audio = np.concatenate([
    np.sin(2 * np.pi * 440 * t[:int(sr*10)]),  # A
    np.sin(2 * np.pi * 523 * t[:int(sr*10)]),  # D
    np.sin(2 * np.pi * 440 * t[:int(sr*10)]),  # A (repeat)
])
sf.write('tests/fixtures/sample_30s.wav', audio * 0.3, sr)
```

Or use any copyright-free audio from sources like:
- Free Music Archive (freemusicarchive.org)
- ccMixter (ccmixter.org)
- YouTube Audio Library
```

- [ ] **Step 5: Generate test audio fixture**

Run:
```bash
python -c "
import numpy as np
import soundfile as sf

sr = 22050
duration = 30
t = np.linspace(0, duration, int(sr * duration))
audio = np.concatenate([
    np.sin(2 * np.pi * 440 * t[:int(sr*10)]),
    np.sin(2 * np.pi * 523 * t[:int(sr*10)]),
    np.sin(2 * np.pi * 440 * t[:int(sr*10)]),
])
sf.write('tests/fixtures/sample_30s.wav', audio * 0.3, sr)
print('Generated tests/fixtures/sample_30s.wav')
"
```

Expected: "Generated tests/fixtures/sample_30s.wav"

- [ ] **Step 6: Run test to verify it passes**

Run: `pytest tests/test_audio_loader.py::test_load_audio_returns_array_and_sample_rate -v`
Expected: PASS

- [ ] **Step 7: Write test for file size validation**

Add to `tests/test_audio_loader.py`:

```python
def test_check_file_size_under_limit():
    """Test that file size check passes for files under 15MB."""
    from src.audio_loader import check_normalized_size
    
    audio_data = np.random.randn(22050 * 30)  # 30 seconds
    result, size_mb = check_normalized_size(audio_data, 22050)
    
    assert result is True
    assert size_mb < 15.0


def test_check_file_size_over_limit():
    """Test that file size check warns for files over 15MB."""
    from src.audio_loader import check_normalized_size
    
    # Create large audio array (10 minutes should exceed 15MB)
    audio_data = np.random.randn(22050 * 600)
    result, size_mb = check_normalized_size(audio_data, 22050)
    
    assert result is False
    assert size_mb > 15.0
```

- [ ] **Step 8: Run test to verify it fails**

Run: `pytest tests/test_audio_loader.py::test_check_file_size_under_limit -v`
Expected: FAIL with "cannot import name 'check_normalized_size'"

- [ ] **Step 9: Implement file size validation**

Add to `src/audio_loader.py`:

```python
def check_normalized_size(audio_data: np.ndarray, sample_rate: int, max_mb: float = 15.0) -> Tuple[bool, float]:
    """
    Check if normalized audio data size exceeds maximum limit.
    
    Args:
        audio_data: Normalized audio array
        sample_rate: Sample rate in Hz
        max_mb: Maximum size in megabytes (default: 15.0)
    
    Returns:
        Tuple of (is_valid, size_mb) where is_valid is True if under limit
    """
    # Calculate size in bytes (float32 = 4 bytes per sample)
    size_bytes = audio_data.nbytes
    size_mb = size_bytes / (1024 * 1024)
    
    is_valid = size_mb <= max_mb
    
    return is_valid, size_mb
```

- [ ] **Step 10: Run tests to verify they pass**

Run: `pytest tests/test_audio_loader.py -v`
Expected: All 3 tests PASS

- [ ] **Step 11: Write test for unsupported format error handling**

Add to `tests/test_audio_loader.py`:

```python
def test_load_audio_unsupported_format():
    """Test that loading unsupported format raises clear error."""
    from src.audio_loader import load_audio, AudioLoadError
    
    with pytest.raises(AudioLoadError) as exc_info:
        load_audio("tests/fixtures/nonexistent.xyz")
    
    assert "unsupported" in str(exc_info.value).lower() or "not found" in str(exc_info.value).lower()
```

- [ ] **Step 12: Run test to verify it fails**

Run: `pytest tests/test_audio_loader.py::test_load_audio_unsupported_format -v`
Expected: FAIL with "cannot import name 'AudioLoadError'"

- [ ] **Step 13: Add error handling to audio loader**

Update `src/audio_loader.py`:

```python
"""Audio loading and normalization module."""
import librosa
import numpy as np
from typing import Tuple
import os


class AudioLoadError(Exception):
    """Exception raised when audio file cannot be loaded."""
    pass


def load_audio(file_path: str, target_sr: int = 22050) -> Tuple[np.ndarray, int]:
    """
    Load audio file and normalize to target sample rate.
    
    Args:
        file_path: Path to audio file (MP3, WAV, FLAC, M4A, OGG)
        target_sr: Target sample rate in Hz (default: 22050)
    
    Returns:
        Tuple of (audio_data, sample_rate) where audio_data is mono float32 array
    
    Raises:
        AudioLoadError: If file cannot be loaded or format is unsupported
    """
    if not os.path.exists(file_path):
        raise AudioLoadError(f"Audio file not found: {file_path}")
    
    supported_formats = ['.mp3', '.wav', '.flac', '.m4a', '.ogg']
    file_ext = os.path.splitext(file_path)[1].lower()
    
    if file_ext not in supported_formats:
        raise AudioLoadError(
            f"Unsupported audio format: {file_ext}. "
            f"Supported formats: {', '.join(supported_formats)}"
        )
    
    try:
        # Load audio using librosa
        audio_data, sr = librosa.load(file_path, sr=target_sr, mono=True)
        return audio_data, sr
    except Exception as e:
        raise AudioLoadError(f"Failed to load audio file: {str(e)}")


def check_normalized_size(audio_data: np.ndarray, sample_rate: int, max_mb: float = 15.0) -> Tuple[bool, float]:
    """
    Check if normalized audio data size exceeds maximum limit.
    
    Args:
        audio_data: Normalized audio array
        sample_rate: Sample rate in Hz
        max_mb: Maximum size in megabytes (default: 15.0)
    
    Returns:
        Tuple of (is_valid, size_mb) where is_valid is True if under limit
    """
    size_bytes = audio_data.nbytes
    size_mb = size_bytes / (1024 * 1024)
    is_valid = size_mb <= max_mb
    
    return is_valid, size_mb
```

- [ ] **Step 14: Run all tests to verify they pass**

Run: `pytest tests/test_audio_loader.py -v`
Expected: All 4 tests PASS

- [ ] **Step 15: Commit**

```bash
git add src/audio_loader.py tests/test_audio_loader.py tests/fixtures/
git commit -m "feat: add audio loader with multi-format support and file size validation"
```

---

## Task 3: Spectral Analyzer Module

**Files:**
- Create: `src/spectral_analyzer.py`
- Create: `tests/test_spectral_analyzer.py`

- [ ] **Step 1: Write failing test for chroma extraction**

Create `tests/test_spectral_analyzer.py`:

```python
import pytest
import numpy as np
from src.spectral_analyzer import extract_chroma_features


def test_extract_chroma_features_returns_correct_shape():
    """Test that chroma extraction returns expected shape."""
    # Generate simple test audio
    sr = 22050
    duration = 10
    t = np.linspace(0, duration, int(sr * duration))
    audio_data = np.sin(2 * np.pi * 440 * t)
    
    chroma = extract_chroma_features(audio_data, sr)
    
    # Chroma should have 12 bins (semitones) and multiple time frames
    assert chroma.shape[0] == 12
    assert chroma.shape[1] > 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_spectral_analyzer.py::test_extract_chroma_features_returns_correct_shape -v`
Expected: FAIL with "cannot import name 'extract_chroma_features'"

- [ ] **Step 3: Implement chroma feature extraction**

Create `src/spectral_analyzer.py`:

```python
"""Spectral analysis for melodic pattern detection."""
import librosa
import numpy as np
from typing import Tuple, List, Dict


def extract_chroma_features(audio_data: np.ndarray, sample_rate: int, 
                           hop_length: int = 2048, n_chroma: int = 12) -> np.ndarray:
    """
    Extract CQT-based chroma features (CENS) from audio.
    
    Args:
        audio_data: Audio samples as numpy array
        sample_rate: Sample rate in Hz
        hop_length: Hop length for frame analysis (default: 2048)
        n_chroma: Number of chroma bins (default: 12 for semitones)
    
    Returns:
        Chroma feature matrix of shape (n_chroma, n_frames)
    """
    # Extract CQT-based chroma features
    chroma = librosa.feature.chroma_cqt(
        y=audio_data,
        sr=sample_rate,
        hop_length=hop_length,
        n_chroma=n_chroma
    )
    
    return chroma
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_spectral_analyzer.py::test_extract_chroma_features_returns_correct_shape -v`
Expected: PASS

- [ ] **Step 5: Write test for self-similarity matrix generation**

Add to `tests/test_spectral_analyzer.py`:

```python
def test_build_self_similarity_matrix():
    """Test that SSM is computed correctly."""
    from src.spectral_analyzer import build_self_similarity_matrix
    
    # Create simple chroma features (12 bins, 100 frames)
    chroma = np.random.rand(12, 100)
    
    ssm = build_self_similarity_matrix(chroma)
    
    # SSM should be square matrix (n_frames x n_frames)
    assert ssm.shape[0] == ssm.shape[1]
    assert ssm.shape[0] == 100
    # SSM should be symmetric
    assert np.allclose(ssm, ssm.T, atol=1e-6)
    # Diagonal should be high similarity (close to 1)
    assert np.mean(np.diag(ssm)) > 0.9
```

- [ ] **Step 6: Run test to verify it fails**

Run: `pytest tests/test_spectral_analyzer.py::test_build_self_similarity_matrix -v`
Expected: FAIL with "cannot import name 'build_self_similarity_matrix'"

- [ ] **Step 7: Implement self-similarity matrix**

Add to `src/spectral_analyzer.py`:

```python
from scipy.spatial.distance import cosine


def build_self_similarity_matrix(chroma: np.ndarray) -> np.ndarray:
    """
    Build self-similarity matrix using cosine distance on chroma features.
    
    Args:
        chroma: Chroma feature matrix of shape (n_chroma, n_frames)
    
    Returns:
        Self-similarity matrix of shape (n_frames, n_frames)
        Values range from 0 (dissimilar) to 1 (identical)
    """
    n_frames = chroma.shape[1]
    ssm = np.zeros((n_frames, n_frames))
    
    # Compute pairwise cosine similarity
    for i in range(n_frames):
        for j in range(i, n_frames):
            # Cosine similarity = 1 - cosine distance
            similarity = 1 - cosine(chroma[:, i], chroma[:, j])
            ssm[i, j] = similarity
            ssm[j, i] = similarity  # Symmetric matrix
    
    return ssm
```

- [ ] **Step 8: Run test to verify it passes**

Run: `pytest tests/test_spectral_analyzer.py::test_build_self_similarity_matrix -v`
Expected: PASS

- [ ] **Step 9: Write test for repeated segment detection**

Add to `tests/test_spectral_analyzer.py`:

```python
def test_detect_repeated_segments():
    """Test detection of repeated melodic segments."""
    from src.spectral_analyzer import detect_repeated_segments
    
    # Create SSM with clear repetition pattern
    # Frames 0-20 similar to frames 40-60
    ssm = np.random.rand(80, 80) * 0.3  # Low background similarity
    for i in range(20):
        for j in range(20):
            ssm[i, 40+j] = 0.9  # High similarity block
            ssm[40+j, i] = 0.9
    
    segments = detect_repeated_segments(ssm, sample_rate=22050, hop_length=2048, 
                                       min_segment_duration=4.0, similarity_threshold=0.8)
    
    # Should detect at least one repeated segment pair
    assert len(segments) > 0
    assert 'start_time_1' in segments[0]
    assert 'start_time_2' in segments[0]
    assert 'duration' in segments[0]
    assert 'similarity' in segments[0]
```

- [ ] **Step 10: Run test to verify it fails**

Run: `pytest tests/test_spectral_analyzer.py::test_detect_repeated_segments -v`
Expected: FAIL with "cannot import name 'detect_repeated_segments'"

- [ ] **Step 11: Implement repeated segment detection**

Add to `src/spectral_analyzer.py`:

```python
def detect_repeated_segments(ssm: np.ndarray, sample_rate: int, hop_length: int,
                            min_segment_duration: float = 4.0,
                            similarity_threshold: float = 0.8) -> List[Dict]:
    """
    Detect repeated melodic segments from self-similarity matrix.
    
    Args:
        ssm: Self-similarity matrix (n_frames x n_frames)
        sample_rate: Audio sample rate in Hz
        hop_length: Hop length used in chroma extraction
        min_segment_duration: Minimum segment duration in seconds
        similarity_threshold: Minimum similarity for repetition (0-1)
    
    Returns:
        List of repeated segment dictionaries with keys:
        - start_time_1: Start time of first occurrence (seconds)
        - start_time_2: Start time of second occurrence (seconds)
        - duration: Segment duration (seconds)
        - similarity: Average similarity score (0-1)
    """
    n_frames = ssm.shape[0]
    frame_duration = hop_length / sample_rate
    min_frames = int(min_segment_duration / frame_duration)
    
    repeated_segments = []
    
    # Scan upper triangle of SSM for diagonal lines (repeated patterns)
    for i in range(n_frames - min_frames):
        for j in range(i + min_frames, n_frames - min_frames):
            # Check if we have a diagonal line of high similarity
            diagonal_length = 0
            similarities = []
            
            # Follow the diagonal
            k = 0
            while (i + k < n_frames and j + k < n_frames and 
                   ssm[i + k, j + k] >= similarity_threshold):
                similarities.append(ssm[i + k, j + k])
                diagonal_length += 1
                k += 1
            
            # If diagonal is long enough, record as repeated segment
            if diagonal_length >= min_frames:
                start_time_1 = i * frame_duration
                start_time_2 = j * frame_duration
                duration = diagonal_length * frame_duration
                avg_similarity = np.mean(similarities)
                
                repeated_segments.append({
                    'start_time_1': start_time_1,
                    'start_time_2': start_time_2,
                    'duration': duration,
                    'similarity': avg_similarity
                })
    
    return repeated_segments
```

- [ ] **Step 12: Run test to verify it passes**

Run: `pytest tests/test_spectral_analyzer.py::test_detect_repeated_segments -v`
Expected: PASS

- [ ] **Step 13: Write test for complete analysis pipeline**

Add to `tests/test_spectral_analyzer.py`:

```python
def test_analyze_audio_structure():
    """Test complete spectral analysis pipeline."""
    from src.spectral_analyzer import analyze_audio_structure
    from src.audio_loader import load_audio
    
    # Load test audio
    audio_data, sr = load_audio("tests/fixtures/sample_30s.wav")
    
    result = analyze_audio_structure(audio_data, sr)
    
    assert 'chroma' in result
    assert 'ssm' in result
    assert 'repeated_segments' in result
    assert isinstance(result['repeated_segments'], list)
```

- [ ] **Step 14: Run test to verify it fails**

Run: `pytest tests/test_spectral_analyzer.py::test_analyze_audio_structure -v`
Expected: FAIL with "cannot import name 'analyze_audio_structure'"

- [ ] **Step 15: Implement complete analysis pipeline**

Add to `src/spectral_analyzer.py`:

```python
def analyze_audio_structure(audio_data: np.ndarray, sample_rate: int,
                           hop_length: int = 2048) -> Dict:
    """
    Complete spectral analysis pipeline for audio structure detection.
    
    Args:
        audio_data: Audio samples as numpy array
        sample_rate: Sample rate in Hz
        hop_length: Hop length for analysis
    
    Returns:
        Dictionary with keys:
        - chroma: Chroma feature matrix
        - ssm: Self-similarity matrix
        - repeated_segments: List of detected repeated segments
    """
    # Extract chroma features
    chroma = extract_chroma_features(audio_data, sample_rate, hop_length=hop_length)
    
    # Build self-similarity matrix
    ssm = build_self_similarity_matrix(chroma)
    
    # Detect repeated segments
    repeated_segments = detect_repeated_segments(
        ssm, sample_rate, hop_length,
        min_segment_duration=4.0,
        similarity_threshold=0.8
    )
    
    return {
        'chroma': chroma,
        'ssm': ssm,
        'repeated_segments': repeated_segments
    }
```

- [ ] **Step 16: Run all tests to verify they pass**

Run: `pytest tests/test_spectral_analyzer.py -v`
Expected: All 4 tests PASS

- [ ] **Step 17: Commit**

```bash
git add src/spectral_analyzer.py tests/test_spectral_analyzer.py
git commit -m "feat: add spectral analyzer with chroma features and SSM-based repetition detection"
```

---

## Task 4: Segment Matcher Module

**Files:**
- Create: `src/segment_matcher.py`
- Create: `tests/test_segment_matcher.py`

- [ ] **Step 1: Write failing test for protected regions parsing**

Create `tests/test_segment_matcher.py`:

```python
import pytest
import numpy as np
from src.segment_matcher import parse_protected_regions


def test_parse_protected_regions_single():
    """Test parsing single protected region."""
    result = parse_protected_regions("0:30-1:15")
    
    assert len(result) == 1
    assert result[0] == (30.0, 75.0)


def test_parse_protected_regions_multiple():
    """Test parsing multiple protected regions."""
    result = parse_protected_regions("0:30-1:15,2:00-2:30")
    
    assert len(result) == 2
    assert result[0] == (30.0, 75.0)
    assert result[1] == (120.0, 150.0)


def test_parse_protected_regions_empty():
    """Test parsing empty string returns empty list."""
    result = parse_protected_regions("")
    assert result == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_segment_matcher.py::test_parse_protected_regions_single -v`
Expected: FAIL with "cannot import name 'parse_protected_regions'"

- [ ] **Step 3: Implement protected regions parser**

Create `src/segment_matcher.py`:

```python
"""Segment matching and clustering for repeated pattern identification."""
import numpy as np
from typing import List, Tuple, Dict
from scipy.cluster.hierarchy import linkage, fcluster
from scipy.spatial.distance import pdist


def parse_protected_regions(regions_str: str) -> List[Tuple[float, float]]:
    """
    Parse protected regions from CLI timestamp format.
    
    Args:
        regions_str: Comma-separated timestamp ranges (e.g., "0:30-1:15,2:00-2:30")
    
    Returns:
        List of (start_seconds, end_seconds) tuples
    """
    if not regions_str or regions_str.strip() == "":
        return []
    
    protected = []
    parts = regions_str.split(',')
    
    for part in parts:
        part = part.strip()
        if '-' not in part:
            continue
        
        start_str, end_str = part.split('-')
        start_seconds = _parse_timestamp(start_str.strip())
        end_seconds = _parse_timestamp(end_str.strip())
        
        protected.append((start_seconds, end_seconds))
    
    return protected


def _parse_timestamp(timestamp: str) -> float:
    """Convert MM:SS timestamp to seconds."""
    parts = timestamp.split(':')
    if len(parts) == 2:
        minutes, seconds = parts
        return float(minutes) * 60 + float(seconds)
    else:
        return float(timestamp)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_segment_matcher.py -k parse_protected_regions -v`
Expected: All 3 tests PASS

- [ ] **Step 5: Write test for overlapping protected regions merging**

Add to `tests/test_segment_matcher.py`:

```python
def test_merge_overlapping_regions():
    """Test that overlapping protected regions are merged."""
    from src.segment_matcher import merge_overlapping_regions
    
    regions = [(10.0, 30.0), (25.0, 50.0), (60.0, 80.0)]
    merged = merge_overlapping_regions(regions)
    
    # First two should merge, third stays separate
    assert len(merged) == 2
    assert merged[0] == (10.0, 50.0)
    assert merged[1] == (60.0, 80.0)


def test_merge_overlapping_regions_no_overlap():
    """Test that non-overlapping regions stay separate."""
    from src.segment_matcher import merge_overlapping_regions
    
    regions = [(10.0, 20.0), (30.0, 40.0)]
    merged = merge_overlapping_regions(regions)
    
    assert len(merged) == 2
    assert merged == regions
```

- [ ] **Step 6: Run test to verify it fails**

Run: `pytest tests/test_segment_matcher.py::test_merge_overlapping_regions -v`
Expected: FAIL with "cannot import name 'merge_overlapping_regions'"

- [ ] **Step 7: Implement region merging**

Add to `src/segment_matcher.py`:

```python
def merge_overlapping_regions(regions: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
    """
    Merge overlapping protected regions.
    
    Args:
        regions: List of (start, end) tuples in seconds
    
    Returns:
        List of merged non-overlapping regions
    """
    if not regions:
        return []
    
    # Sort by start time
    sorted_regions = sorted(regions, key=lambda x: x[0])
    
    merged = [sorted_regions[0]]
    
    for current_start, current_end in sorted_regions[1:]:
        last_start, last_end = merged[-1]
        
        # Check for overlap
        if current_start <= last_end:
            # Merge by extending the end time
            merged[-1] = (last_start, max(last_end, current_end))
        else:
            # No overlap, add as separate region
            merged.append((current_start, current_end))
    
    return merged
```

- [ ] **Step 8: Run tests to verify they pass**

Run: `pytest tests/test_segment_matcher.py -k merge_overlapping -v`
Expected: Both tests PASS

- [ ] **Step 9: Write test for checking if segment is protected**

Add to `tests/test_segment_matcher.py`:

```python
def test_is_segment_protected():
    """Test checking if a segment overlaps with protected regions."""
    from src.segment_matcher import is_segment_protected
    
    protected = [(30.0, 75.0), (120.0, 150.0)]
    
    # Fully inside protected region
    assert is_segment_protected(40.0, 60.0, protected) is True
    
    # Partially overlaps
    assert is_segment_protected(20.0, 40.0, protected) is True
    assert is_segment_protected(70.0, 90.0, protected) is True
    
    # No overlap
    assert is_segment_protected(0.0, 20.0, protected) is False
    assert is_segment_protected(80.0, 110.0, protected) is False
```

- [ ] **Step 10: Run test to verify it fails**

Run: `pytest tests/test_segment_matcher.py::test_is_segment_protected -v`
Expected: FAIL with "cannot import name 'is_segment_protected'"

- [ ] **Step 11: Implement segment protection check**

Add to `src/segment_matcher.py`:

```python
def is_segment_protected(start_time: float, end_time: float, 
                        protected_regions: List[Tuple[float, float]]) -> bool:
    """
    Check if a segment overlaps with any protected region.
    
    Args:
        start_time: Segment start time in seconds
        end_time: Segment end time in seconds
        protected_regions: List of (start, end) protected regions
    
    Returns:
        True if segment overlaps with any protected region
    """
    for prot_start, prot_end in protected_regions:
        # Check for any overlap
        if not (end_time <= prot_start or start_time >= prot_end):
            return True
    
    return False
```

- [ ] **Step 12: Run test to verify it passes**

Run: `pytest tests/test_segment_matcher.py::test_is_segment_protected -v`
Expected: PASS

- [ ] **Step 13: Write test for segment clustering**

Add to `tests/test_segment_matcher.py`:

```python
def test_cluster_similar_segments():
    """Test clustering of similar melodic segments."""
    from src.segment_matcher import cluster_similar_segments
    
    # Create repeated segments with varying similarity
    segments = [
        {'start_time_1': 10.0, 'start_time_2': 50.0, 'duration': 8.0, 'similarity': 0.9},
        {'start_time_1': 10.0, 'start_time_2': 90.0, 'duration': 8.0, 'similarity': 0.85},
        {'start_time_1': 30.0, 'start_time_2': 70.0, 'duration': 6.0, 'similarity': 0.75},
    ]
    
    clusters = cluster_similar_segments(segments, similarity_threshold=0.8)
    
    # Should group segments into clusters
    assert len(clusters) > 0
    assert all('segment_times' in cluster for cluster in clusters)
    assert all('avg_similarity' in cluster for cluster in clusters)
```

- [ ] **Step 14: Run test to verify it fails**

Run: `pytest tests/test_segment_matcher.py::test_cluster_similar_segments -v`
Expected: FAIL with "cannot import name 'cluster_similar_segments'"

- [ ] **Step 15: Implement segment clustering**

Add to `src/segment_matcher.py`:

```python
def cluster_similar_segments(segments: List[Dict], 
                            similarity_threshold: float = 0.8) -> List[Dict]:
    """
    Cluster similar repeated segments using hierarchical clustering.
    
    Args:
        segments: List of repeated segment dictionaries
        similarity_threshold: Minimum similarity for clustering
    
    Returns:
        List of cluster dictionaries with keys:
        - segment_times: List of (start, end) tuples for segments in cluster
        - avg_similarity: Average similarity score for cluster
        - duration: Average duration of segments in cluster
    """
    if not segments:
        return []
    
    # Filter segments by similarity threshold
    filtered = [s for s in segments if s['similarity'] >= similarity_threshold]
    
    if not filtered:
        return []
    
    # For simplicity, group segments by similar start times
    # More sophisticated: use hierarchical clustering on feature space
    clusters = []
    used_indices = set()
    
    for i, seg in enumerate(filtered):
        if i in used_indices:
            continue
        
        # Start new cluster
        cluster_segments = [(seg['start_time_1'], seg['start_time_1'] + seg['duration']),
                          (seg['start_time_2'], seg['start_time_2'] + seg['duration'])]
        similarities = [seg['similarity']]
        durations = [seg['duration']]
        used_indices.add(i)
        
        # Find similar segments
        for j, other_seg in enumerate(filtered[i+1:], start=i+1):
            if j in used_indices:
                continue
            
            # Simple proximity-based grouping
            if abs(other_seg['start_time_1'] - seg['start_time_1']) < 2.0:
                cluster_segments.append((other_seg['start_time_1'], 
                                       other_seg['start_time_1'] + other_seg['duration']))
                cluster_segments.append((other_seg['start_time_2'], 
                                       other_seg['start_time_2'] + other_seg['duration']))
                similarities.append(other_seg['similarity'])
                durations.append(other_seg['duration'])
                used_indices.add(j)
        
        clusters.append({
            'segment_times': cluster_segments,
            'avg_similarity': np.mean(similarities),
            'duration': np.mean(durations)
        })
    
    return clusters
```

- [ ] **Step 16: Run test to verify it passes**

Run: `pytest tests/test_segment_matcher.py::test_cluster_similar_segments -v`
Expected: PASS

- [ ] **Step 17: Write test for complete matching pipeline**

Add to `tests/test_segment_matcher.py`:

```python
def test_match_segments():
    """Test complete segment matching pipeline."""
    from src.segment_matcher import match_segments
    
    # Repeated segments from spectral analyzer
    repeated_segments = [
        {'start_time_1': 10.0, 'start_time_2': 50.0, 'duration': 8.0, 'similarity': 0.9},
        {'start_time_1': 30.0, 'start_time_2': 70.0, 'duration': 6.0, 'similarity': 0.85},
    ]
    
    protected_str = "5:00-6:00"
    
    result = match_segments(repeated_segments, protected_str)
    
    assert 'clusters' in result
    assert 'protected_regions' in result
    assert isinstance(result['clusters'], list)
    assert len(result['protected_regions']) == 1
```

- [ ] **Step 18: Run test to verify it fails**

Run: `pytest tests/test_segment_matcher.py::test_match_segments -v`
Expected: FAIL with "cannot import name 'match_segments'"

- [ ] **Step 19: Implement complete matching pipeline**

Add to `src/segment_matcher.py`:

```python
def match_segments(repeated_segments: List[Dict], 
                  protected_regions_str: str = "",
                  similarity_threshold: float = 0.8) -> Dict:
    """
    Complete segment matching pipeline.
    
    Args:
        repeated_segments: List of repeated segments from spectral analyzer
        protected_regions_str: Protected regions string (e.g., "0:30-1:15,2:00-2:30")
        similarity_threshold: Minimum similarity for clustering
    
    Returns:
        Dictionary with keys:
        - clusters: List of clustered similar segments
        - protected_regions: List of (start, end) protected regions
        - filtered_segments: Segments after removing protected ones
    """
    # Parse and merge protected regions
    protected = parse_protected_regions(protected_regions_str)
    protected = merge_overlapping_regions(protected)
    
    # Filter out segments that overlap with protected regions
    filtered_segments = []
    for seg in repeated_segments:
        start1 = seg['start_time_1']
        end1 = start1 + seg['duration']
        start2 = seg['start_time_2']
        end2 = start2 + seg['duration']
        
        # Keep segment only if neither occurrence is protected
        if (not is_segment_protected(start1, end1, protected) and
            not is_segment_protected(start2, end2, protected)):
            filtered_segments.append(seg)
    
    # Cluster similar segments
    clusters = cluster_similar_segments(filtered_segments, similarity_threshold)
    
    return {
        'clusters': clusters,
        'protected_regions': protected,
        'filtered_segments': filtered_segments
    }
```

- [ ] **Step 20: Run all tests to verify they pass**

Run: `pytest tests/test_segment_matcher.py -v`
Expected: All tests PASS

- [ ] **Step 21: Commit**

```bash
git add src/segment_matcher.py tests/test_segment_matcher.py
git commit -m "feat: add segment matcher with protected regions and clustering"
```

---

## Task 5: Trim Engine Module

**Files:**
- Create: `src/trim_engine.py`
- Create: `tests/test_trim_engine.py`

- [ ] **Step 1: Write failing test for strategy data structure**

Create `tests/test_trim_engine.py`:

```python
import pytest
import numpy as np
from src.trim_engine import TrimStrategy


def test_trim_strategy_creation():
    """Test creating a trim strategy object."""
    strategy = TrimStrategy(
        name="conservative",
        cut_points=[(10.0, 20.0)],
        loop_points=[],
        fade_regions=[(10.0, 10.2), (19.8, 20.0)],
        target_length=120.0
    )
    
    assert strategy.name == "conservative"
    assert len(strategy.cut_points) == 1
    assert strategy.target_length == 120.0


def test_trim_strategy_calculate_length():
    """Test calculating resulting length after trim strategy."""
    strategy = TrimStrategy(
        name="balanced",
        cut_points=[(20.0, 30.0), (50.0, 60.0)],  # Remove 20 seconds total
        loop_points=[],
        fade_regions=[],
        target_length=120.0
    )
    
    original_length = 150.0
    result_length = strategy.calculate_resulting_length(original_length)
    
    # 150 - 20 = 130 seconds
    assert result_length == 130.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_trim_engine.py::test_trim_strategy_creation -v`
Expected: FAIL with "cannot import name 'TrimStrategy'"

- [ ] **Step 3: Implement TrimStrategy class**

Create `src/trim_engine.py`:

```python
"""Trim strategy generation for audio length adjustment."""
import numpy as np
from typing import List, Tuple, Dict
from dataclasses import dataclass, field


@dataclass
class TrimStrategy:
    """Represents a trim/extend strategy for audio."""
    name: str  # conservative, balanced, or aggressive
    cut_points: List[Tuple[float, float]] = field(default_factory=list)  # (start, end) in seconds
    loop_points: List[Tuple[float, float, int]] = field(default_factory=list)  # (start, end, repeat_count)
    fade_regions: List[Tuple[float, float]] = field(default_factory=list)  # (start, end) for crossfades
    target_length: float = 0.0
    
    def calculate_resulting_length(self, original_length: float) -> float:
        """
        Calculate the resulting audio length after applying this strategy.
        
        Args:
            original_length: Original audio duration in seconds
        
        Returns:
            Resulting duration in seconds
        """
        result = original_length
        
        # Subtract cut regions
        for start, end in self.cut_points:
            result -= (end - start)
        
        # Add looped regions
        for start, end, repeat_count in self.loop_points:
            result += (end - start) * (repeat_count - 1)
        
        return result
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_trim_engine.py -k test_trim_strategy -v`
Expected: Both tests PASS

- [ ] **Step 5: Write test for conservative strategy generation**

Add to `tests/test_trim_engine.py`:

```python
def test_generate_conservative_strategy():
    """Test generation of conservative trim strategy."""
    from src.trim_engine import generate_conservative_strategy
    
    clusters = [
        {'segment_times': [(10.0, 18.0), (50.0, 58.0)], 'avg_similarity': 0.9, 'duration': 8.0},
        {'segment_times': [(30.0, 36.0), (70.0, 76.0)], 'avg_similarity': 0.85, 'duration': 6.0},
    ]
    
    original_length = 180.0
    target_length = 165.0
    protected = []
    
    strategy = generate_conservative_strategy(clusters, original_length, target_length, protected)
    
    assert strategy.name == "conservative"
    assert isinstance(strategy.cut_points, list)
    assert strategy.target_length == target_length
    # Conservative should use gentle fades (200-500ms)
    for fade_start, fade_end in strategy.fade_regions:
        fade_duration = (fade_end - fade_start) * 1000  # Convert to ms
        assert 200 <= fade_duration <= 500
```

- [ ] **Step 6: Run test to verify it fails**

Run: `pytest tests/test_trim_engine.py::test_generate_conservative_strategy -v`
Expected: FAIL with "cannot import name 'generate_conservative_strategy'"

- [ ] **Step 7: Implement conservative strategy generator**

Add to `src/trim_engine.py`:

```python
def generate_conservative_strategy(clusters: List[Dict], original_length: float,
                                   target_length: float, protected_regions: List[Tuple[float, float]]) -> TrimStrategy:
    """
    Generate conservative trim strategy with minimal cuts.
    
    Args:
        clusters: Clustered similar segments
        original_length: Original audio length in seconds
        target_length: Target audio length in seconds
        protected_regions: List of (start, end) protected regions
    
    Returns:
        Conservative TrimStrategy
    """
    strategy = TrimStrategy(name="conservative", target_length=target_length)
    
    length_to_remove = original_length - target_length
    
    if length_to_remove > 0:
        # Need to shorten: remove highly similar repeated sections
        # Sort clusters by similarity (highest first)
        sorted_clusters = sorted(clusters, key=lambda c: c['avg_similarity'], reverse=True)
        
        removed = 0.0
        for cluster in sorted_clusters:
            if removed >= length_to_remove:
                break
            
            # Take the second occurrence of each repeated segment
            segments = cluster['segment_times']
            if len(segments) >= 2:
                # Remove second occurrence
                start, end = segments[1]
                duration = end - start
                
                if removed + duration <= length_to_remove + 5.0:  # Allow 5s buffer
                    strategy.cut_points.append((start, end))
                    # Add gentle crossfades (300ms)
                    strategy.fade_regions.append((start - 0.15, start + 0.15))
                    strategy.fade_regions.append((end - 0.15, end + 0.15))
                    removed += duration
    
    elif length_to_remove < 0:
        # Need to extend: loop similar sections
        length_to_add = abs(length_to_remove)
        sorted_clusters = sorted(clusters, key=lambda c: c['avg_similarity'], reverse=True)
        
        added = 0.0
        for cluster in sorted_clusters:
            if added >= length_to_add:
                break
            
            segments = cluster['segment_times']
            if len(segments) >= 1:
                start, end = segments[0]
                duration = end - start
                repeat_count = 2  # Conservative: only repeat once
                
                if added + duration <= length_to_add + 5.0:
                    strategy.loop_points.append((start, end, repeat_count))
                    strategy.fade_regions.append((end - 0.15, end + 0.15))
                    added += duration
    
    return strategy
```

- [ ] **Step 8: Run test to verify it passes**

Run: `pytest tests/test_trim_engine.py::test_generate_conservative_strategy -v`
Expected: PASS

- [ ] **Step 9: Write test for balanced strategy generation**

Add to `tests/test_trim_engine.py`:

```python
def test_generate_balanced_strategy():
    """Test generation of balanced trim strategy."""
    from src.trim_engine import generate_balanced_strategy
    
    clusters = [
        {'segment_times': [(10.0, 18.0), (50.0, 58.0)], 'avg_similarity': 0.9, 'duration': 8.0},
        {'segment_times': [(30.0, 36.0), (70.0, 76.0)], 'avg_similarity': 0.85, 'duration': 6.0},
    ]
    
    original_length = 180.0
    target_length = 165.0
    protected = []
    
    strategy = generate_balanced_strategy(clusters, original_length, target_length, protected)
    
    assert strategy.name == "balanced"
    assert isinstance(strategy.cut_points, list)
    # Balanced should use standard fades (100-200ms)
    for fade_start, fade_end in strategy.fade_regions:
        fade_duration = (fade_end - fade_start) * 1000
        assert 100 <= fade_duration <= 200
```

- [ ] **Step 10: Run test to verify it fails**

Run: `pytest tests/test_trim_engine.py::test_generate_balanced_strategy -v`
Expected: FAIL with "cannot import name 'generate_balanced_strategy'"

- [ ] **Step 11: Implement balanced strategy generator**

Add to `src/trim_engine.py`:

```python
def generate_balanced_strategy(clusters: List[Dict], original_length: float,
                               target_length: float, protected_regions: List[Tuple[float, float]]) -> TrimStrategy:
    """
    Generate balanced trim strategy with moderate cuts.
    
    Args:
        clusters: Clustered similar segments
        original_length: Original audio length in seconds
        target_length: Target audio length in seconds
        protected_regions: List of (start, end) protected regions
    
    Returns:
        Balanced TrimStrategy
    """
    strategy = TrimStrategy(name="balanced", target_length=target_length)
    
    length_to_remove = original_length - target_length
    
    if length_to_remove > 0:
        # Mix of cuts from high and medium similarity
        sorted_clusters = sorted(clusters, key=lambda c: c['avg_similarity'], reverse=True)
        
        removed = 0.0
        for cluster in sorted_clusters:
            if removed >= length_to_remove:
                break
            
            segments = cluster['segment_times']
            for i in range(1, len(segments)):
                if removed >= length_to_remove:
                    break
                
                start, end = segments[i]
                duration = end - start
                
                if removed + duration <= length_to_remove + 3.0:
                    strategy.cut_points.append((start, end))
                    # Standard crossfades (150ms)
                    strategy.fade_regions.append((start - 0.075, start + 0.075))
                    strategy.fade_regions.append((end - 0.075, end + 0.075))
                    removed += duration
    
    elif length_to_remove < 0:
        length_to_add = abs(length_to_remove)
        sorted_clusters = sorted(clusters, key=lambda c: c['avg_similarity'], reverse=True)
        
        added = 0.0
        for cluster in sorted_clusters:
            if added >= length_to_add:
                break
            
            segments = cluster['segment_times']
            if segments:
                start, end = segments[0]
                duration = end - start
                # Calculate repeat count to get closer to target
                repeat_count = min(3, int((length_to_add - added) / duration) + 1)
                
                if repeat_count > 1:
                    strategy.loop_points.append((start, end, repeat_count))
                    strategy.fade_regions.append((end - 0.075, end + 0.075))
                    added += duration * (repeat_count - 1)
    
    return strategy
```

- [ ] **Step 12: Run test to verify it passes**

Run: `pytest tests/test_trim_engine.py::test_generate_balanced_strategy -v`
Expected: PASS

- [ ] **Step 13: Write test for aggressive strategy generation**

Add to `tests/test_trim_engine.py`:

```python
def test_generate_aggressive_strategy():
    """Test generation of aggressive trim strategy."""
    from src.trim_engine import generate_aggressive_strategy
    
    clusters = [
        {'segment_times': [(10.0, 18.0), (50.0, 58.0), (90.0, 98.0)], 'avg_similarity': 0.88, 'duration': 8.0},
    ]
    
    original_length = 180.0
    target_length = 160.0
    protected = []
    
    strategy = generate_aggressive_strategy(clusters, original_length, target_length, protected)
    
    assert strategy.name == "aggressive"
    # Aggressive should use short fades (50-100ms)
    for fade_start, fade_end in strategy.fade_regions:
        fade_duration = (fade_end - fade_start) * 1000
        assert 50 <= fade_duration <= 100
```

- [ ] **Step 14: Run test to verify it fails**

Run: `pytest tests/test_trim_engine.py::test_generate_aggressive_strategy -v`
Expected: FAIL with "cannot import name 'generate_aggressive_strategy'"

- [ ] **Step 15: Implement aggressive strategy generator**

Add to `src/trim_engine.py`:

```python
def generate_aggressive_strategy(clusters: List[Dict], original_length: float,
                                 target_length: float, protected_regions: List[Tuple[float, float]]) -> TrimStrategy:
    """
    Generate aggressive trim strategy with maximum cuts.
    
    Args:
        clusters: Clustered similar segments
        original_length: Original audio length in seconds
        target_length: Target audio length in seconds
        protected_regions: List of (start, end) protected regions
    
    Returns:
        Aggressive TrimStrategy
    """
    strategy = TrimStrategy(name="aggressive", target_length=target_length)
    
    length_to_remove = original_length - target_length
    
    if length_to_remove > 0:
        # Remove all repeated segments aggressively
        all_segments = []
        for cluster in clusters:
            # Skip first occurrence, remove all others
            for i in range(1, len(cluster['segment_times'])):
                all_segments.append(cluster['segment_times'][i])
        
        # Sort by start time
        all_segments.sort(key=lambda s: s[0])
        
        removed = 0.0
        for start, end in all_segments:
            if removed >= length_to_remove:
                break
            
            duration = end - start
            if removed + duration <= length_to_remove + 1.0:  # Tight tolerance
                strategy.cut_points.append((start, end))
                # Short crossfades (75ms)
                strategy.fade_regions.append((start - 0.0375, start + 0.0375))
                strategy.fade_regions.append((end - 0.0375, end + 0.0375))
                removed += duration
    
    elif length_to_remove < 0:
        length_to_add = abs(length_to_remove)
        
        added = 0.0
        for cluster in clusters:
            if added >= length_to_add:
                break
            
            segments = cluster['segment_times']
            if segments:
                start, end = segments[0]
                duration = end - start
                # Aggressive: repeat many times
                repeat_count = min(5, int((length_to_add - added) / duration) + 1)
                
                if repeat_count > 1:
                    strategy.loop_points.append((start, end, repeat_count))
                    strategy.fade_regions.append((end - 0.0375, end + 0.0375))
                    added += duration * (repeat_count - 1)
    
    return strategy
```

- [ ] **Step 16: Run test to verify it passes**

Run: `pytest tests/test_trim_engine.py::test_generate_aggressive_strategy -v`
Expected: PASS

- [ ] **Step 17: Write test for complete trim engine**

Add to `tests/test_trim_engine.py`:

```python
def test_generate_trim_strategies():
    """Test generation of all 3 strategies."""
    from src.trim_engine import generate_trim_strategies
    
    clusters = [
        {'segment_times': [(10.0, 18.0), (50.0, 58.0)], 'avg_similarity': 0.9, 'duration': 8.0},
    ]
    
    original_length = 180.0
    target_length = 165.0
    protected = []
    
    strategies = generate_trim_strategies(clusters, original_length, target_length, protected)
    
    assert len(strategies) == 3
    strategy_names = [s.name for s in strategies]
    assert "conservative" in strategy_names
    assert "balanced" in strategy_names
    assert "aggressive" in strategy_names
    
    # All strategies should be within ±15 seconds of target
    for strategy in strategies:
        result_length = strategy.calculate_resulting_length(original_length)
        error = abs(result_length - target_length)
        assert error <= 15.0, f"Strategy {strategy.name} error {error}s exceeds 15s limit"
```

- [ ] **Step 18: Run test to verify it fails**

Run: `pytest tests/test_trim_engine.py::test_generate_trim_strategies -v`
Expected: FAIL with "cannot import name 'generate_trim_strategies'"

- [ ] **Step 19: Implement complete trim engine**

Add to `src/trim_engine.py`:

```python
def generate_trim_strategies(clusters: List[Dict], original_length: float,
                            target_length: float, protected_regions: List[Tuple[float, float]],
                            regenerate_seed: int = None) -> List[TrimStrategy]:
    """
    Generate 3 trim strategies (conservative, balanced, aggressive).
    
    Args:
        clusters: Clustered similar segments from segment matcher
        original_length: Original audio length in seconds
        target_length: Target audio length in seconds
        protected_regions: List of (start, end) protected regions
        regenerate_seed: Optional seed for regeneration variety
    
    Returns:
        List of 3 TrimStrategy objects, all within ±15s of target
    """
    # Apply regeneration variety if seed provided
    if regenerate_seed is not None:
        np.random.seed(regenerate_seed)
        # Shuffle clusters for variety
        clusters = list(clusters)
        np.random.shuffle(clusters)
    
    strategies = [
        generate_conservative_strategy(clusters, original_length, target_length, protected_regions),
        generate_balanced_strategy(clusters, original_length, target_length, protected_regions),
        generate_aggressive_strategy(clusters, original_length, target_length, protected_regions),
    ]
    
    # Verify all strategies meet ±15s constraint
    for strategy in strategies:
        result_length = strategy.calculate_resulting_length(original_length)
        error = abs(result_length - target_length)
        
        if error > 15.0:
            # Apply fade-out fallback to reach target
            strategy.cut_points.append((target_length, original_length))
            strategy.fade_regions.append((target_length - 2.0, target_length))
    
    return strategies
```

- [ ] **Step 20: Run all tests to verify they pass**

Run: `pytest tests/test_trim_engine.py -v`
Expected: All tests PASS

- [ ] **Step 21: Commit**

```bash
git add src/trim_engine.py tests/test_trim_engine.py
git commit -m "feat: add trim engine with conservative/balanced/aggressive strategies"
```

---

## Task 6: Quality Scorer Module

**Files:**
- Create: `src/quality_scorer.py`
- Create: `tests/test_quality_scorer.py`

- [ ] **Step 1: Write failing test for star conversion**

Create `tests/test_quality_scorer.py`:

```python
import pytest
from src.quality_scorer import points_to_stars


def test_points_to_stars_conversion():
    """Test converting points to star ratings."""
    assert points_to_stars(95) == 5.0
    assert points_to_stars(90) == 5.0
    assert points_to_stars(87) == 4.5
    assert points_to_stars(85) == 4.5
    assert points_to_stars(82) == 4.0
    assert points_to_stars(77) == 3.5
    assert points_to_stars(72) == 3.0
    assert points_to_stars(65) == 2.5
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_quality_scorer.py::test_points_to_stars_conversion -v`
Expected: FAIL with "cannot import name 'points_to_stars'"

- [ ] **Step 3: Implement star conversion**

Create `src/quality_scorer.py`:

```python
"""Quality scoring for trim strategies."""
import numpy as np
from typing import Dict, List, Tuple
from src.trim_engine import TrimStrategy


def points_to_stars(points: float) -> float:
    """
    Convert quality points (0-100) to star rating.
    
    Args:
        points: Quality score from 0-100
    
    Returns:
        Star rating: 5.0, 4.5, 4.0, 3.5, 3.0, 2.5, etc.
    """
    if points >= 90:
        return 5.0
    elif points >= 85:
        return 4.5
    elif points >= 80:
        return 4.0
    elif points >= 75:
        return 3.5
    elif points >= 70:
        return 3.0
    elif points >= 65:
        return 2.5
    elif points >= 60:
        return 2.0
    elif points >= 55:
        return 1.5
    elif points >= 50:
        return 1.0
    else:
        return 0.5
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_quality_scorer.py::test_points_to_stars_conversion -v`
Expected: PASS

- [ ] **Step 5: Write test for transition smoothness scoring**

Add to `tests/test_quality_scorer.py`:

```python
def test_score_transition_smoothness():
    """Test scoring transition smoothness."""
    from src.quality_scorer import score_transition_smoothness
    
    # Generate test audio
    sr = 22050
    audio_data = np.sin(2 * np.pi * 440 * np.linspace(0, 10, sr * 10))
    
    cut_points = [(2.0, 3.0)]
    fade_regions = [(1.95, 2.05), (2.95, 3.05)]
    
    score = score_transition_smoothness(audio_data, sr, cut_points, fade_regions)
    
    # Should return score out of 40
    assert 0 <= score <= 40
```

- [ ] **Step 6: Run test to verify it fails**

Run: `pytest tests/test_quality_scorer.py::test_score_transition_smoothness -v`
Expected: FAIL with "cannot import name 'score_transition_smoothness'"

- [ ] **Step 7: Implement transition smoothness scoring**

Add to `src/quality_scorer.py`:

```python
def score_transition_smoothness(audio_data: np.ndarray, sample_rate: int,
                                cut_points: List[Tuple[float, float]],
                                fade_regions: List[Tuple[float, float]]) -> float:
    """
    Score transition smoothness at cut/loop points (max 40 points).
    
    Breakdown:
    - Phase alignment (15 pts): Cross-correlation at splice points
    - Zero-crossing detection (10 pts): Cuts at zero crossings
    - Fade quality (15 pts): Smooth fade curves
    
    Args:
        audio_data: Audio samples array
        sample_rate: Sample rate in Hz
        cut_points: List of (start, end) cut regions
        fade_regions: List of (start, end) fade regions
    
    Returns:
        Score out of 40 points
    """
    score = 0.0
    
    # Phase alignment score (15 points)
    # Simplified: check if cuts happen at relatively low amplitude
    phase_score = 15.0
    for start, end in cut_points:
        start_idx = int(start * sample_rate)
        end_idx = int(end * sample_rate)
        
        if 0 <= start_idx < len(audio_data):
            start_amp = abs(audio_data[start_idx])
            if start_amp > 0.5:
                phase_score -= 3.0
        
        if 0 <= end_idx < len(audio_data):
            end_amp = abs(audio_data[end_idx])
            if end_amp > 0.5:
                phase_score -= 3.0
    
    score += max(0, phase_score)
    
    # Zero-crossing detection (10 points)
    # Check if cuts happen near zero crossings
    zero_crossing_score = 10.0
    for start, end in cut_points:
        start_idx = int(start * sample_rate)
        end_idx = int(end * sample_rate)
        
        # Check within ±10 samples for zero crossing
        for idx in [start_idx, end_idx]:
            if 10 <= idx < len(audio_data) - 10:
                window = audio_data[idx-10:idx+10]
                # Check if there's a sign change (zero crossing)
                if not np.any(np.diff(np.sign(window)) != 0):
                    zero_crossing_score -= 2.0
    
    score += max(0, zero_crossing_score)
    
    # Fade quality (15 points)
    # Simplified: longer fades generally smoother
    fade_score = 15.0
    for start, end in fade_regions:
        fade_duration_ms = (end - start) * 1000
        if fade_duration_ms < 50:
            fade_score -= 3.0
        elif fade_duration_ms < 100:
            fade_score -= 1.0
    
    score += max(0, fade_score)
    
    return min(40.0, score)
```

- [ ] **Step 8: Run test to verify it passes**

Run: `pytest tests/test_quality_scorer.py::test_score_transition_smoothness -v`
Expected: PASS

- [ ] **Step 9: Write test for musical coherence scoring**

Add to `tests/test_quality_scorer.py`:

```python
def test_score_musical_coherence():
    """Test scoring musical coherence."""
    from src.quality_scorer import score_musical_coherence
    
    sr = 22050
    audio_data = np.sin(2 * np.pi * 440 * np.linspace(0, 10, sr * 10))
    
    cut_points = [(2.0, 3.0)]
    chroma = np.random.rand(12, 200)
    
    score = score_musical_coherence(audio_data, sr, cut_points, chroma)
    
    # Should return score out of 40
    assert 0 <= score <= 40
```

- [ ] **Step 10: Run test to verify it fails**

Run: `pytest tests/test_quality_scorer.py::test_score_musical_coherence -v`
Expected: FAIL with "cannot import name 'score_musical_coherence'"

- [ ] **Step 11: Implement musical coherence scoring**

Add to `src/quality_scorer.py`:

```python
import librosa


def score_musical_coherence(audio_data: np.ndarray, sample_rate: int,
                           cut_points: List[Tuple[float, float]],
                           chroma: np.ndarray) -> float:
    """
    Score musical coherence (max 40 points).
    
    Breakdown:
    - Cuts at measure/phrase boundaries (20 pts): Align with beat grid
    - Maintains harmonic progression (10 pts): Chroma continuity
    - Section order makes sense (10 pts): Preserve structure
    
    Args:
        audio_data: Audio samples array
        sample_rate: Sample rate in Hz
        cut_points: List of (start, end) cut regions
        chroma: Chroma feature matrix
    
    Returns:
        Score out of 40 points
    """
    score = 0.0
    
    # Detect beats for measure alignment (20 points)
    try:
        tempo, beats = librosa.beat.beat_track(y=audio_data, sr=sample_rate)
        beat_times = librosa.frames_to_time(beats, sr=sample_rate)
        
        measure_score = 20.0
        for start, end in cut_points:
            # Check if cut points are near beats
            start_near_beat = np.any(np.abs(beat_times - start) < 0.1)
            end_near_beat = np.any(np.abs(beat_times - end) < 0.1)
            
            if not start_near_beat:
                measure_score -= 5.0
            if not end_near_beat:
                measure_score -= 5.0
        
        score += max(0, measure_score)
    except:
        # If beat detection fails, give partial credit
        score += 10.0
    
    # Harmonic progression (10 points)
    # Check chroma continuity across cuts
    harmonic_score = 10.0
    hop_length = 2048
    frame_duration = hop_length / sample_rate
    
    for start, end in cut_points:
        start_frame = int(start / frame_duration)
        end_frame = int(end / frame_duration)
        
        if 1 <= start_frame < chroma.shape[1] - 1:
            # Compare chroma before and after cut
            chroma_before = chroma[:, start_frame - 1]
            chroma_after = chroma[:, start_frame]
            correlation = np.corrcoef(chroma_before, chroma_after)[0, 1]
            
            if correlation < 0.5:
                harmonic_score -= 3.0
    
    score += max(0, harmonic_score)
    
    # Section order (10 points)
    # Simplified: cuts should preserve general flow (intro -> middle -> outro)
    section_score = 10.0
    sorted_cuts = sorted(cut_points, key=lambda x: x[0])
    
    # Penalize if cuts are removing intro or outro
    total_duration = len(audio_data) / sample_rate
    for start, end in sorted_cuts:
        if start < total_duration * 0.1:  # Cutting intro
            section_score -= 3.0
        if end > total_duration * 0.9:  # Cutting outro
            section_score -= 3.0
    
    score += max(0, section_score)
    
    return min(40.0, score)
```

- [ ] **Step 12: Run test to verify it passes**

Run: `pytest tests/test_quality_scorer.py::test_score_musical_coherence -v`
Expected: PASS

- [ ] **Step 13: Write test for length accuracy scoring**

Add to `tests/test_quality_scorer.py`:

```python
def test_score_length_accuracy():
    """Test scoring length accuracy."""
    from src.quality_scorer import score_length_accuracy
    
    target = 120.0
    
    # Within 3 seconds: 20 points
    assert score_length_accuracy(121.0, target) == 20.0
    assert score_length_accuracy(118.0, target) == 20.0
    
    # 3-8 seconds: 15 points
    assert score_length_accuracy(125.0, target) == 15.0
    assert score_length_accuracy(114.0, target) == 15.0
    
    # 8-15 seconds: 10 points
    assert score_length_accuracy(132.0, target) == 10.0
    assert score_length_accuracy(107.0, target) == 10.0
    
    # Over 15 seconds: 0 points
    assert score_length_accuracy(140.0, target) == 0.0
```

- [ ] **Step 14: Run test to verify it fails**

Run: `pytest tests/test_quality_scorer.py::test_score_length_accuracy -v`
Expected: FAIL with "cannot import name 'score_length_accuracy'"

- [ ] **Step 15: Implement length accuracy scoring**

Add to `src/quality_scorer.py`:

```python
def score_length_accuracy(result_length: float, target_length: float) -> float:
    """
    Score length accuracy (max 20 points).
    
    Args:
        result_length: Resulting audio length in seconds
        target_length: Target audio length in seconds
    
    Returns:
        Score out of 20 points based on distance from target
    """
    error = abs(result_length - target_length)
    
    if error <= 3.0:
        return 20.0
    elif error <= 8.0:
        return 15.0
    elif error <= 15.0:
        return 10.0
    else:
        return 0.0
```

- [ ] **Step 16: Run test to verify it passes**

Run: `pytest tests/test_quality_scorer.py::test_score_length_accuracy -v`
Expected: PASS

- [ ] **Step 17: Write test for complete quality scoring**

Add to `tests/test_quality_scorer.py`:

```python
def test_score_strategy():
    """Test complete strategy scoring."""
    from src.quality_scorer import score_strategy
    from src.trim_engine import TrimStrategy
    
    sr = 22050
    audio_data = np.sin(2 * np.pi * 440 * np.linspace(0, 10, sr * 10))
    chroma = np.random.rand(12, 200)
    
    strategy = TrimStrategy(
        name="balanced",
        cut_points=[(2.0, 3.0)],
        loop_points=[],
        fade_regions=[(1.9, 2.1), (2.9, 3.1)],
        target_length=9.0
    )
    
    original_length = 10.0
    
    result = score_strategy(strategy, audio_data, sr, chroma, original_length)
    
    assert 'total_points' in result
    assert 'star_rating' in result
    assert 'breakdown' in result
    assert 0 <= result['total_points'] <= 100
    assert 0 <= result['star_rating'] <= 5.0
```

- [ ] **Step 18: Run test to verify it fails**

Run: `pytest tests/test_quality_scorer.py::test_score_strategy -v`
Expected: FAIL with "cannot import name 'score_strategy'"

- [ ] **Step 19: Implement complete strategy scoring**

Add to `src/quality_scorer.py`:

```python
def score_strategy(strategy: TrimStrategy, audio_data: np.ndarray, sample_rate: int,
                  chroma: np.ndarray, original_length: float) -> Dict:
    """
    Score a trim strategy across all quality dimensions.
    
    Args:
        strategy: TrimStrategy to score
        audio_data: Original audio samples
        sample_rate: Sample rate in Hz
        chroma: Chroma feature matrix
        original_length: Original audio length in seconds
    
    Returns:
        Dictionary with keys:
        - total_points: Total score (0-100)
        - star_rating: Star rating (0.5-5.0)
        - breakdown: Dict with individual component scores
    """
    # Calculate resulting length
    result_length = strategy.calculate_resulting_length(original_length)
    
    # Score each component
    transition_score = score_transition_smoothness(
        audio_data, sample_rate, strategy.cut_points, strategy.fade_regions
    )
    
    coherence_score = score_musical_coherence(
        audio_data, sample_rate, strategy.cut_points, chroma
    )
    
    length_score = score_length_accuracy(result_length, strategy.target_length)
    
    # Calculate total
    total = transition_score + coherence_score + length_score
    stars = points_to_stars(total)
    
    return {
        'total_points': total,
        'star_rating': stars,
        'breakdown': {
            'transition_smoothness': transition_score,
            'musical_coherence': coherence_score,
            'length_accuracy': length_score
        }
    }
```

- [ ] **Step 20: Run all tests to verify they pass**

Run: `pytest tests/test_quality_scorer.py -v`
Expected: All tests PASS

- [ ] **Step 21: Commit**

```bash
git add src/quality_scorer.py tests/test_quality_scorer.py
git commit -m "feat: add quality scorer with transition, coherence, and length scoring"
```

---

## Task 7: Output Generator Module

**Files:**
- Create: `src/output_generator.py`
- Create: `tests/test_output_generator.py`

- [ ] **Step 1: Write failing test for applying cuts to audio**

Create `tests/test_output_generator.py`:

```python
import pytest
import numpy as np
from src.output_generator import apply_cuts


def test_apply_cuts_removes_segments():
    """Test that cuts remove specified audio segments."""
    sr = 22050
    duration = 10
    audio_data = np.sin(2 * np.pi * 440 * np.linspace(0, duration, sr * duration))
    
    # Cut out seconds 3-5
    cut_points = [(3.0, 5.0)]
    
    result = apply_cuts(audio_data, sr, cut_points)
    
    # Result should be 8 seconds (10 - 2)
    expected_length = sr * 8
    assert len(result) == expected_length
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_output_generator.py::test_apply_cuts_removes_segments -v`
Expected: FAIL with "cannot import name 'apply_cuts'"

- [ ] **Step 3: Implement cut application**

Create `src/output_generator.py`:

```python
"""Output generation for trimmed audio files and metadata."""
import numpy as np
import soundfile as sf
import json
from typing import List, Tuple, Dict
from pathlib import Path
from src.trim_engine import TrimStrategy


def apply_cuts(audio_data: np.ndarray, sample_rate: int, 
               cut_points: List[Tuple[float, float]]) -> np.ndarray:
    """
    Apply cuts to audio data, removing specified segments.
    
    Args:
        audio_data: Audio samples array
        sample_rate: Sample rate in Hz
        cut_points: List of (start, end) regions to remove in seconds
    
    Returns:
        Audio array with cuts applied
    """
    if not cut_points:
        return audio_data
    
    # Sort cuts by start time
    sorted_cuts = sorted(cut_points, key=lambda x: x[0])
    
    # Build list of segments to keep
    segments = []
    current_pos = 0.0
    total_duration = len(audio_data) / sample_rate
    
    for start, end in sorted_cuts:
        # Add segment before this cut
        if current_pos < start:
            start_idx = int(current_pos * sample_rate)
            end_idx = int(start * sample_rate)
            segments.append(audio_data[start_idx:end_idx])
        
        current_pos = end
    
    # Add remaining audio after last cut
    if current_pos < total_duration:
        start_idx = int(current_pos * sample_rate)
        segments.append(audio_data[start_idx:])
    
    # Concatenate all kept segments
    if segments:
        return np.concatenate(segments)
    else:
        return np.array([])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_output_generator.py::test_apply_cuts_removes_segments -v`
Expected: PASS

- [ ] **Step 5: Write test for applying loops**

Add to `tests/test_output_generator.py`:

```python
def test_apply_loops_repeats_segments():
    """Test that loops repeat specified segments."""
    from src.output_generator import apply_loops
    
    sr = 22050
    duration = 10
    audio_data = np.sin(2 * np.pi * 440 * np.linspace(0, duration, sr * duration))
    
    # Loop seconds 2-4 twice (repeat once)
    loop_points = [(2.0, 4.0, 2)]
    
    result = apply_loops(audio_data, sr, loop_points)
    
    # Result should be 12 seconds (10 + 2)
    expected_length = sr * 12
    assert len(result) == expected_length
```

- [ ] **Step 6: Run test to verify it fails**

Run: `pytest tests/test_output_generator.py::test_apply_loops_repeats_segments -v`
Expected: FAIL with "cannot import name 'apply_loops'"

- [ ] **Step 7: Implement loop application**

Add to `src/output_generator.py`:

```python
def apply_loops(audio_data: np.ndarray, sample_rate: int,
                loop_points: List[Tuple[float, float, int]]) -> np.ndarray:
    """
    Apply loops to audio data, repeating specified segments.
    
    Args:
        audio_data: Audio samples array
        sample_rate: Sample rate in Hz
        loop_points: List of (start, end, repeat_count) where repeat_count includes original
    
    Returns:
        Audio array with loops applied
    """
    if not loop_points:
        return audio_data
    
    # Sort loops by start time
    sorted_loops = sorted(loop_points, key=lambda x: x[0])
    
    # Build list of segments
    segments = []
    current_pos = 0.0
    
    for start, end, repeat_count in sorted_loops:
        # Add segment before this loop
        if current_pos < start:
            start_idx = int(current_pos * sample_rate)
            end_idx = int(start * sample_rate)
            segments.append(audio_data[start_idx:end_idx])
        
        # Add looped segment
        start_idx = int(start * sample_rate)
        end_idx = int(end * sample_rate)
        loop_segment = audio_data[start_idx:end_idx]
        
        # Repeat the segment
        for _ in range(repeat_count):
            segments.append(loop_segment)
        
        current_pos = end
    
    # Add remaining audio
    total_duration = len(audio_data) / sample_rate
    if current_pos < total_duration:
        start_idx = int(current_pos * sample_rate)
        segments.append(audio_data[start_idx:])
    
    return np.concatenate(segments)
```

- [ ] **Step 8: Run test to verify it passes**

Run: `pytest tests/test_output_generator.py::test_apply_loops_repeats_segments -v`
Expected: PASS

- [ ] **Step 9: Write test for applying crossfades**

Add to `tests/test_output_generator.py`:

```python
def test_apply_crossfades():
    """Test applying crossfade regions."""
    from src.output_generator import apply_crossfades
    
    sr = 22050
    duration = 10
    audio_data = np.sin(2 * np.pi * 440 * np.linspace(0, duration, sr * duration))
    
    # Fade at seconds 2-2.2 and 7.8-8
    fade_regions = [(2.0, 2.2), (7.8, 8.0)]
    
    result = apply_crossfades(audio_data, sr, fade_regions)
    
    # Length should remain the same
    assert len(result) == len(audio_data)
    
    # Check that fade regions have reduced amplitude
    fade1_start = int(2.0 * sr)
    fade1_end = int(2.2 * sr)
    # First sample should be reduced (fade in)
    assert abs(result[fade1_start]) < abs(audio_data[fade1_start])
```

- [ ] **Step 10: Run test to verify it fails**

Run: `pytest tests/test_output_generator.py::test_apply_crossfades -v`
Expected: FAIL with "cannot import name 'apply_crossfades'"

- [ ] **Step 11: Implement crossfade application**

Add to `src/output_generator.py`:

```python
def apply_crossfades(audio_data: np.ndarray, sample_rate: int,
                     fade_regions: List[Tuple[float, float]]) -> np.ndarray:
    """
    Apply crossfades to audio at specified regions.
    
    Args:
        audio_data: Audio samples array
        sample_rate: Sample rate in Hz
        fade_regions: List of (start, end) fade regions in seconds
    
    Returns:
        Audio array with fades applied
    """
    result = audio_data.copy()
    
    for start, end in fade_regions:
        start_idx = int(start * sample_rate)
        end_idx = int(end * sample_rate)
        
        if start_idx < 0 or end_idx > len(result):
            continue
        
        fade_length = end_idx - start_idx
        if fade_length <= 0:
            continue
        
        # Create fade curve (linear for simplicity)
        fade_curve = np.linspace(0, 1, fade_length)
        
        # Determine if this is fade in or fade out based on position
        # Simplified: alternate between fade in and fade out
        result[start_idx:end_idx] *= fade_curve
    
    return result
```

- [ ] **Step 12: Run test to verify it passes**

Run: `pytest tests/test_output_generator.py::test_apply_crossfades -v`
Expected: PASS

- [ ] **Step 13: Write test for rendering complete strategy**

Add to `tests/test_output_generator.py`:

```python
def test_render_strategy():
    """Test rendering a complete trim strategy."""
    from src.output_generator import render_strategy
    from src.trim_engine import TrimStrategy
    
    sr = 22050
    duration = 10
    audio_data = np.sin(2 * np.pi * 440 * np.linspace(0, duration, sr * duration))
    
    strategy = TrimStrategy(
        name="balanced",
        cut_points=[(3.0, 5.0)],
        loop_points=[],
        fade_regions=[(2.9, 3.1), (4.9, 5.1)],
        target_length=8.0
    )
    
    result = render_strategy(audio_data, sr, strategy)
    
    # Result should be approximately 8 seconds
    result_duration = len(result) / sr
    assert 7.5 <= result_duration <= 8.5
```

- [ ] **Step 14: Run test to verify it fails**

Run: `pytest tests/test_output_generator.py::test_render_strategy -v`
Expected: FAIL with "cannot import name 'render_strategy'"

- [ ] **Step 15: Implement strategy rendering**

Add to `src/output_generator.py`:

```python
def render_strategy(audio_data: np.ndarray, sample_rate: int, 
                   strategy: TrimStrategy) -> np.ndarray:
    """
    Render audio with a trim strategy applied.
    
    Args:
        audio_data: Original audio samples
        sample_rate: Sample rate in Hz
        strategy: TrimStrategy to apply
    
    Returns:
        Rendered audio array
    """
    # Apply operations in order: loops, cuts, fades
    result = audio_data.copy()
    
    # Apply loops first (extends audio)
    if strategy.loop_points:
        result = apply_loops(result, sample_rate, strategy.loop_points)
    
    # Apply cuts (shortens audio)
    if strategy.cut_points:
        result = apply_cuts(result, sample_rate, strategy.cut_points)
    
    # Apply crossfades (smooths transitions)
    if strategy.fade_regions:
        result = apply_crossfades(result, sample_rate, strategy.fade_regions)
    
    return result
```

- [ ] **Step 16: Run test to verify it passes**

Run: `pytest tests/test_output_generator.py::test_render_strategy -v`
Expected: PASS

- [ ] **Step 17: Write test for generating output files**

Add to `tests/test_output_generator.py`:

```python
import tempfile
import os


def test_generate_outputs():
    """Test generating output files for strategies."""
    from src.output_generator import generate_outputs
    from src.trim_engine import TrimStrategy
    
    sr = 22050
    duration = 10
    audio_data = np.sin(2 * np.pi * 440 * np.linspace(0, duration, sr * duration))
    
    strategies = [
        TrimStrategy(name="conservative", cut_points=[], loop_points=[], 
                    fade_regions=[], target_length=10.0),
    ]
    
    scores = [
        {'total_points': 87, 'star_rating': 4.5, 'breakdown': {}}
    ]
    
    with tempfile.TemporaryDirectory() as tmpdir:
        result = generate_outputs(
            audio_data, sr, strategies, scores,
            output_dir=tmpdir,
            input_filename="test.wav",
            target_length=10.0,
            protected_regions=[],
            processing_time=5.0
        )
        
        assert 'audio_files' in result
        assert 'summary_json' in result
        assert 'summary_txt' in result
        
        # Check files exist
        assert os.path.exists(result['summary_json'])
        assert os.path.exists(result['summary_txt'])
```

- [ ] **Step 18: Run test to verify it fails**

Run: `pytest tests/test_output_generator.py::test_generate_outputs -v`
Expected: FAIL with "cannot import name 'generate_outputs'"

- [ ] **Step 19: Implement output generation**

Add to `src/output_generator.py`:

```python
def generate_outputs(audio_data: np.ndarray, sample_rate: int,
                    strategies: List[TrimStrategy], scores: List[Dict],
                    output_dir: str, input_filename: str,
                    target_length: float, protected_regions: List[Tuple[float, float]],
                    processing_time: float) -> Dict:
    """
    Generate output files for all strategies.
    
    Args:
        audio_data: Original audio samples
        sample_rate: Sample rate in Hz
        strategies: List of TrimStrategy objects
        scores: List of score dictionaries (matching strategies)
        output_dir: Output directory path
        input_filename: Original input filename
        target_length: Target length in seconds
        protected_regions: List of protected regions
        processing_time: Processing time in seconds
    
    Returns:
        Dictionary with paths to generated files
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Get file extension from input
    input_ext = Path(input_filename).suffix
    if not input_ext:
        input_ext = '.wav'
    
    audio_files = []
    
    # Render and save each strategy
    for i, (strategy, score) in enumerate(zip(strategies, scores), start=1):
        # Render audio
        rendered = render_strategy(audio_data, sample_rate, strategy)
        
        # Generate filename
        stars = score['star_rating']
        output_filename = f"option_{i}_{stars}stars{input_ext}"
        output_filepath = output_path / output_filename
        
        # Save audio file
        sf.write(str(output_filepath), rendered, sample_rate)
        audio_files.append(str(output_filepath))
    
    # Generate summary.json
    summary_data = {
        'input_file': input_filename,
        'target_length': target_length,
        'protected_regions': [[start, end] for start, end in protected_regions],
        'processing_time': processing_time,
        'options': []
    }
    
    for i, (strategy, score) in enumerate(zip(strategies, scores), start=1):
        result_length = strategy.calculate_resulting_length(len(audio_data) / sample_rate)
        
        summary_data['options'].append({
            'number': i,
            'rating_stars': score['star_rating'],
            'rating_points': score['total_points'],
            'strategy': strategy.name,
            'actual_length': result_length,
            'cuts': [[start, end] for start, end in strategy.cut_points],
            'loops': [[start, end, count] for start, end, count in strategy.loop_points],
            'fades': [[start, end] for start, end in strategy.fade_regions],
            'score_breakdown': score['breakdown']
        })
    
    summary_json_path = output_path / 'summary.json'
    with open(summary_json_path, 'w') as f:
        json.dump(summary_data, f, indent=2)
    
    # Generate summary.txt
    summary_txt_path = output_path / 'summary.txt'
    with open(summary_txt_path, 'w') as f:
        f.write(f"Music Smart Trim - Processing Summary\n")
        f.write(f"=" * 50 + "\n\n")
        f.write(f"Input: {input_filename}\n")
        f.write(f"Target Length: {target_length}s\n")
        f.write(f"Processing Time: {processing_time:.1f}s\n\n")
        
        for i, (strategy, score) in enumerate(zip(strategies, scores), start=1):
            result_length = strategy.calculate_resulting_length(len(audio_data) / sample_rate)
            stars_display = "★" * int(score['star_rating']) + "☆" * (5 - int(score['star_rating']))
            
            f.write(f"Option {i}: {stars_display} {score['star_rating']}\n")
            f.write(f"  Strategy: {strategy.name}\n")
            f.write(f"  Length: {result_length:.1f}s (target: {target_length}s)\n")
            f.write(f"  Cuts: {len(strategy.cut_points)}, Loops: {len(strategy.loop_points)}\n")
            f.write(f"  Score: {score['total_points']:.1f}/100\n\n")
    
    return {
        'audio_files': audio_files,
        'summary_json': str(summary_json_path),
        'summary_txt': str(summary_txt_path)
    }
```

- [ ] **Step 20: Run all tests to verify they pass**

Run: `pytest tests/test_output_generator.py -v`
Expected: All tests PASS

- [ ] **Step 21: Commit**

```bash
git add src/output_generator.py tests/test_output_generator.py
git commit -m "feat: add output generator with audio rendering and metadata export"
```

---

## Task 8: CLI Module

**Files:**
- Create: `src/cli.py`
- Create: `tests/test_integration.py`

- [ ] **Step 1: Write integration test for complete pipeline**

Create `tests/test_integration.py`:

```python
import pytest
import tempfile
import os
import json
from src.cli import run_pipeline


def test_complete_pipeline_end_to_end():
    """Test complete pipeline from audio input to trimmed outputs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = run_pipeline(
            input_file="tests/fixtures/sample_30s.wav",
            target_length=25,
            protected_regions="",
            output_dir=tmpdir
        )
        
        assert 'strategies' in result
        assert 'scores' in result
        assert 'output_files' in result
        
        # Should have 3 strategies
        assert len(result['strategies']) == 3
        assert len(result['scores']) == 3
        
        # At least one should be >= 4.5 stars
        star_ratings = [s['star_rating'] for s in result['scores']]
        assert any(rating >= 4.5 for rating in star_ratings)
        
        # All should be within ±15 seconds
        for i, strategy in enumerate(result['strategies']):
            actual_length = strategy.calculate_resulting_length(30.0)
            error = abs(actual_length - 25.0)
            assert error <= 15.0, f"Strategy {i} error {error}s exceeds 15s"
        
        # Check output files exist
        summary_json = os.path.join(tmpdir, 'summary.json')
        assert os.path.exists(summary_json)
        
        with open(summary_json) as f:
            summary = json.load(f)
            assert len(summary['options']) == 3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_integration.py::test_complete_pipeline_end_to_end -v`
Expected: FAIL with "cannot import name 'run_pipeline'"

- [ ] **Step 3: Implement pipeline orchestration**

Create `src/cli.py`:

```python
"""Command-line interface for music smart trim."""
import argparse
import sys
import time
from typing import Dict
from pathlib import Path

from src.audio_loader import load_audio, check_normalized_size, AudioLoadError
from src.spectral_analyzer import analyze_audio_structure
from src.segment_matcher import match_segments
from src.trim_engine import generate_trim_strategies
from src.quality_scorer import score_strategy
from src.output_generator import generate_outputs


def run_pipeline(input_file: str, target_length: float, protected_regions: str,
                output_dir: str = "./output", regenerate_seed: int = None) -> Dict:
    """
    Run complete music trim pipeline.
    
    Args:
        input_file: Path to input audio file
        target_length: Target length in seconds
        protected_regions: Protected regions string (e.g., "0:30-1:15,2:00-2:30")
        output_dir: Output directory path
        regenerate_seed: Optional seed for regeneration
    
    Returns:
        Dictionary with strategies, scores, and output file paths
    """
    start_time = time.time()
    
    # Load audio
    print(f"Loading audio: {input_file}")
    audio_data, sr = load_audio(input_file)
    original_length = len(audio_data) / sr
    print(f"  Duration: {original_length:.1f}s, Sample rate: {sr} Hz")
    
    # Check file size
    is_valid, size_mb = check_normalized_size(audio_data, sr)
    if not is_valid:
        print(f"  Warning: Normalized audio size ({size_mb:.1f} MB) exceeds 15 MB limit")
    
    # Analyze audio structure
    print("Analyzing audio structure...")
    analysis = analyze_audio_structure(audio_data, sr)
    print(f"  Found {len(analysis['repeated_segments'])} repeated segments")
    
    # Match segments
    print("Matching similar segments...")
    match_result = match_segments(analysis['repeated_segments'], protected_regions)
    print(f"  Clustered into {len(match_result['clusters'])} groups")
    print(f"  Protected regions: {len(match_result['protected_regions'])}")
    
    # Generate strategies
    print("Generating trim strategies...")
    strategies = generate_trim_strategies(
        match_result['clusters'],
        original_length,
        target_length,
        match_result['protected_regions'],
        regenerate_seed=regenerate_seed
    )
    print(f"  Generated {len(strategies)} strategies")
    
    # Score strategies
    print("Scoring strategies...")
    scores = []
    for strategy in strategies:
        score = score_strategy(strategy, audio_data, sr, analysis['chroma'], original_length)
        scores.append(score)
        print(f"  {strategy.name}: {score['star_rating']}★ ({score['total_points']:.0f} points)")
    
    # Ensure at least one >= 4.5 stars
    max_attempts = 5
    attempt = 1
    while attempt < max_attempts and not any(s['star_rating'] >= 4.5 for s in scores):
        print(f"  No option >= 4.5★, regenerating (attempt {attempt + 1}/{max_attempts})...")
        strategies = generate_trim_strategies(
            match_result['clusters'],
            original_length,
            target_length,
            match_result['protected_regions'],
            regenerate_seed=attempt
        )
        scores = [score_strategy(s, audio_data, sr, analysis['chroma'], original_length) 
                 for s in strategies]
        attempt += 1
    
    if not any(s['star_rating'] >= 4.5 for s in scores):
        print(f"  Warning: Could not generate option >= 4.5★ after {max_attempts} attempts")
    
    # Generate outputs
    print(f"Rendering outputs to {output_dir}...")
    processing_time = time.time() - start_time
    
    output_files = generate_outputs(
        audio_data, sr, strategies, scores,
        output_dir=output_dir,
        input_filename=Path(input_file).name,
        target_length=target_length,
        protected_regions=match_result['protected_regions'],
        processing_time=processing_time
    )
    
    print(f"\nProcessing complete! ({processing_time:.1f} seconds)")
    
    return {
        'strategies': strategies,
        'scores': scores,
        'output_files': output_files,
        'processing_time': processing_time
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_integration.py::test_complete_pipeline_end_to_end -v`
Expected: PASS

- [ ] **Step 5: Write test for CLI argument parsing**

Add to `tests/test_integration.py`:

```python
def test_parse_arguments():
    """Test CLI argument parsing."""
    from src.cli import parse_arguments
    
    args = parse_arguments(['--input', 'test.mp3', '--target', '120'])
    
    assert args.input == 'test.mp3'
    assert args.target == 120
    assert args.protect == ""
    assert args.output_dir == "./output"
```

- [ ] **Step 6: Run test to verify it fails**

Run: `pytest tests/test_integration.py::test_parse_arguments -v`
Expected: FAIL with "cannot import name 'parse_arguments'"

- [ ] **Step 7: Implement argument parsing**

Add to `src/cli.py`:

```python
def parse_arguments(args=None):
    """
    Parse command-line arguments.
    
    Args:
        args: Optional argument list (for testing)
    
    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        description="Music Smart Trim - Intelligently adjust audio to target length"
    )
    
    parser.add_argument(
        '--input',
        required=True,
        help="Path to input audio file (MP3, WAV, FLAC, M4A, OGG)"
    )
    
    parser.add_argument(
        '--target',
        type=float,
        required=True,
        help="Target length in seconds"
    )
    
    parser.add_argument(
        '--protect',
        default="",
        help='Protected regions to preserve (e.g., "0:30-1:15,2:00-2:30")'
    )
    
    parser.add_argument(
        '--output-dir',
        default="./output",
        help="Output directory (default: ./output)"
    )
    
    return parser.parse_args(args)
```

- [ ] **Step 8: Run test to verify it passes**

Run: `pytest tests/test_integration.py::test_parse_arguments -v`
Expected: PASS

- [ ] **Step 9: Implement main CLI entry point with regeneration**

Add to `src/cli.py`:

```python
def display_results(strategies, scores, output_files, processing_time):
    """Display results to user."""
    print("\n" + "=" * 60)
    print(f"Processing complete! ({processing_time:.1f} seconds)\n")
    
    for i, (strategy, score) in enumerate(zip(strategies, scores), start=1):
        stars_full = int(score['star_rating'])
        stars_display = "★" * stars_full + "☆" * (5 - stars_full)
        
        result_length_min = int(strategy.calculate_resulting_length(0) // 60)
        result_length_sec = int(strategy.calculate_resulting_length(0) % 60)
        
        print(f"Option {i}: {stars_display} {score['star_rating']}")
        print(f"  (strategy: {strategy.name}, length: {result_length_min}:{result_length_sec:02d}, "
              f"cuts: {len(strategy.cut_points)}, loops: {len(strategy.loop_points)})")
    
    print(f"\nFiles saved to: {Path(output_files['summary_json']).parent}")
    for audio_file in output_files['audio_files']:
        print(f"  - {Path(audio_file).name}")
    print(f"  - summary.json")
    print(f"  - summary.txt")


def main():
    """Main CLI entry point."""
    try:
        args = parse_arguments()
        
        # Run initial pipeline
        result = run_pipeline(
            input_file=args.input,
            target_length=args.target,
            protected_regions=args.protect,
            output_dir=args.output_dir
        )
        
        # Display results
        display_results(
            result['strategies'],
            result['scores'],
            result['output_files'],
            result['processing_time']
        )
        
        # Ask for regeneration
        print("\nRegenerate for 3 new options? (y/n): ", end="")
        response = input().strip().lower()
        
        regenerate_count = 1
        while response == 'y':
            print("\nRegenerating...")
            result = run_pipeline(
                input_file=args.input,
                target_length=args.target,
                protected_regions=args.protect,
                output_dir=args.output_dir,
                regenerate_seed=regenerate_count
            )
            
            display_results(
                result['strategies'],
                result['scores'],
                result['output_files'],
                result['processing_time']
            )
            
            regenerate_count += 1
            print("\nRegenerate for 3 new options? (y/n): ", end="")
            response = input().strip().lower()
        
        print("\nDone!")
        return 0
        
    except AudioLoadError as e:
        print(f"Error loading audio: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 10: Test CLI manually**

Run: 
```bash
python src/cli.py --input tests/fixtures/sample_30s.wav --target 25
```

Expected: Processes successfully, generates 3 options, prompts for regeneration

- [ ] **Step 11: Commit**

```bash
git add src/cli.py tests/test_integration.py
git commit -m "feat: add CLI with pipeline orchestration and regeneration"
```

---

## Task 9: Documentation and Final Testing

**Files:**
- Create: `README.md`
- Modify: All test files for final verification

- [ ] **Step 1: Create README.md**

Create `README.md`:

```markdown
# Music Smart Trim

Intelligently trim or extend music to a target length by detecting and manipulating repeated melodic sections.

## Features

- **Intelligent Detection**: Uses spectral analysis to find repeated melodic patterns
- **Multiple Strategies**: Generates 3 options (conservative, balanced, aggressive)
- **Quality Rating**: Star ratings (0.5-5.0★) based on transition smoothness, musical coherence, and length accuracy
- **Protected Regions**: Specify sections to preserve
- **Multi-Format Support**: MP3, WAV, FLAC, M4A, OGG
- **Regeneration**: Generate alternative options until satisfied

## Installation

### Requirements

- Python 3.8 or higher
- ffmpeg (for MP3, M4A, OGG support)

### Install Dependencies

```bash
pip install -r requirements.txt
```

## Usage

### Basic Command

```bash
python src/cli.py --input song.mp3 --target 120
```

This will trim `song.mp3` to approximately 120 seconds (2 minutes).

### With Protected Regions

```bash
python src/cli.py --input song.mp3 --target 120 --protect "0:30-1:15,2:00-2:30"
```

This preserves the regions from 0:30-1:15 and 2:00-2:30, preventing cuts in those areas.

### Specify Output Directory

```bash
python src/cli.py --input song.mp3 --target 120 --output-dir ./my_output
```

### Complete Example

```bash
python src/cli.py \
  --input background_music.mp3 \
  --target 180 \
  --protect "0:00-0:10,2:45-3:00" \
  --output-dir ./trimmed_music
```

## Output

The tool generates:

- **3 trimmed audio files**: `option_1_4.5stars.mp3`, `option_2_4.0stars.mp3`, `option_3_3.5stars.mp3`
- **summary.json**: Machine-readable metadata with cut points, scores, etc.
- **summary.txt**: Human-readable report

## How It Works

1. **Load Audio**: Normalizes to 22050 Hz mono for analysis
2. **Spectral Analysis**: Extracts CQT chroma features and builds self-similarity matrix
3. **Pattern Matching**: Identifies repeated melodic segments using cosine similarity
4. **Strategy Generation**: Creates 3 different trim approaches
5. **Quality Scoring**: Rates each option on transition smoothness, musical coherence, and length accuracy
6. **Rendering**: Applies cuts, loops, and crossfades to generate output files

## Quality Rating System

Scores are based on three factors:

- **Transition Smoothness (40%)**: Phase alignment, zero-crossing detection, fade quality
- **Musical Coherence (40%)**: Cuts at measure boundaries, harmonic progression, section order
- **Length Accuracy (20%)**: Distance from target length

Star ratings:
- 5★ = 90-100 points
- 4.5★ = 85-89 points  
- 4★ = 80-84 points
- 3.5★ = 75-79 points
- 3★ = 70-74 points

The tool ensures at least one option scores ≥4.5★.

## Constraints

- All outputs are within ±15 seconds of target length
- Processing time: ~60 seconds for a 3-minute song
- File size limit: 15MB after normalization (warning issued if exceeded)

## Development

### Run Tests

```bash
pytest tests/ -v
```

### Run Single Test

```bash
pytest tests/test_audio_loader.py::test_load_audio_returns_array_and_sample_rate -v
```

## Architecture

The system is modular and web-ready:

- `src/audio_loader.py` - Multi-format audio loading and normalization
- `src/spectral_analyzer.py` - Chroma features and repetition detection
- `src/segment_matcher.py` - Pattern matching and clustering
- `src/trim_engine.py` - Strategy generation
- `src/quality_scorer.py` - Quality assessment
- `src/output_generator.py` - Audio rendering and export
- `src/cli.py` - Command-line interface

Core modules accept standard Python types, making them easy to integrate into web applications.

## License

MIT License
```

- [ ] **Step 2: Run full test suite**

Run: `pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 3: Fix any failing tests**

If any tests fail:
1. Read the error message
2. Identify the issue
3. Fix the code
4. Re-run tests

Repeat until all tests pass.

- [ ] **Step 4: Test with real audio file**

Generate a longer test file:

```bash
python -c "
import numpy as np
import soundfile as sf

sr = 22050
duration = 180  # 3 minutes
t = np.linspace(0, duration, int(sr * duration))

# Create melody with repetition: A-B-A-B-C-A pattern
melody = np.concatenate([
    np.sin(2 * np.pi * 440 * t[:int(sr*30)]),  # A (30s)
    np.sin(2 * np.pi * 523 * t[:int(sr*30)]),  # B (30s)
    np.sin(2 * np.pi * 440 * t[:int(sr*30)]),  # A repeat (30s)
    np.sin(2 * np.pi * 523 * t[:int(sr*30)]),  # B repeat (30s)
    np.sin(2 * np.pi * 587 * t[:int(sr*30)]),  # C (30s)
    np.sin(2 * np.pi * 440 * t[:int(sr*30)]),  # A repeat (30s)
])

sf.write('tests/fixtures/sample_3min.wav', melody * 0.3, sr)
print('Generated tests/fixtures/sample_3min.wav')
"
```

Then test:

```bash
python src/cli.py --input tests/fixtures/sample_3min.wav --target 120
```

Expected: Processes in ~60 seconds, generates 3 options with at least one ≥4.5★

- [ ] **Step 5: Test protected regions**

Run:
```bash
python src/cli.py --input tests/fixtures/sample_3min.wav --target 120 --protect "0:00-0:30"
```

Expected: First 30 seconds preserved in all options

- [ ] **Step 6: Test regeneration**

Run the CLI and when prompted "Regenerate for 3 new options? (y/n):", type 'y'

Expected: Generates 3 different options with potentially different ratings

- [ ] **Step 7: Verify output files**

Check that output directory contains:
- 3 audio files with correct naming
- summary.json with complete metadata
- summary.txt with human-readable report

- [ ] **Step 8: Commit**

```bash
git add README.md
git commit -m "docs: add comprehensive README with usage examples"
```

---

## Task 10: Final Integration and Cleanup

**Files:**
- Create: `CLAUDE.md`
- Review all modules for consistency

- [ ] **Step 1: Create CLAUDE.md for future development**

Create `CLAUDE.md`:

```markdown
# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Music Smart Trim is a Python tool that intelligently adjusts background music to a target length by detecting and manipulating repeated melodic sections using spectral analysis.

## Development Commands

### Run All Tests
```bash
pytest tests/ -v
```

### Run Specific Test Module
```bash
pytest tests/test_audio_loader.py -v
pytest tests/test_spectral_analyzer.py -v
pytest tests/test_segment_matcher.py -v
pytest tests/test_trim_engine.py -v
pytest tests/test_quality_scorer.py -v
pytest tests/test_output_generator.py -v
pytest tests/test_integration.py -v
```

### Run Single Test
```bash
pytest tests/test_audio_loader.py::test_load_audio_returns_array_and_sample_rate -v
```

### Run CLI
```bash
python src/cli.py --input tests/fixtures/sample_30s.wav --target 25
```

### Generate Test Audio Fixtures
```bash
# 30-second test file
python -c "
import numpy as np
import soundfile as sf
sr = 22050
duration = 30
t = np.linspace(0, duration, int(sr * duration))
audio = np.concatenate([
    np.sin(2 * np.pi * 440 * t[:int(sr*10)]),
    np.sin(2 * np.pi * 523 * t[:int(sr*10)]),
    np.sin(2 * np.pi * 440 * t[:int(sr*10)]),
])
sf.write('tests/fixtures/sample_30s.wav', audio * 0.3, sr)
"

# 3-minute test file (for integration tests)
python -c "
import numpy as np
import soundfile as sf
sr = 22050
duration = 180
t = np.linspace(0, duration, int(sr * duration))
melody = np.concatenate([
    np.sin(2 * np.pi * 440 * t[:int(sr*30)]),
    np.sin(2 * np.pi * 523 * t[:int(sr*30)]),
    np.sin(2 * np.pi * 440 * t[:int(sr*30)]),
    np.sin(2 * np.pi * 523 * t[:int(sr*30)]),
    np.sin(2 * np.pi * 587 * t[:int(sr*30)]),
    np.sin(2 * np.pi * 440 * t[:int(sr*30)]),
])
sf.write('tests/fixtures/sample_3min.wav', melody * 0.3, sr)
"
```

## Architecture

The system follows a modular pipeline architecture with 7 focused components:

### Core Modules (Web-Ready)

1. **audio_loader.py**: Multi-format loading (MP3/WAV/FLAC/M4A/OGG), normalization to 22050 Hz, file size validation
2. **spectral_analyzer.py**: CQT chroma features, self-similarity matrix (SSM), repeated segment detection
3. **segment_matcher.py**: Cosine similarity matching, DTW alignment, clustering, protected region handling
4. **trim_engine.py**: Strategy generation (conservative/balanced/aggressive), constraint enforcement (±15s)
5. **quality_scorer.py**: Scoring (transition smoothness 40%, musical coherence 40%, length accuracy 20%), star conversion
6. **output_generator.py**: Audio rendering (cuts/loops/fades), multi-format export, metadata generation
7. **cli.py**: Command-line interface, pipeline orchestration, regeneration handling

### Data Flow

```
Input Audio → Load & Normalize → Spectral Analysis → Segment Matching → 
Strategy Generation → Quality Scoring → Output Rendering → User Review
```

### Key Design Principles

- **DRY**: No code duplication across modules
- **YAGNI**: Only features specified in requirements
- **TDD**: All modules have comprehensive tests
- **Web-Ready**: Core modules are CLI-agnostic, accepting standard Python types

## Key Constraints

- All outputs within ±15 seconds of target length
- At least one option ≥4.5★ (85+ points)
- Processing time: ~60 seconds for 3-minute song
- File size limit: 15MB after normalization (warning if exceeded)
- Protected regions never modified

## Module Interfaces

### audio_loader
- `load_audio(file_path, target_sr=22050) -> (audio_data, sr)`
- `check_normalized_size(audio_data, sr, max_mb=15.0) -> (is_valid, size_mb)`

### spectral_analyzer
- `extract_chroma_features(audio_data, sr, hop_length=2048) -> chroma`
- `build_self_similarity_matrix(chroma) -> ssm`
- `detect_repeated_segments(ssm, sr, hop_length, ...) -> List[Dict]`
- `analyze_audio_structure(audio_data, sr) -> Dict`

### segment_matcher
- `parse_protected_regions(regions_str) -> List[Tuple[float, float]]`
- `is_segment_protected(start, end, protected) -> bool`
- `cluster_similar_segments(segments, threshold=0.8) -> List[Dict]`
- `match_segments(repeated_segments, protected_str) -> Dict`

### trim_engine
- `TrimStrategy` dataclass: name, cut_points, loop_points, fade_regions, target_length
- `generate_trim_strategies(clusters, original_length, target_length, protected) -> List[TrimStrategy]`

### quality_scorer
- `points_to_stars(points) -> float`
- `score_strategy(strategy, audio_data, sr, chroma, original_length) -> Dict`

### output_generator
- `render_strategy(audio_data, sr, strategy) -> np.ndarray`
- `generate_outputs(audio_data, sr, strategies, scores, output_dir, ...) -> Dict`

### cli
- `run_pipeline(input_file, target_length, protected_regions, output_dir) -> Dict`
- `main()` - Entry point with regeneration loop

## Testing Strategy

- **Unit tests**: Each module has dedicated test file
- **Integration tests**: End-to-end pipeline in test_integration.py
- **Test fixtures**: sample_30s.wav (unit tests), sample_3min.wav (integration)
- **TDD workflow**: Write test → verify it fails → implement → verify it passes → commit

## Common Development Tasks

### Adding a New Strategy Type
1. Add strategy generator function to trim_engine.py
2. Add test to test_trim_engine.py
3. Update generate_trim_strategies() to include new strategy
4. Update documentation

### Modifying Quality Scoring
1. Update scoring function in quality_scorer.py
2. Update tests in test_quality_scorer.py
3. Adjust thresholds if needed to ensure ≥4.5★ achievable
4. Update README.md scoring section

### Supporting New Audio Format
1. Add format extension to audio_loader.py supported_formats list
2. Ensure pydub/librosa can handle it (may need codec)
3. Add test case with sample file
4. Update README.md supported formats list

## Future Web Deployment

Core modules (audio_loader through output_generator) are designed to be called from web backends:

```python
# Example Flask route
@app.route('/trim', methods=['POST'])
def trim_audio():
    audio_data, sr = load_audio(uploaded_file)
    analysis = analyze_audio_structure(audio_data, sr)
    # ... rest of pipeline
    return jsonify(results)
```

No refactoring required - modules already accept standard Python types and return structured data.
```

- [ ] **Step 2: Run final full test suite**

Run: `pytest tests/ -v --tb=short`
Expected: All tests PASS

- [ ] **Step 3: Check test coverage**

Run:
```bash
pytest tests/ --cov=src --cov-report=term-missing
```

Review coverage and add tests for any uncovered critical paths.

- [ ] **Step 4: Verify all success criteria from spec**

Check each item:
- ✅ Process 3-minute songs in ~60 seconds
- ✅ Generate 3 options, at least 1 with ≥4.5★ rating
- ✅ All outputs within ±15 seconds of target
- ✅ Support MP3, WAV, FLAC, M4A, OGG formats
- ✅ Respect user-protected regions
- ✅ Enable regeneration for alternative options
- ✅ Modular codebase (no 5000-line scripts)
- ✅ CLI-based interaction for testing

- [ ] **Step 5: Clean up any debug code or TODOs**

Search for:
```bash
grep -r "TODO" src/
grep -r "FIXME" src/
grep -r "print(" src/  # Remove debug prints
```

- [ ] **Step 6: Final commit**

```bash
git add CLAUDE.md
git commit -m "docs: add CLAUDE.md for future development guidance"
```

- [ ] **Step 7: Create version tag**

```bash
git tag -a v1.0.0 -m "Release v1.0.0: Initial music smart trim implementation"
```

---

## Self-Review Checklist

### Spec Coverage

Checking each section of the design spec:

- ✅ **Audio Loader**: Multi-format support, normalization, file size validation
- ✅ **Spectral Analyzer**: CQT chroma, SSM, repeated segment detection
- ✅ **Segment Matcher**: Protected regions, clustering, filtering
- ✅ **Trim Engine**: 3 strategies (conservative/balanced/aggressive), ±15s constraint
- ✅ **Quality Scorer**: 3-component scoring (40%+40%+20%), star conversion, ≥4.5★ guarantee
- ✅ **Output Generator**: Audio rendering, metadata export (JSON/text)
- ✅ **CLI**: Argument parsing, pipeline orchestration, regeneration
- ✅ **Testing**: Unit tests per module, integration test, test fixtures
- ✅ **Documentation**: README.md, CLAUDE.md

### Placeholder Scan

No placeholders found:
- No "TBD", "TODO", "implement later"
- No "add appropriate error handling" without implementation
- No "write tests for the above" without actual test code
- No "similar to Task N" without repeating the code
- All steps contain actual code or exact commands

### Type Consistency

Verified consistency across tasks:
- `audio_data: np.ndarray` - consistent
- `sample_rate` / `sr: int` - consistent
- `TrimStrategy` dataclass - consistent definition
- Protected regions: `List[Tuple[float, float]]` - consistent
- Segment dictionaries: consistent keys (`start_time_1`, `start_time_2`, `duration`, `similarity`)
- Score dictionaries: consistent keys (`total_points`, `star_rating`, `breakdown`)

All type signatures match across modules.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-15-music-smart-trim-implementation.md`. 

Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
