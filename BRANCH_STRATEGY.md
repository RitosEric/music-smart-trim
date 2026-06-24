# Branch Structure and Iteration Strategy

## Current Branch Overview

### 1. `main` branch
- **Status:** Stable, proven trim engine
- **Content:** Core CLI tool with original trim logic
- **Performance:** Works best in real-world scenarios (per user feedback)
- **Last commit:** `505688c` - docs: simplify README for demo project

### 2. `feature/web-ui` branch
- **Status:** Experimental section-aware convergence
- **Content:** 
  - Complete web UI/UX (React + Tailwind)
  - Modified trim engine with section-aware convergence
  - Reduced cut counts (max_cuts enforcement)
  - Increased tolerance (CONVERGE_TOL = 6.0s)
- **Test results:** 37/37 tests passing, 80-100% section alignment
- **Issue:** Real-world performance worse than main branch
- **Last commit:** `9030154` - feat: experimental section-aware convergence with reduced cuts

### 3. `feature/web-ui-main-engine` branch ⭐ **CURRENT**
- **Status:** Active development base - BEST OF BOTH
- **Content:**
  - ✅ Proven trim engine from `main` branch
  - ✅ Modern web UI/UX from `feature/web-ui` branch
  - ✅ All frontend features (WebSocket, waveform, recent uploads)
  - ✅ Flask API with async processing
- **Strategy:** Iterate on this stable foundation
- **Last commit:** `391335b` - feat: integrate web UI with main branch engine

## Iteration Strategy

### Phase 1: Baseline Validation ✅ **COMPLETE**
- [x] Create new branch from main
- [x] Integrate web UI from feature/web-ui
- [x] Commit baseline with stable engine
- **Result:** Clean slate with best-performing engine + modern UI

### Phase 2: Incremental Engine Improvements (Next Steps)
Start from the proven `main` engine and make **small, targeted improvements**:

1. **Test real files first** - Always validate against `/Users/ericli/Downloads/ex/`
2. **One change at a time** - Make small commits, test each change
3. **TDD approach** - Write failing test → fix → verify
4. **Compare against main** - Keep main branch output as baseline

### Key Learnings from feature/web-ui Experiments

**What worked:**
- ✅ Section-aware convergence concept (align cuts to section boundaries)
- ✅ Exact section boundaries (not inward-adjusted)
- ✅ Soft max_cuts preference in initial generation
- ✅ Increased tolerance reduces small filler cuts

**What didn't work:**
- ❌ Hard max_cuts enforcement (broke legitimate scenarios)
- ❌ Tolerance too high (10s) - lost strategy diversity
- ❌ Changing too many things at once - hard to isolate root cause

**Optimal values found:**
- CONVERGE_TOL: 6.0s (balance between cuts and accuracy)
- max_cuts: 2 per strategy (soft preference, not enforced)
- Section alignment: Try first, fallback to downbeat

## Recommended Next Steps

### 1. Baseline Testing
```bash
# Test current main engine performance
python -m src.cli --input "/Users/ericli/Downloads/ex/One Direction - What Makes You Beautiful.mp3" --target 120

# Document current behavior:
# - How many cuts?
# - Are they section-aligned?
# - What's the length accuracy?
```

### 2. Small Targeted Improvements
Consider these incremental changes (one at a time):

**Option A: Section-aware convergence only**
- Add sections parameter to `_converge_to_length()`
- Try section alignment before downbeat
- Keep all other logic identical
- Test: Does this improve section alignment without breaking length accuracy?

**Option B: Slightly increase tolerance**
- Change CONVERGE_TOL from 2.5s → 4.0s (small step)
- Test: Does this reduce filler cuts while maintaining diversity?

**Option C: Exact section boundaries**
- Modify `align_to_section_boundaries()` to use exact edges
- Test: Does this improve musical flow without breaking tests?

### 3. Always Compare
For each change:
```bash
# Before change
python -m src.cli --input "test.mp3" --target 120 > before.txt

# After change  
python -m src.cli --input "test.mp3" --target 120 > after.txt

# Compare
diff before.txt after.txt
```

### 4. Maintain Test Coverage
```bash
# After each change
python -m pytest tests/ -v

# Must pass all tests before committing
```

## File Organization

### Documentation from Experiments (Reference Only)
The following files document the experimental approach but are **NOT part of the current branch**:
- `COMPLETE_IMPLEMENTATION_SUMMARY.md`
- `SECTION_AWARE_CONVERGENCE.md`
- `TDD_CUT_REDUCTION_SUMMARY.md`
- `ROOT_CAUSE_FINAL.md`

These are valuable for understanding what was tried but should not be used as the implementation guide going forward.

### Current Branch Structure
```
feature/web-ui-main-engine/
├── src/
│   ├── trim_engine.py        ← MAIN BRANCH VERSION (proven)
│   ├── extension_engine.py   ← MAIN BRANCH VERSION
│   ├── cli.py                ← MAIN BRANCH VERSION
│   └── ...
├── frontend/                 ← FROM feature/web-ui (modern UI)
│   ├── src/
│   │   ├── components/
│   │   ├── services/
│   │   └── ...
│   └── ...
├── api/                      ← FROM feature/web-ui (Flask backend)
│   ├── app.py
│   ├── processing.py
│   ├── routes.py
│   └── ...
└── tests/                    ← MAIN BRANCH VERSION
```

## Success Criteria

For each improvement iteration:

1. **Must maintain:** All existing tests pass
2. **Must improve:** At least one of:
   - Fewer cuts (2-3 instead of 3-4)
   - Better section alignment (more cuts at boundaries)
   - Better musical quality (user feedback)
3. **Must not regress:** Real-world file performance
4. **Must document:** Clear commit message explaining change and results

## Quick Reference

### Switch between branches
```bash
# Work on new integrated branch (current)
git checkout feature/web-ui-main-engine

# Reference experimental changes
git checkout feature/web-ui

# Reference original stable engine
git checkout main
```

### Test suite
```bash
# Run all tests
python -m pytest tests/ -v

# Test specific file
python -m pytest tests/test_trim_engine.py -v
```

### Real-world validation
```bash
# Process real audio file
python -m src.cli --input "/Users/ericli/Downloads/ex/[filename].mp3" --target 120
```

---

**Current Status:** On `feature/web-ui-main-engine` branch with stable main engine + modern web UI
**Ready for:** Incremental, test-driven improvements
**Strategy:** Small changes, always compare against baseline, maintain test coverage
