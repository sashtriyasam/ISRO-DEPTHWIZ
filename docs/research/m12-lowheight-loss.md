# M12 Low-Height-Weighted L1 on the Stable M10 Recipe

**Date:** 2026-09-05
**Author:** Shravan (ML/data)
**Branch:** `feat/shravan-m10-lowheight-loss`
**Experiment:** `experiments/dav2-gamus-head-m12-lowheight-loss-e01`
**Geographic Eval:** `experiments/m12-geographic-eval`
**Control:** M10/M11 recipe — 16 DC + 4 PHL + 4 NYC, train-only z-score (mu=8.0373, sigma=10.3040), frozen DA-V2-Small + ~23k head, Adam lr=1e-3, 30 epochs, seed 0
**References:** M10 seed0 5.8204 m · M11 mean 5.7428 m (std 0.0573, range 5.6836–5.8204) · M9 raw 6.0206 m · M5 raw 5.1500 m

**M12 changed ONLY the loss formulation.**

---

## 1. Motivation

M11 confirmed the M10 recipe is stable across seeds 0/1/2 but also confirmed one consistent failure mode: 0–1m, ground, and low vegetation regress on all three seeds, while 20–30m, 30+m, and tree improve consistently.

## 2. M10/M11 Control

Frozen: 24 exact train IDs (16/4/4), 8 exact DC val tiles, z-score normalization with train-only statistics, DA-V2-Small frozen backbone (`output_conv1` tap, 1×64×296×296), 64→32→16→1 head, Adam lr=1e-3 wd=0, 30 epochs, batch 1, seed 0, no augmentation/scheduler/clipping, fresh init, min-val-MAE (meters) selection.

## 3. Observed M11 Failure Mode

Three-seed means vs M9: 0–1m 2.6095 vs 1.5368 · ground 2.7217 vs 1.6006 · low vegetation 2.7951 vs 1.8535 — regressed on every seed. Meanwhile 20–30m 15.3055 vs 17.5777, 30+m 21.0868 vs 25.5143, tree 10.0939 vs 11.8946 — improved on every seed.

## 4. M12 Hypothesis

A fixed 2× emphasis on targets below 5 m recovers the low-height regime while preserving the M10 tail behavior. Pre-registered; not assumed to work.

## 5. Exact Loss Formula

Valid pixels (finite pred_z AND finite target_z AND finite target_m):

```
w(y) = 2.0  if y < 5.0 meters (meter-scale target, assigned BEFORE z-score conversion)
w(y) = 1.0  if y >= 5.0 meters
L_M12 = sum(w * |pred_z - target_z|) / sum(w)
```

Comparison stays in z-space; the prediction is never converted to meters for the loss. Negatives are valid and fall in the <5 m group. No clipping, no class labels, no validation data in the rule.

## 6. Exact Threshold / Weight

Threshold = 5.0 m (strict `<`; 5.0 itself gets weight 1). Low weight = 2.0, high weight = 1.0. Fixed constants (`HEIGHT_THRESHOLD_M`, `LOW_HEIGHT_WEIGHT`), not tuned after results.

## 7. Exact Dataset

Train IDs byte-identical to M10/M11 (verified pre-run): DC_01_25, DC_02_24, DC_02_25, DC_02_27, DC_03_23, DC_03_24, DC_03_25, DC_03_27, DC_03_28, DC_04_24, DC_04_25, DC_04_26, DC_04_28, DC_05_20, DC_05_21, DC_05_26, PHL_0451, PHL_0496, PHL_0497, PHL_0498, NYC_22835, NYC_22836, NYC_22837, NYC_22840. Val IDs identical (8 DC). 24 train, 16/4/4, overlap 0, test unused.

## 8. Normalization

z = (height − mu_train)/sigma_train with mu=8.037330237035235, sigma=10.304011604437477 recomputed from the M12 train set and verified bit-identical to M10/M11 (n=25,165,824 valid, 316,724 negatives, min −5.0, max 55.049). M7 values not used. Metrics in meters via inverse transform.

## 9. Training Configuration

Epochs 30, Adam lr=1e-3 wd=0, batch 1, seed 0, CPU, fresh init. Train loss is the weighted z-loss (1.241 → 0.503, monotonic). Val MAE (meters): 10.24 (ep0) → 6.81 (ep3) → 6.1–6.2 oscillation from ep24 → **best 6.0616 @ epoch 29 (final epoch)**. Train time 793.2 s. Best-at-last-epoch is noted as a limitation (possible under-training); epochs were not extended per the one-factor rule.

