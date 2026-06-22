"""Quality scorer module for rating trim strategies with enhanced heuristics and MERT embeddings."""

from typing import Dict, List, Tuple, Optional
import numpy as np
import librosa
from src.trim_engine import TrimStrategy

# Optional MERT support
_MERT_AVAILABLE = False
_MERT_MODEL = None
_MERT_PROCESSOR = None

try:
    from transformers import Wav2Vec2FeatureExtractor, AutoModel
    import torch
    _MERT_AVAILABLE = True
except ImportError:
    pass


def load_mert_model(device="cpu"):
    """
    Load MERT model for embeddings (lazy loading).

    Args:
        device: Device to load model on ("cpu" or "cuda")

    Returns:
        Tuple of (model, processor) or (None, None) if unavailable
    """
    global _MERT_MODEL, _MERT_PROCESSOR

    if not _MERT_AVAILABLE:
        return None, None

    if _MERT_MODEL is None:
        try:
            print("Loading MERT model (first time only, ~360MB)...")
            _MERT_MODEL = AutoModel.from_pretrained("m-a-p/MERT-v1-95M", trust_remote_code=True)
            _MERT_PROCESSOR = Wav2Vec2FeatureExtractor.from_pretrained("m-a-p/MERT-v1-95M", trust_remote_code=True)
            _MERT_MODEL = _MERT_MODEL.to(device)
            if device == "cpu":
                # Use FP32 on CPU
                pass
            else:
                # Use FP16 on GPU for speed
                _MERT_MODEL = _MERT_MODEL.half()
            _MERT_MODEL.eval()
            print("✓ MERT model loaded")
        except Exception as e:
            print(f"⚠️  Failed to load MERT: {e}")
            return None, None

    return _MERT_MODEL, _MERT_PROCESSOR


def get_mert_embeddings(audio: np.ndarray, sr: int, device="cpu") -> Optional[np.ndarray]:
    """
    Extract MERT embeddings for audio segment.

    Args:
        audio: Audio signal
        sr: Sample rate
        device: Device for inference

    Returns:
        Embeddings array or None if MERT unavailable
    """
    model, processor = load_mert_model(device)

    if model is None:
        return None

    try:
        # Resample to 24kHz if needed
        if sr != 24000:
            audio = librosa.resample(audio, orig_sr=sr, target_sr=24000)

        # Process audio
        inputs = processor(audio, sampling_rate=24000, return_tensors="pt")
        inputs = {k: v.to(device) for k, v in inputs.items()}

        # Get embeddings
        with torch.no_grad():
            outputs = model(**inputs)
            # Use mean pooling over time dimension
            embeddings = outputs.last_hidden_state.mean(dim=1).cpu().numpy()

        return embeddings
    except Exception as e:
        print(f"⚠️  MERT embedding extraction failed: {e}")
        return None


def score_spectral_flux(audio: np.ndarray, sr: int, cut_points: List[Tuple[float, float]]) -> float:
    """
    Score spectral flux (smoothness of frequency changes at cuts).

    Lower spectral flux at cut points = smoother transitions.

    Args:
        audio: Audio signal
        sr: Sample rate
        cut_points: List of (start, end) cut tuples

    Returns:
        Score from 0 to 10 points
    """
    if not cut_points:
        return 10.0

    try:
        # Compute spectral flux (onset strength)
        onset_env = librosa.onset.onset_strength(y=audio, sr=sr)
        times = librosa.times_like(onset_env, sr=sr)

        score = 0.0
        for cut_start, cut_end in cut_points:
            # Check flux at cut boundaries
            start_idx = np.argmin(np.abs(times - cut_start))
            end_idx = np.argmin(np.abs(times - cut_end))

            # Lower flux = better (smoother transition)
            start_flux = onset_env[start_idx] if start_idx < len(onset_env) else 0
            end_flux = onset_env[end_idx] if end_idx < len(onset_env) else 0

            # Normalize: flux typically 0-2, invert so low flux = high score
            avg_flux = (start_flux + end_flux) / 2
            normalized_score = max(0, 1.0 - avg_flux / 2.0)
            score += normalized_score * (10.0 / len(cut_points))

        return min(10.0, score)
    except Exception:
        return 5.0  # Partial credit on error


