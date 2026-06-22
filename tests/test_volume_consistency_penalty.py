"""
Test for volume consistency penalty in quality scoring.

RED TEST: Quality scorer should penalize strategies that end with
significantly quieter audio than the average, as this creates a
perceived "abrupt volume drop" for listeners.
"""

import pytest
import numpy as np
from src.quality_scorer import score_strategy
from src.trim_engine import TrimStrategy


def test_quality_scorer_penalizes_quiet_endings():
    """
    RED: Score should be lower for strategies with quiet endings.

    Two strategies with identical cuts, but one has quiet outro.
    The one with quiet outro should score lower.
    """
    np.random.seed(42)  # Fixed seed for reproducibility
    sr = 22050
    duration = 60.0

    # Strategy 1: Audio with consistent volume throughout
    consistent_audio = np.random.randn(sr * 60) * 0.3
    strategy1 = TrimStrategy(
        name="consistent",
        cut_points=[(20.0, 30.0)],  # Remove 10s from middle
        loop_points=[],
        fade_regions=[(19.95, 20.05)],
        target_length=50.0
    )

    # Strategy 2: Same cuts, but audio has quiet ending (simulates quiet outro)
    np.random.seed(42)  # Same seed for main section
    loud_section = np.random.randn(sr * 57) * 0.3
    quiet_outro = np.random.randn(sr * 3) * 0.05  # Last 3s is quiet
    quiet_ending_audio = np.concatenate([loud_section, quiet_outro])

    strategy2 = TrimStrategy(
        name="quiet_ending",
        cut_points=[(20.0, 30.0)],  # Same cuts
        loop_points=[],
        fade_regions=[(19.95, 20.05)],
        target_length=50.0
    )

    # Score both strategies - pass original audio as rendered_audio for testing
    # (in real use, rendered_audio would be the output after apply_cuts)
    score1 = score_strategy(strategy1, consistent_audio, sr, duration,
                           rendered_audio=consistent_audio, use_mert=False)
    score2 = score_strategy(strategy2, quiet_ending_audio, sr, duration,
                           rendered_audio=quiet_ending_audio, use_mert=False)

    print(f"\nConsistent volume score: {score1['total_points']:.2f} ({score1['star_rating']:.1f}★)")
    print(f"Quiet ending score: {score2['total_points']:.2f} ({score2['star_rating']:.1f}★)")
    print(f"Total difference: {score1['total_points'] - score2['total_points']:.2f} points")
    print(f"Coherence difference: {score1['breakdown']['musical_coherence'] - score2['breakdown']['musical_coherence']:.2f} points")

    # The quiet ending should be penalized in the coherence score
    # The penalty should be at least 5 points in coherence
    assert score2['breakdown']['musical_coherence'] < score1['breakdown']['musical_coherence'] - 5, \
        "Quiet endings should be penalized by at least 5 points in musical coherence"


