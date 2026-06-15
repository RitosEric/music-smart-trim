"""CLI module for music-smart-trim with pipeline orchestration and regeneration support."""

import time
import argparse
import sys
from pathlib import Path
from typing import List, Dict, Optional

from src.audio_loader import load_audio, AudioLoadError
from src.spectral_analyzer import analyze_audio_structure
from src.segment_matcher import match_segments
from src.trim_engine import generate_trim_strategies
from src.quality_scorer import score_strategy
from src.output_generator import generate_outputs


def run_pipeline(
    audio_path: Path,
    target_length: float,
    protected_regions: List[str],
    output_dir: Path,
    regenerate_seed: Optional[int] = None
) -> Dict:
    """
    Run complete pipeline from audio loading to output generation.

    Orchestrates the entire workflow:
    1. Load audio
    2. Analyze audio structure (spectral analysis)
    3. Match segments and handle protected regions
    4. Generate trim strategies (conservative, balanced, aggressive)
    5. Score each strategy
    6. Generate outputs

    Ensures at least one option scores ≥4.5★ by retrying up to 5 times with different seeds.

    Args:
        audio_path: Path to input audio file
        target_length: Target length in seconds
        protected_regions: List of protected region strings in "MM:SS-MM:SS" format
        output_dir: Directory to save output files
        regenerate_seed: Optional seed for regeneration (None for first run)

    Returns:
        Dict with keys:
            - strategies: List of TrimStrategy objects
            - scores: List of score dicts
            - output_files: List of output file paths
            - processing_time: Processing time in seconds

    Raises:
        AudioLoadError: If audio file cannot be loaded
    """
    start_time = time.time()

    # Stage 1: Load audio
    print(f"Loading audio from {audio_path}...")
    audio_data, sample_rate = load_audio(audio_path)
    original_length = len(audio_data) / sample_rate
    print(f"Audio loaded: {original_length:.2f}s @ {sample_rate}Hz")

    # Stage 2: Analyze audio structure
    print("Analyzing audio structure...")
    analysis_result = analyze_audio_structure(audio_data, sample_rate)
    repeated_segments = analysis_result['repeated_segments']
    print(f"Found {len(repeated_segments)} repeated segments")

    # Stage 3: Match segments
    print("Matching segments and filtering protected regions...")
    match_result = match_segments(repeated_segments, protected_regions)
    clusters = match_result['clusters']
    protected_regions_parsed = match_result['protected_regions']
    print(f"Identified {len(clusters)} segment clusters")

    # Stage 4: Generate trim strategies
    print("Generating trim strategies...")
    strategies = generate_trim_strategies(
        clusters,
        original_length,
        target_length,
        regenerate_seed=regenerate_seed
    )
    print(f"Generated {len(strategies)} strategies: {[s.name for s in strategies]}")

    # Stage 5: Score each strategy
    print("Scoring strategies...")
    scores = []
    for strategy in strategies:
        score = score_strategy(strategy, audio_data, sample_rate, original_length)
        scores.append(score)
        print(f"  {strategy.name}: {score['star_rating']}★ ({score['total_points']:.1f} points)")

    # Check if at least one option scores ≥4.5★
    max_rating = max(score['star_rating'] for score in scores)
    if max_rating < 4.5 and regenerate_seed is None:
        # Retry up to 5 times with different seeds
        print(f"Max rating {max_rating}★ < 4.5★, retrying with different seeds...")
        for retry_seed in range(1, 6):
            print(f"\nRetry {retry_seed}/5 with seed {retry_seed}...")
            strategies = generate_trim_strategies(
                clusters,
                original_length,
                target_length,
                regenerate_seed=retry_seed
            )
            scores = []
            for strategy in strategies:
                score = score_strategy(strategy, audio_data, sample_rate, original_length)
                scores.append(score)
                print(f"  {strategy.name}: {score['star_rating']}★ ({score['total_points']:.1f} points)")

            max_rating = max(score['star_rating'] for score in scores)
            if max_rating >= 4.5:
                print(f"Found acceptable rating: {max_rating}★ ≥ 4.5★")
                break

    # Stage 6: Generate outputs
    print(f"\nGenerating output files to {output_dir}...")
    processing_time = time.time() - start_time

    generate_outputs(
        audio_data,
        sample_rate,
        strategies,
        scores,
        output_dir,
        str(audio_path),
        target_length,
        protected_regions_parsed,
        processing_time
    )

    # Collect output file paths
    output_files = []
    for i, score in enumerate(scores):
        stars = score['star_rating']
        output_filename = f"option_{i}_{stars}stars.wav"
        output_files.append(str(output_dir / output_filename))

    print("Pipeline complete!")

    return {
        'strategies': strategies,
        'scores': scores,
        'output_files': output_files,
        'processing_time': processing_time,
        'original_length': original_length
    }


