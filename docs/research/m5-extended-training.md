# M5 — Single-Factor Extended Training of the Frozen DA-V2 Adaptation Head

**Date:** 2026-09-04 · **Author:** Shravan (ML) · **Branch:** `feat/shravan-dav2-gamus-extended-training`
**Label:** single-factor extension of M4 · **Experiment:** `experiments/dav2-gamus-head-m5-e01`

## 1. Hypothesis

M4 stopped too early: train loss and validation MAE were still decreasing at epoch 15 (best = epoch 14).
M5 asks whether additional optimization alone improves validation without any model/data change.

## 2. Controlled vs frozen variables

- Controlled (only change): `epochs: 15 → 30`
- Frozen: backbone (DA-V2-Small @ `03876f86…`, Apache-2.0), tap (`output_conv1` input, 1×64×296×296),
  head (64→32→16→1 + bilinear), masked-L1 raw meters, Adam lr=1e-3 wd=0, batch 1 tile, seed 0,
  no augmentation, no scheduler, no normalization, manifest `gamus.m4.manifest.json` (24 train / 8 val),
  test unused. Config diff M4→M5 verified: only `experiment_id` + `epochs`.
- Fresh head initialization (seed 0), NOT resumed from M4 best (weights verified different; debug replicated).

## 3. Reproduction proof

M5 epochs 0–14 are **bit-identical** to M4 e01 `log.jsonl` (all fields, all 15 rows) — same environment,
same protocol. M4 e01 artifacts untouched (tracked files byte-identical; verified via `git diff`).

## 4. Learning curves (val MAE per epoch)

14: 5.4914 (M4 best) → 15: 5.4034 → 16: 5.2467 → 17: 5.2498 → 18: 5.2228 → 19: 5.2557 →
20: 5.1506 → 21: 5.1923 → 22: 5.3231 → **23: 5.1500 (M5 best)** → 24: 5.2540 → 25: 5.4876 →
26: 5.2199 → 27: 5.3160 → 28: 5.6252 → 29: 5.3177. Train MAE fell monotonically 6.69→6.22.
Pearson 0.575→0.631 (peak 0.637 @29); RMSE 8.589→7.369.

## 5. M4 vs M5 (same direct-meters val protocol — valid controlled comparison)

| Metric | M4 | M5 | Δ |
|---|---|---|---|
| best epoch | 14 | 23 | — |
| val MAE | 5.4914 | 5.1500 | −0.3414 (−6.22%) |
| val RMSE | 8.5888 | 7.3685 | −1.2202 |
| median | 2.8925 | 3.4361 | +0.5436 |
| p90 / p95 | 15.365 / 20.136 | 12.769 / 16.117 | −2.596 / −4.019 |
| Pearson / Spearman | 0.575 / 0.572 | 0.631 / 0.586 | +0.056 / +0.014 |
| trainable params | 23201 | 23201 | 0 |
| wall time (CPU) | 430 s | 850 s | — |

## 6. Tail, class, residual behavior

- Height bins MAE: 0–1m 1.651→3.526 (+1.875) · 1–5m 2.391→3.414 (+1.023) · 5–10m 3.681→3.490 ·
  10–20m 8.540→6.294 · 20–30m 15.688→10.500 (−5.188) · 30+m 23.247→16.287 (−6.960). Capacity shifted to tall structures.
- Class MAE: tree 10.310→7.600 (−2.710), buildings 3.943→3.637; ground 1.666→3.478 (+1.812),
  low-veg 2.223→4.247 (+2.023), road 3.301→4.262 (+0.961), water 11.017→13.590 (+2.573, n=2727),
  others 4.804→5.288. Negative-target px MAE 12.296→15.094 (n=6683).
- Residual mean −3.665→−0.761 (systematic under-prediction largely corrected), std 7.767→7.329,
  p5 −20.135→−15.183, p95 +5.511→+10.105.

## 7. Interpretation — Outcome A (continued improvement), with caveats

M4 under-trained: validation improved substantially with more optimization. Late-epoch oscillation
(ep25 5.49, ep28 5.63) suggests diminishing returns past ~epoch 23, but no overfit signature
(train still falling; val best at 23, not early). Trade-off accepted consciously: low/ground accuracy
regressed while tall-structure error fell sharply — consistent with L1 allocating capacity to large
residuals, not with a protocol breach (masking/targets unchanged).

## 8. Decision

**M5 becomes the current adaptation reference** (best val MAE 5.1500 @23). M4 e01 remains frozen history.
Magnitude note: −6.2% MAE is modest but real on 8.4M val pixels, concentrated where M4 failed worst
(30+m −30%, residual bias −79%).

## 9. Next experiment (one factor only)

Per §43 rules: train-set-only target normalization to address the remaining tall-tail error and the
low-bin regression — OR a geographic validation study. Not both, no architecture/loss/augmentation
changes, no fine-tuning, no DA3.

## 10. Reproducibility

```bash
pip install -e ".[dev]" && pip install -e ".[dav2]"
PYTHONPATH=src:<pinned-DA-V2-clone @ a561b84> python -m depthwizard.experiments.adapt_dav2 \
  --manifest manifests/gamus.m4.manifest.json --experiment-id dav2-gamus-head-m5-e01 \
  --epochs 30 --lr 1e-3 --seed 0 --output experiments/dav2-gamus-head-m5-e01 --visuals
python -m pytest -q
```

Backbone/checkpoint/dataset pins identical to M4. Test split untouched. Memory: not measured. CPU-only.
Geographic limitation stands: 100% DC-prefix at this scale; no generalization claim.