## 10. Sanity-Test Results

12 fixture tests pass pre-run: 2× below 5 m (loss 2/3 on the toy), 1× at/above 5 m including the exact 5.0 boundary, negatives weighted, denominator = sum(w), masking, all-invalid raises, shape-mismatch raises, finite gradients ([2/3, 1/3]), z-compatibility (constant z-error reproduces exactly; inverse unaffected), no validation dependency, recipe freeze. Real-data precheck: 54.45% of valid train pixels <5 m (70.5% of weighted loss vs 54.45% under plain L1), negatives in group, constant-error real-tile loss exact, grads finite.

## 11. Primary Validation Results (Same 8 DC Tiles)

| Metric | M9 raw | M10 s0 | M11 mean (range) | M12 (ep29) | M12 vs M11 mean |
|--------|--------|--------|------------------|------------|-----------------|
| **Val MAE** | 6.0206 | 5.8204 | 5.7428 (5.68–5.82) | **6.0616** | **+0.3188** |
| Val RMSE | 9.3546 | 8.4924 | 8.4086 | 9.3140 | +0.9054 |
| Median | 3.1906 | 3.4405 | ~3.35 | 2.9160 | −0.44 |
| p90 | 16.9095 | 15.2181 | ~14.9 | 16.8998 | +2.0 |
| p95 | 22.0421 | 19.4134 | ~19.02 | 21.7387 | +2.7 |
| Pearson | 0.4776 | 0.5678 | 0.5782 | 0.5308 | −0.047 |
| Spearman | 0.4803 | 0.4984 | 0.5121 | 0.4863 | −0.026 |
| Residual mean | −4.3029 | −3.2913 | ~−3.31 | −4.6382 | −1.35 (bias worse) |

`results.json` validation MAE matches `train_summary.json` best_value to 6e-11 (meter-consistency holds).

## 12. M10/M11/M12 Comparison

M12 overall MAE (6.0616) is worse than M9 (6.0206) and every M11 seed (5.68–5.82). Median improves (2.92 vs ~3.35) but p90/p95, RMSE, correlations, and bias all regress toward or past M9.

## 13. Low-Height Analysis (DC Val MAE)

| Bin/Class | M9 | M11 mean | M12 | M12 vs M11 mean |
|-----------|-----|----------|-----|-----------------|
| 0–1 m | 1.5368 | 2.6095 | **1.5769** | **−1.0326** |
| 1–5 m | 2.4907 | 2.4224 | **2.0062** | −0.4162 (also < M9) |
| ground | 1.6006 | 2.7217 | **1.6612** | **−1.0605** |
| low vegetation | 1.8535 | 2.7951 | **1.7507** | −1.0444 (also < M9) |
| road | 3.4494 | 3.9812 | 3.4743 | −0.5069 (≈M9) |
| others/background | 5.2049 | 5.2933 | 4.5432 | −0.7501 (< M9) |

The targeted correction works: 0–1m/ground recover to ≈M9; 1–5m/low-veg/others/water beat M9 outright.

## 14. Tail Analysis (DC Val MAE)

| Bin/Class | M9 | M11 range | M12 | Retained M9→M11 gain |
|-----------|-----|-----------|-----|----------------------|
| 20–30 m | 17.5777 | 14.95–15.84 | 17.8056 | none (−0.23 vs M9) |
| 30+ m | 25.5143 | 20.77–21.61 | 24.6054 | ~21% (0.91 of 4.43) |
| tree | 11.8946 | 10.00–10.18 | 11.9024 | none (+0.01 vs M9) |
| buildings | 3.9641 | 3.71–3.99 | 4.1318 | worse than both |
| water | 12.9534 | 9.69–13.85 | 9.6846 | < all (but seed-sensitive) |

M12 falls outside the M11 reference ranges on 20–30m, 30+m, and tree — the stable tail gains are largely sacrificed back toward M9.

## 15. Class Analysis

See §§13–14. Net: low-magnitude classes recover; tall/structure classes (buildings, tree) regress to ≈M9 or worse.

## 16. Residual Analysis

