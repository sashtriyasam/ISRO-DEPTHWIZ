# Remote-Sensing Adaptation — Frozen DA-V2-Small + Lightweight Head (M4)

**Date:** 2026-09-04 · **Author:** Shravan (ML) · **Branch:** `feat/shravan-dav2-gamus-adaptation`
**Experiment A:** `experiments/dav2-gamus-head-m4-e01` (scientific) + `m4debug` temp run (debug only)

## 1. Hypothesis

A lightweight trainable head on FROZEN Depth Anything V2 Small representations can learn a useful
overhead-imagery → GAMUS nDSM/AGL mapping, reducing the domain gap observed in M3 (frozen relative
depth ≈ zero/negative correlation with nDSM) without expensive full-model fine-tuning.

## 2. M3 frozen baseline reference (unchanged)

- Bring-up (3 train tiles): aligned MAE mean 9.302 m, RMSE 10.921 m, Pearson −0.067, Spearman +0.077
- `experiments/depth-anything-v2/bringup-cpu-3tile/` untouched by M4
- Same-val reference recomputed in M4 on the 8 val tiles (declared affine protocol): aligned MAE mean **5.798 m**
- Semantics differ (M3 relative+aligned vs M4 direct meters) — §17 states the comparison rule

## 3. Dataset & revision

- HF `earthflow/GAMUS` @ `a3c0e251...` (M1 pin); manifest `manifests/gamus.m4.manifest.json` (32 records, probed)
- Train: first 24 sorted train tiles (DC_01_25…DC_06_29 — ALL `DC` prefix, zero city diversity at this scale)
- Val: first 8 sorted val tiles (DC_02_26…DC_11_33 — ALL `DC` prefix)
- Test: NEVER downloaded, never used
- Target: float32 meters, raw, unclipped; labels float32 integer-valued (M2 finding, reused)

## 4. Train/validation protocol

- Train split fits (masked L1, Adam lr=1e-3, wd=0, batch=1 tile, 15 epochs, seed 0, no augmentation)
- Val split selects (best val MAE; e01 best = epoch 14)
- Sorted manifest order, no shuffle, no re-split; train/val ID overlap guarded in code (raises)
- Debug first: 2 train tiles × 2 epochs in temp dir — loss 12.47→12.26, checkpoint roundtrip OK — then scientific run

## 5. Feature representation

- Source: input tensor to `depth_head.scratch.output_conv1` (`path_1`, deepest fused DPT scale), read-only forward hook; no upstream modification; frozen `infer` path intact
- Measured: (1,64,296,296) float32 for 1024px tiles @518 working resolution; gradients disabled (`no_grad` + `requires_grad False` asserted every epoch and in tests)
- Why: dense spatial map (per-pixel regression), multi-scale fusion without own pyramid, 64ch keeps head tiny

## 6. Head architecture

`conv3x3(64→32)+BN+ReLU → conv3x3(32→16)+BN+ReLU → conv1x1(16→1) → bilinear→1024²`, no final nonlinearity (negatives preserved). Kaiming init (seeded).

## 7. Parameter counts (measured)

Backbone total 24,785,089 / trainable 0; head total 23,201 / trainable 23,201; model total 24,808,290. Trainable fraction ≈ 0.09% — quantitatively lightweight.

## 8. Loss

Masked L1 on raw meters over finite-pred AND finite-target pixels (negatives incl. −5.0 kept); raises on zero-valid instead of fake zero. Formulation in `src/depthwizard/adapt/loss.py`.

## 9. Target handling

Raw meters, no normalization (`TargetScale("raw")` identity; unknown modes raise — no leakage surface). Continuous bilinear only on the PREDICTION upsampling; target never resampled (full-tile 1024 alignment preserved).

## 10. Preprocessing

RGB uint8 1024² → official-equivalent backbone input @518 (aspect-kept lower-bound ×14 snap, INTER_CUBIC, ImageNet norm, CHW). Prediction bilinear→1024². Labels unused in training (val analysis only, nearest-exact values).

## 11. Optimizer & hyperparameters

Adam, lr=1e-3, weight_decay=0, batch=1 tile, epochs=15, seed=0, no scheduler/warmup/clipping. Conservative proof-of-concept; no hyperparameter search performed.

## 12. Checkpoint-selection rule

Best val MAE (epoch 14, 5.4914 m). `checkpoints/best.pt` inside experiment dir (git-ignored `*.pt`); payload = head state + tap/input-size/semantics + epoch. Restored before final val analysis.

## 13. Metrics (val, n=8 tiles / 8,388,608 px, direct meters)

