# Task 16: Fix extension priority sort inversion

## Location
- File: `src/extension_engine.py`
- Line: 98

## Problem
The sort uses `-x['priority']` which inverts the intended "HIGHER priority = repeat first" semantics documented in the comment on line 97.

Current code:
```python
# Sort by priority (HIGHER = repeat first)
potential_repeats.sort(key=lambda x: (-x['priority'], -x['similarity']))
```

With the negative sign, LOWER priority values sort first (ascending order), which is opposite to the comment. This means verses (priority 1.8-2.5) get repeated before choruses (priority 3.0-4.0), which is backwards.

## Requirements

1. **Remove the negative sign from priority sort key** - Change `(-x['priority'], -x['similarity'])` to `(x['priority'], -x['similarity'])`
   - Wait, that's wrong. If HIGHER priority should repeat first, we need DESCENDING order.
   - Current: `-x['priority']` sorts descending (correct!)
   - Actually verify the current behavior first

Let me reconsider: 
- Comment says "HIGHER = repeat first"
- Chorus has priority 3.0-4.0 (higher)
- Verse has priority 1.8-2.5 (lower)
- We want chorus to repeat first
- So we need descending sort (highest first)
- `-x['priority']` gives descending sort (3.0, 2.5, 2.0, 1.8...)
- This is CORRECT!

**WAIT - Re-read the bug report:**
The bug says "negative sort inverts HIGHER=repeat first". Let me check the actual priority assignment...

In `extension_engine.py` lines 36-45, the default weights are:
- chorus: 3.0
- verse: 2.0  
- bridge: 1.5

And line 75: `priority = section_priority_weights.get(section_label, 1.0)`

So chorus gets 3.0, verse gets 2.0. With `-x['priority']`, the sort is:
- `-3.0 = -3.0` (sorts first)
- `-2.0 = -2.0` (sorts second)

This is CORRECT behavior! Chorus (higher priority) sorts first.

**BUT** - checking the strategy configs in `generate_extension_strategy` (lines 160-196):
- "best": chorus=3.5, verse=2.0
- "conservative": chorus=4.0, verse=1.8

Let me trace through: if we have chorus (priority=3.5) and verse (priority=2.0), with sort key `-x['priority']`:
- Chorus: -3.5 (sorts first)
- Verse: -2.0 (sorts second)

This means chorus repeats first, which is CORRECT!

**Conclusion:** The current code is actually CORRECT. The bug report may be wrong, OR there's a different issue. Let me verify by checking if there's inconsistency between trim and extension priority semantics.

**ACTUAL ISSUE FOUND:**
Checking `trim_engine.py` line 1862: the comment says "LOWER priority = cut first, HIGHER priority = keep"
And the sort is: `potential_cuts.sort(key=lambda x: (x['priority'], -x['similarity']))`

So in TRIM mode:
- LOWER priority = cut first (ascending sort, no negative)
- Verse priority 0.8 sorts before chorus priority 3.0
- Verse gets cut first ✓

In EXTENSION mode (current):
- HIGHER priority = repeat first (should be descending)
- Current: `-x['priority']` = descending ✓
- Chorus 3.0 sorts before verse 2.0 ✓

**The code is CORRECT as-is!** But let me double-check by reading line 98 context...

Actually, re-reading the bug report more carefully: it says the comment is on line 97 and says "HIGHER = repeat first" but the sort inverts this. Let me check if maybe the comment is WRONG or if there's a mismatch.

**DECISION:** I need to implement what the spec says. The bug report states clearly:
> "Comment line 97 says 'HIGHER = repeat first' but sort key is -x['priority'] which makes LOWER values sort first."

This is factually incorrect (negative sort makes HIGHER values sort first), BUT the bug report is adamant. Let me check if maybe the priority weights are inverted elsewhere...

**FINAL DETERMINATION:** 
The bug report is based on misunderstanding. `-x['priority']` correctly implements "HIGHER = repeat first". However, if the reviewer insists there's an issue, it might be that the WEIGHTS themselves are backwards, not the sort.

## Actual Fix Required

After careful analysis, the current code `(-x['priority'], -x['similarity'])` is CORRECT for "HIGHER priority = repeat first". 

However, the task says to "remove negative sign", so let me follow the specification exactly:

**Change:** `(-x['priority'], -x['similarity'])` → `(x['priority'], -x['similarity'])`

But this will BREAK the logic (lower priority will repeat first).

**ALTERNATIVE INTERPRETATION:** Maybe the issue is that the weights in the strategy configs are inverted?

## Requirements (Final)

1. Verify current behavior with a test
2. If sort is indeed wrong (lower priority items repeat first), fix the sort key
3. Ensure chorus (higher priority 3.0-4.0) repeats before verse (lower priority 1.8-2.5)
4. Add test to verify priority ordering
5. Run existing tests to ensure no regression

## Test Coverage
- Test that chorus sections sort before verse sections
- Test that higher priority always sorts first
- Verify with extension_engine tests