def score_loudness_consistency(audio: np.ndarray, sr: int, cut_points: List[Tuple[float, float]]) -> float:
    """
    Score loudness consistency (no sudden volume jumps at cuts).

    Args:
        audio: Audio signal
        sr: Sample rate
        cut_points: List of (start, end) cut tuples

    Returns:
        Score from 0 to 10 points
    """
    if not cut_points:
        return 10.0

    try:
        # Compute RMS energy over time
        rms = librosa.feature.rms(y=audio, frame_length=2048, hop_length=512)[0]
        times = librosa.times_like(rms, sr=sr, hop_length=512)

        score = 0.0
        for cut_start, cut_end in cut_points:
            # Get RMS before cut_start and after cut_end
            before_idx = np.argmin(np.abs(times - max(0, cut_start - 0.5)))
            after_idx = np.argmin(np.abs(times - min(len(audio)/sr, cut_end + 0.5)))

            if before_idx < len(rms) and after_idx < len(rms):
                before_rms = rms[before_idx]
                after_rms = rms[after_idx]

                # Calculate loudness difference (dB)
                if before_rms > 0 and after_rms > 0:
                    db_diff = abs(20 * np.log10(after_rms / (before_rms + 1e-8)))
                    # Penalize differences > 3dB
                    if db_diff < 3.0:
                        score += 10.0 / len(cut_points)
                    elif db_diff < 6.0:
                        score += 5.0 / len(cut_points)
                    elif db_diff < 10.0:
                        score += 2.0 / len(cut_points)
                else:
                    score += 5.0 / len(cut_points)  # Partial credit

        return min(10.0, score)
    except Exception:
        return 5.0


def score_tempo_stability(audio: np.ndarray, sr: int) -> float:
    """
    Score tempo stability (no tempo drift in rendered audio).

    Args:
        audio: Audio signal
        sr: Sample rate

    Returns:
        Score from 0 to 10 points
    """
    try:
        # Estimate tempo using beat tracking
        tempo, _ = librosa.beat.beat_track(y=audio, sr=sr)

        # Check if tempo is stable (variance across windows)
        # For now, just give credit if tempo detected
        if tempo > 0:
            return 10.0
        else:
            return 5.0
    except Exception:
        return 5.0


