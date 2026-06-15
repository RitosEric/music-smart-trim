"""Integration tests for complete pipeline."""

import pytest
from pathlib import Path
from src.cli import run_pipeline, parse_arguments
from src.audio_loader import AudioLoadError
import sys


def test_run_pipeline_end_to_end():
    """Test complete pipeline from load to output generation."""
    # Arrange
    fixture_path = Path("/Users/ericli/Documents/Projects/music-smart-trim/tests/fixtures/sample_30s.wav")
    target_length = 25.0
    protected_regions = []
    output_dir = Path("/tmp/music_smart_trim_test_output")

    # Act
    result = run_pipeline(
        audio_path=fixture_path,
        target_length=target_length,
        protected_regions=protected_regions,
        output_dir=output_dir,
        regenerate_seed=None
    )

    # Assert
    assert 'strategies' in result
    assert 'scores' in result
    assert 'output_files' in result
    assert 'processing_time' in result

    # Should have 3 strategies (conservative, balanced, aggressive)
    assert len(result['strategies']) == 3
    assert len(result['scores']) == 3

    # Check that at least one option has ≥4.5★
    star_ratings = [score['star_rating'] for score in result['scores']]
    assert any(rating >= 4.5 for rating in star_ratings), \
        f"Expected at least one option ≥4.5★, got {star_ratings}"

    # Check processing time is recorded
    assert result['processing_time'] > 0

    # Check output files were created
    assert output_dir.exists()
    assert (output_dir / "summary.json").exists()
    assert (output_dir / "summary.txt").exists()


def test_run_pipeline_with_protected_regions():
    """Test pipeline with protected regions."""
    # Arrange
    fixture_path = Path("/Users/ericli/Documents/Projects/music-smart-trim/tests/fixtures/sample_30s.wav")
    target_length = 25.0
    protected_regions = ["00:00-00:05", "00:25-00:30"]
    output_dir = Path("/tmp/music_smart_trim_test_protected")

    # Act
    result = run_pipeline(
        audio_path=fixture_path,
        target_length=target_length,
        protected_regions=protected_regions,
        output_dir=output_dir,
        regenerate_seed=None
    )

    # Assert
    assert len(result['strategies']) == 3
    assert any(score['star_rating'] >= 4.5 for score in result['scores'])


def test_run_pipeline_with_regenerate_seed():
    """Test pipeline with regeneration seed for variety."""
    # Arrange
    fixture_path = Path("/Users/ericli/Documents/Projects/music-smart-trim/tests/fixtures/sample_30s.wav")
    target_length = 25.0
    protected_regions = []
    output_dir = Path("/tmp/music_smart_trim_test_regen")

    # Act - run twice with different seeds
    result1 = run_pipeline(
        audio_path=fixture_path,
        target_length=target_length,
        protected_regions=protected_regions,
        output_dir=output_dir,
        regenerate_seed=1
    )

    result2 = run_pipeline(
        audio_path=fixture_path,
        target_length=target_length,
        protected_regions=protected_regions,
        output_dir=output_dir,
        regenerate_seed=2
    )

    # Assert - results should exist and have valid scores
    assert len(result1['strategies']) == 3
    assert len(result2['strategies']) == 3

    # Both should have at least one ≥4.5★
    assert any(score['star_rating'] >= 4.5 for score in result1['scores'])
    assert any(score['star_rating'] >= 4.5 for score in result2['scores'])


def test_run_pipeline_handles_audio_load_error():
    """Test pipeline handles AudioLoadError appropriately."""
    # Arrange
    nonexistent_path = Path("/nonexistent/file.wav")
    target_length = 25.0
    protected_regions = []
    output_dir = Path("/tmp/music_smart_trim_test_error")

    # Act & Assert
    with pytest.raises(AudioLoadError):
        run_pipeline(
            audio_path=nonexistent_path,
            target_length=target_length,
            protected_regions=protected_regions,
            output_dir=output_dir,
            regenerate_seed=None
        )


def test_parse_arguments_required_args():
    """Test argument parsing with required arguments."""
    # Arrange
    sys.argv = [
        'cli.py',
        '--input', '/path/to/audio.wav',
        '--target', '25.0'
    ]

    # Act
    args = parse_arguments()

    # Assert
    assert args.input == Path('/path/to/audio.wav')
    assert args.target == 25.0
    assert args.protect == []
    assert args.output_dir == Path('output')


def test_parse_arguments_all_args():
    """Test argument parsing with all arguments."""
    # Arrange
    sys.argv = [
        'cli.py',
        '--input', '/path/to/audio.wav',
        '--target', '30.5',
        '--protect', '00:00-00:10', '00:50-01:00',
        '--output-dir', '/custom/output'
    ]

    # Act
    args = parse_arguments()

    # Assert
    assert args.input == Path('/path/to/audio.wav')
    assert args.target == 30.5
    assert args.protect == ['00:00-00:10', '00:50-01:00']
    assert args.output_dir == Path('/custom/output')


def test_parse_arguments_missing_required():
    """Test argument parsing fails when required args are missing."""
    # Arrange
    sys.argv = ['cli.py', '--input', '/path/to/audio.wav']
    # Missing --target

    # Act & Assert
    with pytest.raises(SystemExit):
        parse_arguments()
