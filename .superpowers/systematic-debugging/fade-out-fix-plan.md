# Fade-Out Bug Fix Plan

## Root Cause (Confirmed)
Double fade-out: Original song outro naturally fades (238-255s: -16dB → -60dB), then code applies ANOTHER fade (311-312.5s: additional -27dB drop), creating abrupt drops.

## Phase 2: Pattern Analysis

### Working Examples
1. **Trim mode** (`apply_cuts()`): Applies fade-out to final segment - CORRECT behavior
   - Final segment is a CUT piece that needs smooth ending
   - No natural fade exists

2. **Extension mode natural fade**: Original outro (248-255s) fades smoothly
   - Natural musical fade over 7 seconds
   - Should be PRESERVED, not doubled

### The Difference
- **Trim mode final segment**: Cut from middle of song → needs artificial fade
- **Extension mode final segment**: Original outro → already has natural fade

## Phase 3: Hypothesis

**Hypothesis**: The fade-out should only be applied when:
1. The final segment is from a CUT (trim mode), OR
2. The final segment does NOT already have a natural fade-out

**Test**: Check if last 2 seconds of final segment is already decreasing in energy before applying fade

## Phase 4: Implementation Options

### Option A: Detect Natural Fade (RECOMMENDED)
```python
def has_natural_fadeout(audio_segment, sr, threshold_db=6.0):
    """Check if audio already has natural fade-out in last 2s."""
    if len(audio_segment) < 2 * sr:
        return False
    
    last_2s = audio_segment[-int(2*sr):]
    first_1s_rms = np.sqrt(np.mean(last_2s[:sr]**2))
    last_1s_rms = np.sqrt(np.mean(last_2s[sr:]**2))
    
    if last_1s_rms < 1e-6:  # Already silent
        return True
    
    db_drop = 20 * np.log10((first_1s_rms + 1e-10) / (last_1s_rms + 1e-10))
    return db_drop > threshold_db  # >6dB drop = natural fade

# In apply_loops():
if last_end < len(audio):
    final_segment = audio[last_end:]
    
    # Only apply fade if not already fading
    if not has_natural_fadeout(final_segment, sr):
        fade_out_duration = min(crossfade_samples, len(final_segment) // 2)
        final_segment = apply_smooth_fade_out(final_segment, fade_out_duration)
```

### Option B: Shorter Fade (500ms → 50ms)
- Apply very short fade (50ms) to prevent clicks only
- Don't interfere with musical fade
- Simpler but less elegant

### Option C: Mode-Aware Fade
- Track whether we're in trim or extension mode
- Only apply fade in trim mode
- Problem: Needs mode passed through multiple functions

## Recommendation
**Option A** - Smart detection of natural fades. Benefits:
- Works for both trim and extension modes
- Handles various song endings (fade, abrupt, sustained)
- No mode tracking needed
- Preserves musical intent

## Test Plan
1. Create test with audio that has natural fade-out
2. Create test with audio that has abrupt ending
3. Verify fade applied only when needed
4. Test with both trim and extension modes