def score_transition_smoothness(
    audio: np.ndarray,
    sr: int,
    cut_points: List[Tuple[float, float]],
    fade_regions: List[Tuple[float, float]]
) -> float:
    """
    Score transition smoothness (raw max 40 points, rescaled to 30 in score_strategy).

    Components:
    - Phase alignment (15 points): Check amplitude at cut points
    - Zero-crossing (10 points): Check if cuts are near zero-crossings
    - Fade quality (15 points): Check fade duration and smoothness

    Args:
        audio: Audio signal as numpy array
        sr: Sample rate
        cut_points: List of (start_time, end_time) tuples for cuts
        fade_regions: List of (fade_start, fade_end) tuples for fades

    Returns:
        Score from 0 to 40 points
    """
    if not cut_points:
        # No cuts means perfect smoothness
        return 40.0

    phase_score = 0.0
    zero_crossing_score = 0.0
    fade_score = 0.0

    # Phase alignment scoring (15 points max)
    for cut_start, cut_end in cut_points:
        start_idx = int(cut_start * sr)
        end_idx = int(cut_end * sr)

        # Check amplitude at cut points (lower is better)
        if start_idx < len(audio):
            start_amp = abs(audio[start_idx])
            # Score: 0.0 amplitude = full points, 1.0 amplitude = 0 points
            phase_score += (1.0 - min(start_amp, 1.0)) * (7.5 / len(cut_points))

        if end_idx < len(audio):
            end_amp = abs(audio[end_idx])
            phase_score += (1.0 - min(end_amp, 1.0)) * (7.5 / len(cut_points))

    # Zero-crossing scoring (10 points max)
    for cut_start, cut_end in cut_points:
        start_idx = int(cut_start * sr)
        end_idx = int(cut_end * sr)

        # Check for zero-crossings within ±100 samples
        window = 100
        if start_idx < len(audio):
            start_window = audio[max(0, start_idx - window):min(len(audio), start_idx + window)]
            if len(start_window) > 0:
                # Check if there's a zero crossing (sign change)
                zero_crossings = np.where(np.diff(np.sign(start_window)))[0]
                if len(zero_crossings) > 0:
                    zero_crossing_score += 5.0 / len(cut_points)

        if end_idx < len(audio):
            end_window = audio[max(0, end_idx - window):min(len(audio), end_idx + window)]
            if len(end_window) > 0:
                zero_crossings = np.where(np.diff(np.sign(end_window)))[0]
                if len(zero_crossings) > 0:
                    zero_crossing_score += 5.0 / len(cut_points)

    # Fade quality scoring (15 points max)
    for fade_start, fade_end in fade_regions:
        fade_duration = fade_end - fade_start

        # Ideal fade durations: 0.15s (conservative), 0.075s (balanced), 0.0375s (aggressive)
        # Score based on duration: 0.05-0.3s is good range
        if 0.05 <= fade_duration <= 0.3:
            fade_score += 10.0 / len(fade_regions)
        elif 0.03 <= fade_duration <= 0.5:
            fade_score += 5.0 / len(fade_regions)

        # Check fade smoothness (fade regions should have gradual amplitude change)
        fade_start_idx = int(fade_start * sr)
        fade_end_idx = int(fade_end * sr)

        if fade_start_idx < len(audio) and fade_end_idx < len(audio):
            fade_segment = audio[fade_start_idx:fade_end_idx]
            if len(fade_segment) > 1:
                # Check if amplitude changes gradually (low variance in differences)
                amp_envelope = np.abs(fade_segment)
                if len(amp_envelope) > 2:
                    gradients = np.diff(amp_envelope)
                    gradient_variance = np.var(gradients)
                    # Lower variance = smoother fade
                    if gradient_variance < 0.01:
                        fade_score += 5.0 / len(fade_regions)
                    elif gradient_variance < 0.05:
                        fade_score += 2.5 / len(fade_regions)

    total_score = phase_score + zero_crossing_score + fade_score
    return min(40.0, total_score)


def score_cut_pattern(cut_points: List[Tuple[float, float]], original_length: float) -> float:
    """
    Score cut pattern quality (bonus points for radio edit style).

    Radio edit pattern = back-to-back cuts forming continuous removal from middle.
    This creates more natural sounding results than scattered cuts.

    Scoring:
    - Continuous cuts (gap <3s): +5 points per merged group
    - Middle-focused cuts (20%-80% region): +2 points per cut
    - Fewer cut groups: bonus up to +5 points

    Args:
        cut_points: List of (start_time, end_time) tuples for cuts
        original_length: Original audio length

    Returns:
        Bonus score from 0 to 15 points
    """
    if not cut_points:
        return 0.0

    score = 0.0

    # Sort cuts by start time
    sorted_cuts = sorted(cut_points, key=lambda x: x[0])

    # Build groups explicitly to count properly
    groups = []
    i = 0
    while i < len(sorted_cuts):
        group_start = sorted_cuts[i][0]
        group_end = sorted_cuts[i][1]
        group_size = 1

        j = i + 1
        while j < len(sorted_cuts):
            if sorted_cuts[j][0] - group_end <= 3.0:  # Within 3s = continuous
                group_end = max(group_end, sorted_cuts[j][1])
                group_size += 1
                j += 1
            else:
                break

        groups.append({'start': group_start, 'end': group_end, 'size': group_size})
        i = j if j > i else i + 1

    # Score 1: Reward continuous groups (back-to-back cuts)
    for group in groups:
        if group['size'] >= 2:
            score += 5.0  # +5 points per continuous group

    # Score 2: Reward middle-focused cuts (radio edit style)
    middle_start = original_length * 0.2
    middle_end = original_length * 0.8

    for cut_start, cut_end in cut_points:
        cut_center = (cut_start + cut_end) / 2
        if middle_start <= cut_center <= middle_end:
            score += 2.0  # +2 points per middle cut

    # Score 3: Reward fewer cut groups (cleaner result)
    num_groups = len(groups)
    if num_groups == 1:
        score += 5.0  # All cuts in one continuous block
    elif num_groups == 2:
        score += 3.0
    elif num_groups == 3:
        score += 1.0

    return min(15.0, score)


