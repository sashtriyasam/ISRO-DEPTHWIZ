# M7 Target Normalization Experiment — Frozen M5 Adaptation with Z-Score Targets

**Date:** 2026-09-04
**Author:** Shravan (ML)
**Branch:** `feat/shravan-dav2-target-normalization`
**Experiment:** `experiments/dav2-gamus-head-m7-targetnorm-e01`
**M5 Reference:** `experiments/dav2-gamus-head-m5-e01` (epoch 23, val MAE 5.1500 m)

---

## 1. Hypothesis

M5 established a strong frozen DA-V2-Small + lightweight head baseline with 30 epochs of training on raw GAMUS nDSM/AGL meters. The long-tailed height distribution (heavy ground/low-vegetation pixels, sparse tall structures) may benefit from z-score target normalization, which reweights the loss to balance contributions across the height range.

**Single-factor change:** Target normalization only (`raw` → `zscore`). All other factors frozen to M5.

---

## 2. M5 Frozen Baseline (Unchanged)

| Component | Setting |
|-----------|---------|
| Backbone | Depth Anything V2 Small (frozen) |
| Checkpoint | `depth-anything/Depth-Anything-V2-Small` @ `03876f86` (Apache-2.0) |
| Feature tap | `depth_head.scratch.output_conv1` input (1×64×296×296) |
| Head | Conv 64→32→16→1 + bilinear upsample |
| Trainable params | ~23,201 |
| Loss | Masked L1 |
| Optimizer | Adam, lr=1e-3, wd=0 |
| Epochs | 30 |
| Seed | 0 |
| Augmentation | None |
| Train subset | 24 DC tiles (manifest `gamus.m4.manifest.json`) |
| Val subset | 8 DC tiles (same manifest) |
| Test | Unused |

---

## 3. M7 Single-Factor Change

| Variable | M5 (Raw) | M7 (Z-Score) |
|----------|----------|--------------|
| Target mode | `raw` | `zscore` |
| Normalization stats | N/A | μ=9.54, σ=10.53 (train pixels only) |
| Loss domain | Raw meters | Z-score units |
| Eval metric | Meters (inverse norm) | Meters (inverse norm) |

Normalization statistics computed **exclusively from training pixels** (no leakage).

---

## 4. Training Results (30 epochs, seed 0)

### Learning Curves (Validation MAE in Meters)
| Epoch | Train MAE | Val MAE | Val RMSE | Pearson |
|-------|-----------|---------|----------|---------|
| 0 | 1.150 | 11.121 | 13.12 | 0.363 |
| 1 | 0.889 | 7.741 | 9.61 | 0.448 |
| 2 | 0.768 | 6.770 | 8.55 | 0.488 |
| 3 | 0.703 | 5.961 | 7.89 | 0.553 |
| 4 | 0.669 | 5.737 | 7.71 | 0.584 |
| 5 | 0.649 | 5.636 | 7.64 | 0.596 |
| 6 | 0.638 | 5.557 | 7.56 | 0.607 |
| 7 | 0.630 | 5.540 | 7.54 | 0.608 |
| **8** | **0.623** | **5.536** | **7.49** | **0.613** |
| 9 | 0.617 | 5.558 | 7.49 | 0.614 |
| 10 | 0.612 | 5.630 | 7.54 | 0.612 |
| ... | ... | ... | ... | ... |
| 29 | 0.566 | 5.928 | 7.87 | 0.604 |

- **Best epoch:** 8 (val MAE = **5.536 m**)
- **Training time:** 794 s (CPU)
- **Trainable params:** 23,201 / 24.8M total (0.09%)
- **Target normalization:** μ = 9.54 m, σ = 10.53 m (computed from 25.1M train pixels)

---

## 5. M5 vs M7 Comparison (Same Protocol, Direct Meters)

| Metric | M5 (Epoch 23) | M7 (Epoch 8) | Δ |
|--------|---------------|--------------|---|
| **Val MAE (m)** | **5.150** | **5.536** | **+0.386 (+7.5%)** |
| Val RMSE (m) | 7.369 | 7.492 | +0.123 |
| Pearson | 0.631 | 0.613 | -0.018 |
| Spearman | 0.586 | 0.532 | -0.054 |
| Best epoch | 23 | 8 | -15 |

**Result: M7 with z-score normalization does NOT improve validation MAE over M5 raw.**

---

## 6. Detailed Error Analysis

### Height-Bin MAE (meters)
| Bin | M5 | M7 | Δ |
|-----|----|----|---|
| 0–1 m | 1.651 | **0.652** | **-0.999** |
| 1–5 m | 2.391 | 3.382 | +0.991 |
| 5–10 m | 3.681 | 7.530 | +3.849 |
| 10–20 m | 8.540 | 14.385 | +5.845 |
| 20–30 m | 15.688 | 23.831 | +8.143 |
| 30+ m | 23.247 | 33.270 | +10.023 |

### Per-Class MAE (meters)
| Class | M5 | M7 | Δ |
|-------|----|----|---|
| ground | 1.666 | 0.668 | **-0.998** |
| low vegetation | 2.223 | 1.115 | **-1.108** |
| road | 3.301 | 3.523 | +0.222 |
| buildings | 3.943 | 7.553 | +3.610 |
| others | 4.804 | 4.109 | -0.695 |
| tree | 10.310 | 16.396 | +6.086 |
| water | 11.017 | 4.675 | **-6.342** |

### Residual Analysis
| Metric | M5 | M7 |
|--------|----|----|
| Mean residual | -0.761 m | -3.67 m |
| Std | 7.33 m | 11.2 m |
| p5 | -15.2 m | -28.1 m |
| p95 | +10.1 m | +20.8 m |

---

## 7. Outcome Classification: **Outcome C — Normalization does not improve overall validation**

### Interpretation
- **M7 val MAE (5.54 m) > M5 val MAE (5.15 m)** — z-score normalization **degraded** overall performance by 7.5%
- **Convergence speed:** M7 reaches peak at epoch 8 vs M5 at epoch 23 — faster convergence but lower ceiling
- **Low-height improvement:** Ground/low-veg MAE significantly better (z-score upweights low-magnitude pixels)
- **Tall-structure degradation:** Tree/water/building errors increase substantially (z-score downweights large-magnitude pixels)
- **Residual bias:** M7 mean residual -3.67 m vs M5 -0.76 m — stronger systematic under-prediction

### Root Cause Analysis
Z-score normalization reweights the L1 loss by `1/σ ≈ 0.095`, dramatically reducing the gradient contribution from high-magnitude targets (tall buildings, trees). While this helps the model fit the abundant low-height pixels (ground, roads), it starves the tall-structure pixels of gradient signal. The M5 raw L1 loss naturally balances all pixels equally in absolute terms, which better serves the long-tailed GAMUS distribution where tail accuracy matters for the application.

---

## 8. Next Experiment Recommendation

**Do NOT adopt z-score normalization.** M5 remains the current adaptation reference.

Per §43 decision tree: **M7 does not improve overall validation → keep M5 as reference and investigate geographically diverse training data as the next single factor.**

> **Next experiment:** Geographic training diversity experiment (expand M5 train subset beyond DC-only to include PHL/NYC tiles), keeping M5's raw-meter L1 loss and architecture frozen.