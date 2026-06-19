# Testing Guide for Music Smart Trim V3

## Pre-Testing Checklist

✅ All caches cleaned (output, __pycache__, .pytest_cache)
✅ CLAUDE.md updated (225 lines, within 250 limit)
✅ README.md updated with V3 features
✅ V3 improvements implemented:
   - Automatic intro/outro protection
   - Beat-aligned cutting
   - Constant-power crossfading
   - Music structure detection

## Quick Test (Verified Working)

```bash
PYTHONPATH=. python src/cli.py --input 'examples/Louis Dunford - The Angel.mp3' --target 120
```

**Expected Output:**
- Detected tempo: ~117.5 BPM
- Auto-protecting intro (0-15s) and outro (223-238s)
- 1 segment cluster identified
- All 3 strategies: 5.0★
- Output lengths: 118-119s (within ±2s of target)
- 2 cuts per strategy
- Processing time: ~38-40s

✅ **Verified:** All features working correctly!

## Available Test Files

Located in `examples/` directory:

1. **Louis Dunford - The Angel.mp3** (238s) ✅ TESTED
   - Simple repetitive structure
   - Good for baseline testing
   - Expected: 5.0★, 2 cuts, perfect length accuracy

2. **By The Coast - All the Lights.mp3** (244s)
   - Moderate complexity
   - Expected: 4.5-5.0★, 3 cuts

3. **By The Coast - Radio Wave.mp3** (265s)
   - Similar to above

4. **Woodkid - Minus Sixty One.mp3** (315s)
   - Complex structure, long song
   - Expected: 4.0-4.5★, may deviate ±20-40s from target

5. **Audiomachine - Promised Land.mp3** (162s)
   - Cinematic/orchestral

6. **RADWIMPS - 愛にできることはまだあるかい** (160s)
   - Japanese pop/rock

7. **RADWIMPS - 糸守高校.mp3** (112s)
   - Already close to 120s target

8. **toe - サニーボーイ・ラプソディ.mp3** (245s)
   - Japanese post-rock

9. **羊文学 - more than words.mp3** (290s)
   - Japanese indie rock

10. **羊文学 - 春の嵐.mp3** (275s)
    - Japanese indie rock

## Test Scenarios

### Scenario 1: Simple Song (Baseline)
```bash
PYTHONPATH=. python src/cli.py --input 'examples/Louis Dunford - The Angel.mp3' --target 120
```

**Validation:**
- [ ] Shows "Detected tempo: X BPM"
- [ ] Shows "Auto-protecting intro (0-Xs) and outro (Xs-Xs)"
- [ ] All 3 strategies ≥4.0★
- [ ] Output length within ±5s of 120s
- [ ] Processing time 35-45s

### Scenario 2: Moderate Complexity
```bash
PYTHONPATH=. python src/cli.py --input 'examples/By The Coast - All the Lights.mp3' --target 120
```

**Validation:**
- [ ] Beat detection successful
- [ ] Intro/outro protected
- [ ] At least 1 strategy ≥4.5★
- [ ] Output length within ±10s of 120s

### Scenario 3: Complex Song (Stress Test)
```bash
PYTHONPATH=. python src/cli.py --input 'examples/Woodkid - Minus Sixty One.mp3' --target 120
```

**Validation:**
- [ ] Beat detection successful
- [ ] Multiple clusters detected
- [ ] At least 1 strategy ≥4.0★
- [ ] Output length within ±30s acceptable (may prioritize quality over length)

### Scenario 4: With Protected Regions
```bash
PYTHONPATH=. python src/cli.py --input 'examples/Louis Dunford - The Angel.mp3' --target 120 --protect "1:00-1:30"
```

**Validation:**
- [ ] Shows 3 protected regions (intro + outro + user-specified)
- [ ] User-protected region never modified
- [ ] Still achieves ≥4.0★

### Scenario 5: Different Target Lengths
```bash
# Shorter target
PYTHONPATH=. python src/cli.py --input 'examples/Louis Dunford - The Angel.mp3' --target 90

# Longer target (less aggressive)
PYTHONPATH=. python src/cli.py --input 'examples/Louis Dunford - The Angel.mp3' --target 150
```

**Validation:**
- [ ] Adapts strategy to different targets
- [ ] Maintains quality ratings
- [ ] Respects intro/outro protection