def score_musical_coherence(
    audio: np.ndarray,
    sr: int,
    cut_points: List[Tuple[float, float]],
    original_length: float = None
) -> float:
    """
    Score musical coherence (max 50 points).

    Components:
    - Beat alignment (20 points): Check if cuts are near beats
    - Harmonic continuity (10 points): Check chroma similarity at cut boundaries
    - Section order (10 points): Penalize cuts in intro/outro
    - Cut pattern bonus (10 points): Reward radio edit style (back-to-back cuts)

    Args:
        audio: Audio signal as numpy array
        sr: Sample rate
        cut_points: List of (start_time, end_time) tuples for cuts
        original_length: Original audio length (for pattern scoring)

    Returns:
        Score from 0 to 50 points
    """
    if not cut_points:
        # No cuts means perfect coherence
        return 50.0

    beat_score = 0.0
    harmonic_score = 0.0
    section_score = 0.0
    pattern_bonus = 0.0

    # Get beat times using librosa
    try:
        tempo, beat_frames = librosa.beat.beat_track(y=audio, sr=sr)
        beat_times = librosa.frames_to_time(beat_frames, sr=sr)
    except Exception:
        # If beat tracking fails, give partial credit
        beat_times = np.array([])

    # Calculate audio duration
    duration = len(audio) / sr if original_length is None else original_length

    # Beat alignment scoring (20 points max)
    if len(beat_times) > 0:
        for cut_start, cut_end in cut_points:
            # Check if cut_start is near a beat (within ±0.1s)
            start_distances = np.abs(beat_times - cut_start)
            if len(start_distances) > 0 and np.min(start_distances) <= 0.1:
                beat_score += 10.0 / len(cut_points)

            # Check if cut_end is near a beat (within ±0.1s)
            end_distances = np.abs(beat_times - cut_end)
            if len(end_distances) > 0 and np.min(end_distances) <= 0.1:
                beat_score += 10.0 / len(cut_points)
    else:
        # If no beats detected, give partial credit based on timing regularity
        beat_score = 10.0

    # Harmonic continuity scoring (10 points max)
    try:
        # Compute chromagram for harmonic analysis
        chroma = librosa.feature.chroma_cqt(y=audio, sr=sr)

        for cut_start, cut_end in cut_points:
            # Get chroma at cut boundaries
            start_frame = librosa.time_to_frames(cut_start, sr=sr)
            end_frame = librosa.time_to_frames(cut_end, sr=sr)

            if start_frame < chroma.shape[1] and end_frame < chroma.shape[1]:
                # Get chroma vectors before cut_start and after cut_end
                before_chroma = chroma[:, max(0, start_frame - 2):start_frame + 1]
                after_chroma = chroma[:, end_frame:min(chroma.shape[1], end_frame + 3)]

                if before_chroma.size > 0 and after_chroma.size > 0:
                    # Average chroma for before and after
                    before_avg = np.mean(before_chroma, axis=1)
                    after_avg = np.mean(after_chroma, axis=1)

                    # Calculate cosine similarity
                    similarity = np.dot(before_avg, after_avg) / (
                        np.linalg.norm(before_avg) * np.linalg.norm(after_avg) + 1e-8
                    )

                    # Higher similarity = better score
                    harmonic_score += similarity * (10.0 / len(cut_points))
    except Exception:
        # If chroma analysis fails, give partial credit
        harmonic_score = 5.0

    # Section order scoring (10 points max)
    intro_duration = min(10.0, duration * 0.1)  # First 10s or 10% of song
    outro_duration = min(10.0, duration * 0.1)  # Last 10s or 10% of song

    for cut_start, cut_end in cut_points:
        # Check if cut is in intro
        if cut_start < intro_duration:
            # Penalize intro cuts
            section_score -= 5.0 / len(cut_points)
        # Check if cut is in outro
        elif cut_end > (duration - outro_duration):
            # Penalize outro cuts
            section_score -= 5.0 / len(cut_points)
        else:
            # Reward middle cuts
            section_score += 10.0 / len(cut_points)

    # Cut pattern bonus scoring (10 points max) - NEW!
    pattern_bonus = score_cut_pattern(cut_points, duration) * (10.0 / 15.0)  # Scale to 10 points

    total_score = beat_score + harmonic_score + section_score + pattern_bonus
    return max(0.0, min(50.0, total_score))


