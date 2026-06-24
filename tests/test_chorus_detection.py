"""Tests for chorus-detection improvements in structure_analyzer.

The old detector normalized a raw repeated-segment overlap count by an
arbitrary //100, which collapsed to noise on real songs (tens of thousands of
raw overlaps). The replacement counts, per section, how many *other* sections
share its harmonic content (chroma cosine similarity) — the direct signal that
a section is a repeat, which is what makes a chorus a chorus.
"""
import numpy as np
import librosa

from src.structure_analyzer import count_section_repetitions, label_sections


def test_counts_identical_sections_as_repetitions():
    a = np.zeros(12); a[0] = 1.0
    b = np.zeros(12); b[1] = 1.0
    counts = count_section_repetitions([a, a, a, b], similarity_threshold=0.9)
    assert counts == [2, 2, 2, 0]   # each 'a' matches the other two; 'b' matches none


def test_counts_zero_when_all_sections_distinct():
    vecs = [np.eye(12)[i] for i in range(4)]   # orthogonal pitch classes
    assert count_section_repetitions(vecs, similarity_threshold=0.9) == [0, 0, 0, 0]


def test_threshold_controls_match_sensitivity():
    a = np.array([1.0, 0.5] + [0.0] * 10)
    b = np.array([1.0, 0.4] + [0.0] * 10)   # cosine ~0.997
    assert count_section_repetitions([a, b], similarity_threshold=0.999) == [0, 0]
    assert count_section_repetitions([a, b], similarity_threshold=0.9) == [1, 1]


def test_label_sections_tags_repeated_high_energy_section_as_chorus():
    """A mid-song section that repeats (same chroma) and is loud should be a
    chorus, even outside the old rigid 12-30s duration window."""
    sr = 22050
    duration = 100.0
    # 6 sections; #1 and #3 are the chorus (identical chroma, loud), #2/#4 verse.
    boundaries = np.array([0.0, 10.0, 30.0, 50.0, 70.0, 90.0, 100.0])

    # Build chroma on librosa's frame grid (default hop 512) so it indexes the
    # same way label_sections reads it via librosa.time_to_frames.
    n_frames = int(librosa.time_to_frames(duration, sr=sr)) + 1
    chroma = np.zeros((12, n_frames), dtype=float)
    frame_time = librosa.frames_to_time(np.arange(n_frames), sr=sr)

    def fill(t0, t1, vec):
        mask = (frame_time >= t0) & (frame_time < t1)
        chroma[:, mask] = np.asarray(vec)[:, None]

    chorus_vec = np.zeros(12); chorus_vec[[0, 4, 7]] = 1.0      # a triad
    verse_a = np.zeros(12); verse_a[[2, 5, 9]] = 1.0
    verse_b = np.zeros(12); verse_b[[1, 3, 8]] = 1.0
    intro_vec = np.zeros(12); intro_vec[[11]] = 1.0
    fill(0, 10, intro_vec)
    fill(10, 30, chorus_vec)     # section 1 — chorus
    fill(30, 50, verse_a)        # section 2 — verse
    fill(50, 70, chorus_vec)     # section 3 — chorus (repeat of #1)
    fill(70, 90, verse_b)        # section 4 — verse
    fill(90, 100, intro_vec)     # section 5 — outro-ish

    # Audio: louder under the chorus sections so they read as high energy.
    audio = np.zeros(int(duration * sr), dtype=np.float32)
    for (t0, t1, amp) in [(10, 30, 0.6), (50, 70, 0.6), (30, 50, 0.2), (70, 90, 0.2)]:
        audio[int(t0 * sr):int(t1 * sr)] = amp

    sections = label_sections(audio, sr, boundaries, chroma)
    labels = [s['label'] for s in sections]
    # Sections index 1 and 3 (10-30, 50-70) should be choruses.
    assert sections[1]['label'] == 'chorus'
    assert sections[3]['label'] == 'chorus'
