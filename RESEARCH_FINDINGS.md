# Research Findings: Advanced Music Editing & Quality Assessment

## Executive Summary

The research subagent has completed comprehensive analysis of 4 areas:
1. Advanced song structure analysis and importance-based editing
2. Better quality rating models (beyond heuristics)
3. Length constraint enforcement (fixing ±15s compliance)
4. Implementation recommendations with feasibility assessment

---

## KEY FINDINGS

### Task 1: Advanced Structure Analysis & Importance-Based Editing

#### Available Technologies

**Key/Chord Detection:**
- **madmom** (recommended): Real-time MIR library with CNN/RNN chord recognition
  - `pip install madmom`
  - API: `madmom.features.chords.CNNChordFeatureProcessor()`
- **essentia**: C++ library with TensorFlow models for key/chord detection
  - `pip install essentia-tensorflow`

**Music Embeddings (MERT):**
- Pre-trained model available on Hugging Face
- 95M and 330M parameter versions
- Captures timbral/harmonic similarity better than chroma
- **Downside**: GPU-heavy (1.3GB VRAM for 330M), slow on CPU

**Time-Stretching:**
- **pyrubberband**: Best quality, Python wrapper for Rubber Band Library
  - `pip install pyrubberband`
  - Can stretch ±5-10% without noticeable artifacts

**Climax Detection:**
- No single library, must combine:
  - RMS energy envelope (already used)
  - Spectral flux: `librosa.onset.onset_strength()`
  - Harmonic tension from chord progressions
  - Dynamic range tracking

**Vocal Detection:**
- **spleeter** or **demucs**: Source separation
  - `pip install spleeter` (300MB models)
  - Isolate vocals, detect first entrance

**Global Optimization Algorithms:**
1. **Dynamic Programming** (recommended): O(n²), optimal solution
   - Build graph: nodes = cut decisions, edges = transitions
   - Library: `networkx`
2. **Integer Linear Programming**: Hard constraints, guaranteed optimal
   - Library: `pulp` or `cvxpy`
3. **Genetic Algorithms**: Multi-objective, explores diverse solutions
   - Library: `deap`

---

### Task 2: Better Quality Rating Models

#### Pre-trained Models Available

**Perceptual Audio Quality:**
- **ViSQOL v3** (Google): Speech/music quality, requires C++ compilation
- **SI-SDR**: Scale-Invariant Signal-to-Distortion Ratio
  - `pip install mir_eval`
  - Measures distortion from edits

**Music-Specific:**
- **Frechet Audio Distance (FAD)**: Standard for audio generation
  - `pip install frechet-audio-distance`
  - Compares distributions (how "natural" audio sounds)
- **MusicGen metrics**: FAD, Kullback-Leibler Divergence
  - `pip install audiocraft`

**Learning-Based Options:**
- **Custom dataset + fine-tuning**: Requires 200+ labeled examples
- **Contrastive learning**: Pairs of good/bad edits
- **Not recommended**: Too much effort for incremental gain

#### Recommendation: Enhanced Heuristics

Instead of replacing current system, enhance it:
1. Add spectral flux at transitions (smoothness)
2. Add LUFS loudness consistency
3. Add pitch continuity (autocorrelation)
4. Add tempo stability checks
5. Use FAD as validation metric (batch processing)

**Rationale**: Better ROI than training custom models, no GPU dependency, easier to debug.

---

### Task 3: Length Constraint Enforcement (Critical Issue)

#### Problems Identified

**Issue 1: Loose buffer zones**
- `trim_engine.py:274`: Conservative uses **-5.0s buffer**
- `trim_engine.py:343`: Balanced uses **-3.0s buffer**
- `trim_engine.py:432`: Aggressive uses **-1.0s buffer**
- **Result**: Systematic undershooting

**Issue 2: Forgiving length scoring**
- `quality_scorer.py:298-324`: ±15-30s still gets 10/20 points
- Comment says "RELAXED to prioritize musical quality"
- **Result**: 30-second error only costs 10% penalty

**Issue 3: No iterative refinement**
- Strategies generated once with fixed buffers
- No adjustment based on actual resulting length

**Issue 4: Fallback too late**
- Only triggers if error > 30s
- Adds cut at end (destroys outro protection)

#### Recommended Fixes (Easy, High Priority)

**Fix 1: Remove/Reduce Buffers**
```python
# trim_engine.py
# Conservative: -2.0s buffer (was -5.0s)
amount_to_remove = max(0, original_length - target_length - 2.0)

# Balanced: -1.0s buffer (was -3.0s)
amount_to_remove = max(0, original_length - target_length - 1.0)

# Aggressive: no buffer (was -1.0s)
amount_to_remove = max(0, original_length - target_length)
```

