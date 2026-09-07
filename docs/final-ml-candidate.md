# Final ML Candidate — Release Document (PS 26175)

**Date:** 2026-09-05 · **Author:** Shravan (ML/data) · **Branch:** `feat/shravan-final-ml-release`
**Status:** `FINAL ML CANDIDATE = LOCKED (M17)` — with the formal test-city verification defined below as pure verification (test cities played zero role in selection).

---

## 1. Executive Decision

**M17** — frozen DA-V2-Small + M10-initialized 23k head adapted with the Pearson structural objective on 24 GeoNRW train triplets (epoch 6). Uniform external gains over M10 (Pearson 0.25→0.37 macro, 6/6 cities, 3/3 height terciles), determinism-verified, degeneracy-free. DA3 rejected with evidence. Formal duesseldorf/herne/neuss scoring is blocked on data access (quantified) and remains pending as verification-only.

## 2. PS 26175 Alignment

PS needs RGB→elevation→calibration→rDSM/metric-DSM→textured 3D→flythrough, 50% DSM accuracy across landscapes + 50% rendering/UX. ML owns extraction (relative representation + validity + provenance); calibration/DSM/export/rendering belong to Shivam/Aryan tracks. This decision serves the extraction leg only.

## 3. Candidate History

M10 (5.8204 internal) → M11 stable (5.7428±0.0573) → M13 rejects 2× weighting (5.9323, Outcome 2) → M15 exposes external gap (0.25) + DSM≠nDSM gate → M16 L1 adaptation fails (0.21, scale-fit collapse, Outcome C) → M17 structural adaptation succeeds on probe (0.37, Outcome A). Each rejection was for cause; nothing selected on GAMUS MAE alone or novelty.

## 4. External Dataset / Target Semantics

GeoNRW target = absolute DSM (first-return LiDAR, meters, DHHN92 — verified on file headers). GAMUS = nDSM/AGL. DA-V2 = relative camera depth. DFC2022 = bare-earth DTM (reference only). SIH2026 repo = PS text only, no samples. Direct cross-quantity MAE is invalid; affine-structural comparison is the defensible metric.

## 5. Formal Evaluation Protocol

Per-triplet affine fit + Pearson/Spearman on finite∩valid pixels; RGB first-3 channels; output pinned to source grid; frozen M10 zstats; cities separate + macro + triplet-weighted micro; single frozen run per checkpoint. Formal test cities: BLOCKED (see §6 of selection evidence: xet 1 byte/6 min fresh attempt; 29 GB free on C vs 32 GB tarball; IEEE login wall).

## 6. M10 Baseline

Same 943-triplet probe: macro Pearson 0.25 / MAE 6.57; terciles 0.28/0.29/0.18; city Pearson 0.15–0.38. M10 `best.pt` SHA256 `B3DFD54F…` (epoch 22), untouched.

## 7. M17 Results

Probe macro Pearson **0.37** / Spearman 0.32 / aligned MAE 6.22 (943 unseen tiles); val-12 macro 0.47; terciles 0.42/0.42/0.28; nondegenerate (val pred-std min 8.85); rerun reproduced city macros to 4 decimals.

## 8. M10 vs M17 Comparison

| City (n) | M10 P | M17 P | ΔP | M10 MAE | M17 MAE |
|---|---:|---:|---:|---:|---:|
| bochum (178) | 0.22 | 0.32 | +0.10 | 8.40 | 8.14 |
| coesfeld (171) | 0.29 | 0.40 | +0.11 | 4.87 | 4.58 |
| gelsenkirchen (131) | 0.22 | 0.34 | +0.12 | 5.65 | 5.38 |
| guetersloh (142) | 0.38 | 0.55 | +0.17 | 3.78 | 3.24 |
| herford (105) | 0.15 | 0.27 | +0.12 | 9.23 | 8.96 |
| paderborn (216) | 0.22 | 0.35 | +0.13 | 7.49 | 7.02 |
| macro (943) | 0.25 | 0.37 | +0.12 | 6.57 | 6.22 |
| micro (≈tw) | — | — | — | 6.57 | 6.21 |

## 9. Height-Level Results

Frozen tercile cuts [80.50, 111.01] m (triplet-mean-target): low 0.28→0.42, mid 0.29→0.42, high 0.18→0.28 (MAE improves in all three). Broad, not regime-specific. No class crosswalk (never equated).

## 10. Geographic Results

Six unseen German cities, all improve; worst (herford 0.27) beats M15 macro (0.25). No nationwide/global claim — scope is exactly these cities.

## 11. DA3 Decision

`NOT SCIENTIFICALLY JUSTIFIED`: metric variant needs focal length (absent from triplets); zero-shot-vs-adapted confounds backbone with adaptation; CPU lab infeasible above Small; Giant/Nested NC-licensed; no aerial relevance. Revisit triggers: GPU + intrinsics-bearing set + GeoNRW baseline to beat.

## 12. Final Model Configuration