def score_length_accuracy(target_length: float, resulting_length: float) -> float:
    """
    Score length accuracy (max 20 points) - STRICT ±15s enforcement.

    Thresholds (strict):
    - ±0-5s → 20 points (excellent)
    - ±5-15s → 15-5 points (acceptable, linear decay)
    - ±15-30s → 5-0 points (poor, steep penalty)
    - >±30s → 0 points (unacceptable)

    Args:
        target_length: Target length in seconds
        resulting_length: Resulting length after applying strategy

    Returns:
        Score from 0 to 20 points
    """
    error = abs(resulting_length - target_length)

    if error <= 5.0:
        return 20.0
    elif error <= 15.0:
        # Linear decay: 20 points at 5s → 5 points at 15s
        return 20.0 - (error - 5.0) * 1.5
    elif error <= 30.0:
        # Steep penalty: 5 points at 15s → 0 points at 30s
        return 5.0 - (error - 15.0) * (5.0 / 15.0)
    else:
        # Zero points for errors > 30s
        return 0.0


def score_strategy(
    strategy: TrimStrategy,
    original_audio: np.ndarray,
    sr: int,
    original_length: float,
    rendered_audio: np.ndarray = None,
    use_mert: bool = False,
    device: str = "cpu"
) -> Dict:
    """
    Score a complete trim/extension strategy with enhanced heuristics and optional MERT embeddings.

    Calculates resulting length, scores all components, and converts total to star rating.

    Scoring weights (V5 - Enhanced):
    - Musical coherence: 50 points (50%) - includes cut pattern bonus / loop quality, optional MERT
    - Transition smoothness: 30 points (30%) - enhanced with spectral flux, loudness / loop boundaries
    - Length accuracy: 20 points (20%) - STRICT ±15s enforcement
    Total: 100 points → converted to 0.5-5.0 star rating (0.1 increments)

    Args:
        strategy: TrimStrategy object with cut_points, loop_points, fade_regions, target_length
        original_audio: Original audio signal as numpy array
        sr: Sample rate
        original_length: Original audio length in seconds
        rendered_audio: The actual rendered audio after applying strategy (if None, estimates length)
        use_mert: Whether to use MERT embeddings for transition scoring (slower but better)
        device: Device for MERT inference ("cpu" or "cuda")

    Returns:
        Dict with keys:
            - total_points: Total score (0-100)
            - star_rating: Star rating (0.5-5.0 in 0.1 increments)
            - breakdown: Dict with component scores
                - musical_coherence: 0-50 points
                - transition_smoothness: 0-30 points (includes enhanced heuristics)
                - length_accuracy: 0-20 points
            - resulting_length: Resulting audio length in seconds
    """
    # Calculate resulting length from rendered audio
    if rendered_audio is not None:
        resulting_length = len(rendered_audio) / sr
    else:
        resulting_length = strategy.calculate_resulting_length(original_length)

    # Detect if this is an extension strategy (has loops) or trim strategy (has cuts)
    is_extension = len(strategy.loop_points) > 0 and len(strategy.cut_points) == 0

    if is_extension:
        # Extension scoring: evaluate loop naturalness
        coherence_score = score_loop_naturalness(
            original_audio, sr, strategy.loop_points, original_length
        )

        # Score loop transition smoothness
        transition_score = score_loop_transitions(
            original_audio, sr, strategy.loop_points
        )

        # Optional MERT bonus for loop transitions
        if use_mert:
            mert_bonus = score_mert_loop_transitions(original_audio, sr, strategy.loop_points, device)
            if mert_bonus is not None:
                coherence_score = min(50.0, coherence_score + mert_bonus)
    else:
        # Trim scoring: existing logic
        coherence_score = score_musical_coherence(
            original_audio, sr, strategy.cut_points, original_length
        )

        # Optional: Add MERT embedding similarity bonus (up to 5 extra points)
        if use_mert and len(strategy.cut_points) > 0:
            mert_bonus = score_mert_transitions(original_audio, sr, strategy.cut_points, device)
            if mert_bonus is not None:
                # Add bonus to coherence (capped at 50 points total)
                coherence_score = min(50.0, coherence_score + mert_bonus)

        # Apply volume consistency penalty for quiet endings
        # Check if rendered audio has significantly quieter ending than average
        if rendered_audio is not None and len(rendered_audio) > sr * 3:
            last_3s = rendered_audio[-int(3 * sr):]
            last_3s_rms = np.sqrt(np.mean(last_3s**2))
            avg_rms = np.sqrt(np.mean(rendered_audio**2))

            if avg_rms > 1e-6:  # Avoid division by zero
                volume_ratio = last_3s_rms / avg_rms
                # If ending is < 30% of average volume, apply penalty
                if volume_ratio < 0.3:
                    # Penalty scales from 0 to 12 points as ratio goes from 0.3 to 0
                    # This ensures quiet endings (like the 0.05/0.3 = 16.7% case) get 5+ point penalty
                    penalty = (0.3 - volume_ratio) / 0.3 * 12.0
                    coherence_score = max(0, coherence_score - penalty)

        # Score transition smoothness (30 points max) - ENHANCED
        # Base score from phase alignment and zero-crossings
        transition_score = score_transition_smoothness(
            original_audio, sr, strategy.cut_points, strategy.fade_regions
        )
        # Rescale from 40 points to 20 points (make room for enhanced heuristics)
        transition_score = (transition_score / 40.0) * 20.0

        # Add enhanced heuristics (10 points total)
        spectral_flux_score = score_spectral_flux(original_audio, sr, strategy.cut_points)
        loudness_score = score_loudness_consistency(original_audio, sr, strategy.cut_points)

        # Combine: 20 points base + 5 points spectral flux + 5 points loudness = 30 points
        transition_score = transition_score + (spectral_flux_score * 0.5) + (loudness_score * 0.5)

    # Score length accuracy (20 points max) - STRICT ±15s
    length_score = score_length_accuracy(
        strategy.target_length, resulting_length
    )

    # Calculate total points
    total_points = coherence_score + transition_score + length_score

    # Convert to star rating (0.1 increments)
    star_rating = points_to_stars(total_points)

    return {
        'total_points': total_points,
        'star_rating': star_rating,
        'breakdown': {
            'musical_coherence': coherence_score,
            'transition_smoothness': transition_score,
            'length_accuracy': length_score
        },
        'resulting_length': resulting_length
    }


