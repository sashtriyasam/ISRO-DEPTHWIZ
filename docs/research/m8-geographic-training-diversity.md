# M8 Geographic Training Diversity Experiment

**Date:** 2026-09-05  
**Author:** Shravan (ML/data)  
**Branch:** `feat/shravan-dav2-geographic-diversity`  
**Experiment:** `experiments/dav2-gamus-head-m8-diversity-e01`  
**Geographic Eval:** `experiments/m8-geographic-eval`  
**M5 Reference:** `experiments/dav2-gamus-head-m5-e01` (epoch 23, val MAE 5.1500 m)  
**M6 Reference:** `experiments/m6-geographic-eval` (M5 model geographic eval)

---

## 1. Scientific Question

> Does training the DA-V2-Small adaptation head on geographically diverse tiles (8 DC + 8 PHL + 8 NYC) improve geographic generalization compared to DC-only training (M5), without changing any other factors?

**Hypothesis:** Geographic diversity in the training set will reduce the in-city/out-of-city performance gap, potentially improving cross-city transfer at the cost of some in-city (DC) performance.

---

## 2. Experimental Design (One Factor Changed)

| Factor | M5 (Baseline) | M8 (This Experiment) | Changed? |
|--------|---------------|----------------------|----------|
| **Train city composition** | 24 DC | 8 DC + 8 PHL + 8 NYC | **YES** |
| Train tile count | 24 | 24 | No |
| Val tiles | 8 DC | 8 DC (identical) | No |
| Target mode | raw meters | raw meters | No |
| Epochs | 30 | 30 | No |
| LR / optimizer / seed | 1e-3 / Adam / 0 | 1e-3 / Adam / 0 | No |
| Augmentation | none | none | No |
| Backbone | frozen DA-V2-Small | frozen DA-V2-Small | No |
| Head architecture | ~23k params | ~23k params | No |
| Loss | masked L1 (raw) | masked L1 (raw) | No |

---

## 3. Training Results (Primary: Same 8 DC Val Tiles as M5)

| Metric | M5 (DC-only train) | M8 (8/8/8 train) | Delta |
|--------|-------------------|------------------|-------|
| **Val MAE (best epoch)** | **5.1500 m** (epoch 23) | **6.8036 m** (epoch 28) | **+1.6536 m** |
| Val RMSE | 7.3685 m | 10.9885 m | +3.6200 m |
| Val Pearson | 0.631 | 0.219 | -0.412 |
| Best epoch | 23 | 28 | — |

**Training dynamics:** M8 val MAE starts at ~7.41 (epoch 0), improves to ~6.80 by epoch 28, plateaus. Train MAE drops from 5.33 → 4.76. The gap between train and val MAE narrows from ~2.1 to ~2.0 m.

**Key finding:** Training on geographic diversity (8/8/8) **degrades in-city DC validation performance** by +1.65 MAE (32% worse). The model does not achieve the same DC performance as the DC-only trained M5.

---

## 4. Geographic Evaluation (M6 Protocol: DC/PHL/NYC on val+test)

### 4.1 Overall Metrics (Direct Meters)

| Metric | M5 Model (M6 eval) | M8 Model (This eval) | Delta |
|--------|-------------------|---------------------|-------|
| **Macro MAE** (city avg) | 5.018 m | **4.709 m** | **-0.309 m** |
| **Micro MAE** (pixel-weighted) | 4.949 m | **4.101 m** | **-0.848 m** |
| **In-city MAE** (DC) | 5.272 m | **6.950 m** | **+1.678 m** |
| **Cross-city MAE** (PHL+NYC) | 4.890 m | **3.589 m** | **-1.301 m** |
| **Generalization Gap** | -0.382 m | **-3.361 m** | **-2.979 m** |

### 4.2 Per-City Results

| City | Samples | M5 Model MAE | M8 Model MAE | Delta |
|------|---------|--------------|--------------|-------|
| **DC** (in-city) | 18 | 5.272 m | **6.950 m** | **+1.678 m** |
| **PHL** (cross) | 50 | 3.957 m | **2.203 m** | **-1.754 m** |
| **NYC** (cross) | 50 | 5.824 m | **4.974 m** | **-0.850 m** |

