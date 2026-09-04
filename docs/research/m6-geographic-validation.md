# M6 Geographic Validation — Frozen M5 Adapted DA-V2-Small

**Date:** 2026-09-04
**Author:** Shravan (ML)
**Branch:** `feat/shravan-m5-geographic-validation`
**Experiment:** `experiments/m6-geographic-eval`
**M5 Reference:** `experiments/dav2-gamus-head-m5-e01` (epoch 23, val MAE 5.1500 m)

---

## 1. Scientific Question

> Does the M5 adapted DA-V2-Small model (frozen backbone + 23k-param head, 30 epochs) generalize across geographic regions, or is its performance driven by within-city similarity?

M5 trained on 24 DC tiles only. M5 validation used 8 DC tiles. This evaluation tests geographic transfer to PHL (val+test) and NYC (test) — cities seen in the full GAMUS training set but **not** in the M5 training subset.

---

## 2. M5 Reference (Frozen Baseline)

| Metric | Value |
|--------|-------|
| Val MAE (DC) | 5.1500 m |
| Val RMSE | 7.3685 m |
| Pearson | 0.631 |
| Spearman | 0.586 |
| Best epoch | 23 / 30 |
| Train tiles | 24 (DC only) |
| Val tiles | 8 (DC only) |

Checkpoint: `experiments/dav2-gamus-head-m5-e01/checkpoints/best.pt` (epoch 23, frozen)

---

## 3. Evaluation Protocol

- **Model:** Frozen M5 (DA-V2-Small backbone + 23k head, epoch 23 checkpoint)
- **Manifest:** `manifests/gamus.m6.geographic.json` (142 records)
- **Splits evaluated:** `val` + `test`
- **Cities:** DC (18), NYC (50), PHL (50) — 118 tiles total
- **Mask:** finite prediction AND finite target (negatives kept, no clipping)
- **Metrics:** MAE, RMSE, median, p90, p95, Pearson, Spearman, per-class, height bins
- **No training, no fine-tuning, no target normalization**
- **M5 checkpoint:** byte-identical before/after evaluation (verified)

---

## 4. City Distribution

| City | Train | Val | Test | Total |
|------|-------|-----|------|-------|
| DC   | 24    | 8   | 10   | 42    |
| PHL  | 0     | 30  | 20   | 50    |
| NYC  | 0     | 0   | 50   | 50    |
| **Total** | **24** | **38** | **80** | **142** |

> **Critical:** M5 training subset was DC-only (24 tiles). PHL and NYC tiles were **never seen** by M5 during training. NYC is absent from the M5 validation split entirely.

---

## 5. Results

### 5.1 Overall Metrics (Direct Meters)

| Metric | Value |
|--------|-------|
| **Macro MAE** (city avg) | **5.018 m** |
| **Micro MAE** (pixel-weighted) | **4.949 m** |
| **In-city MAE** (DC) | **5.272 m** |
| **Cross-city MAE** (NYC+PHL) | **4.890 m** |
| **Generalization Gap** | **−0.382 m** |

> **Key finding:** Cross-city MAE (4.89 m) is **lower** than in-city DC MAE (5.27 m). The generalization gap is **negative** — cross-city performance is better than within-city on this evaluation set.

### 5.2 Per-City Results

| City | Samples | MAE (m) | RMSE (m) | Pearson | Spearman | Best In |
|------|---------|---------|----------|---------|----------|---------|
| **DC** (in-city) | 18 | **5.272** | 7.608 | 0.582 | 0.551 | — |
| **PHL** (cross) | 50 | **3.957** | 6.139 | 0.193 | 0.285 | — |
| **NYC** (cross) | 50 | **5.824** | 8.025 | 0.227 | 0.279 | — |

> **Surprising:** PHL (cross-city) achieves **lower MAE (3.96 m)** than DC (in-city, 5.27 m). NYC is the outlier with highest error.

---

## 6. Height-Bin Analysis (Per City)

| Bin | DC MAE | NYC MAE | PHL MAE |
|-----|--------|---------|---------|
| 0–1 m | 3.25 | 4.88 | **3.17** |
| 1–5 m | 3.30 | 5.02 | 4.44 |
| 5–10 m | 3.46 | 4.83 | 4.76 |
| 10–20 m | 6.99 | 7.56 | 6.81 |
| 20–30 m | 11.78 | 14.92 | 14.80 |
| 30+ m | 16.94 | 29.49 | 29.81 |

> **Key observations:**
> - Low-height bins (0–5 m): PHL best, NYC worst
> - 20–30 m: PHL ~ DC (~14.8 vs 11.8), NYC worse
> - 30+ m: All cities struggle; NYC/PHL ~29 m vs DC ~17 m
> - NYC 30+ m has only 636 pixels (statistically fragile)

---

## 7. Per-Class Analysis

| Class | DC MAE | NYC MAE | PHL MAE | Notes |
|-------|--------|---------|---------|-------|
| ground | 3.20 | 3.64 | **2.46** | Best class everywhere |
| low vegetation | 3.96 | 6.55 | 3.54 | NYC high |
| road | 4.21 | 3.64 | **2.30** | PHL best |
| buildings | 3.86 | 4.04 | 4.84 | DC best |
| others | 3.98 | 2.72 | 5.28 | NYC dominant (11.4M px) |
| tree | 8.00 | 7.66 | **6.94** | PHL best, all high |
| water | 9.46 | 7.65 | 5.88 | PHL best |

