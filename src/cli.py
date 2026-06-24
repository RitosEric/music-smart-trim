"""CLI module for music-smart-trim with pipeline orchestration and regeneration support."""

import time
import argparse
import sys
from pathlib import Path
from typing import List, Dict, Optional, Tuple

from src.audio_loader import load_audio, AudioLoadError
from src.spectral_analyzer import analyze_audio_structure
from src.segment_matcher import match_segments
from src.trim_engine import generate_trim_strategies, generate_strategies
from src.quality_scorer import score_strategy
from src.output_generator import generate_outputs


# Constants
MIN_ACCEPTABLE_QUALITY = 3.5
MAX_QUALITY_RETRIES = 5


def format_time_string(seconds: float) -> str:
    """
    Format seconds as MM:SS string.

    Args:
        seconds: Time in seconds

    Returns:
        Time string in "MM:SS" format
    """
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes}:{secs:02d}"


def get_all_protected_regions(
    user_protected: List[str],
    auto_protect: bool,
    structure: Dict,
    audio_data,
    sample_rate: int,
    original_length: float
) -> List[str]:
    """
    Get all protected regions (user-specified + auto intro/outro).

    Args:
        user_protected: User-specified protected regions
        auto_protect: Whether to auto-protect intro/outro
        structure: Music structure with sections
        audio_data: Audio data array
        sample_rate: Sample rate
        original_length: Original audio length in seconds

    Returns:
        List of all protected region strings in "MM:SS-MM:SS" format
    """
    if not auto_protect:
        print("\nAuto-protection disabled - intro/outro may be cut")
        return user_protected

    # Automatically protect intro and outro (section-aligned)
    from src.structure_analyzer import get_protected_intro_outro
    auto_protected = get_protected_intro_outro(audio_data, sample_rate, structure['sections'])
    intro_end = int(auto_protected[0][1])
    outro_start = int(auto_protected[1][0])
    print(f"\nAuto-protecting intro (0-{intro_end}s) and outro ({outro_start}s-{int(original_length)}s)")

    # Format as time strings and add to protected regions
    intro_str = f"0:00-{format_time_string(intro_end)}"
    outro_str = f"{format_time_string(outro_start)}-{format_time_string(original_length)}"

    return user_protected + [intro_str, outro_str]


def retry_for_quality(
    scored_strategies: List[Dict],
    clusters: List[Dict],
    original_length: float,
    target_length: float,
    structure: Dict,
    audio_data,
    sample_rate: int,
    use_mert: bool,
    regenerate_seed: Optional[int],
    mode: str,
    min_segment_duration: float = 10.0
) -> Tuple[List, List]:
    """
    Retry strategy generation if quality is below threshold.

    Args:
        scored_strategies: Initial scored strategies
        clusters: Segment clusters
        original_length: Original audio length
        target_length: Target length
        structure: Music structure
        audio_data: Audio data array
        sample_rate: Sample rate
        use_mert: Whether to use MERT embeddings
        regenerate_seed: Current regeneration seed (None for first run)
        mode: Processing mode ("trim" or "extend")

    Returns:
        Tuple of (strategies, scores) - top 3 strategies and their scores
    """
    from src.output_generator import render_strategy

    scored_strategies.sort(key=lambda x: x['score']['star_rating'], reverse=True)
    # Take top 3 strategies instead of just the best
    top_strategies = scored_strategies[:3]
    strategies = [s['strategy'] for s in top_strategies]
    scores = [s['score'] for s in top_strategies]

    max_rating = scores[0]['star_rating']

    # Only retry on first run (not during manual regeneration)
    if max_rating < MIN_ACCEPTABLE_QUALITY and regenerate_seed is None:
        print(f"Max rating {max_rating:.1f}★ < {MIN_ACCEPTABLE_QUALITY}★, retrying with different seeds...")

        for retry_seed in range(1, MAX_QUALITY_RETRIES + 1):
            print(f"\nRetry {retry_seed}/{MAX_QUALITY_RETRIES} with seed {retry_seed}...")

            all_strategies = generate_strategies(
                mode=mode,
                clusters=clusters,
                original_length=original_length,
                target_length=target_length,
                sections=structure['sections'],
                downbeats=structure['beat_info']['downbeats'],
                regenerate_seed=retry_seed,
                num_strategies=10,
                min_segment_duration=min_segment_duration
            )

            scored_strategies = []
            for strategy in all_strategies:
                rendered_audio = render_strategy(strategy, audio_data, sample_rate)
                score = score_strategy(strategy, audio_data, sample_rate, original_length, rendered_audio, use_mert=use_mert)
                scored_strategies.append({
                    'strategy': strategy,
                    'score': score,
                    'rendered_audio': rendered_audio
                })

            scored_strategies.sort(key=lambda x: x['score']['star_rating'], reverse=True)
            # Take top 3 strategies instead of just the best
            top_strategies = scored_strategies[:3]
            strategies = [s['strategy'] for s in top_strategies]
            scores = [s['score'] for s in top_strategies]

            max_rating = scores[0]['star_rating']
            if max_rating >= MIN_ACCEPTABLE_QUALITY:
                print(f"Found acceptable rating: {max_rating:.1f}★ ≥ {MIN_ACCEPTABLE_QUALITY}★")
                break

    return strategies, scores


