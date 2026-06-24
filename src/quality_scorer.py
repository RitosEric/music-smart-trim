"""Unified quality scorer for trim and extend edits.

The previous scorer used two different rubrics — one for trims (musical
coherence + transition smoothness + length) and another for extends (loop
naturalness + loop transitions + length) — with different component scales and
rescale factors. A 4-star trim and a 4-star extend therefore did not mean the
same thing, and the rescale arithmetic was fragile.

This rewrite scores every edit, trim or extend, on one 100-point rubric built
from the signals the music-structure-analysis literature finds most predictive
of a clean splice:

    beat alignment      30   do the edit boundaries land on downbeats?
    harmonic continuity 25   does the chroma match across each join?
    structural position 20   do the boundaries sit on section edges?
    energy continuity   15   is there a loudness jump across a join?
    length accuracy     10   how close to the requested duration?
                       ----
                        100

The 100-point base is then multiplied by a cut-count penalty so a clean
single splice always outranks a fragmented multi-cut edit of equal raw score.
The total maps linearly to a 0-5 star rating (20 points per star).

A "join" is the seam an edit creates: for a trim it is the moment the audio
before the cut meets the audio after it; for an extend it is the loop wrap
(end of a repeated section meeting its own start). Both are evaluated on the
original audio, where the two sides of every seam still exist.
"""
import numpy as np
from typing import Dict, List, Optional, Sequence, Tuple

# Component weights — must sum to 100.
W_BEAT = 30.0
W_HARMONIC = 25.0
W_STRUCTURE = 20.0
W_ENERGY = 15.0
W_LENGTH = 10.0

# Tolerances / windows.
BEAT_TOLERANCE = 0.07      # 70 ms — a boundary this close to a downbeat counts as aligned
STRUCT_TOLERANCE = 1.0     # 1 s — a boundary this close to a section edge counts as on-structure
CONTINUITY_WINDOW = 0.5    # seconds analysed on each side of a join

_EPS = 1e-8


def score_length_accuracy(target_length: float, resulting_length: float) -> float:
    """Length closeness, 0..10.

    Anything within 5% of target is treated as on-target (full marks) — the
    design deliberately values a clean edit over the last few seconds. Beyond
    25% off scores zero; in between it falls off linearly.
    """
    if target_length <= 0:
        return W_LENGTH
    rel = abs(resulting_length - target_length) / target_length
    if rel <= 0.05:
        return W_LENGTH
    if rel >= 0.25:
        return 0.0
    return W_LENGTH * (0.25 - rel) / (0.25 - 0.05)


def cut_count_multiplier(n_edits: int) -> float:
    """Anti-fragmentation penalty applied to the 100-point base.

    One clean splice is unpenalized; every additional cut/loop costs more,
    because scattered micro-edits read as sloppy no matter how each individual
    seam scores.
    """
    return {0: 1.0, 1: 1.0, 2: 0.85, 3: 0.65}.get(n_edits, 0.40)


def score_beat_alignment(
    boundary_times: Sequence[float],
    downbeats: Optional[Sequence[float]],
    tolerance: float = BEAT_TOLERANCE,
) -> float:
    """Fraction of edit boundaries that land on a downbeat, scaled to 0..30.

    No boundaries → nothing to misalign, full marks. No downbeat data →
    neutral midpoint (we can neither reward nor punish).
    """
    if len(boundary_times) == 0:
        return W_BEAT
    if downbeats is None or len(downbeats) == 0:
        return W_BEAT * 0.5
    db = np.asarray(list(downbeats), dtype=float)
    aligned = sum(1 for t in boundary_times if np.min(np.abs(db - t)) <= tolerance)
    return W_BEAT * (aligned / len(boundary_times))


def score_structural_position(
    boundary_times: Sequence[float],
    sections: Optional[List[Dict]],
    tolerance: float = STRUCT_TOLERANCE,
) -> float:
    """Fraction of boundaries sitting on a section edge, scaled to 0..20.

    Rewards edits that happen at structural seams (intro/verse/chorus edges)
    rather than mid-phrase. No boundaries → full; no section data → neutral.
    """
    if len(boundary_times) == 0:
        return W_STRUCTURE
    if not sections:
        return W_STRUCTURE * 0.5
    edges = np.asarray(
        [edge for s in sections for edge in (s['start'], s['end'])], dtype=float
    )
    on_edge = sum(1 for t in boundary_times if np.min(np.abs(edges - t)) <= tolerance)
    return W_STRUCTURE * (on_edge / len(boundary_times))


def score_harmonic_continuity(
    audio: np.ndarray,
    sr: int,
    joins: List[Tuple[float, float]],
    window_sec: float = CONTINUITY_WINDOW,
) -> float:
    """Mean chroma similarity across each join, scaled to 0..25.

    For each (left_time, right_time) seam we compare the average chroma of the
    window ending at ``left_time`` with the window starting at ``right_time``.
    High cosine similarity means the harmonic context is the same on both sides
    — the dominant perceptual cue that a splice "sounds like the same song".
    """
    if not joins:
        return W_HARMONIC
    import librosa

    sims = []
    for left_t, right_t in joins:
        left = _slice(audio, sr, left_t - window_sec, left_t)
        right = _slice(audio, sr, right_t, right_t + window_sec)
        if len(left) < sr // 20 or len(right) < sr // 20:  # need ~50ms to mean anything
            continue
        cl = librosa.feature.chroma_cqt(y=np.asarray(left, dtype=float), sr=sr).mean(axis=1)
        cr = librosa.feature.chroma_cqt(y=np.asarray(right, dtype=float), sr=sr).mean(axis=1)
        sims.append(max(0.0, _cosine(cl, cr)))
    if not sims:
        return W_HARMONIC
    return W_HARMONIC * float(np.mean(sims))