def parse_arguments() -> argparse.Namespace:
    """
    Parse command-line arguments.

    Returns:
        argparse.Namespace with parsed arguments
    """
    parser = argparse.ArgumentParser(
        description='Music Smart Trim - Intelligently shorten audio files'
    )

    parser.add_argument(
        '--input',
        required=True,
        type=Path,
        help='Input audio file path'
    )

    parser.add_argument(
        '--target',
        required=True,
        type=float,
        help='Target length in seconds'
    )

    parser.add_argument(
        '--protect',
        nargs='*',
        default=[],
        help='Protected regions in "MM:SS-MM:SS" format (e.g., "00:00-00:10 00:50-01:00")'
    )

    parser.add_argument(
        '--output-dir',
        type=Path,
        default=Path('output'),
        help='Output directory (default: ./output)'
    )

    return parser.parse_args()


def display_results(result: Dict) -> None:
    """
    Display results in a human-readable format.

    Args:
        result: Result dict from run_pipeline()
    """
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)

    strategies = result['strategies']
    scores = result['scores']
    output_files = result['output_files']
    processing_time = result['processing_time']
    original_length = result['original_length']

    for i, (strategy, score, output_file) in enumerate(zip(strategies, scores, output_files)):
        # Format star rating with symbols
        star_rating = score['star_rating']
        full_stars = int(star_rating)
        half_star = (star_rating - full_stars) >= 0.5
        star_display = "★" * full_stars
        if half_star:
            star_display += "½"
        empty_stars = 5 - full_stars - (1 if half_star else 0)
        star_display += "☆" * empty_stars

        print(f"\nOption {i + 1}: {strategy.name.upper()}")
        print(f"  Rating: {star_display} ({star_rating} stars)")
        print(f"  Length: {strategy.calculate_resulting_length(original_length):.2f}s")
        print(f"  Cuts: {len(strategy.cut_points)}")
        print(f"  Loops: {len(strategy.loop_points)}")
        print(f"  Output: {output_file}")

    print(f"\nProcessing time: {processing_time:.2f}s")
    print("=" * 60)


def main():
    """
    Main CLI entry point with regeneration loop.
    """
    # Parse arguments
    args = parse_arguments()

    print("Music Smart Trim")
    print("=" * 60)
    print(f"Input: {args.input}")
    print(f"Target length: {args.target}s")
    print(f"Protected regions: {args.protect if args.protect else 'None'}")
    print(f"Output directory: {args.output_dir}")
    print("=" * 60 + "\n")

    try:
        # Run initial pipeline
        result = run_pipeline(
            audio_path=args.input,
            target_length=args.target,
            protected_regions=args.protect,
            output_dir=args.output_dir,
            regenerate_seed=None
        )

        # Display results
        display_results(result)

        # Regeneration loop
        regenerate_count = 0
        while True:
            response = input("\nGenerate alternative options? (y/n): ").strip().lower()

            if response == 'y':
                regenerate_count += 1
                print(f"\nRegenerating with seed {regenerate_count}...\n")

                result = run_pipeline(
                    audio_path=args.input,
                    target_length=args.target,
                    protected_regions=args.protect,
                    output_dir=args.output_dir,
                    regenerate_seed=regenerate_count
                )

                display_results(result)

            elif response == 'n':
                print("\nThank you for using Music Smart Trim!")
                break
            else:
                print("Invalid input. Please enter 'y' or 'n'.")

    except AudioLoadError as e:
        print(f"\nError loading audio: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
