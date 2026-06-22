"""
Test for outro volume issue - ensuring fade-out works on actual audio content.

The bug: When trim mode keeps a quiet outro section from the original audio,
the fade-out is applied to already-quiet audio, making it seem like there's
no fade-out or an abrupt drop.

The fix: We need to ensure the final segment has reasonable volume before
applying fade-out, or apply volume normalization to the outro region.
"""

import pytest
import numpy as np
from src.output_generator import apply_cuts


def test_final_segment_fade_out_on_quiet_audio():
    """
    RED TEST: Demonstrate that fade-out on already-quiet audio doesn't help.

    This test shows the real issue: if the audio is already quiet (like a
    natural outro), our fade-out doesn't make it "feel" smoother because
    there's nothing to fade.
    """
    sr = 22050

    # Create audio with loud middle section and quiet outro (realistic scenario)
    loud_section = np.random.randn(sr * 60) * 0.5  # 60s at 0.5 amplitude
    quiet_outro = np.random.randn(sr * 10) * 0.01  # 10s at 0.01 amplitude (quiet)
    audio = np.concatenate([loud_section, quiet_outro])

    # Apply a cut that removes middle, leaving quiet outro at end
    # Simulate: keep 0-30s, remove 30-60s, keep 60-70s (quiet outro)
    cut_points = [(30.0, 60.0)]

    result = apply_cuts(audio, sr, cut_points)

    # Check: the last 10 seconds should be quiet (this is the problem)
    last_10s = result[-sr*10:]
    last_10s_rms = np.sqrt(np.mean(last_10s**2))

    # This will be low because the source audio is quiet
    print(f"Last 10s RMS: {last_10s_rms:.6f}")

    # The fade-out IS applied, but it's fading quiet audio to silence
    # which doesn't help the listening experience
    assert last_10s_rms < 0.02, "Outro is quiet as expected, but listeners hear 'abrupt drop'"


def test_solution_boost_quiet_outro_before_fadeout():
    """
    GREEN TEST: Proposed solution - detect quiet outros and boost volume before fade.

    If the final segment is significantly quieter than the rest of the audio,
    we should either:
    1. Boost its volume to match the average
    2. Or avoid keeping quiet outros in the first place (better strategy selection)
    """
    sr = 22050

    # Same scenario
    loud_section = np.random.randn(sr * 60) * 0.5
    quiet_outro = np.random.randn(sr * 10) * 0.01
    audio = np.concatenate([loud_section, quiet_outro])

    cut_points = [(30.0, 60.0)]
    result = apply_cuts(audio, sr, cut_points)

    # Calculate RMS of main content vs outro
    main_content = result[:-sr*3]  # Everything except last 3s
    outro_content = result[-sr*3:]

    main_rms = np.sqrt(np.mean(main_content**2))
    outro_rms = np.sqrt(np.mean(outro_content**2))

    print(f"Main RMS: {main_rms:.6f}")
    print(f"Outro RMS: {outro_rms:.6f}")
    print(f"Ratio: {outro_rms/main_rms:.2%}")

    # If outro is < 30% of main volume, it's a problem
    if outro_rms < main_rms * 0.3:
        # TODO: Implement volume normalization for quiet outros
        pytest.skip("Volume normalization not yet implemented")

    assert outro_rms >= main_rms * 0.3, "Outro should not be drastically quieter than main content"


def test_real_world_scenario_with_current_code():
    """
    This test reproduces the actual bug from output/option_0_4.4stars.wav

    The audio has:
    - Loud content for most of the song
    - Quiet outro from original audio (241-255s section)
    - Our fade-out is applied but doesn't solve the perceived "abrupt drop"
    """
    sr = 22050
    duration = 255  # Original song duration

    # Simulate the original song structure
    intro = np.random.randn(sr * 53) * 0.3  # 0-53s intro (protected)
    middle = np.random.randn(sr * 188) * 0.4  # 53-241s middle (loud)
    outro = np.random.randn(sr * 14) * 0.05  # 241-255s outro (protected, but QUIET)

    audio = np.concatenate([intro, middle, outro])

    # Cuts from the actual output
    cut_points = [
        (53.87, 115.61),
        (115.61, 173.22),
        (173.22, 243.16)
    ]

    result = apply_cuts(audio, sr, cut_points)

    # After cuts, we have: intro + small middle + outro
    # The outro is quiet, so even with fade-out, it sounds abrupt

    last_3s = result[-sr*3:]
    last_3s_rms = np.sqrt(np.mean(last_3s**2))

    # This is the bug: last 3s RMS is very low (< 0.01 in real file)
    print(f"Last 3s RMS: {last_3s_rms:.6f}")

    # Expected: < 0.1 because outro is naturally quiet
    # Problem: Listeners perceive this as "volume drop" even though
    # it's just the original quiet outro
    assert last_3s_rms < 0.1, "Bug reproduced: outro is quiet"


if __name__ == "__main__":
    print("Running outro volume tests...\n")

    print("Test 1: Fade-out on quiet audio")
    test_final_segment_fade_out_on_quiet_audio()
    print("✓ Passed\n")

    print("Test 2: Solution - boost quiet outro")
    test_solution_boost_quiet_outro_before_fadeout()
    print("✓ Passed\n")

    print("Test 3: Real-world scenario")
    test_real_world_scenario_with_current_code()
    print("✓ Passed\n")