def score_energy_continuity(
    audio: np.ndarray,
    sr: int,
    joins: List[Tuple[float, float]],
    window_sec: float = CONTINUITY_WINDOW,
) -> float:
    """Penalty for loudness jumps across each join, scaled to 0..15.

    A seam with a <=3 dB RMS jump is inaudible (full marks); the score falls
    linearly to zero by 9 dB. Continuous silence on both sides counts as
    seamless; silence meeting sound does not.
    """
    if not joins:
        return W_ENERGY
    fractions = []
    for left_t, right_t in joins:
        left = _slice(audio, sr, left_t - window_sec, left_t)
        right = _slice(audio, sr, right_t, right_t + window_sec)
        rms_l = _rms(left)
        rms_r = _rms(right)
        if rms_l < _EPS and rms_r < _EPS:
            fractions.append(1.0)        # silence → silence, seamless
        elif rms_l < _EPS or rms_r < _EPS:
            fractions.append(0.0)        # silence meets sound, jarring
        else:
            delta_db = abs(20.0 * np.log10(rms_r / rms_l))
            fractions.append(_db_jump_to_fraction(delta_db))
    return W_ENERGY * float(np.mean(fractions)) if fractions else W_ENERGY


def points_to_stars(points: float) -> float:
    """Map a 0-100 point total to a 0.0-5.0 star rating (0.1 increments)."""
    points = max(0.0, min(100.0, points))
    return round(points / 20.0, 1)


def score_strategy(
    strategy,
    original_audio: np.ndarray,
    sr: int,
    original_length: float,
    rendered_audio: Optional[np.ndarray] = None,
    downbeats: Optional[Sequence[float]] = None,
    sections: Optional[List[Dict]] = None,
) -> Dict:
    """Score a trim or extend strategy on the unified 100-point rubric.

    The same five components and the same cut-count penalty apply to both
    directions, so star ratings are directly comparable across trim and extend.

    ``downbeats`` and ``sections`` come from the structure analysis; when a
    caller cannot supply them the relevant components fall back to neutral
    scoring rather than failing.

    Returns a dict with ``total_points``, ``star_rating``, ``breakdown`` (the
    five component scores plus the applied multiplier) and ``resulting_length``.
    """
    if rendered_audio is not None:
        resulting_length = len(rendered_audio) / sr
    else:
        resulting_length = strategy.calculate_resulting_length(original_length)

    is_extension = len(strategy.loop_points) > 0 and len(strategy.cut_points) == 0

    boundary_times: List[float] = []
    joins: List[Tuple[float, float]] = []
    if is_extension:
        for ls, le, _count in strategy.loop_points:
            boundary_times.extend([ls, le])
            joins.append((le, ls))   # loop wrap: section end meets its own start
        n_edits = len(strategy.loop_points)
    else:
        for cs, ce in strategy.cut_points:
            boundary_times.extend([cs, ce])
            joins.append((cs, ce))   # cut seam: audio before meets audio after
        n_edits = len(strategy.cut_points)

    beat = score_beat_alignment(boundary_times, downbeats)
    harmonic = score_harmonic_continuity(original_audio, sr, joins)
    structure = score_structural_position(boundary_times, sections)
    energy = score_energy_continuity(original_audio, sr, joins)
    length = score_length_accuracy(strategy.target_length, resulting_length)

    base = beat + harmonic + structure + energy + length
    multiplier = cut_count_multiplier(n_edits)
    total_points = base * multiplier
    star_rating = points_to_stars(total_points)

    return {
        'total_points': total_points,
        'star_rating': star_rating,
        'breakdown': {
            'beat_alignment': beat,
            'harmonic_continuity': harmonic,
            'structural_position': structure,
            'energy_continuity': energy,
            'length_accuracy': length,
            'cut_count_multiplier': multiplier,
        },
        'resulting_length': resulting_length,
    }


# --- internal helpers -------------------------------------------------------

def _slice(audio: np.ndarray, sr: int, t0: float, t1: float) -> np.ndarray:
    """Sample slice for the time window [t0, t1], clamped to the audio bounds."""
    i0 = max(0, int(t0 * sr))
    i1 = min(len(audio), int(t1 * sr))
    if i1 <= i0:
        return np.zeros(0, dtype=float)
    return audio[i0:i1]


def _rms(samples: np.ndarray) -> float:
    if len(samples) == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(np.asarray(samples, dtype=float)))))


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    na = np.linalg.norm(a)
    nb = np.linalg.norm(b)
    if na < _EPS or nb < _EPS:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def _db_jump_to_fraction(delta_db: float) -> float:
    """Map an RMS jump in dB to a 0..1 quality fraction (<=3 dB best, >=9 dB worst)."""
    if delta_db <= 3.0:
        return 1.0
    if delta_db >= 9.0:
        return 0.0
    return (9.0 - delta_db) / (9.0 - 3.0)