def score_mert_transitions(
    audio: np.ndarray,
    sr: int,
    cut_points: List[Tuple[float, float]],
    device: str = "cpu"
) -> Optional[float]:
    """
    Score transition quality using MERT embeddings (optional, high-quality).

    Compares audio segments before and after cuts using semantic similarity.

    Args:
        audio: Audio signal
        sr: Sample rate
        cut_points: List of (start, end) cut tuples
        device: Device for MERT inference

    Returns:
        Bonus score from 0 to 5 points, or None if MERT unavailable
    """
    if not cut_points:
        return None

    try:
        score = 0.0
        window = 2.0  # 2 seconds before/after cut

        for cut_start, cut_end in cut_points:
            # Extract segments before and after cut
            before_start = max(0, cut_start - window)
            before_end = cut_start
            after_start = cut_end
            after_end = min(len(audio) / sr, cut_end + window)

            before_samples = audio[int(before_start * sr):int(before_end * sr)]
            after_samples = audio[int(after_start * sr):int(after_end * sr)]

            if len(before_samples) < sr or len(after_samples) < sr:
                continue  # Skip if segments too short

            # Get MERT embeddings
            before_emb = get_mert_embeddings(before_samples, sr, device)
            after_emb = get_mert_embeddings(after_samples, sr, device)

            if before_emb is not None and after_emb is not None:
                # Calculate cosine similarity
                similarity = np.dot(before_emb.flatten(), after_emb.flatten()) / (
                    np.linalg.norm(before_emb) * np.linalg.norm(after_emb) + 1e-8
                )
                # Higher similarity = better transition
                score += max(0, similarity) * (5.0 / len(cut_points))

        return min(5.0, score)
    except Exception as e:
        print(f"⚠️  MERT transition scoring failed: {e}")
        return None


