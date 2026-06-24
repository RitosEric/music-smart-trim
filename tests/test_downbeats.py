"""Tests for madmom-first downbeat detection with librosa fallback.

madmom 0.16.x cannot load on Python 3.12, so the production path here is the
fallback. These tests pin both the integration wiring (madmom result preferred
when present, librosa grouping otherwise) and the graceful-failure contract
(the madmom helper never raises — it returns None on any problem).
"""
import numpy as np

from src import structure_analyzer
from src.structure_analyzer import detect_beats_and_bars, _downbeats_via_madmom


def _click_track(bpm=120, dur=8.0, sr=22050):
    """A simple click track librosa can beat-track to a known tempo."""
    period = 60.0 / bpm
    audio = np.zeros(int(dur * sr), dtype=np.float32)
    for t in np.arange(0.0, dur, period):
        i = int(t * sr)
        audio[i:i + 200] = 1.0
    return audio, sr


def test_madmom_helper_never_raises_and_returns_none_or_array():
    """The graceful-failure contract: import/runtime errors degrade to None."""
    audio, sr = _click_track()
    result = _downbeats_via_madmom(audio, sr)
    assert result is None or isinstance(result, np.ndarray)


def test_detect_prefers_madmom_when_available(monkeypatch):
    audio, sr = _click_track()
    fake = np.array([1.0, 2.0, 3.0])
    monkeypatch.setattr(structure_analyzer, '_downbeats_via_madmom', lambda a, s: fake)
    info = detect_beats_and_bars(audio, sr)
    assert np.array_equal(info['downbeats'], fake)


def test_detect_falls_back_to_librosa_grouping(monkeypatch):
    audio, sr = _click_track()
    monkeypatch.setattr(structure_analyzer, '_downbeats_via_madmom', lambda a, s: None)
    info = detect_beats_and_bars(audio, sr)
    beats = set(np.round(info['beats'], 3))
    downbeats = info['downbeats']
    # Fallback downbeats are a subset of detected beats (every Nth beat).
    assert len(downbeats) > 0
    assert set(np.round(downbeats, 3)).issubset(beats)
