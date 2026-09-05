# M16 — Controlled GeoNRW Adaptation Probe From Frozen M10

**Date:** 2026-09-05
**Author:** Shravan (ML/data)
**Branch:** `feat/shravan-m16-geonrw-adapt`
**Experiment:** `experiments/m16-geonrw-adapt-e01` (train) · `experiments/m16-probe-eval/` (development probe, untracked)
**Frozen base:** M10 seed-0 `best.pt` (epoch 22, val MAE 5.8204; head-only state, never modified)
**Outcome: C — adaptation ineffective.**

---

## 1. Objective

Answer whether a small, controlled GeoNRW head adaptation of the existing M10 model recovers meaningful external structural information — not whether GeoNRW MAE can be made to look better, not GAMUS performance, not test-tuned results.

## 2. PS Alignment

PS 26175 needs RGB→elevation→calibration→DSM/rDSM→3D. M16 tests the elevation-extraction leg: if head adaptation cannot recover structural correlation on real DSM, the downstream calibration stage would have nothing worth calibrating, and the M10 recipe cannot carry the DSM-accuracy half of the evaluation.

## 3. Pre-Implementation Study

Studied before any code: PS text; AGENTS.md ownership rules; M14 audit; M15 report + probe artifacts (979 triplets/6 cities, affine macro 6.51/Pearson 0.25, DSM-not-nDSM gate, no-resampling grids, `out_hw` behavior); GeoNRW organization (Dataset4EO `train_list` 40 cities incl. all 6 local ones; `test_list` = duesseldorf/herne/neuss, absent locally); M10 recipe (30 epochs, Adam 1e-3, zscore, plain masked L1); `train.py` (minimization-only selection → needed a max-mode extension for Pearson); `model.py` (`predict_height` inverse + `out_hw`); `eval/alignment.py` (affine protocol); CPU/storage reality (24-triplet budget ≈ M10's 13-min scale).

Decisions forced by evidence: (a) city-disjoint val (stronger than tile-disjoint given 1 km² spatial autocorrelation); (b) Option A frozen M10 z-score stats (preserves head output semantics at init; selection metric is affine-invariant so the choice cannot bias selection); (c) 30 epochs to match M10 exactly; (d) probe on all 943 reserve triplets (every tile OOD for GAMUS-only M10); formal test cities stay pending (bytes absent).

## 4. GeoNRW Target Semantics

Absolute DSM: first-return LiDAR surface elevation, meters, DHHN92 vertical datum (verified on real file headers in M15). Not nDSM/AGL, not DTM, not camera depth. No DTM available → no DSM−DTM derivation (would fabricate reference). Scoring uses the affine structural protocol only; direct MAE is datum-offset diagnostic.

## 5. Split / Leakage Audit

- Adaptation-train: bochum, coesfeld, gelsenkirchen, guetersloh — first 6 sorted stems each = **24 triplets** (matches M10's 24-tile budget).
- Adaptation-val: herford, paderborn — first 6 sorted stems each = **12 triplets**, city-disjoint.
- Held-out: duesseldorf/herne/neuss — **absent from local pool** (audit asserts presence→raise); plus 943 reserve triplets (probe only, post-selection).
- Verified pre-train by script: train∩val=∅, train∩test=∅, val∩test=∅, city sets disjoint, 16/4/4-style counts exact, M10 mu/sigma constants, head-key compatibility, backbone frozen. Manifest SHA `manifest_sha` recorded in results (see artifacts).

## 6. M10 Initialization

Fresh seed-0 head via `AdaptedDepthModel.from_backend`, then `head.load_state_dict` from M10 `best.pt` (`extra: {epoch: 22, mae: 5.8204}`); key sets verified equal pre-train; `assert_frozen()` passes; `target_scale` set to frozen M10 zscore. M10 checkpoint bytes never written (mtime preserved). This tests domain adaptation from the candidate, not fresh training.

## 7. Adaptation Protocol

Plain masked L1 in z-space (finite pred AND finite target; negatives kept) with explicit frozen M10 `TargetScale` (no auto-compute, no GeoNRW stats, no M7 values). `out_hw=(1000,1000)` so predictions land exactly on target pixels (no resampling either side).

## 8. Frozen Factors

Backbone, tap (`output_conv1`), head arch (23,201 trainable), preprocessing (518), loss family, optimizer, LR, batch, seed, augmentation (none), target stats, selection data. Only data domain changed (GAMUS→GeoNRW-train-cities).

## 9. Single Experimental Factor

```
GAMUS-trained M10 head → GeoNRW train-city adaptation (24 triplets, 30 epochs)
```

Documented infrastructure addition (not a factor): `selection_mode="max"` in `train.py` (default `"min"` preserves all legacy behavior), required because the hypothesis demands Pearson selection and the trainer only minimized.

## 10. Training Configuration

Adam lr=1e-3, wd=0, batch 1, seed 0, 30 epochs, CPU, fresh M10-init head. Train time 860.3 s. Weighted train z-loss falls 5.77→1.11 monotonically.

## 11. Validation / Checkpoint Selection

MAX pooled direct Pearson on the 12-triplet city-disjoint val set (affine-invariant ⇒ the M15 structural signal). Curve: 0.11 (ep0) → 0.22 (ep1–2) → **collapse to 0.03–0.07 (ep3–17)** while train loss keeps falling → recovery to **0.23 @ ep25 (selected)** → oscillation. The mid-training collapse is itself evidence: the head rapidly overfits the 24 train triplets' absolute scale, destroying structural correlation; late recovery never exceeds the M10-init level. Direct val MAE falls 97→46 monotonically — meaningless (datum fitting), which is exactly why Pearson selection was specified.

## 12. External Test Protocol

No formal held-out test exists locally (test cities absent) — so NO formal test is claimed. Development probe: all 943 non-train/val triplets, evaluated once post-selection with the frozen M15 protocol. Labeled probe throughout; formal test-city scoring remains pending full download.

## 13. Results

| Model | Data | Adaptation | External Pearson | External Affine MAE | Notes |
|-------|------|-----------|-----------------:|--------------------:|-------|
| M15 frozen M10 | GeoNRW | none | ~0.25 | ~6.51 | external baseline (979) |
| **M16** | GeoNRW | head, 24 triplets | **0.21 (probe)** / 0.23 (val-selected) | **6.67** / 6.51 | **no robust gain** |

Internal reference: M10 Pearson ~0.57; M11 mean MAE 5.7428 ± 0.0573 (GAMUS quantities — not directly comparable to external affine values; stated once, clearly).

## 14. City-Level Analysis (Probe, 943 Unseen Tiles)

| City | n | M16 Pearson | M15 Pearson (same tiles) | M16 aligned MAE |
|------|---:|---:|---:|---:|
| bochum | 184 | 0.19 | ~0.22 | 8.52 |
| coesfeld | 177 | 0.11 | ~0.29 | 5.22 |
| gelsenkirchen | 137 | 0.23 | ~0.24 | 5.69 |
| guetersloh | 148 | 0.27 | ~0.38 | 3.99 |
| herford | 105 | 0.20 | ~0.15 | 9.19 |
| paderborn | 192 | 0.26 | ~0.23 | 7.38 |
| macro | 943 | **0.21** | **0.25** | **6.67** |

No city improves robustly; coesfeld (0.29→0.11) and guetersloh (0.38→0.27) degrade. Do not cherry-pick herford/paderborn micro-gains. (M15 same-tile values aggregated from stored per-triplet results for the identical 943 set.)

## 15. Height Analysis

Val-pool terciles of the absolute target (5.9–183.3 m, mean 116.6): low (<107.8 m) MAE 3.34/Pearson 0.10; mid MAE 4.62/Pearson 0.02 (no structure); high (>126.4 m) MAE 5.29/Pearson 0.28. Structure concentrates in high relief; mid-terrain unpredicted. (Bins defined from target terciles, fixed from target data — not tuned; GAMUS classes never mapped onto GeoNRW IDs.)

## 16. Training Curves

Train z-loss monotonic down; val Pearson U-shaped (0.22 → 0.03 → 0.23); val direct-MAE monotonic down (scale fitting). Selection @25 is a local late peak, not a trend break — neighboring epochs oscillate ±0.02.

## 17. M15 vs M16 Comparison

Pearson 0.25 → 0.21 (probe); affine MAE 6.51 → 6.67; RMSE/Spearman move with Pearson; slopes stay <1. The val-set 0.23 does not survive outside selection. Verdict: no improvement; if anything, slight degradation from overfitting absolute scale.

## 18. PS Impact

Lowers confidence that head-only adaptation bridges the GAMUS→real-DSM gap: the M10 head is already at its correlation local optimum, and 24-triplet L1 adaptation overfits scale instead of learning structure. Raises the stakes for the calibration track only modestly — calibration cannot fix uncorrelated structure. The rDSM path (relative output on any RGB) is unaffected. Implication for the system: DSM accuracy will need either genuinely structural supervision (multi-view/DTM-referenced) or a different representation — not more of the same head-tuning.

## 19. Scientific Outcome

**Outcome C — adaptation ineffective.** Little/no improvement (probe Pearson below baseline; val at baseline); the training dynamics explain why (scale overfit). Not a blocker (D): the protocol executed validly.

## 20. Recommended Next Milestone

Exactly ONE: **M17 = scale-decoupled structural adaptation probe** — same frozen M15 protocol/splits, but a loss that cannot reward absolute-scale fitting (e.g. scale-shift-invariant correlation-style objective on the 24 triplets), testing whether the failure is the L1-on-absolute-DSM formulation rather than adaptation per se. Do NOT start it here.

---

## Artifacts

- `experiments/m16-geonrw-adapt-e01/` (config/results/log/train_summary/README, best.pt git-ignored; manifest SHA + M10 provenance inside)
- `experiments/m16-probe-eval/results.json` (untracked development probe, 943 triplets)
- `src/depthwizard/experiments/m16_geonrw_adapt.py` (split + runner; reuses M15 loader/evaluator)
- `src/depthwizard/adapt/train.py` (`selection_mode` minimax extension, default-preserving)
- `tests/test_m16_geonrw_adapt.py` (9 tests)
- `docs/research/m16-geonrw-adaptation.md` (this document)

---

**Prepared by:** Shravan (ML) · **Date:** 2026-09-05 · **Branch:** `feat/shravan-m16-geonrw-adapt`
