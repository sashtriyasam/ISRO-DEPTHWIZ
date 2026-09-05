# M10 Target Normalization on M9 Composition

**Date:** 2026-09-05
**Author:** Shravan (ML/data)
**Branch:** `feat/shravan-dav2-target-normalization-m9`
**Experiment:** `experiments/dav2-gamus-head-m10-m9-targetnorm-e01`
**Geographic Eval:** `experiments/m10-geographic-eval`
**M9 Reference:** `experiments/dav2-gamus-head-m9-composition-16-4-4-e01` (epoch 20, val MAE 6.0206 m, raw)
**M5 Reference:** `experiments/dav2-gamus-head-m5-e01` (epoch 23, val MAE 5.1500 m, raw)
**M7 Reference:** `experiments/dav2-gamus-head-m7-targetnorm-e01` (epoch 8, val MAE 5.5358 m train-summary, zscore on 24-DC)
**M8 Reference:** `experiments/dav2-gamus-head-m8-diversity-e01` (epoch 28, val MAE 6.8036 m, raw)

---

## 1. Hypothesis

> Does z-score target normalization become useful after geographic training composition has been improved to 16/4/4, without changing the M9 data composition or model/training recipe?

M7 showed z-score degrading the DC-only M5 recipe (5.1500 → 5.5358 m). M10 asks the question again with the M9 16/4/4 composition frozen as the control. This is scientifically legitimate because the training distribution changed: normalization interacts with data composition, so M7's result does not settle M10's question.

---

## 2. M9 Frozen Control

| Component | Setting |
|-----------|---------|
| Backbone | Depth Anything V2 Small, frozen (`depth-anything/Depth-Anything-V2-Small`, pin `03876f8651c73a60fe4c2c48294e09fcb6838fcf`) |
| Feature tap | `depth_head.scratch.output_conv1` input (1×64×296×296) |
| Head | Conv 64→32→16→1 + bilinear → 1024×1024 (~23,201 trainable) |
| Loss | Masked L1 (finite pred AND finite target; negatives kept) |
| Optimizer | Adam, lr=1e-3, weight_decay=0 |
| Training | 30 epochs, seed 0, batch 1 tile, no augmentation/scheduler/warmup/clipping |
| Init | Fresh head (no resume from M5/M7/M8/M9) |

---

## 3. M10 Single-Factor Definition

```
M9:  16 DC + 4 PHL + 4 NYC, 24 train tiles, raw meters
M10: 16 DC + 4 PHL + 4 NYC, 24 train tiles, z-score using M10 TRAIN-ONLY mu/sigma

Everything except target normalization is frozen.
```

---

## 4. Exact Train / Validation IDs

M10 train IDs are byte-identical to M9 (verified programmatically):

DC (16): DC_01_25, DC_02_24, DC_02_25, DC_02_27, DC_03_23, DC_03_24, DC_03_25, DC_03_27, DC_03_28, DC_04_24, DC_04_25, DC_04_26, DC_04_28, DC_05_20, DC_05_21, DC_05_26
PHL (4): PHL_0451, PHL_0496, PHL_0497, PHL_0498
NYC (4): NYC_22835, NYC_22836, NYC_22837, NYC_22840

Validation (8 DC, identical M5/M8/M9): DC_02_26, DC_04_23, DC_04_27, DC_08_31, DC_09_33, DC_10_30, DC_11_16, DC_11_33

City counts: train DC 16 / PHL 4 / NYC 4 (= 24); val DC 8. Train/val overlap 0. Duplicate train IDs 0. Test samples in train 0.

---

## 5. Train-Only Normalization Statistics

Computed exclusively from valid finite TRAIN pixels (16/4/4 set, negatives kept):

| Statistic | Value |
|-----------|-------|
| n_valid_pixels | 25,165,824 |
| n_negative_pixels | 316,724 (preserved, no clipping) |
| mu (mean) | 8.0373 m |
| sigma (std) | 10.3040 m |
| min | -5.0 m |
| max | 55.049 m |

M7 values (mu=9.54, sigma=10.53, from the 24-DC set) were NOT reused — verified by precheck and by a source test asserting those literals are absent from the M10 runner.

Formulas — training: `z = (height - mu_train) / sigma_train`, masked L1 in z-space; evaluation: `height_pred_m = pred_z * sigma_train + mu_train`. All reported metrics are in meters. Validation targets were never used for statistics; only predictions are inverse-transformed.