def run_pipeline(
    audio_path: Path,
    target_length: float,
    protected_regions: List[str],
    output_dir: Path,
    regenerate_seed: Optional[int] = None,
    use_mert: bool = False,
    excluded_strategies: Optional[List[str]] = None,
    auto_protect: bool = False,
    min_segment_duration: float = 10.0
) -> Dict:
    """
    Run complete pipeline from audio loading to output generation.

    Automatically detects mode (trim vs extend) based on target vs original length.

    Orchestrates the entire workflow:
    1. Load audio
    2. Analyze audio structure (spectral analysis + beat detection)
    3. Match segments and handle protected regions
    4. Auto-detect mode: trim (target < original) or extend (target > original)
    5. Generate 5 diverse strategies (trim or extend based on mode)
    6. Score all strategies and select top 3 by quality
    7. Generate outputs for top 3 only

    NEW IN V8 (BUG FIX):
    - Generates 5 TRULY diverse strategies (fixed bug where all 10 were identical)
    - Each strategy uses different parameters: best, diverse, varied, balanced, conservative
    - Shows top 3 by quality score

    NEW IN V6:
    - Generates multiple strategies, shows only top 3 by quality
    - Excludes previously shown strategies on regeneration
    - Ensures variety in output options

    Args:
        audio_path: Path to input audio file
        target_length: Target length in seconds
        protected_regions: List of protected region strings in "MM:SS-MM:SS" format
        output_dir: Directory to save output files
        regenerate_seed: Optional seed for regeneration (None for first run)
        use_mert: Whether to use MERT embeddings for quality scoring (slower but better)
        excluded_strategies: List of strategy names to exclude (for regeneration)
        auto_protect: Whether to automatically protect intro/outro (default: False)

    Returns:
        Dict with keys:
            - strategies: List of top 3 TrimStrategy objects
            - scores: List of top 3 score dicts
            - output_files: List of output file paths
            - processing_time: Processing time in seconds
            - all_strategies: List of all strategy names (for exclusion tracking)

    Raises:
        AudioLoadError: If audio file cannot be loaded
    """
    start_time = time.time()

    # Stage 1: Load audio
    print(f"Loading audio from {audio_path}...")
    audio_data, sample_rate = load_audio(audio_path)
    original_length = len(audio_data) / sample_rate
    print(f"Audio loaded: {original_length:.2f}s @ {sample_rate}Hz")

    # Stage 2: Analyze audio structure (including beats and sections)
    print("Analyzing audio structure...")
    from src.structure_analyzer import analyze_structure, get_protected_intro_outro

    analysis_result = analyze_audio_structure(audio_data, sample_rate)
    repeated_segments = analysis_result['repeated_segments']
    chroma = analysis_result['chroma']

    # Detect music structure (intro, verse, chorus, outro) and beats
    # V2: Pass repeated_segments for better chorus detection
    structure = analyze_structure(audio_data, sample_rate, chroma, repeated_segments)

    print(f"Found {len(repeated_segments)} repeated segments")
    print(f"Detected tempo: {structure['beat_info']['tempo']:.1f} BPM")
    print(f"Detected {len(structure['sections'])} sections:")
    for section in structure['sections']:
        print(f"  {section['start']:.1f}s - {section['end']:.1f}s: {section['label']}")

    # Get all protected regions (user-specified + optional auto intro/outro)
    all_protected_regions = get_all_protected_regions(
        protected_regions, auto_protect, structure, audio_data, sample_rate, original_length
    )

    # Stage 3: Match segments
    print("Matching segments and filtering protected regions...")
    match_result = match_segments(repeated_segments, all_protected_regions)
    clusters = match_result['clusters']
    protected_regions_parsed = match_result['protected_regions']
    print(f"Identified {len(clusters)} segment clusters")
    print(f"Protected regions: {len(protected_regions_parsed)}")

    # Stage 4: Detect mode and generate strategies
    mode = "trim" if target_length < original_length else "extend"
    print(f"\nMode: {mode.upper()} ({original_length:.1f}s → {target_length:.1f}s)")

    print(f"Generating 5 diverse {mode} strategies...")
    all_strategies = generate_strategies(
        mode=mode,
        clusters=clusters,
        original_length=original_length,
        target_length=target_length,
        sections=structure['sections'],
        downbeats=structure['beat_info']['downbeats'],
        regenerate_seed=regenerate_seed,
        num_strategies=5,
        min_segment_duration=min_segment_duration
    )
    print(f"Generated {len(all_strategies)} strategies")

    # DEBUG: Show strategy details
    print(f"\nStrategy details:")
    for strategy in all_strategies:
        if mode == "trim" and strategy.cut_points:
            cut_summary = ", ".join([f"{start:.1f}-{end:.1f}s" for start, end in strategy.cut_points])
            total_cut = sum(end - start for start, end in strategy.cut_points)
            print(f"  {strategy.name}: {len(strategy.cut_points)} cuts ({total_cut:.1f}s removed): [{cut_summary}]")
        elif mode == "extend" and strategy.loop_points:
            loop_summary = ", ".join([f"{start:.1f}-{end:.1f}s×{count}" for start, end, count in strategy.loop_points])
            total_added = sum((end - start) * (count - 1) for start, end, count in strategy.loop_points)
            print(f"  {strategy.name}: {len(strategy.loop_points)} loops ({total_added:.1f}s added): [{loop_summary}]")
        else:
            print(f"  {strategy.name}: No modifications")

    # Stage 5: Render and score ALL strategies
    print("Scoring all strategies...")
    if use_mert:
        print("  Using MERT embeddings for enhanced quality scoring...")
    from src.output_generator import render_strategy

    scored_strategies = []
    for strategy in all_strategies:
        # Render the strategy to get actual output
        rendered_audio = render_strategy(strategy, audio_data, sample_rate)
        # Score based on rendered output (with optional MERT)
        score = score_strategy(strategy, audio_data, sample_rate, original_length, rendered_audio, use_mert=use_mert)
        scored_strategies.append({
            'strategy': strategy,
            'score': score,
            'rendered_audio': rendered_audio
        })
        print(f"  {strategy.name}: {score['star_rating']:.1f}★ ({score['total_points']:.1f} points, {score['resulting_length']:.1f}s)")

    # Filter out excluded strategies if this is a regeneration
    if excluded_strategies:
        print(f"\nFiltering out {len(excluded_strategies)} previously shown strategies...")
        scored_strategies = [s for s in scored_strategies if s['strategy'].name not in excluded_strategies]
        print(f"Remaining candidates: {len(scored_strategies)}")

    # Hard filter: reject strategies that miss target by >25% (e.g., 60s target → reject >75s or <45s)
    # The user explicitly requested a target length - we shouldn't return wildly different results.
    # Use the larger of 15s or 25% of target as the max acceptable deviation.
    max_deviation = max(15.0, target_length * 0.25)
    print(f"\nFiltering strategies within ±{max_deviation:.1f}s of target ({target_length:.1f}s)...")

    on_target_strategies = [
        s for s in scored_strategies
        if abs(s['score']['resulting_length'] - target_length) <= max_deviation
    ]

    if on_target_strategies:
        print(f"  Kept {len(on_target_strategies)}/{len(scored_strategies)} on-target strategies")
        scored_strategies = on_target_strategies
    else:
        # No strategies hit target - keep all and sort by closeness to target
        print(f"  No strategies within tolerance - sorting all by closeness to target")
        scored_strategies.sort(key=lambda s: abs(s['score']['resulting_length'] - target_length))

    # Select top 3 strategies (with quality retry if needed)
    strategies, scores = retry_for_quality(
        scored_strategies, clusters, original_length, target_length,
        structure, audio_data, sample_rate, use_mert, regenerate_seed, mode,
        min_segment_duration
    )

    print(f"\n✨ Top {len(strategies)} strategies selected:")
    for i, (strategy, score) in enumerate(zip(strategies, scores)):
        marker = "★ BEST" if i == 0 else "      "
        print(f"  {marker}  {strategy.name} - {score['star_rating']:.1f}★")

    # Stage 6: Generate output for ALL top strategies
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
        output_filename = f"option_{i}_{stars:.1f}stars.wav"
        output_files.append(str(output_dir / output_filename))

    print("Pipeline complete!")

    return {
        'strategies': strategies,
        'scores': scores,
        'output_files': output_files,
        'processing_time': processing_time,
        'original_length': original_length,
        'all_strategy_names': [s['strategy'].name for s in scored_strategies[:5]]  # Track all 5 for exclusion
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

    parser.add_argument(
        '--use-mert',
        action='store_true',
        help='Use MERT embeddings for enhanced quality scoring (slower but better quality assessment)'
    )

    parser.add_argument(
        '--auto-protect',
        action='store_true',
        help='Enable automatic intro/outro protection (prevents cutting from first/last 10%% or 15s)'
    )

    parser.add_argument(
        '--min-segment-duration',
        type=float,
        default=10.0,
        help='Minimum segment duration for extension mode in seconds (default: 10.0)'
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
    print(f"Auto-protect intro/outro: {'Yes' if args.auto_protect else 'No'}")
    print(f"Output directory: {args.output_dir}")
    print(f"MERT embeddings: {'Enabled' if args.use_mert else 'Disabled'}")
    print("=" * 60)
    print("=" * 60 + "\n")

    try:
        # Track excluded strategies across regenerations
        excluded_strategies = []

        # Run initial pipeline
        result = run_pipeline(
            audio_path=args.input,
            target_length=args.target,
            protected_regions=args.protect,
            output_dir=args.output_dir,
            regenerate_seed=None,
            use_mert=args.use_mert,
            excluded_strategies=None,
            auto_protect=args.auto_protect,
            min_segment_duration=args.min_segment_duration
        )

        # Display results
        display_results(result)

        # Track shown strategies
        excluded_strategies.extend([s.name for s in result['strategies']])

        # Regeneration loop
        regenerate_count = 0
        while True:
            try:
                response = input("\nGenerate alternative options? (y/n): ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                # Non-interactive mode or user interrupt
                print("\nExiting.")
                break

            if response == 'y':
                regenerate_count += 1
                print(f"\nRegenerating with seed {regenerate_count}...\n")

                result = run_pipeline(
                    audio_path=args.input,
                    target_length=args.target,
                    protected_regions=args.protect,
                    output_dir=args.output_dir,
                    regenerate_seed=regenerate_count,
                    use_mert=args.use_mert,
                    excluded_strategies=excluded_strategies,
                    auto_protect=args.auto_protect,
                    min_segment_duration=args.min_segment_duration
                )

                display_results(result)

                # Track newly shown strategies
                excluded_strategies.extend([s.name for s in result['strategies']])

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