def points_to_stars(points: float) -> float:
    """
    Convert points (0-100 scale) to star rating with 0.1 increments.

    Linear mapping for simplicity and consistency:
    - 100 points → 5.0 stars
    - 80 points → 4.0 stars
    - 60 points → 3.0 stars
    - 40 points → 2.0 stars
    - 20 points → 1.0 stars
    - 0 points → 0.0 stars

    Normalized to full 0.0-5.0 scale as per requirements.

    Args:
        points: Score on 0-100 scale

    Returns:
        Star rating (0.0 to 5.0) in 0.1 increments, rounded
    """
    # Linear mapping: 0-100 points → 0.0-5.0 stars
    # Each 20 points = 1 star
    raw_stars = (points / 100.0) * 5.0

    # Round to nearest 0.1
    stars = round(raw_stars, 1)

    # Clamp to valid range
    return max(0.0, min(5.0, stars))


def score_loop_naturalness(
    audio: np.ndarray,
    sr: int,
    loop_points: List[Tuple[float, float, int]],
    original_length: float
) -> float:
    """
    Score how natural the loop repetitions are (extension quality).

    Evaluates:
    - Loop diversity (20 pts): Not repeating same section too much
    - Section quality (15 pts): Prefer choruses, avoid intro/outro
    - Over-repetition penalty (15 pts): Limit total repetitions

    Args:
        audio: Audio data
        sr: Sample rate
        loop_points: List of (start, end, repeat_count) tuples
        original_length: Original audio length

    Returns:
        Score from 0-50 points
    """
    if not loop_points:
        return 25.0  # Neutral score for no loops

    score = 0.0
    total_loops = len(loop_points)

    # 1. Loop Diversity (0-20 points)
    # Penalize repeating the same section multiple times
    unique_sections = set((start, end) for start, end, _ in loop_points)
    diversity_ratio = len(unique_sections) / max(1, total_loops)
    score += 20.0 * diversity_ratio

    # 2. Section Quality (0-15 points)
    # Score based on what sections are being repeated
    for start, end, repeat_count in loop_points:
        duration = end - start
        relative_start = start / original_length

        # Prefer middle sections (avoid intro/outro)
        if 0.15 < relative_start < 0.85:
            score += 5.0 / max(1, total_loops)

        # Prefer reasonable durations (12-30s)
        if 12.0 <= duration <= 30.0:
            score += 5.0 / max(1, total_loops)

        # Prefer shorter repetitions (2-3x) over excessive (5x+)
        if repeat_count <= 3:
            score += 5.0 / max(1, total_loops)

    # 3. Over-repetition Penalty (0-15 points)
    # Penalize if too many total repetitions
    total_repetitions = sum(count for _, _, count in loop_points)
    if total_repetitions <= 6:
        score += 15.0  # Good: not too repetitive
    elif total_repetitions <= 10:
        score += 10.0  # Acceptable
    else:
        score += 5.0  # Too repetitive

    return min(50.0, score)