---

## 6. Training Configuration

Same as M9 except `target_mode: raw → zscore`. Fresh head init, seed 0, 30 epochs, CPU. Train loss logged in z-space; val MAE/RMSE/Pearson logged in meters (inverse-transformed).

Learning curve (val MAE, meters): 0: 9.56 → 5: 6.46 → 10: 6.35 → 15: 6.12 → 17: 6.05 → 20: 5.87 → **22: 5.8204 (best)** → 24: 5.8208 → 28: 5.8332 → 29: 6.0118. Train z-loss falls monotonically 1.177 → 0.593. No early overfit signature; late oscillation (ep29 +0.19) suggests diminishing returns past epoch 22.

---

## 7. Primary Validation Results (Same 8 DC Tiles)

| Metric | M9 raw (ep 20) | M10 zscore (ep 22) | Δ (M10−M9) |
|--------|----------------|--------------------|------------|
| **Val MAE** | 6.0206 | **5.8204** | **−0.2002 (−3.3%)** |
| Val RMSE | 9.3546 | **8.4924** | −0.8623 |
| Median | 3.1906 | 3.4405 | +0.2499 |
| p90 | 16.9095 | **15.2181** | −1.6915 |
| p95 | 22.0421 | **19.4134** | −2.6287 |
| Pearson | 0.4776 | **0.5678** | +0.0902 |
| Spearman | 0.4803 | 0.4984 | +0.0180 |
| Residual mean | −4.3029 | **−3.2913** | +1.0116 (bias↓) |
| Residual std | 8.3063 | 7.8287 | −0.4776 |
| Residual p5 / p95 | −22.04 / +5.17 | −19.41 / +5.62 | improved |

Best epoch: M10 @ 22 (vs M9 @ 20, M5 @ 23, M7 @ 8).

---

## 8. M9 vs M10 Table (Primary)

| Metric | M9 (16/4/4 raw) | M10 (16/4/4 zscore) | Delta |
|--------|-----------------|---------------------|-------|
| Val MAE | 6.0206 m | **5.8204 m** | **−0.2002 m** |
| Val RMSE | 9.3546 m | **8.4924 m** | −0.8623 m |
| Pearson | 0.4776 | **0.5678** | +0.0902 |

---

## 9. M5 / M9 / M10 Context Table

| Metric | M5 (24 DC raw) | M9 (16/4/4 raw) | M10 (16/4/4 zscore) |
|--------|----------------|-----------------|---------------------|
| Val MAE | 5.1500 m | 6.0206 m | **5.8204 m** |
| Δ vs M5 | — | +0.8706 m | **+0.6704 m** |
| Δ vs M9 | — | — | **−0.2002 m** |

M10 closes ~23% of the M9→M5 gap (0.20 of 0.87 m) but remains 0.67 m behind M5 on DC validation.

---

## 10. Height-Bin Analysis (DC Val, MAE in Meters)

| Bin | M9 | M10 | Δ |
|-----|-----|-----|-----|
| 0–1 m | 1.5368 | 2.7210 | +1.1842 (regression) |
| 1–5 m | 2.4907 | 2.2722 | −0.2185 |
| 5–10 m | 3.9459 | 3.3717 | −0.5741 |
| 10–20 m | 9.9112 | 8.9492 | −0.9620 |
| 20–30 m | 17.5777 | 15.8361 | −1.7415 |
| 30+ m | 25.5143 | **21.6053** | **−3.9089** |

Tail improvement grows monotonically with height — consistent with z-score rebalancing gradient toward large-magnitude pixels on this composition (opposite of the M7 DC-only failure, where 30+m degraded by +10.02 m). The 0–1 m regression (+1.18) is the mirror cost.

---

## 11. Class Analysis (DC Val, MAE in Meters)

| Class | M9 | M10 | Δ |
|-------|-----|-----|-----|
| ground | 1.6006 | 2.8646 | +1.2640 |
| low vegetation | 1.8535 | 2.8921 | +1.0387 |
| road | 3.4494 | 3.9649 | +0.5155 |
| buildings | 3.9641 | 3.9888 | +0.0248 (flat) |
| others/background | 5.2049 | 5.3797 | +0.1748 |
| tree | 11.8946 | **10.1750** | **−1.7197** |
| water | 12.9534 | **9.6918** | **−3.2616** |