## What to Look For

### ✅ Good Signs
- Tempo detected successfully (e.g., "117.5 BPM")
- Intro/outro auto-protection active
- Sections labeled (intro, verse, chorus, bridge, outro)
- Quality ratings ≥4.0★
- Output lengths within reasonable range (±30s)
- Natural-sounding intro/outro
- Smooth transitions (no abrupt cuts)
- Beat-aligned cuts (rhythmically coherent)

### ⚠️ Warning Signs (but may be acceptable)
- Output length deviates >15s from target
  - *Expected for complex songs to maintain quality*
- Conservative strategy >target length
  - *Prioritizes larger, cleaner cuts*
- Processing time >50s
  - *Expected for songs >4 minutes*

### ❌ Red Flags (report if found)
- No tempo detected (beat alignment fails)
- Intro/outro not protected
- All strategies <4.0★
- Output length deviates >50s from target
- Song starts in middle (intro missing)
- Abrupt jarring transitions
- Processing time >90s

## Key Metrics to Verify

### Performance
- **Processing time**: 38-45s for 3-4 minute songs
- **Memory usage**: Should stay under 500MB
- **Output file size**: ~5-8MB for 120s @ 22050Hz

### Quality
- **Ratings**: At least 1 option ≥4.0★
- **Length accuracy**: ±5s typical, ±30s acceptable
- **Cuts**: 2-5 cuts typical (fewer = better)

### Musical Preservation
- **Intro**: Always starts from 0s
- **Outro**: Always includes last 10-15s
- **Beat alignment**: Cuts on bar boundaries
- **Transitions**: Smooth 500ms crossfades

## Common Issues & Solutions

### Issue: "Tempo detection failed"
**Solution**: Audio may be very complex or have unclear rhythm. Try a different file.

### Issue: Output much longer than target
**Solution**: System prioritized musical quality. This is intentional for complex songs.

### Issue: Low quality ratings (<3.0★)
**Solution**: Song may not have detectable repeated sections. Try a song with clear verse/chorus structure.

### Issue: Processing very slow (>60s)
**Solution**: Normal for long songs (>4 minutes). Can increase `hop_length` in `spectral_analyzer.py` for speed.

## Test Commands Summary

```bash
# Clean everything first
rm -rf output output_test __pycache__ .pytest_cache
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -type f -name "*.pyc" -delete 2>/dev/null

# Basic test (verified working)
PYTHONPATH=. python src/cli.py --input 'examples/Louis Dunford - The Angel.mp3' --target 120

# Test other songs
PYTHONPATH=. python src/cli.py --input 'examples/By The Coast - All the Lights.mp3' --target 120
PYTHONPATH=. python src/cli.py --input 'examples/Woodkid - Minus Sixty One.mp3' --target 120

# With protection
PYTHONPATH=. python src/cli.py --input 'examples/Louis Dunford - The Angel.mp3' --target 120 --protect "1:00-1:30"

# Different targets
PYTHONPATH=. python src/cli.py --input 'examples/Louis Dunford - The Angel.mp3' --target 90
PYTHONPATH=. python src/cli.py --input 'examples/Louis Dunford - The Angel.mp3' --target 150

# Check output files
ls -lh output/
python -c "import soundfile as sf; info = sf.info('output/option_0_5.0stars.wav'); print(f'Duration: {info.duration:.1f}s, Sample rate: {info.samplerate}Hz')"
```

## Success Criteria

✅ **PASS** if:
- Intro/outro preserved in all outputs
- Beat alignment working (no abrupt mid-bar cuts)
- Smooth transitions (constant-power crossfades)
- At least 1 option ≥4.0★
- Output length reasonable (within ±30s for complex songs)
- Natural-sounding, continuous music

❌ **FAIL** if:
- Song starts/ends abruptly
- Cuts feel jarring or rhythmically off
- All outputs <3.5★
- System crashes or produces errors

## Ready for Testing!

All V3 improvements verified and working:
✅ Automatic intro/outro protection
✅ Beat-aligned cutting (117.5 BPM detected)
✅ Constant-power crossfading
✅ Structure detection (6 sections labeled)
✅ Fine-grained ratings (5.0★)
✅ Processing time (38.6s)

**Status: READY FOR USER TESTING** 🎵