Backbone DA-V2-Small frozen (`output_conv1`, 1×64×296×296); head 64→32→16→1 (~23,201 trainable); M10-init → 30-epoch Pearson adaptation (24 triplets, Adam 1e-3, seed 0); checkpoint `experiments/m17-geonrw-struct-e01/checkpoints/best.pt`, SHA256 `D7C0BE91…EDAC`, `extra: {epoch: 6, pearson: 0.1875}`; DA-V2 upstream `a561b84` (re-verified live); GeoNRW `torchgeo/geonrw @ eeb5fc3e`, set SHA `012c318944ef205f`; ID lists in `m16-geonrw-adapt-e01/results.json` + `m17-probe-eval/results.json`.

## 13. Final Preprocessing

RGB HWC uint8 → first-3 channels → ImageNet/518 pipeline; output follows source grid; frozen M10 zstats (mu 8.037330237035235 / sigma 10.304011604437477); nodata→NaN; finite mask; negatives kept. FROZEN — no post-freeze changes.

## 14. Final Output Semantics

Relative geometric representation (`depth_scale = RELATIVE`, `is_metric = False`, units None). Validity = finite-mask behavior. No confidence channel (DA-V2 supplies none; affine a/b eval-only). **NOT metric DSM.**

## 15. Runtime

CPU-only validated; ~1.5–2 s/tile/forward (observed 943-triplet probe ≈ 25–30 min); M17 training 862.6 s / 30 epochs; RAM: single-tile batch, no measurement beyond feasibility. Giant-class models infeasible in this lab.

## 16. Failure Cases

Mid-terrain tercile weak in absolute terms; near-zero Pearson tiles exist; high-relief tiles dominate pooled stats (macro-vs-pooled gap); relief compression (slopes <1) persists; datum offset makes raw MAE meaningless (~97 m diagnostic); water-class seed sensitivity (M11); best-at-final-epoch confound closed by M13 only for the weighted loss.

## 17. Limitations

Moderate absolute correlation (0.37 vs 0.57 internal); one-seed M17; 6 train-side cities; formal test cities pending; calibration undemonstrated; CPU-only; dl-de/by-2.0 attribution + Baier et al. citation required for GeoNRW-derived artifacts.

## 18. Reproducibility

Commands: M17 train (`adapt_dav2_m12.py` lineage → `m17_geonrw_struct`, `--seed 0`, 30 epochs) + M15-protocol probe (`m15_geonrw_eval`, `--target-mu/sigma` M10 values). Provenance: checkpoint SHAs + `a561b84` + `eeb5fc3e` + set SHA `012c318944ef205f` (§12). Determinism verified by exact rerun. No stale metadata (config values verified against runtime in M17/M13 sessions).

## 19. Shivam Handoff

```text
Final ML candidate: M17 (DA-V2-Small frozen + Pearson-adapted 23k head, epoch 6)
Checkpoint: experiments/m17-geonrw-struct-e01/checkpoints/best.pt
SHA-256: D7C0BE9127FAFAC5F4C2D207E3626D335AF148A8CBB7489A10EE8C7F7DA4EDAC
ML output semantics: RELATIVE (is_metric=False, units None)
Input assumptions: RGB HWC uint8, any H/W, ImageNet/518 pipeline, first-3-channels
Preprocessing: frozen §13; nodata→NaN; negatives kept
Validity: finite-mask behavior; no confidence channel
External evidence: probe Pearson 0.37 (6/6 cities over M10 0.25); slopes <1 persist
Known limitations: §17 (moderate correlation, compression, mid-terrain hole, test cities pending)
Calibration may assume: relative ordering per §8, validity/provenance, frozen preprocessing
Calibration must NOT assume: metric scale, uniform global bias, affine-MAE-as-calibrated-accuracy
```

## 20. Aryan Handoff

```text
Final ML candidate: M17 (relative height maps; checkpoint above)
Input: RGB HWC uint8 (PNG/JPG now; GeoTIFF ingest is a known ML-track gap)
Output raster behavior: follows source image grid (out_hw = H/W)
Relative-vs-metric semantics: RELATIVE ONLY until Shivam's calibration stage
Validity: finite-pixel mask accompanies every output
Confidence: none available
Visualization assumptions: source-grid relative relief + validity + provenance
Visualization restrictions: NEVER assume metric heights or calibrated DSM; consume the rDSM/DSM product boundary, not checkpoint internals or training scripts/GAMUS assumptions
```

## 21. Final Recommendation

**M17** — strongest defensible, externally validated, reproducible, deployable representation within our constraints.

## 22. Freeze Statement

```text
FINAL ML CANDIDATE = LOCKED (M17; model/config/protocol/provenance frozen §§9,12–14,18; formal test-city scoring pending as pure verification with zero selection role)
```

---

**Prepared by:** Shravan (ML) · **Date:** 2026-09-05 · **Branch:** `feat/shravan-final-ml-freeze`