> **Notable:**
> - PHL dominates on ground, road, water, tree
> - NYC "others" class dominates pixel count (11.4M px) with low MAE (2.72)
> - Trees consistently hardest class across all cities

---

## 8. Residual Analysis

| City | Mean Residual | Std | p5 | p95 |
|------|---------------|-----|-----|-----|
| DC | −3.67 m | 7.67 | −20.1 | +5.5 |
| NYC | −1.86 m | 7.38 | −18.2 | +8.1 |
| PHL | +0.42 m | 6.53 | −12.3 | +9.8 |

> **DC:** Strong systematic under-prediction (−3.67 m bias)
> **PHL:** Near-zero mean bias, tightest std
> **NYC:** Moderate under-prediction, high variance

---

## 9. Comparison with M5 Baseline (Same-City DC Val)

| Metric | M5 (DC val, 8 tiles) | M6 DC (18 tiles) | M6 Cross-city Avg |
|--------|----------------------|-------------------|-------------------|
| MAE | 5.150 m | 5.272 m | 4.890 m |
| RMSE | 7.369 m | 7.608 m | 7.082 m |
| Pearson | 0.631 | 0.582 | 0.210 |
| Spearman | 0.586 | 0.551 | 0.282 |

> M6 DC performance slightly worse than M5 (different sample set, more tiles). Cross-city macro avg better than M5's DC result — but semantics differ (see §11).

---

## 10. Generalization Assessment

| Outcome | Evidence |
|---------|----------|
| **Cross-city transfer: MODERATE** | Cross-city MAE (4.89) close to in-city (5.27); PHL outperforms DC |
| **Geographic gap: NEGATIVE** | Cross-city avg MAE **lower** than in-city (gap = −0.38 m) |
| **True held-out city: NONE** | All eval cities (DC, NYC, PHL) appear in full GAMUS train set |
| **NYC is outlier** | Highest MAE (5.82), lowest correlations, 30+m MAE = 29.5 m |

> **No true held-out-city evaluation possible** — all test cities (DC, NYC, PHL) appear in full GAMUS training set. The M5 training subset (24 DC tiles) did not include PHL or NYC, making them "effectively held-out" for the M5 model.

---

## 11. Limitations & Caveats

1. **No true held-out city** — All evaluation cities appear in full GAMUS train split. Geographic leakage cannot be ruled out.
2. **DC-dominated M5 training** — M5 saw only 24 DC tiles. Generalization measured is "from DC to {PHL, NYC}", not "from diverse train to held-out city".
3. **Sample size** — NYC 30+m bin has only 636 pixels (statistically unreliable).
4. **City bias** — PHL val (30) + test (20) = 50 samples; NYC test only (50); DC test (10) + val (8) = 18. Imbalanced.
5. **M5 train subset bias** — M5 trained on 24 DC tiles only. Full GAMUS train has 1439 DC, 1167 NYC, 2398 PHL. M5 is a DC specialist.
6. **Semantic difference** — M5 val MAE uses per-image affine alignment; M6 uses direct meters. Not apples-to-apples.

---

## 12. Outcome Classification

**Outcome B — Moderate geographic degradation (with caveats)**

- Cross-city MAE (4.89) is close to in-city (5.27) — gap = −0.38 m
- PHL outperforms DC significantly (3.96 vs 5.27 MAE)
- NYC degrades noticeably (5.82 vs 5.27, +10%)
- Correlations drop substantially cross-city (Pearson 0.58 → 0.21)

> The negative macro gap is driven by PHL's strong performance, not universal generalization.

---

## 12. Geographic Generalization Status

> **Geographic generalization: PARTIALLY DEMONSTRATED, NOT PROVEN**

- PHL transfers well from DC (better than DC itself)
- NYC degrades moderately
- No true held-out city available in GAMUS splits
- **Cannot claim geographic generalization proven**

---

## 13. Next Experiment (Per Decision Tree)

> **Outcome B → Next: Train-set-only target normalization experiment** (to address tall-tail error and low-bin regression), OR geographic training diversity experiment.

Per §43 one-factor-at-a-time rule: next experiment changes ONE factor only.

---

## 14. Reproducibility

```bash
pip install -e ".[dev]" && pip install -e ".[dav2]"
PYTHONPATH=src:<pinned-DA-V2-clone @ a561b84> python -m depthwizard.experiments.m6_geographic \
  --manifest manifests/gamus.m6.geographic.json \
  --base-checkpoint checkpoints/depth_anything_v2_vits.pth \
  --adapt-checkpoint experiments/dav2-gamus-head-m5-e01/checkpoints/best.pt \
  --output experiments/m6-geographic-eval --visuals
python -m pytest -q
```

- M5 checkpoint: byte-identical pre/post evaluation (verified)
- No training, no fine-tuning, no target normalization
- Geographic manifest: `manifests/gamus.m6.geographic.json`
- Results: `experiments/m6-geographic-eval/results.json`

---

## 15. Artifacts

- `experiments/m6-geographic-eval/config.json`
- `experiments/m6-geographic-eval/results.json`
- `experiments/m6-geographic-eval/README.md`
- `outputs/m6-geographic/*.png` (diagnostic visuals, git-ignored)
- `manifests/gamus.m6.geographic.json` (geographic manifest)
- `docs/research/m6-geographic-validation.md` (this document)
- `tests/test_m6_geographic.py` (12 tests, all passing)

---

**Prepared by:** Shravan (ML)  
**Date:** 2026-09-04  
**Branch:** `feat/shravan-m5-geographic-validation`  
**Commit:** (pending)