M10 preserves the M9 building recovery (flat) while improving the two hardest classes (tree, water). Low-magnitude classes (ground, low-veg) regress — same trade as the 0–1 m bin.

---

## 12. Residual Analysis (DC Val)

M9: mean −4.30 m, std 8.31, p5 −22.04, p95 +5.17. M10: mean −3.29 m, std 7.83, p5 −19.41, p95 +5.62. Systematic under-prediction reduced by ~1.0 m with tighter spread — consistent with (not proof of) better tall-structure calibration.

---

## 13. Learning Curves

Train z-loss: monotonic 1.177 → 0.593. Val MAE (m): 9.56 (ep0) → 6.46 (ep5) → 6.35 (ep10) → 6.12 (ep15) → 5.87 (ep20) → 5.8204 (ep22 best) → 5.82–5.86 plateau → 6.01 (ep29). Pearson rises 0.39 → 0.57 @22. Selection by min val MAE @22 is stable (ep24 within 0.0004).

---

## 14. Geographic Evaluation (M6 Protocol, Frozen M10 Checkpoint)

Evaluated with train-derived mu/sigma inverse-transform (new optional `--target-mu/--target-sigma` path; raw default preserved for legacy runs).

| Metric | M5 (M6) | M9 | M10 | M10−M9 | M10−M5 |
|--------|---------|-----|-----|--------|--------|
| DC MAE (18) | 5.272 | 6.374 | **6.243** | −0.131 | +0.971 |
| PHL MAE (50) | 3.957 | 2.888 | 3.275 | +0.387 | −0.682 |
| NYC MAE (50) | 5.824 | 5.198 | 5.355 | +0.156 | −0.469 |
| Cross-city MAE | 4.890 | 4.043 | 4.315 | +0.272 | −0.575 |
| Macro MAE | 5.018 | 4.820 | 4.957 | +0.137 | −0.061 |
| Micro MAE | 4.949 | 4.399 | 4.609 | +0.210 | −0.340 |
| Gap (cross−in) | −0.382 | −2.331 | −1.928 | +0.403 | −1.546 |

DC geo Pearson 0.357→0.446 (+0.089); PHL Pearson 0.478→0.425 (−0.053); NYC Pearson 0.238→0.215 (−0.023). DC residual mean −4.30→−3.29 on val; geo residual bias follows the same direction.

30m+ geo MAE: DC 26.76→23.39 (improve), PHL 11.75→15.34 (regress), NYC 32.65→32.15 (flat). PHL 30+m has only 191k/52M px (0.37%) — fragile.

Interpretation: normalization slightly helps the in-city geography (DC −0.13) while costing cross-city PHL (+0.39) and NYC (+0.16). The gap becomes less negative (−2.33→−1.93). Per §17 of the task spec, "more negative" is not automatically better — the objective is the trade-off, and here the trade-off moves modestly toward DC/tail at a small cross-city cost.

---

## 15. Contamination / Limitations

- M10 train IDs == M9 train IDs (verified); 0 overlap with M6/M8 geographic eval ID sets (val+test splits; M10 trains on train split only).
- No true held-out-city generalization: DC/PHL/NYC all exist in the full GAMUS train distribution.
- One seed (0), one composition, one validation geography, small PHL/NYC train subsets (4 tiles each). No significance claim; language below uses "improved/suggests".
- PHL 30+m and NYC 30+m (636 px) bins are statistically fragile.
- M5 primary validation is direct metric prediction in meters under the adaptation protocol (same as M8/M9/M10). Per-image affine alignment belongs to the M3 frozen relative-depth protocol only. The M8 report's §7 limitation item misstated this ("M5 primary val uses per-image affine"); it is corrected in this branch to the direct-meters wording with no change to any historical numbers (see §18).

---

## 16. Error Analysis vs M7 Failure Mode

M7 (DC-only + zscore) showed: low-height improvement, severe tall degradation (30+m +10.02), stronger under-prediction (−3.67 mean), overall MAE +0.386. M10 (16/4/4 + zscore) shows the OPPOSITE tall behavior: 30+m −3.91, 20–30m −1.74, residual bias reduced (−4.30→−3.29), overall MAE −0.20. The 0–1m/ground/low-veg regression (+1.04 to +1.26) is the shared cost. Evidence suggests the normalization × composition interaction is real: on the diverse 16/4/4 distribution, z-score reallocates capacity toward tall structures without the DC-only collapse. Buildings hold flat (3.96→3.99); trees improve (11.89→10.18). No causal mechanism beyond the measurements is claimed.

