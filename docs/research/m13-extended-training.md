# M13 — Extended Training of M12 Weighted Loss

**Date:** 2026-09-05
**Author:** Shravan (ML/data)
**Branch:** `feat/shravan-m13-extended-training`
**Experiment:** `experiments/dav2-gamus-head-m13-extended-e01`
**Geographic Eval:** `experiments/m13-geographic-eval`
**Control:** M12 recipe — 16 DC + 4 PHL + 4 NYC, train-only z-score (mu=8.037330237035235, sigma=10.304011604437477), 2×/1× low-height-weighted masked L1 (threshold 5.0 m), frozen DA-V2-Small + ~23k head, Adam lr=1e-3 wd=0, batch 1, seed 0, no augmentation, fresh init
**References:** M12 6.0616 m @29/30 · M9 6.0206 m · M10 5.8204 m · M11 mean 5.7428 m (std 0.0573, range 5.6836–5.8204)

**M13 changed ONLY the training budget (epochs 30 → 60).**

---

## 1. Metadata

- Experiment code/report commit: `14455a339cb112e4c08f62b0f0be54339db24f2a` (M13 experiment was executed from the M13 branch state corresponding to this commit; the M13 run itself required zero source changes — Case A)
- Final documentation commit: recorded in the closing handoff after the final commit exists (this report's provenance section was finalized post-run without touching any scientific result)
- Branch: `feat/shravan-m13-extended-training` (based on M12 `369608b`, no rebase onto main)
- Experiment ID: `dav2-gamus-head-m13-extended-e01`
- Timestamp: 2026-09-05 (artifacts carry `generated_utc`)
- Implementation decision: **Case A** — the M12 runner (`adapt_dav2_m12.py`: `epochs` parameter line 170, CLI `--epochs` line 414, `train_adapted_model` loops `range(epochs)`) already supports configurable epochs. Zero training-logic changes; `src/depthwizard/adapt/loss.py` and `src/depthwizard/adapt/train.py` untouched. Clean 60-epoch invocation, fresh init (not resumed from M12).

## 2. Motivation

M12's best checkpoint occurred at the final epoch (29/30), leaving open whether the 2× low-height weighting was genuinely harmful or merely under-trained. M13 separates loss formulation from training-budget effects.

## 3. Frozen Control

Dataset: exact 24 M12 train IDs (16/4/4) and 8 DC val IDs (verified pre-run, byte-identical). Normalization: recomputed train-only mu/sigma, verified bit-identical to M10/M11/M12 (n=25,165,824). Loss: weight 2.0 if meter target < 5.0 (strict), else 1.0; denominator sum(w); negatives kept; comparison in z-space. Architecture: frozen DA-V2-Small, `output_conv1` tap, 64→32→16→1 head (head_trainable 23201, verified). Optimizer Adam lr=1e-3 wd=0, batch 1, seed 0, no augmentation/scheduler/warmup/clipping, fresh init. Selection: min val MAE (meters), fixed 8 DC tiles.

## 4. Single Experimental Factor

```
epochs: 30 → 60
```

Exact invocation:

```bash
PYTHONPATH=src:<pinned-DA-V2-clone> python -m depthwizard.experiments.adapt_dav2_m12 \
  --manifest manifests/gamus.m8.geographic.json \
  --experiment-id dav2-gamus-head-m13-extended-e01 \
  --epochs 60 --lr 1e-3 --seed 0 --target-mode zscore \
  --output experiments/dav2-gamus-head-m13-extended-e01
```

Config records epochs=60, seed=0, lr=0.001, zscore, low-height-weighted/5.0/2.0 (verified post-run; no M10-style metadata staleness).

## 5. Results

| Experiment | Epochs | Best Epoch | MAE | RMSE | Pearson | Notes |
| ---------- | -----: | ---------: | ----: | ----: | ------: | ----- |
| M12 | 30 | 29 | 6.0616 | 9.314 | 0.531 | weighted, best-at-final |
| **M13** | **60** | **54** | **5.9323** | **9.104** | **0.549** | **extended weighted** |
| M9 (context) | 30 | 20 | 6.0206 | 9.355 | 0.478 | raw L1 |
| M10 (context) | 30 | 22 | 5.8204 | 8.492 | 0.568 | unweighted z-L1 |
| M11 (context) | 30 | 22–27 | 5.7428 ± 0.0573 | 8.4086 | 0.5782 | 3-seed z-L1 |

M13 − M12 = **−0.1293 m (−2.1%)**. M13 vs M9 = −0.0883 (beats M9). M13 vs M10 = +0.1119; vs M11 mean = +0.1895 (outside the 5.68–5.82 seed band). Median 2.9458, p90 16.5045, p95 21.0389, Spearman 0.4931, residual mean −4.4459 / std 7.9451. `results.json` MAE matches `train_summary.json` best_value to 6e-11. Train time 1612.6 s.

## 6. Height-Bin Analysis (DC Val MAE)

| Bin | M12 | M13 | M9 | M11 range |
|-----|-----|-----|-----|-----------|
| 0–1 m | 1.5769 | 1.5349 | 1.5368 | 2.39–2.72 |
| 1–5 m | 2.0062 | 2.1475 | 2.4907 | 2.27–2.60 |
| 5–10 m | 4.2107 | 4.1725 | 3.9459 | 3.37–3.65 |
| 10–20 m | 10.3235 | 10.1292 | 9.9112 | 8.72–8.95 |
| 20–30 m | 17.8056 | 17.3358 | 17.5777 | 14.95–15.84 |
| 30+ m | 24.6054 | 23.3597 | 25.5143 | 20.77–21.61 |

Extended training improves every bin slightly vs M12 but changes nothing structurally: low bins stay ≈M9-or-better, tall bins stay ≈M9-or-worse and far outside M11 ranges.

## 7. Class Analysis (DC Val MAE)

ground 1.6674 (≈M12 1.6612, M9 1.6006) · low veg 1.7730 (≈1.7507, M9 1.8535) · road 3.4478 (≈3.4743, M9 3.4494) · buildings 4.0884 (≈4.1318) · others 4.9179 (vs 4.5432) · tree 11.5531 (vs 11.9024, M9 11.8946) · water 9.8658 (≈9.6846). No class changes direction vs the M12 verdict.

## 8. Geographic Analysis (M6 Protocol, M10 mu/sigma)

| Metric | M12 | M13 | M11 mean | M9 |
|--------|-----|-----|----------|-----|
| DC (18) | 6.4393 | 6.3042 | 6.2009 | 6.3739 |
| PHL (50) | 2.8531 | 2.8824 | 3.3089 | 2.8877 |
| NYC (50) | 5.0505 | 5.0500 | 5.3127 | 5.1985 |
| Cross-city | 3.9518 | 3.9162 | 4.3108 | 4.0431 |
| Macro | 4.7810 | **4.7122** | 4.9408 | 4.8200 |
| Micro | 4.3312 | **4.2805** | 4.5991 | 4.3987 |
| Gap | −2.4875 | −2.3881 | −1.8901 | −2.3308 |

DC Pearson 0.452 (M12 0.416); PHL 0.443; NYC 0.284. Geo 30+m: DC 24.61 (M12 26.13), PHL 10.95 (M12 18.81 (!), M9 11.75), NYC 33.13 (≈M12 33.34). M13 has the best macro/micro/cross-city of any run — but geography never selected the checkpoint, and the primary verdict stands.

## 9. Training-Curve Interpretation

Weighted train loss falls monotonically (~1.24 → ~0.474). Val MAE: 10.24 (ep0) → ~6.1–6.2 plateau ep24–53 → best 5.9323 @54 → degradation after (55–59: 6.77/6.54/6.17/6.41/6.76, final 6.76). Because the best (ep54) sits inside the budget with clear post-best overfitting, training was sufficient — the curve answers the hypothesis directly. No plateau-at-final ambiguity remains.

## 10. Scientific Outcome

**Outcome 2 — Partial recovery.**

M13 improves over M12 (−0.1293 m) and edges past M9 (−0.0883), but remains +0.11 vs M10 and +0.19 vs the M11 mean — outside the observed seed band. Extended training helped, but the weighted loss still appears inferior to the stable unweighted z-score formulation. Under-training is unlikely to explain the M12 failure (best @54 with post-best degradation); the 2× low-height weighting itself is likely the dominant problem. This is a mixed conclusion, not a full exoneration or condemnation: the formulation's low-height correction is real (see M12), but at 2× it costs more tail than it buys.

## 11. Recommendation

**Reject the 2× low-height weighting as a replacement for the M10 recipe.** Keep the M10 plain z-score masked-L1 recipe (three-seed 5.7428 ± 0.0573) as the stable candidate reference. Do not pursue 60-epoch weighted training further; if low-height cost is revisited, test a milder emphasis (e.g. 1.5×) as its own one-factor experiment — not started here.

## 12. Reproducibility

Commit/branch/experiment ID/manifests/sample IDs/split/seed(0)/mu/sigma/loss(2× <5 m strict)/optimizer/Adam/lr 1e-3/wd 0/batch 1/no-aug/epochs 60/backbone DA-V2-Small pin 03876f86/tap output_conv1/fresh head/CPU recorded above and in `config.json`/`train_summary.json` (`height_weight: {threshold_m: 5.0, low_weight: 2.0}`). Geo eval command mirrors M12 with the M13 checkpoint and `--output experiments/m13-geographic-eval`.

---

**On tests (§15):** no new code was required (Case A — epochs already configurable), so no new unit tests are appropriate. Verified instead: M12 loss tests (12/12) + full suite pass; pre-run audit verified IDs/split/stats/loss-rule/params; post-run verified config (epochs 60, seed 0) and meter-consistency (6e-11).

**Prepared by:** Shravan (ML)
**Date:** 2026-09-05
**Branch:** `feat/shravan-m13-extended-training`
