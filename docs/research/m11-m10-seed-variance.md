# M11 M10 Seed Variance Study

**Date:** 2026-09-05
**Author:** Shravan (ML/data)
**Branch:** `feat/shravan-m10-seed-repeat`
**Runs:** `experiments/dav2-gamus-head-m11-seed1-e01`, `experiments/dav2-gamus-head-m11-seed2-e01`
**Geo evals:** `experiments/m11-seed1-geographic-eval`, `experiments/m11-seed2-geographic-eval`
**M10 Reference (seed 0):** `experiments/dav2-gamus-head-m10-m9-targetnorm-e01` (epoch 22, val MAE 5.8204 m)
**M9 Reference:** 6.0206 m (raw, epoch 20)

---

## 1. Motivation

M10 improved over M9 by −0.2002 m (−3.3%) on fixed DC validation with a single seed. The margin is promising but too small to trust from one run. M11 quantifies run-to-run variance of the exact M10 recipe before declaring it the adaptation reference.

---

## 2. M10 Seed-0 Reference

16 DC + 4 PHL + 4 NYC (24 tiles), z-score targets with train-only mu=8.0373 / sigma=10.3040, frozen DA-V2-Small + ~23k head, masked L1, Adam lr=1e-3, 30 epochs, seed 0, best val MAE 5.8204 m @ epoch 22.

---

## 3. One-Factor Definition

```
M11-seed1 = exact M10 recipe, seed = 1
M11-seed2 = exact M10 recipe, seed = 2
```

Only `seed: 0 → 1 → 2` changes. Dataset, normalization, architecture, loss, optimizer, epochs, validation, and output semantics are frozen. Each run uses fresh head initialization from its own seed (no chaining).

---

## 4. Exact Dataset

Train IDs identical to M10/M9 (verified programmatically before launch): 16 DC (DC_01_25 … DC_05_26), 4 PHL (PHL_0451/0496/0497/0498), 4 NYC (NYC_22835/22836/22837/22840). Validation identical (8 DC: DC_02_26, DC_04_23, DC_04_27, DC_08_31, DC_09_33, DC_10_30, DC_11_16, DC_11_33). Train count 24, composition 16/4/4, train/val overlap 0, test unused.

---

## 5. Normalization Protocol

z = (height − mu_train)/sigma_train with statistics recomputed from the same 24 training tiles per run (not hardcoded): seed1 mu=8.037330237035235 / sigma=10.304011604437477; seed2 identical to 15 decimals. M7 values not used. Negatives preserved (316,724 train px). All metrics in meters via inverse transform.

---

## 6. Exact mu/sigma Verification

| Run | mu | sigma | n_valid | Match M10 |
|-----|-----|-------|---------|-----------|
| seed 0 | 8.037330237035235 | 10.304011604437477 | 25,165,824 | — |
| seed 1 | 8.037330237035235 | 10.304011604437477 | 25,165,824 | exact |
| seed 2 | 8.037330237035235 | 10.304011604437477 | 25,165,824 | exact |

Statistics are deterministic functions of the frozen train set, as required.

---

## 7. Seed-1 Results (30 Epochs)

Best val MAE **5.7243 m @ epoch 25** (train_summary best_value 5.7243479289016665; results.json validation MAE identical — meter-consistency holds). RMSE 8.3611, median 3.3380, p90 14.8120, p95 19.0162, Pearson 0.5806, Spearman 0.5117, residual mean −3.2552 / std 7.7014. Train time 778.4 s.

---

## 8. Seed-2 Results (30 Epochs)

Best val MAE **5.6836 m @ epoch 27** (train_summary 5.6836285057836875; results.json identical). RMSE 8.3723, median 3.2862, p90 14.9767, p95 19.0164, Pearson 0.5860, Spearman 0.5262, residual mean −3.3664 / std 7.6657. Train time 784.5 s.

---

## 9. Three-Seed Summary (Primary, 8 DC Val Tiles)

