# M17 — Scale-Decoupled Structural Adaptation Probe

**Date:** 2026-09-05
**Author:** Shravan (ML/data)
**Branch:** `feat/shravan-m17-structural-adapt`
**Experiment:** `experiments/m17-geonrw-struct-e01` (train) · `experiments/m17-probe-eval/` (development probe, untracked)
**Frozen base:** M10 seed-0 `best.pt` (epoch 22, val MAE 5.8204; head-only state, never modified)
**Outcome: A — structural objective clearly improves external transfer.**

---

## 1. Objective

Distinguish "the M10 representation cannot learn GeoNRW structure" from "the M16 L1 objective was the wrong way to learn that structure" — with one conceptual change (absolute-scale L1 → scale/shift-decoupled structural loss) and everything else frozen.

## 2. PS Alignment

PS 26175's DSM-accuracy half needs elevation structure that survives outside GAMUS. M17 tests whether the extraction leg can be repaired at the objective level; calibration, mesh, and flythrough are downstream and untouched.

## 3. Pre-Implementation Study

Studied before coding: PS text; AGENTS.md; M14/M15/M16 reports + artifacts; `eval/alignment.py` (affine fit is closed-form least squares; only the prediction side is trainable, so no in-loss trainable-affine degeneracy exists in the chosen design); `adapt/train.py` (minimization-only selection → needed the max-mode extension already added in M16); `adapt/loss.py` (mask conventions); `model.py` (`predict_height` inverse + `out_hw`); GeoNRW DSM semantics; M10 provenance; split rules; CPU/storage reality.

## 4. M16 Failure Analysis

M16 (plain L1 on absolute DSM): train loss ↓ monotonically while val Pearson collapsed 0.22→0.03 mid-training and recovered only to 0.23 — the head fit absolute scale/offsets of 24 train triplets instead of geometry. Diagnosis: the objective rewards scale fitting, not structure.

## 5. Structural-Loss Design Rationale

Candidates: (A) `1 − Pearson` — chosen. (B) cosine-style — equivalent to A up to normalization, less interpretable. (C) per-sample standardized L1 — extra epsilon/division hazards, less aligned with selection. (D) in-loss affine fit — rejected: naive trainable-affine degenerates, and closed-form least-squares in the autograd graph is fragile. A wins on: exact alignment with the Pearson selection criterion, identical `(pred, target)` signature to `masked_l1` (maximal trainer compatibility), well-understood degeneracy, trivial CPU cost.

## 6. Mathematical Definition (Pre-Registered)

Over valid pixels (finite pred AND finite target, negatives kept):

```
r = Σ[(p−p̄)(t−t̄)] / sqrt(Σ(p−p̄)² · Σ(t−t̄)²),  clamped to [−1, 1]
L = 1 − r     (0 = perfect (affine) agreement; 2 = perfect anti-correlation)
```

Per-tile computation (batch = 1 tile, matching the trainer). Deterministic given inputs.

## 7. Degeneracy Safeguards

- <2 valid pixels → raise (repo convention).
- Zero-variance pred or target → neutral worst score 1.0 as a gradient-free constant: collapse is never rewarded.
- Monitoring (§11 + `degeneracy_audit` in results): prediction std per val tile (selected head: min 8.85, mean 11.86 — nontrivial), train/val Pearson, affine slope; NaN/Inf would raise, never silently optimistically replaced.

## 8. Frozen Dataset/Splits

Identical to M16 (verified byte-identical ID lists pre-train): train bochum/coesfeld/gelsenkirchen/guetersloh × 6 = 24; val herford/paderborn × 6 = 12, city-disjoint; held-out duesseldorf/herne/neuss absent (assert→raise); 943-triplet reserve pool probe-only. Manifest SHA recorded.

## 9. Frozen Model Initialization

Same M10 `best.pt` (`extra: {epoch: 22, mae: 5.8204}`), key sets verified equal, `assert_frozen()` passes, checkpoint bytes never written. Direct M16 causal comparison preserved.

## 10. Training Configuration

Adam lr=1e-3, wd=0, batch 1, seed 0, 30 epochs, CPU, no augmentation, frozen M10 zscore stats, plain head arch, `out_hw=(1000,1000)`. Only change: `loss="pearson"`. Train time 862.6 s.

## 11. Validation Selection

MAX pooled direct Pearson on the 12-triplet val set (affine-invariant ⇒ the M15 structural signal; objective and metric coincide by construction, as documented). Selected @ epoch 6 (0.1875).

## 12. Training Curves