def test_volume_consistency_penalty_threshold():
    """
    RED: Only penalize if ending is SIGNIFICANTLY quieter (< 30% of average).

    Slight volume variations are normal and shouldn't be penalized.
    """
    np.random.seed(42)  # Fixed seed for reproducibility
    sr = 22050
    duration = 60.0

    # Case 1: Ending at 80% of average volume (normal variation)
    main_section = np.random.randn(sr * 57) * 0.3
    slightly_quieter_outro = np.random.randn(sr * 3) * 0.24  # 80% of 0.3
    normal_audio = np.concatenate([main_section, slightly_quieter_outro])

    # Case 2: Ending at 20% of average volume (problematic)
    np.random.seed(42)  # Same main section
    main_section2 = np.random.randn(sr * 57) * 0.3
    quiet_outro = np.random.randn(sr * 3) * 0.06  # 20% of 0.3
    quiet_audio = np.concatenate([main_section2, quiet_outro])

    strategy = TrimStrategy(
        name="test",
        cut_points=[(20.0, 30.0)],
        loop_points=[],
        fade_regions=[(19.95, 20.05)],
        target_length=50.0
    )

    score_normal = score_strategy(strategy, normal_audio, sr, duration,
                                  rendered_audio=normal_audio, use_mert=False)
    score_quiet = score_strategy(strategy, quiet_audio, sr, duration,
                                 rendered_audio=quiet_audio, use_mert=False)

    print(f"\n80% ending volume score: {score_normal['total_points']:.2f}")
    print(f"20% ending volume score: {score_quiet['total_points']:.2f}")
    print(f"Coherence diff: {score_normal['breakdown']['musical_coherence'] - score_quiet['breakdown']['musical_coherence']:.2f}")

    # Quiet ending SHOULD be penalized significantly in coherence
    # Note: The actual penalty depends on the exact volume ratio after mixing
    # 20% target doesn't guarantee exactly 20% in the final mix due to RMS calculation
    assert score_quiet['breakdown']['musical_coherence'] < score_normal['breakdown']['musical_coherence'], \
        "Significantly quiet endings (< 30%) should be penalized in coherence"

    # Verify the penalty is meaningful (at least 3 points, ideally 5+)
    penalty = score_normal['breakdown']['musical_coherence'] - score_quiet['breakdown']['musical_coherence']
    assert penalty >= 3.0, f"Penalty should be at least 3 points, got {penalty:.2f}"


def test_volume_penalty_applies_to_rendered_audio():
    """
    RED: Volume consistency check should use rendered audio, not original.

    The rendered audio (after cuts/loops) is what the user hears.
    """
    sr = 22050
    duration = 60.0

    # Original audio is all loud
    original_audio = np.random.randn(sr * 60) * 0.3

    # But after rendering with cuts, we might end up with a quiet section
    # (This simulates what happened in the real bug)
    loud_section = np.random.randn(sr * 47) * 0.3
    quiet_section = np.random.randn(sr * 3) * 0.05
    rendered_audio = np.concatenate([loud_section, quiet_section])

    strategy = TrimStrategy(
        name="test",
        cut_points=[(20.0, 30.0)],
        loop_points=[],
        fade_regions=[(19.95, 20.05)],
        target_length=50.0
    )

    # Pass rendered audio explicitly
    score = score_strategy(strategy, original_audio, sr, duration,
                          rendered_audio=rendered_audio, use_mert=False)

    print(f"\nScore with quiet rendered ending: {score['total_points']:.2f}")

    # Should be penalized based on rendered audio, not original
    # (This will fail until we implement the check on rendered_audio)
    assert score['total_points'] < 85, \
        "Should penalize quiet endings in rendered audio"


def test_no_penalty_for_extension_mode():
    """
    RED: Extension mode (loops) should not be penalized for volume consistency.

    Extension strategies repeat sections, so ending volume depends on
    which section is repeated. This is intentional, not a bug.
    """
    sr = 22050
    duration = 60.0

    # Audio with quiet section in middle
    section1 = np.random.randn(sr * 20) * 0.3
    quiet_section = np.random.randn(sr * 20) * 0.05
    section2 = np.random.randn(sr * 20) * 0.3
    audio = np.concatenate([section1, quiet_section, section2])

    # Extension strategy that repeats the quiet section
    strategy = TrimStrategy(
        name="extension",
        cut_points=[],  # No cuts = extension mode
        loop_points=[(20.0, 40.0, 2)],  # Repeat quiet section
        fade_regions=[],
        target_length=80.0
    )

    score = score_strategy(strategy, audio, sr, duration, use_mert=False)

    print(f"\nExtension mode score (quiet section repeated): {score['total_points']:.2f}")

    # Extension mode should NOT be penalized for volume consistency
    # (loops are intentional, not a quality issue)
    assert score['total_points'] > 70, \
        "Extension mode should not be penalized for ending volume"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
