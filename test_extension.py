#!/usr/bin/env python3
"""Test script for audio extension feature."""

import sys
import numpy as np
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.audio_loader import load_audio
from src.spectral_analyzer import analyze_audio_structure
from src.structure_analyzer import analyze_structure
from src.trim_engine import generate_extension_strategies
from src.output_generator import render_strategy
from src.quality_scorer import score_strategy


def test_extension_feature():
    """Test the extension feature end-to-end."""

    # Find a test audio file
    test_file = Path("./output/option_0_3.8stars.wav")
    if not test_file.exists():
        # Try to find any wav file
        output_files = list(Path("./output").glob("*.wav"))
        if not output_files:
            print("❌ No test audio files found")
            return False
        test_file = output_files[0]

    print(f"🎵 Testing extension with: {test_file}")

    # Load audio
    print("\n1. Loading audio...")
    audio_data, sample_rate = load_audio(str(test_file))
    original_length = len(audio_data) / sample_rate
    print(f"   Original length: {original_length:.2f}s")

    # Set target length (extend by 30 seconds)
    target_length = original_length + 30.0
    print(f"   Target length: {target_length:.2f}s (+30s extension)")

    # Analyze structure
    print("\n2. Analyzing structure...")
    analysis = analyze_audio_structure(audio_data, sample_rate)
    structure = analyze_structure(
        audio_data, sample_rate,
        analysis['chroma'],
        analysis['repeated_segments']
    )
    print(f"   Detected {len(structure['sections'])} sections")
    print(f"   Tempo: {structure['beat_info']['tempo']:.1f} BPM")

    # Generate extension strategies
    print("\n3. Generating extension strategies...")
    try:
        strategies = generate_extension_strategies(
            clusters=[],  # Not needed for extension
            original_length=original_length,
            target_length=target_length,
            sections=structure['sections'],
            downbeats=structure['beat_info']['downbeats'],
            audio_data=audio_data,
            sample_rate=sample_rate,
            num_strategies=3
        )
        print(f"   ✓ Generated {len(strategies)} strategies")

        if not strategies:
            print("   ❌ No strategies generated!")
            return False

        # Show loop details
        for strategy in strategies:
            print(f"\n   {strategy.name}:")
            print(f"      Loop points: {len(strategy.loop_points)}")
            for start, end, count in strategy.loop_points:
                duration = end - start
                print(f"         - {start:.1f}-{end:.1f}s ({duration:.1f}s) ×{count}")

            expected_length = strategy.calculate_resulting_length(original_length)
            print(f"      Expected length: {expected_length:.2f}s")

    except Exception as e:
        print(f"   ❌ Strategy generation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test rendering and scoring
    print("\n4. Rendering and scoring strategies...")
    for i, strategy in enumerate(strategies[:2]):  # Test first 2
        try:
            # Render
            rendered = render_strategy(strategy, audio_data, sample_rate)
            rendered_length = len(rendered) / sample_rate
            print(f"\n   {strategy.name}:")
            print(f"      Rendered length: {rendered_length:.2f}s")

            # Score
            score = score_strategy(
                strategy, audio_data, sample_rate,
                original_length, rendered, use_mert=False
            )
            print(f"      Quality score: {score['star_rating']:.1f}★ ({score['total_points']:.1f} points)")
            print(f"      Breakdown:")
            print(f"         Musical coherence: {score['breakdown']['musical_coherence']:.1f}/50")
            print(f"         Transition smoothness: {score['breakdown']['transition_smoothness']:.1f}/30")
            print(f"         Length accuracy: {score['breakdown']['length_accuracy']:.1f}/20")

        except Exception as e:
            print(f"   ❌ Rendering/scoring failed: {e}")
            import traceback
            traceback.print_exc()
            return False

    print("\n✅ Extension feature test completed successfully!")
    return True


if __name__ == "__main__":
    success = test_extension_feature()
    sys.exit(0 if success else 1)