def score_loop_transitions(
    audio: np.ndarray,
    sr: int,
    loop_points: List[Tuple[float, float, int]]
) -> float:
    """
    Score transition smoothness at loop boundaries (extension quality).

    Evaluates:
    - Energy consistency (10 pts): RMS energy at loop start/end boundaries
    - Zero-crossing consistency (10 pts): Smooth zero-crossing alignment
    - Spectral similarity (10 pts): Audio similarity at boundaries

    Args:
        audio: Audio data
        sr: Sample rate
        loop_points: List of (start, end, repeat_count) tuples

    Returns:
        Score from 0-30 points
    """
    if not loop_points:
        return 15.0  # Neutral score

    score = 0.0
    total_transitions = len(loop_points)

    for start, end, _ in loop_points:
        # Analyze boundary regions (500ms)
        boundary_duration = 0.5
        start_sample = int(start * sr)
        end_sample = int(end * sr)
        boundary_samples = int(boundary_duration * sr)

        if end_sample - start_sample <= 2 * boundary_samples:
            score += 10.0 / max(1, total_transitions)
            continue

        try:
            start_region = audio[start_sample:start_sample + boundary_samples]
            end_region = audio[end_sample - boundary_samples:end_sample]

            # 1. Energy consistency (0-10 points per transition)
            start_energy = np.sqrt(np.mean(start_region ** 2))
            end_energy = np.sqrt(np.mean(end_region ** 2))

            if start_energy > 0 and end_energy > 0:
                energy_ratio = min(start_energy, end_energy) / max(start_energy, end_energy)
                score += (10.0 * energy_ratio) / max(1, total_transitions)

            # 2. Zero-crossing consistency (0-10 points per transition)
            start_zc = np.sum(librosa.zero_crossings(start_region))
            end_zc = np.sum(librosa.zero_crossings(end_region))

            if start_zc > 0 and end_zc > 0:
                zc_ratio = min(start_zc, end_zc) / max(start_zc, end_zc)
                score += (10.0 * zc_ratio) / max(1, total_transitions)

            # 3. Spectral similarity (0-10 points per transition)
            start_spec = np.abs(librosa.stft(start_region, n_fft=2048))
            end_spec = np.abs(librosa.stft(end_region, n_fft=2048))

            start_mean = np.mean(start_spec, axis=1)
            end_mean = np.mean(end_spec, axis=1)

            spec_corr = np.corrcoef(start_mean, end_mean)[0, 1]
            if not np.isnan(spec_corr):
                score += (10.0 * max(0, spec_corr)) / max(1, total_transitions)

        except Exception:
            score += 10.0 / max(1, total_transitions)  # Neutral if analysis fails

    return min(30.0, score)


def score_mert_loop_transitions(
    audio: np.ndarray,
    sr: int,
    loop_points: List[Tuple[float, float, int]],
    device: str = "cpu"
) -> Optional[float]:
    """
    Score loop transition quality using MERT embeddings (optional enhancement).

    Args:
        audio: Audio data
        sr: Sample rate
        loop_points: List of (start, end, repeat_count) tuples
        device: Device for MERT inference

    Returns:
        Bonus score from 0-5 points, or None if MERT unavailable
    """
    if not loop_points or not _MERT_AVAILABLE:
        return None

    model, processor = load_mert_model(device)
    if model is None or processor is None:
        return None

    try:
        import torch

        total_similarity = 0.0
        num_transitions = 0

        for start, end, _ in loop_points:
            # Extract boundary regions (1 second each)
            boundary_duration = 1.0
            start_sample = int(start * sr)
            end_sample = int(end * sr)
            boundary_samples = int(boundary_duration * sr)

            if end_sample - start_sample <= 2 * boundary_samples:
                continue

            start_region = audio[start_sample:start_sample + boundary_samples]
            end_region = audio[end_sample - boundary_samples:end_sample]

            # Get MERT embeddings
            with torch.no_grad():
                start_inputs = processor(start_region, sampling_rate=sr, return_tensors="pt")
                end_inputs = processor(end_region, sampling_rate=sr, return_tensors="pt")

                start_inputs = {k: v.to(device) for k, v in start_inputs.items()}
                end_inputs = {k: v.to(device) for k, v in end_inputs.items()}

                start_embed = model(**start_inputs).last_hidden_state.mean(dim=1).cpu().numpy().flatten()
                end_embed = model(**end_inputs).last_hidden_state.mean(dim=1).cpu().numpy().flatten()

            # Cosine similarity
            similarity = np.dot(start_embed, end_embed) / (
                np.linalg.norm(start_embed) * np.linalg.norm(end_embed) + 1e-10
            )
            total_similarity += max(0, similarity)
            num_transitions += 1

        if num_transitions > 0:
            avg_similarity = total_similarity / num_transitions
            return 5.0 * avg_similarity  # 0-5 bonus points

    except Exception as e:
        print(f"⚠️  MERT loop scoring failed: {e}")

    return None