| Metric | seed 0 | seed 1 | seed 2 | mean | std | min | max | range |
|--------|--------|--------|--------|------|-----|-----|-----|-------|
| Val MAE | 5.8204 | 5.7243 | 5.6836 | 5.7428 | 0.0573 | 5.6836 | 5.8204 | 0.1368 |
| Val RMSE | 8.4924 | 8.3611 | 8.3723 | 8.4086 | 0.0594 | 8.3611 | 8.4924 | 0.1313 |
| Pearson | 0.5678 | 0.5806 | 0.5860 | 0.5782 | 0.0076 | 0.5678 | 0.5860 | 0.0182 |
| Spearman | 0.4984 | 0.5117 | 0.5262 | 0.5121 | 0.0114 | 0.4984 | 0.5262 | 0.0278 |

(std = population std over the 3 seeds; descriptive only, not an inference claim.)

---

## 10–12. Variation Details

Best epoch: 22 / 25 / 27 → mean 24.67, std 2.05. Training time: 788.7 / 778.4 / 784.5 s (stable, ±1%).

---

## 13. Reference Comparisons

Deltas vs M9 (6.0206): seed0 −0.2002, seed1 −0.2963, seed2 −0.3370. Deltas vs M10-seed0: seed1 −0.0961, seed2 −0.1368. Three-seed mean 5.7428 → mean improvement vs M9 **0.2778 m**. The mean improvement (0.28) is ~2× the seed-to-seed range (0.14), and every seed beats M9 — the M10 effect is larger than the observed run-to-run spread. Do not cherry-pick seed 2 as "the model."

---

## 14. Height-Bin Variation (DC Val MAE)

| Bin | seed 0 | seed 1 | seed 2 | mean | range | M9 | All < M9? |
|-----|--------|--------|--------|------|-------|-----|-----------|
| 0–1 m | 2.7210 | 2.7175 | 2.3901 | 2.6095 | 0.3309 | 1.5368 | no (consistent cost) |
| 1–5 m | 2.2722 | 2.3960 | 2.5989 | 2.4224 | 0.3267 | 2.4907 | mixed (s0/s1 yes) |
| 5–10 m | 3.3717 | 3.5313 | 3.6522 | 3.5184 | 0.2804 | 3.9459 | yes |
| 10–20 m | 8.9492 | 8.7225 | 8.8203 | 8.8307 | 0.2266 | 9.9112 | yes |
| 20–30 m | 15.8361 | 14.9492 | 15.1312 | 15.3055 | 0.8869 | 17.5777 | yes |
| 30+ m | 21.6053 | 20.8810 | 20.7742 | 21.0868 | 0.8311 | 25.5143 | yes |

---

## 15. Class Variation (DC Val MAE)

| Class | seed 0 | seed 1 | seed 2 | mean | range | M9 | Verdict |
|-------|--------|--------|--------|------|-------|-----|---------|
| ground | 2.8646 | 2.7843 | 2.5164 | 2.7217 | 0.3482 | 1.6006 | consistent cost |
| low vegetation | 2.8921 | 2.8546 | 2.6386 | 2.7951 | 0.2536 | 1.8535 | consistent cost |
| road | 3.9649 | 4.1192 | 3.8595 | 3.9812 | 0.2597 | 3.4494 | consistent cost |
| buildings | 3.9888 | 3.7051 | 3.8905 | 3.8615 | 0.2837 | 3.9641 | stable, ≈M9 |
| others/background | 5.3797 | 5.7844 | 4.7158 | 5.2933 | 1.0686 | 5.2049 | noisy (tiny n=11k) |
| tree | 10.1750 | 10.0032 | 10.1037 | 10.0939 | 0.1718 | 11.8946 | very stable gain |
| water | 9.6918 | 13.8476 | 11.9403 | 11.8265 | 4.1558 | 12.9534 | seed-sensitive (n=2727) |

M10 seed-0 tail observations replicate: 20–30m, 30+m, and tree gains hold on all seeds with tight ranges (≤0.89). Water is seed-sensitive (range 4.16 on n=2727 px) — treat the seed-0 water gain (−3.26) as suggestive, not established. Buildings hold ≈M9 across seeds.

---

## 16. Geographic Evaluation (M6 Protocol, Frozen Checkpoints)