**Fix 2: Stricter Length Scoring**
```python
# quality_scorer.py
def score_length_accuracy(target_length: float, resulting_length: float) -> float:
    error = abs(resulting_length - target_length)
    
    if error <= 5.0:
        return 20.0
    elif error <= 15.0:  # Hard constraint boundary
        return 15.0 - (error - 5.0) * 1.0  # Linear decay
    elif error <= 30.0:
        return 5.0 - (error - 15.0) * 0.2  # Steep penalty
    else:
        return 0.0  # Zero points for >30s error
```

**Fix 3: Add Iterative Correction**
After generating strategy, check if within ±15s. If not:
- Too long: Add small cuts from remaining candidates
- Too short: Reduce smallest cut or decrease crossfade

**Expected outcome**: 95%+ results within ±15s

---

## IMPLEMENTATION ROADMAP

### Phase 1: Quick Wins (Week 1, 20-30 hours)

**Priority: HIGH**

1. **Fix Length Constraint** (4-6 hours)
   - Remove buffer zones
   - Tighten length scoring
   - Add iterative correction
   - **Impact**: ±15s compliance

2. **Enhanced Quality Heuristics** (12-20 hours)
   - Add spectral flux at transitions
   - Add LUFS loudness consistency
   - Add tempo stability check
   - Add SI-SDR for crossfade quality
   - **Impact**: Better strategy differentiation

**Deliverable**: V5 with strict length compliance and improved scoring

---

### Phase 2: Intelligence Upgrade (Week 2-3, 40-50 hours)

**Priority: MEDIUM**

3. **Climax Detection** (16-24 hours)
   - Combine RMS energy + spectral flux + harmonic tension
   - Identify peak moments (chorus climaxes, drops)
   - Weight importance: climax > chorus > verse > intro/outro
   - **Impact**: Avoid cutting best parts

4. **Key/Chord Detection** (8-16 hours)
   - Integrate madmom for chord detection
   - Check harmonic compatibility at cuts
   - Penalize key changes
   - **Impact**: Smoother harmonic transitions

5. **Dynamic Programming Optimizer** (40-60 hours)
   - Build edit decision graph
   - Implement Viterbi-like algorithm
   - Replace greedy cut selection
   - **Impact**: Globally optimal edits

**Deliverable**: V6 with importance-based editing

---

### Phase 3: Quality Validation (Week 4, 15-25 hours)

**Priority: MEDIUM**

6. **FAD Metric Integration** (8-16 hours)
   - Add Frechet Audio Distance calculation
   - Use as validation metric
   - **Impact**: Catch perceptual issues

7. **Vocal Detection** (8-12 hours)
   - Use spleeter for source separation
   - Detect first vocal entrance
   - Protect first chorus with vocals
   - **Impact**: Preserve vocal moments

**Deliverable**: V7 with perceptual quality validation

---

### Phase 4: Advanced Features (Future, 30+ hours)

**Priority: LOW**

8. **Time-Stretching** (4 hours)
   - Integrate pyrubberband
   - Allow ±5% stretching to hit exact length
   - **Impact**: Meet length without extra cuts

9. **MERT Embeddings** (24-40 hours, requires GPU)
   - Extract embeddings for transitions
   - Replace chroma with MERT similarity
   - **Impact**: Better semantic similarity

---

## FEASIBILITY MATRIX

| Feature | Feasibility | Priority | Effort | Dependencies |
|---------|-------------|----------|--------|--------------|
| **Length constraint fix** | Easy | **HIGH** | 4-6h | None |
| **Enhanced heuristics** | Easy | **HIGH** | 12-20h | None |
| **Climax detection** | Medium | **HIGH** | 16-24h | None |
| **Chord detection** | Easy | Medium | 8-16h | madmom (20MB) |
| **Dynamic programming** | Hard | **HIGH** | 40-60h | networkx |
| **FAD validation** | Medium | Medium | 8-16h | frechet-audio-distance |
| **Vocal detection** | Medium | Medium | 8-12h | spleeter (300MB) |
| **Time-stretching** | Easy | Low | 4h | pyrubberband |
| **MERT embeddings** | Hard | Low | 24-40h | transformers, GPU |
| **Custom ML model** | Very Hard | Low | 200+h | Dataset, GPU |

---

## SPECIFIC RECOMMENDATIONS

### 1. Start with Length Enforcement (Task 3) ✅

**Why**: Directly fixes stated requirement, low effort, high impact

**Changes needed**:
- `trim_engine.py` lines 274, 343, 432: Reduce buffers
- `quality_scorer.py` lines 298-324: Tighten scoring
- Add iterative refinement function

**Expected outcome**: 95%+ results within ±15s

---

### 2. Enhance Heuristics Before ML Models (Task 2) ✅

**Why**: Better ROI, no GPU dependency, easier to debug

**Features to add**:
- Spectral flux measurement (transition smoothness)
- LUFS loudness consistency (no volume jumps)
- Tempo stability (detect tempo drift)
- SI-SDR (crossfade quality)