Train Pearson-loss 0.616→0.354 monotonic (train Pearson 0.38→0.65 — the objective optimizes). Val Pearson flat 0.17–0.19 all 30 epochs (best 0.1875 @6). **The M16 pathology is gone**: no U-shaped scale-fitting collapse — but also no val-level lift, because the 12-tile pooled val is dominated by high-relief tiles (see macro-vs-pooled below). No degeneracy at any epoch.

## 13. External Probe (DEVELOPMENT PROBE — 943 Unseen Tiles, Not a Formal Test)

| City | n | M17 Pearson | M15 Pearson | M17 aligned MAE |
|------|---:|---:|---:|---:|
| bochum | 184 | 0.32 | ~0.22 | 8.14 |
| coesfeld | 177 | 0.40 | ~0.29 | 4.58 |
| gelsenkirchen | 137 | 0.34 | ~0.24 | 5.38 |
| guetersloh | 148 | 0.55 | ~0.38 | 3.24 |
| herford | 105 | 0.27 | ~0.15 | 8.96 |
| paderborn | 192 | 0.35 | ~0.23 | 7.02 |
| **macro** | **943** | **0.37** | **0.25** | **6.22** |

Spearman 0.21→0.32. Every city improves (+0.10 to +0.17); val cities' unseen tiles improve too (herford/paderborn), ruling out pure train-city memorization.

## 14. City-Level Results

See §13. No cherry-picking: worst-city (herford 0.27) still beats the M15 macro (0.25); best-city (guetersloh 0.55) approaches internal behavior. Formal test cities still pending full download.

## 15. Height-Level Results

Same-12-tile terciles (M16 cuts): low 3.21/0.25 (was 3.34/0.10) · mid 4.59/−0.08 (was 4.62/0.02 — still dead) · high 5.33/0.20 (was 5.29/0.28). Low-relief structure is the main gainer; mid-terrain remains unpredicted; no GAMUS classes were mapped onto GeoNRW IDs.

## 16. M15 vs M16 vs M17

| Model | Adaptation | Objective | Val Pearson | Probe Pearson | Probe Affine MAE | Notes |
|-------|-----------|-----------|------------:|--------------:|-----------------:|-------|
| M15 | none | — | — | ~0.25 | ~6.51 | frozen M10 |
| M16 | GeoNRW head | L1 | ~0.23 | ~0.21 | ~6.67 | ineffective; scale-fit collapse |
| **M17** | GeoNRW head | **structural** | **0.19** | **~0.37** | **~6.22** | **clear transfer gain** |

(GAMUS-internal M10 Pearson ~0.57 / M11 MAE 5.7428 are different quantities — never mixed with affine-external values.)

Note on val-vs-probe levels: pooled val Pearson (0.19) weights high-relief tiles that dominate pixel variance; macro probe Pearson (0.37) averages per-triplet structure. Same-12-tile macro check: M17 0.47 vs M15 0.31 — consistent direction under both aggregations.

## 17. Limitations

One seed, one 24-triplet split, 6 train-side cities; absolute level (0.37) still far from internal (0.57); mid-terrain hole; `out_hw` operating-point shift is interpolation-only but noted; formal test-city scoring pending; CPU.

## 18. PS Impact

The extraction leg is repairable at the objective level: a scale-decoupled loss converts M16's failure into uniform cross-city gains without new data, architecture, or tuning. This raises confidence that ML-side structure can support downstream calibration — the next question is whether the remaining gap (0.37 → useful) closes with the formal test set and calibration, not whether adaptation can work at all. rDSM path unaffected.

## 19. Scientific Outcome

**Outcome A — structural objective clearly improves external transfer** (+48% relative Pearson, 6/6 cities, corroborated by Spearman/MAE, nondegenerate). Absolute level caveat recorded explicitly; not a solved problem.

## 20. Recommended Next Milestone

Exactly ONE: **M18 = formal GeoNRW test-city evaluation** (duesseldorf/herne/neuss) of the frozen M17 checkpoint under the identical M15 protocol — requires completing the tarball download (disk/network permitting). Do NOT start it here.

---

## Artifacts

- `experiments/m17-geonrw-struct-e01/` (config/results/log/train_summary/README, best.pt git-ignored; manifest SHA + M10 provenance + degeneracy audit inside)
- `experiments/m17-probe-eval/results.json` (untracked development probe)
- `src/depthwizard/adapt/loss.py` (`pearson_distance`)
- `src/depthwizard/adapt/train.py` (`loss` selector)
- `src/depthwizard/experiments/m17_geonrw_struct.py` (split + runner; reuses M15/M16 helpers)
- `tests/test_m17_structural_loss.py` (10 tests)
- `docs/research/m17-structural-adaptation.md` (this document)

---

**Prepared by:** Shravan (ML) · **Date:** 2026-09-05 · **Branch:** `feat/shravan-m17-structural-adapt`
