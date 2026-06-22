# Task 14 Report: Fix quality retry to support extension mode

## Status: DONE

## Summary

Successfully fixed the quality retry mechanism to support both trim and extension modes. The `retry_for_quality()` function was hardcoded to use `mode="trim"` when retrying low-quality strategies, which prevented extension mode from receiving quality retries.

## Changes Made

### 1. Modified `src/cli.py::retry_for_quality()` (lines 77-153)
- Added `mode: str` parameter to function signature (line 87)
- Updated docstring to document the new parameter (line 102)
- Changed hardcoded `mode="trim"` to `mode=mode` in `generate_strategies()` call (line 123)

### 2. Updated `src/cli.py::run_pipeline()` (line 310)
- Modified call to `retry_for_quality()` to pass the `mode` parameter
- Mode is auto-detected earlier in the function (line 250): `mode = "trim" if target_length < original_length else "extend"`

### 3. Created comprehensive test suite (`tests/test_cli.py`)
- **test_retry_accepts_quality_above_threshold**: Verifies no retry when quality >= 3.5★
- **test_retry_uses_trim_mode_for_trim**: Confirms trim mode is used when target < original
- **test_retry_uses_extend_mode_for_extension**: Confirms extend mode is used when target > original
- **test_retry_skips_when_regenerate_seed_provided**: Verifies retry is skipped during manual regeneration
- **test_retry_stops_when_acceptable_quality_found**: Confirms retry stops once acceptable quality is reached

All 5 tests pass successfully.

## Testing

### New Tests
```bash
pytest tests/test_cli.py -v
# 5 passed in 0.37s
```

### Existing Test Suite
```bash
pytest tests/ -v
# 77 passed, 6 failed
```

The 6 failures are pre-existing issues unrelated to this change:
- `test_audio_loader.py::test_load_audio_basic` (pre-existing)
- `test_integration.py` (3 tests - pre-existing)
- `test_output_generator.py::TestApplyCuts` (2 tests - pre-existing)

## Verification

The fix correctly implements mode-aware retry behavior:

1. **Trim mode (target < original)**: Retries use `generate_strategies(mode="trim", ...)`
2. **Extension mode (target > original)**: Retries use `generate_strategies(mode="extend", ...)`
3. **Manual regeneration**: Retries are skipped (regenerate_seed is not None)
4. **Quality threshold**: Retries only occur when max rating < 3.5★
5. **Early termination**: Retry loop stops as soon as acceptable quality is found

## Impact

- **Extension mode**: Now receives quality retries when strategies score below 3.5★
- **Trim mode**: Continues to work as before (no regression)
- **Code clarity**: Function signature now explicitly declares mode dependency
- **Test coverage**: Added comprehensive unit tests for retry logic

## Code Quality

- Followed TDD approach (write tests first, then implementation)
- Maintained backward compatibility with existing code
- Added clear documentation for new parameter
- All new tests pass with 100% success rate