---

## 17. Outcome Classification

**Outcome A — normalization improves M9 (modestly).**

- Primary val MAE improves 6.0206 → 5.8204 (−3.3%).
- RMSE −0.86, p90 −1.69, p95 −2.63, Pearson +0.09, residual bias −1.01.
- Material tail improvement: 20–30m −1.74, 30+m −3.91, tree −1.72, water −3.26.
- Geographic cost is small: macro +0.14, micro +0.21, PHL +0.39, NYC +0.16; DC geo improves −0.13. PHL/NYC remain substantially better than M5.
- No unacceptable regression: the only regressions (0–1m, ground/low-veg, PHL tall-from-small-base) do not erase M9's cross-city advantage over M5.

Z-score on the 16/4/4 composition is therefore a serious candidate for the reference recipe. Given one seed and a modest margin, it is adopted as a *candidate* (not proven-optimal) reference.

---

## 18. Documentation Corrections Made in This Branch

1. `docs/research/m8-geographic-training-diversity.md` §7 item 6: corrected "M5 primary val uses per-image affine" → direct-meters wording (terminology only; no numbers changed), as required by the task's scientific-correction section.
2. `src/depthwizard/experiments/adapt_dav2_m10.py`: new runner; applies the fitted train-only z-score scale to the model before final validation analysis so `results.json` validation metrics are in meters and consistent with `train_summary.json` (the M7 runner omitted this; its results.json validation block at 8.14 m was inconsistent with its train-summary best 5.54 m).
3. `src/depthwizard/experiments/m6_geographic.py`: added optional `--target-mu/--target-sigma` (default raw) so z-score checkpoints evaluate in meters; legacy raw behavior unchanged.

---

## 19. Next Recommendation

Keep the M10 recipe (16/4/4 + train-only z-score) as the candidate adaptation reference. The evidence-based next one-factor step — NOT run here — is a seed-repeat of M10 (e.g. seeds 1–2, validation-only) to quantify run-to-run variance before declaring it the reference, since the primary margin (−0.20 m) is modest and only one seed exists. No M11 is started in this task.

---

## 20. Artifacts

- `experiments/dav2-gamus-head-m10-m9-targetnorm-e01/config.json`
- `experiments/dav2-gamus-head-m10-m9-targetnorm-e01/results.json`
- `experiments/dav2-gamus-head-m10-m9-targetnorm-e01/train_summary.json`
- `experiments/dav2-gamus-head-m10-m9-targetnorm-e01/log.jsonl`
- `experiments/dav2-gamus-head-m10-m9-targetnorm-e01/checkpoints/best.pt` (git-ignored)
- `experiments/m10-geographic-eval/config.json`
- `experiments/m10-geographic-eval/results.json`
- `experiments/m10-geographic-eval/README.md`
- `docs/research/m10-target-normalization-on-m9.md` (this document)
- `tests/test_m10_targetnorm.py` (12 tests, passing)

Reproducibility:

```bash
pip install -e ".[dev]" && pip install -e ".[dav2]"
export PYTHONPATH=src:<pinned-DA-V2-clone @ a561b84>
python -m depthwizard.experiments.adapt_dav2_m10 \
  --manifest manifests/gamus.m8.geographic.json \
  --experiment-id dav2-gamus-head-m10-m9-targetnorm-e01 \
  --epochs 30 --lr 1e-3 --seed 0 --target-mode zscore \
  --output experiments/dav2-gamus-head-m10-m9-targetnorm-e01
python -m depthwizard.experiments.m6_geographic \
  --manifest manifests/gamus.m6.geographic.json \
  --base-checkpoint checkpoints/depth_anything_v2_vits.pth \
  --adapt-checkpoint experiments/dav2-gamus-head-m10-m9-targetnorm-e01/checkpoints/best.pt \
  --output experiments/m10-geographic-eval \
  --target-mu 8.037330237035235 --target-sigma 10.304011604437477
```

---

**Prepared by:** Shravan (ML)
**Date:** 2026-09-05
**Branch:** `feat/shravan-dav2-target-normalization-m9`