MAE 5.491 · RMSE 8.589 · median 2.892 · p90 15.365 · p95 20.136 · Pearson 0.575 · Spearman 0.572 · coverage 100%.
Train MAE 6.691 vs val 5.491 — no memorization signature (val distribution has more low ground).

Height bins (target): 0–1m MAE 1.651 (36.2%) · 1–5m 2.391 (14.9%) · 5–10m 3.681 (17.7%) · 10–20m 8.540 (18.7%) · 20–30m 15.688 (8.0%) · 30+m 23.247 (4.4%). Error grows with height (long tail). Negative-target px (n=6683): MAE 12.296.

Per class: ground 1.666 · low-veg 2.223 · road 3.301 · buildings 3.943 · others 4.804 · tree 10.310 · water 11.017 (n=2727, tiny).
Residual: mean −3.665 m (systematic under-prediction of tall structures), std 7.767, p5 −20.135, p95 +5.511.

## 14. Leakage limitations

Train AND val are 100% `DC`-prefix at this deterministic scale (sorted-first selection); full-distribution listing shows DC/PHL shared across splits. NO geographic-generalization claim. Test unused. City-level leakage status: still unresolved (M1/M2 standing finding).

## 15. Results (Experiment A)

- Learning: train loss 8.898→6.691 monotone; val MAE 7.410→5.491; val Pearson 0.085→0.575 across 15 epochs (curve still descending at epoch 14 — noted, not chased; one factor at a time)
- Structural: Pearson/Spearman ≈ 0.57 vs M3 ≈ 0 — frozen features DO contain usable aerial-height signal once a metric head is learned
- Failure modes: tall trees/canopy underestimated (tree MAE 10.3, 30+m bin 23.2); −5.0-region pixels high error (12.3); smoothing of fine detail; residual bias −3.7 m

## 16. Comparison (semantics-explicit, §43-compliant)

M4 validation MAE = 5.491 m (direct nDSM/AGL meters, 8 val tiles) versus M3's scale-aligned research MAE = 5.798 m on the SAME 8 val tiles (relative depth + per-image affine eval) and 9.302 m on the original 3-tile bring-up. These are different output/evaluation semantics and therefore NOT a direct apples-to-apples improvement claim. What IS comparable: structural correlation 0.57 (M4) vs ≈0 (M3) shows the head learned real height structure the frozen baseline lacks.

## 17. Failure modes & next experiment

Evidence points to: (a) longer training / mild LR schedule (curve still descending); (b) target normalization experiment (tall-tail under-prediction); (c) different feature layer (earlier DPT scale for detail). Exactly ONE factor next: extend epochs (Experiment B candidate) OR train-set normalization (Experiment D candidate) — not both. Geographic validation study and DA3 remain later milestones.

## 18. Reproducibility

```bash
pip install -e ".[dev]" && pip install -e ".[dav2]"
export GAMUS_ROOT=data/gamus   # 24 train + 8 val tiles per §3 (acquire.py or manual)
PYTHONPATH=src:<pinned-DA-V2-clone> python -m depthwizard.experiments.adapt_dav2 \
  --manifest manifests/gamus.m4.manifest.json --experiment-id dav2-gamus-head-m4-e01 \
  --epochs 15 --lr 1e-3 --seed 0 --output experiments/dav2-gamus-head-m4-e01 --visuals
python -m pytest -q
```

Backbone: `DepthAnythingV2-Small` @ `03876f86...` (Apache-2.0); upstream code @ `a561b84`. No calibration engine involvement; adapted output is research metric prediction, not calibrated elevation.

---

# M5 — Single-Factor Extended Training (epochs 15 -> 30)

**Branch:** `feat/shravan-dav2-gamus-extended-training` - **Experiment:** `experiments/dav2-gamus-head-m5-e01`
**Full report:** `docs/research/m5-extended-training.md` (this section summarizes; numbers identical).

- Controlled change: epochs only (config diff verified: `experiment_id` + `epochs`). All else frozen.
- Reproduction: M5 epochs 0-14 bit-identical to M4 e01 log; M4 artifacts untouched.
- Result: best val MAE **5.1500 @epoch 23** vs M4 5.4914 @14 -> **dMAE -0.3414 (-6.22%)**; RMSE -1.22;
  Pearson +0.056; 30+m bin 23.247->16.287; residual mean -3.665->-0.761. Low bins regressed
  (0-1m +1.875, ground +1.812) - capacity shift, not protocol breach.
- Outcome A (M4 under-trained); late oscillation past ~23 noted. **M5 is the current adaptation reference.**
- Next: exactly one of (train-only target normalization) or (geographic validation study).