### 4.3 Height-Bin Analysis (MAE in meters)

| Bin | M5 DC | M8 DC | M5 PHL | M8 PHL | M5 NYC | M8 NYC |
|-----|-------|-------|--------|--------|--------|--------|
| 0–1 m | 3.25 | 0.69 | **3.17** | **0.62** | 4.88 | 0.75 |
| 1–5 m | 3.30 | 2.35 | 4.44 | **2.10** | 5.02 | 2.23 |
| 5–10 m | 3.46 | 4.56 | 4.76 | **4.85** | 4.83 | 5.69 |
| 10–20 m | 6.99 | 12.37 | 6.81 | **10.05** | 7.56 | 12.97 |
| 20–30 m | 11.78 | 22.42 | 14.80 | **18.00** | 14.92 | 20.42 |
| 30+ m | 16.94 | 31.64 | 29.81 | **18.73** | 29.49 | 33.25 |

**Key observations:**
- M8 dominates M5 on **low-height bins (0–5 m)** across ALL cities — massive improvement
- M8 is worse on **mid-height bins (5–20 m)** for DC and NYC
- M8 **improves on tall bins (30+ m) for PHL** (18.7 vs 29.8) but degrades for DC/NYC
- PHL has very few tall pixels (0.5% in 30+ m) — statistically fragile

### 4.4 Per-Class Analysis (MAE in meters)

| Class | M5 DC | M8 DC | M5 PHL | M8 PHL | M5 NYC | M8 NYC |
|-------|-------|-------|--------|--------|--------|--------|
| ground | 3.20 | 0.60 | 2.46 | **0.77** | 3.64 | 0.57 |
| low vegetation | 3.96 | 1.08 | 3.54 | **0.61** | 6.55 | 1.12 |
| road | 4.21 | 3.40 | 2.30 | **0.89** | 3.64 | 0.48 |
| buildings | 3.86 | 4.42 | 4.84 | **4.83** | 4.04 | 4.40 |
| tree | 8.00 | 14.83 | 6.94 | **4.16** | 7.66 | 9.37 |
| water | 9.46 | 7.20 | 5.88 | **0.13** | 7.65 | 1.30 |

**Key observations:**
- M8 **massively improves** on ground, low vegetation, road, water across all cities
- M8 **degrades on buildings and trees** for DC and NYC
- PHL trees: 6.94 → 4.16 m (major improvement)

---

## 5. Comparison Summary: M5 vs M8

| Aspect | M5 (DC-only) | M8 (8/8/8) | Winner |
|--------|--------------|------------|--------|
| **In-city DC val (primary)** | **5.15 m** | 6.80 m | **M5** |
| **In-city DC (geo eval, 18 tiles)** | **5.27 m** | 6.95 m | **M5** |
| **Cross-city PHL** | 3.96 m | **2.20 m** | **M8** |
| **Cross-city NYC** | 5.82 m | **4.97 m** | **M8** |
| **Cross-city avg** | 4.89 m | **3.59 m** | **M8** |
| **Macro MAE** | 5.02 m | **4.71 m** | **M8** |
| **Micro MAE** | 4.95 m | **4.10 m** | **M8** |
| **Generalization gap** | -0.38 m | **-3.36 m** | **M8** |
| **Low-height (0-5m) MAE** | ~3.3-4.9 m | **~0.7-2.4 m** | **M8** |

---

## 6. Outcome Classification

**Outcome B — Moderate geographic improvement with significant in-city degradation**

### Evidence:
- ✅ Cross-city MAE improves substantially (4.89 → 3.59 m, -27%)
- ✅ PHL cross-city MAE drops dramatically (3.96 → 2.20 m, -44%)
- ✅ NYC cross-city MAE improves (5.82 → 4.97 m, -15%)
- ✅ Macro MAE improves (5.02 → 4.71 m)
- ✅ Micro MAE improves (4.95 → 4.10 m)
- ✅ Generalization gap becomes more negative (-0.38 → -3.36 m)
- ❌ In-city DC validation degrades significantly (5.15 → 6.80 m, +32%)
- ❌ DC geographic eval degrades (5.27 → 6.95 m, +32%)
- ❌ Buildings/tree classes degrade on DC/NYC