| Metric | seed 0 | seed 1 | seed 2 | mean | range | M9 |
|--------|--------|--------|--------|------|-------|-----|
| DC MAE | 6.2426 | 6.1552 | 6.2050 | 6.2009 | 0.0873 | 6.3739 |
| PHL MAE | 3.2748 | 3.4565 | 3.1954 | 3.3089 | 0.2611 | 2.8877 |
| NYC MAE | 5.3548 | 5.3920 | 5.1912 | 5.3127 | 0.2008 | 5.1985 |
| Cross-city MAE | 4.3148 | 4.4243 | 4.1933 | 4.3108 | 0.2309 | 4.0431 |
| Macro MAE | 4.9574 | 5.0013 | 4.8639 | 4.9408 | 0.1374 | 4.8200 |
| Micro MAE | 4.6089 | 4.6883 | 4.5002 | 4.5991 | 0.1881 | 4.3987 |
| Gap | −1.9277 | −1.7310 | −2.0117 | −1.8901 | 0.2807 | −2.3308 |

DC geo Pearson mean 0.4694 (all > M9 0.3571); PHL Pearson mean 0.4337 (all < M9 0.4778, all > M5 ~0.19–0.34 band); NYC Pearson mean 0.2395. Geo 30+m: DC [23.39, 22.54, 22.47] (all < M9 26.76); PHL [15.34, 14.65, 15.64] (all > M9 11.75, all < M5 29.81); NYC [32.15, 32.12, 32.70] (≈M9 32.65). All three seeds keep PHL/NYC well ahead of M5 while trailing M9 cross-city — a stable, consistent trade-off direction.

---

## 17. Robustness Assessment

- Primary MAE: all 3 seeds beat M9; spread (0.137) < mean effect (0.278). Stable.
- RMSE/Pearson/Spearman: tight (std ≤ 0.06/0.008/0.012). Stable.
- Best epoch 22–27: late-convergence behavior replicates; no early-peak fluke.
- Tails (20–30m, 30+m, tree): replicate on all seeds. Stable.
- Water/others: seed-sensitive due to tiny pixel counts. Not robust claims.
- Geography: DC improvement over M9 replicates on all seeds (range 0.09); PHL/NYC trail M9 but beat M5 on all seeds. Stable direction.

---

## 18. Limitations

Three seeds describe observed spread; they do not support formal significance claims. One composition, one validation geography, small PHL/NYC train subsets (4 tiles each), tiny water/others classes. No true held-out city. CPU-only timing.

---

## 19. Outcome Classification

**Outcome A — Stable candidate.**

Seeds 1 and 2 (5.7243, 5.6836) land close to seed 0 (5.8204) and preserve — indeed extend — the M10 improvement over M9 (6.0206). Tail and geographic patterns replicate in direction with tight ranges except the tiny water class. The recipe is stable across the three observed seeds. Still not claimed globally optimal.

---

## 20. Recommendation (Recipe vs Checkpoint)

Promote the **M10 recipe** (16/4/4 + train-only z-score, 30 epochs, Adam 1e-3) to **stable candidate reference**; do NOT replace any checkpoint automatically. For any future model-selection step, use the three-seed evidence (mean 5.7428 ± 0.0573) rather than the single best run (seed 2, 5.6836). The evidence-based next one-factor step — not run here — is a targeted fix for the consistent low-magnitude cost (0–1m/ground/low-veg), e.g. a loss-formulation experiment on the frozen M10 recipe.

---

## Artifacts

- `experiments/dav2-gamus-head-m11-seed1-e01/` (config/results/log/train_summary/README, best.pt git-ignored)
- `experiments/dav2-gamus-head-m11-seed2-e01/` (same)
- `experiments/m11-seed1-geographic-eval/`, `experiments/m11-seed2-geographic-eval/`
- `docs/research/m11-m10-seed-variance.md` (this document)
- `tests/test_m11_seed_repeat.py` (9 tests, passing)

Reproducibility: same M10 commands with `--seed 1` / `--seed 2`, `--experiment-id dav2-gamus-head-m11-seed{1,2}-e01`, matching `--output` dirs; geo evals add `--target-mu 8.037330237035235 --target-sigma 10.304011604437477`.

---

**Prepared by:** Shravan (ML)
**Date:** 2026-09-05
**Branch:** `feat/shravan-m10-seed-repeat`