Mean −4.6382 (worse than M11 ~−3.31 and M9 −4.30), std 8.0770, p5 −21.7387, p95 +3.7443. Systematic under-prediction returns — consistent with capacity reallocated away from tall structures.

## 17. Geographic Evaluation (M6 Protocol, Frozen M12 Checkpoint, M10 mu/sigma)

| Metric | M9 | M11 mean | M12 | M12 vs M11 |
|--------|-----|----------|-----|------------|
| DC MAE (18) | 6.3739 | 6.2009 | 6.4393 | +0.2384 |
| PHL MAE (50) | 2.8877 | 3.3089 | 2.8531 | −0.4558 (≈M9) |
| NYC MAE (50) | 5.1985 | 5.3127 | 5.0505 | −0.2622 (< M9) |
| Cross-city | 4.0431 | 4.3108 | 3.9518 | −0.3590 |
| Macro | 4.8200 | 4.9408 | 4.7810 | −0.1598 |
| Micro | 4.3987 | 4.5991 | 4.3312 | −0.2679 |
| Gap | −2.3308 | −1.8901 | −2.4875 | −0.5974 |

DC geo Pearson 0.416 (M11 0.469, M9 0.357); PHL 0.386; NYC 0.229. Geo 30+m: DC 26.13 (M11 ~22.8), PHL 18.81 (M11 ~15.2, M9 11.75), NYC 33.34 (≈M9 32.65). Geography does not degrade vs M11 on macro/micro/PHL/NYC — but checkpoint selection never used geography, and the primary+tail verdict already fails.

## 18. Outcome

**Outcome B — trade-off.**

M12 materially improves the targeted low-height failure (0–1m −1.03, ground −1.06, low-veg −1.04 vs M11 means; several bins/classes even beat M9). But it sacrifices the stable tail (20–30m fully lost, 30+m keeps ~21%, tree fully lost — all outside M11 ranges), regresses overall MAE past M9 (6.06 > 6.02, outside the 5.68–5.82 seed band), and restores under-prediction bias. It cannot replace M10. The geographic macro/micro improvement vs M11 is noted but does not rescue the primary verdict.

## 19. Limitations

One threshold (5.0), one weight (2.0), one seed (0), one composition, one validation geography. Best epoch = final epoch (possible under-training; not extended per one-factor rule). Water/others classes tiny. No significance claims. 2×/5 m is not proven optimal — only this formulation was tested.

## 20. Next Recommendation

Do not adopt M12. Keep the M10 recipe (plain z-score masked L1, three-seed mean 5.7428 ± 0.0573) as the stable candidate reference. The evidence-based next one-factor step — not run here — is a milder low-height emphasis (e.g. 1.5× below 5 m) or, preferably, extended training of the M12 formulation to separate the loss effect from the best-at-final-epoch confound — but only one of these, not both.

---

## Artifacts

- `experiments/dav2-gamus-head-m12-lowheight-loss-e01/` (config/results/log/train_summary/README, best.pt git-ignored)
- `experiments/m12-geographic-eval/` (config/results/README)
- `docs/research/m12-lowheight-loss.md` (this document)
- `tests/test_m12_lowheight_loss.py` (12 tests, passing)

Reproducibility:

```bash
pip install -e ".[dev]" && pip install -e ".[dav2]"
export PYTHONPATH=src:<pinned-DA-V2-clone @ a561b84>
python -m depthwizard.experiments.adapt_dav2_m12 \
  --manifest manifests/gamus.m8.geographic.json \
  --experiment-id dav2-gamus-head-m12-lowheight-loss-e01 \
  --epochs 30 --lr 1e-3 --seed 0 --target-mode zscore \
  --output experiments/dav2-gamus-head-m12-lowheight-loss-e01
python -m depthwizard.experiments.m6_geographic \
  --manifest manifests/gamus.m6.geographic.json \
  --base-checkpoint checkpoints/depth_anything_v2_vits.pth \
  --adapt-checkpoint experiments/dav2-gamus-head-m12-lowheight-loss-e01/checkpoints/best.pt \
  --output experiments/m12-geographic-eval \
  --target-mu 8.037330237035235 --target-sigma 10.304011604437477
```

---

**Prepared by:** Shravan (ML)
**Date:** 2026-09-05
**Branch:** `feat/shravan-m10-lowheight-loss`