### Interpretation:
Geographic training diversity **works as hypothesized for cross-city transfer** — the model learns features that generalize better to PHL and NYC. However, this comes at a **significant cost to in-city (DC) performance**. The training signal from PHL/NYC tiles appears to pull the head away from DC-optimal features.

The negative generalization gap (-3.36 m) means cross-city performance is now **substantially better** than in-city — a reversal from M5 where they were close.

---

## 7. Limitations & Caveats

1. **No true held-out city** — All evaluation cities (DC, NYC, PHL) appear in full GAMUS train split. M8 trains on 8 PHL + 8 NYC tiles from train split; geographic leakage cannot be ruled out.

2. **DC-dominated GAMUS** — Full GAMUS train has 1439 DC, 1167 NYC, 2398 PHL tiles. M8's 8/8/8 is a tiny fraction; PHL/NYC representation is minimal.

3. **Single seed** — Only seed=0 tested. Variance across seeds unknown.

4. **Tall structure regression** — Both models struggle on 20m+ heights. M8 improves PHL tall but degrades DC/NYC tall.

5. **Class imbalance** — PHL has very few tall pixels; NYC 30+m bin has only 636 pixels.

6. **Protocol note (corrected in M10)** — M5/M8 primary validation uses direct metric prediction in meters under the adaptation evaluation protocol; M6/M8 geographic evaluation also uses direct meters, so the M5-vs-M8 primary comparison is valid. Per-image affine alignment belongs to the frozen relative-depth M3 research protocol only.

---

## 8. Next Experiment (Per Decision Tree)

**Outcome B → Next: Investigate why DC degrades and whether rebalancing helps**

Options (one factor at a time):
1. **Rebalance train composition** — Try 12 DC + 6 PHL + 6 NYC or 16 DC + 4 PHL + 4 NYC
2. **Increase PHL/NYC representation** — Use more tiles from train split (if available)
3. **Class-weighted loss** — Address DC building/tree degradation
4. **Two-stage training** — DC pre-train → geographic fine-tune

Per §43 one-factor-at-a-time rule: next experiment changes ONE factor only.

---

## 9. Reproducibility

```bash
# Training (M8)
pip install -e ".[dev]" && pip install -e ".[dav2]"
export PYTHONPATH=C:\Users\Lenovo\Documents\Depth-Anything-V2:$PYTHONPATH
python -m depthwizard.experiments.adapt_dav2_m8 \
  --manifest manifests/gamus.m4.manifest.json \
  --experiment-id dav2-gamus-head-m8-diversity-e01 \
  --epochs 30 --lr 1e-3 --seed 0 \
  --output experiments/dav2-gamus-head-m8-diversity-e01

# Geographic eval (M6 protocol on M8)
python -m depthwizard.experiments.m6_geographic \
  --manifest manifests/gamus.m6.geographic.json \
  --base-checkpoint checkpoints/depth_anything_v2_vits.pth \
  --adapt-checkpoint experiments/dav2-gamus-head-m8-diversity-e01/checkpoints/best.pt \
  --output experiments/m8-geographic-eval
```

---

## 10. Artifacts

- `experiments/dav2-gamus-head-m8-diversity-e01/config.json`
- `experiments/dav2-gamus-head-m8-diversity-e01/results.json`
- `experiments/dav2-gamus-head-m8-diversity-e01/train_summary.json`
- `experiments/dav2-gamus-head-m8-diversity-e01/log.jsonl`
- `experiments/dav2-gamus-head-m8-diversity-e01/checkpoints/best.pt`
- `experiments/m8-geographic-eval/config.json`
- `experiments/m8-geographic-eval/results.json`
- `experiments/m8-geographic-eval/README.md`
- `docs/research/m8-geographic-training-diversity.md` (this document)
- `tests/test_m8_geographic.py` (11 tests, all passing)

---

**Prepared by:** Shravan (ML)  
**Date:** 2026-09-05  
**Branch:** `feat/shravan-dav2-geographic-diversity`  
**Commit:** (pending)