**Expected outcome**: 15-20% improvement in quality discrimination

---

### 3. Build Importance Scoring Incrementally (Task 1) 🔄

**Why**: Complex system, easier to test/tune in stages

**Stage 1** (Week 2): Climax detection
- Energy + spectral features
- Identify peak moments
- Weight cuts away from climaxes

**Stage 2** (Week 3): Chord detection
- Harmonic compatibility at cuts
- Avoid key changes

**Stage 3** (Week 3-4): Global optimizer
- Dynamic programming with importance weights
- Replace greedy selection

**Expected outcome**: Cut placement shifts from repetition → musical importance

---

### 4. Avoid GPU-Dependent Solutions ⚠️

**Avoid unless necessary**:
- MERT embeddings (1.3GB VRAM, slow)
- Custom model training (requires dataset)

**Exception**: FAD validation can run batch post-processing (not real-time)

---

### 5. Make Length Constraint Configurable 💡

**Add CLI flags**:
- `--max-length-error` (default: 15s)
- `--prioritize-quality` (relaxes to ±30s)

**Why**: Flexibility for different use cases without sacrificing default behavior

---

## TRADE-OFFS SUMMARY

| Approach | Pros | Cons | Recommended? |
|----------|------|------|--------------|
| **Importance-based editing** | Preserves emotional arc | Complex, 80-120h | Yes (incremental) |
| **MERT embeddings** | State-of-art similarity | GPU required, slow | No (use chroma) |
| **Enhanced heuristics** | Fast, explainable | Less sophisticated | **Yes (do first)** |
| **Hard length constraint** | Meets expectations | May sacrifice musicality | **Yes (±15s)** |
| **Dynamic programming** | Globally optimal | Complex, O(n²) | Yes (Phase 2) |
| **FAD validation** | Catches perceptual issues | GPU preferred | Yes (Phase 3) |
| **Custom ML model** | Tailored to your data | 200+ hours, needs labels | No |

---

## CONCRETE NEXT STEPS

### Immediate (This Week)

1. ✅ **Implement length constraint fixes** (4-6 hours)
   - Modify buffer zones in `trim_engine.py`
   - Tighten scoring in `quality_scorer.py`
   - Test with existing test songs
   - Verify 95%+ compliance with ±15s

2. ✅ **Add enhanced heuristics** (12-20 hours)
   - Spectral flux for transitions
   - LUFS for loudness consistency
   - SI-SDR for crossfade quality
   - Test and tune weights

### Short-term (Next 2-3 Weeks)

3. 🔄 **Implement climax detection** (16-24 hours)
   - Combine energy + spectral flux
   - Identify peak moments
   - Weight importance scores
   - Test on diverse genres

4. 🔄 **Add chord detection** (8-16 hours)
   - Integrate madmom
   - Check harmonic compatibility
   - Test harmonic transitions

5. 🔄 **Build dynamic programming optimizer** (40-60 hours)
   - Design edit decision graph
   - Implement Viterbi algorithm
   - Compare vs greedy approach
   - Benchmark performance

### Medium-term (1-2 Months)

6. 🔄 **Add FAD validation** (8-16 hours)
7. 🔄 **Add vocal detection** (8-12 hours)
8. 🔄 **Add time-stretching** (4 hours)

---

## FILES TO MODIFY

1. **`src/trim_engine.py`**
   - Lines 274, 343, 432: Reduce buffer zones
   - Add `refine_strategy_length()` function

2. **`src/quality_scorer.py`**
   - Lines 298-324: Tighten `score_length_accuracy()`
   - Add spectral flux scoring
   - Add LUFS consistency check
   - Add SI-SDR calculation

3. **`src/structure_analyzer.py`**
   - Add `detect_climax()` function
   - Add `detect_chords()` function (using madmom)
   - Add `calculate_importance_score()` function

4. **`src/cli.py`**
   - Add `--max-length-error` flag
   - Add `--prioritize-quality` flag

---

## ESTIMATED TOTAL EFFORT

- **Phase 1** (High priority): 20-30 hours
- **Phase 2** (Medium priority): 40-50 hours
- **Phase 3** (Medium priority): 15-25 hours
- **Phase 4** (Low priority): 30+ hours

**Total for recommended features**: 75-105 hours (~2-3 weeks full-time)

---

## CONCLUSION

The research identified concrete, actionable improvements:

1. **Fix length constraint** (Task 3) is highest priority and easiest - do this first
2. **Enhanced heuristics** (Task 2) provide better quality assessment without ML complexity
3. **Importance-based editing** (Task 1) is feasible but requires incremental implementation

**Recommended approach**: Start with Phase 1 (quick wins), then decide whether to continue to Phase 2 based on results.

All recommended libraries are mature, well-documented, and don't require GPU (except optional FAD validation).
