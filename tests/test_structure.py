"""Tests for structure boundary coverage.

The planner removes/repeats whole sections, so the section list MUST tile the
entire song with no gaps. A regression here (boundaries that stop before the
end) silently hides the song's tail from every trim/extend decision.
"""
import numpy as np
import librosa
import pytest

from src.structure_analyzer import detect_structure_boundaries, analyze_structure


def _click(dur=80.0, sr=22050, bpm=120):
    period = 60.0 / bpm
    audio = np.zeros(int(dur * sr), dtype=np.float32)
    # Vary amplitude across the song so the segmenter finds interior boundaries.
    for n in range(int(dur / period)):
        i = int(n * period * sr)
        amp = 0.3 + 0.5 * ((n // 16) % 2)  # blocks of contrasting energy
        audio[i:i + 300] = amp
    return audio, sr


def test_boundaries_span_zero_to_duration():
    audio, sr = _click()
    duration = len(audio) / sr
    b = detect_structure_boundaries(audio, sr)
    assert b[0] == pytest.approx(0.0, abs=0.06)
    assert b[-1] == pytest.approx(duration, abs=0.06)


def test_sections_tile_full_song_without_gaps():
    audio, sr = _click()
    duration = len(audio) / sr
    chroma = librosa.feature.chroma_cqt(y=audio, sr=sr)
    sections = analyze_structure(audio, sr, chroma)['sections']
    assert sections[0]['start'] == pytest.approx(0.0, abs=0.06)
    assert sections[-1]['end'] == pytest.approx(duration, abs=0.06)
    for prev, nxt in zip(sections, sections[1:]):
        assert nxt['start'] == pytest.approx(prev['end'], abs=0.06)
