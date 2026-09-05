# Final ML Candidate Selection for SIH PS 26175

**Date:** 2026-09-05
**Author:** Shravan (ML/data)
**Branch:** `feat/shravan-final-ml-freeze`
**Type:** Decision document (no training; one frozen verification rerun of stored artifacts only)

---

## 1. Executive Decision

**Final ML candidate: M17** — frozen DA-V2-Small backbone + M10-initialized 23k head adapted with the Pearson structural objective on 24 GeoNRW train triplets (checkpoint `experiments/m17-geonrw-struct-e01/checkpoints/best.pt`, epoch 6). It beats frozen M10 on every evaluated external city, height tercile, and corroborating metric, with no degeneracy and byte-reproducible results. DA3 is rejected with evidence (not justified for the freeze). Formal duesseldorf/herne/neuss test scoring is BLOCKED on data access (quantified below) and remains pending as a pure verification rerun — it played zero role in this selection.

## 2. PS 26175 Requirements

Single-view RGB → elevation → calibration → rDSM (PNG/JPG) / metric DSM (GeoTIFF) → textured 3D → flythrough; 50% DSM accuracy across urban/sparse/hilly/forested scenes, 50% rendering/UX. The ML decision serves the extraction leg: relative geometric representation + validity + provenance into Shivam's calibration layer.

## 3. Candidate History

- **M10** (5.8204 m GAMUS val): internal reference; plain z-score L1.
- **M11** (5.7428 ± 0.0573): stability confirmed. Kept as internal yardstick.
- **M13** (5.9323): 2× low-height weighting rejected (Outcome 2; best @54 proves budget sufficed).
- **M15** (frozen M10 → GeoNRW probe): Pearson 0.25 / affine MAE 6.51; established DSM≠nDSM gate, no-resampling grids, affine protocol.
- **M16** (L1 adaptation): probe 0.21 — rejected (Outcome C; scale-fitting collapse diagnosed).
- **M17** (Pearson adaptation): probe 0.37 — uniform gains, no degeneracy.
- Rejected for cause at each step; nothing selected on GAMUS MAE alone or on novelty.

## 4. External Data Semantics

GeoNRW target = absolute DSM (first-return LiDAR, meters, DHHN92 — verified on file headers). GAMUS = nDSM/AGL. DA-V2 = relative camera depth. DFC2022 = bare-earth DTM (reference only). SIH2026 repo = PS text only, no samples (blocker for official validation). Direct MAE across quantities is invalid; affine-structural comparison is the defensible metric.

## 5. Formal Test Protocol (Frozen)

Per-triplet affine fit (`target ≈ a·pred + b`, least squares) + Pearson/Spearman on finite∩valid pixels (nodata −9999 excluded, negatives kept); RGB first-3 channels; model output pinned to source grid (`out_hw` = target size, no resampling); M10 zscore stats for both candidates; cities reported separately + macro + triplet-weighted micro; single frozen run per checkpoint; determinism verified (M17 rerun reproduced city macros to 4 decimals).

## 6. M10 vs M17 (943-Triplet Development Probe — NOT Formal Test Cities)

| City | n | M10 Pearson | M17 Pearson | Δ | M10 MAE | M17 MAE |
|------|---:|---:|---:|---:|---:|---:|
| bochum | 178 | 0.22 | 0.32 | +0.10 | 8.40 | 8.14 |
| coesfeld | 171 | 0.29 | 0.40 | +0.11 | 4.87 | 4.58 |
| gelsenkirchen | 131 | 0.22 | 0.34 | +0.12 | 5.65 | 5.38 |
| guetersloh | 142 | 0.38 | 0.55 | +0.17 | 3.78 | 3.24 |
| herford | 105 | 0.15 | 0.27 | +0.12 | 9.23 | 8.96 |
| paderborn | 216 | 0.22 | 0.35 | +0.13 | 7.49 | 7.02 |
| **macro** | **943** | **0.25** | **0.37** | **+0.12** | **6.57** | **6.22** |
| micro (≈triplet-weighted) | | | | 6.57 | 6.21 | −0.36 |

Spearman 0.21→0.32; slopes stay <1 both (M10 city-mean-a 0.57–0.87; M17 0.23–0.32 — relief still compressed, structure better ordered). Height terciles (frozen cuts 80.50/111.01 m triplet-mean): low 0.28→0.42, mid 0.29→0.42, high 0.18→0.28 (MAE improves in all three) — broad, not regime-specific. **Classification: clearly better** (uniform, corroborated, nondegenerate) on available evidence.

## 7. DA3 Decision

```text
NOT SCIENTIFICALLY JUSTIFIED
```

1. Fair eval: metric variant needs focal length — GeoNRW triplets carry no intrinsics → unfair. 2. Semantics mappable only for the relative variant. 3. Licensing: Small/Mono Apache-2.0 OK, but Giant/Nested NC-licensed. 4. Compute: CPU-only lab cannot execute above Small; 943-triplet CPU eval infeasible on useful scales. 5. Materiality: zero-shot DA3 vs adapted-M10 confounds backbone with adaptation — a fair fight needs DA3 adaptation = a new research track, not a freeze gate. 6. Test-set safety: possible but moot given 1–5. Revisit triggers: GPU access + intrinsics-bearing eval set + a GeoNRW baseline to beat.

## 8. Final Candidate Comparison

| Candidate | Internal Evidence | External Pearson | External MAE | Stability | Deployment | License | Decision |
|-----------|-------------------|-----------------:|-------------:|-----------|------------|---------|----------|
| M10 | 5.8204; stable base | 0.25 | 6.57 | n/a (base) | CPU-ok | Apache-2.0 ckpt | superseded externally |
| M17 | val-selected, nondegenerate | **0.37** | **6.22** | 6/6 cities + 3/3 terciles | CPU-ok | Apache-2.0 ckpt | **SELECTED** |
| DA3 | none on aerial | untested | untested | unknown | CPU-infeasible | mixed (NC on large) | rejected (evidence §7) |

## 9. Final Model Configuration

Backbone DA-V2-Small (frozen, `depth_head.scratch.output_conv1`, 1×64×296×296); head conv3x3(64→32)+BN+ReLU, conv3x3(32→16)+BN+ReLU, conv1x1(16→1) (~23,201 trainable); M10-init → 30-epoch Pearson adaptation (24 triplets, Adam 1e-3, seed 0); checkpoint `experiments/m17-geonrw-struct-e01/checkpoints/best.pt`, SHA256 `D7C0BE9127FAFAC5F4C2D207E3626D335AF148A8CBB7489A10EE8C7F7DA4EDAC`, `extra: {epoch: 6, pearson: 0.1875}`; DA-V2 upstream `a561b84` (re-verified live); M10 base SHA256 `B3DFD54F…`; GeoNRW `torchgeo/geonrw @ eeb5fc3e`, triplet set SHA `012c318944ef205f`; train/val/probe ID lists in `m16-geonrw-adapt-e01/results.json` + `m17-probe-eval/results.json`.

## 10. Final Preprocessing

RGB HWC uint8 → first-3-channels (RGBI slice) → ImageNet normalize/518 pipeline (unchanged `preprocess_rgb`); model output interpolated to source grid (`out_hw` = target H/W); zscore with frozen M10 mu/sigma only for head I/O; nodata −9999 → NaN; finite∩valid mask; negatives kept.

## 11. Final Output Semantics

**Relative geometric representation** (`depth_scale = RELATIVE`, `is_metric = False`, units None). NOT metric DSM. Validity = finite-mask behavior above. Confidence: none provided (DA-V2 supplies none; affine `a/b` are eval-only, never shipped as confidence).

## 12. Known Limitations

External Pearson still moderate (0.37 vs internal 0.57); mid-terrain tercile weak in absolute terms; one-seed M17 (seed-0 only); 6 train-side cities (formal test cities pending); slopes <1 (relief compression persists); absolute calibration undemonstrated; CPU-only validation.

## 13. Calibration Boundary (Shivam-owned; NOT implemented here)

ML delivers: relative height map + validity mask + provenance (candidate, checkpoint SHA, stats, protocol). Calibration owns: scale/offset estimation (SRTM-30 m tie, scene stats, or minimal GCPs — PS-allowed), CRS/transform, DEM/GCP integration, metric DSM generation/export. Calibration MAY assume: relative ordering quality per §6, validity semantics §11, frozen preprocessing §10. Calibration MUST NOT assume: metric scale in ML output, cross-city uniform bias, or that affine-eval numbers equal calibrated accuracy.

## 14. Final Recommendation

**M17 is the final ML candidate.** It is the strongest defensible, externally validated, reproducible, deployable representation within our constraints.

## 15. ML Freeze Statement

```text
FINAL ML CANDIDATE = LOCKED (M17, commit b6b3696 + this decision doc; checkpoint/config/protocol frozen as §9–§11)
```

Scope honesty: the formal duesseldorf/herne/neuss scoring is BLOCKED on data access (32 GB tarball: 0 bytes/11 min on the fast path after legacy-path stall; 29 GB free on C; IEEE login wall; per-city zips GB-scale + PDAL chain). Because test cities played zero role in selection, their future scoring is pure verification: run the §5 protocol with the frozen checkpoint and confirm direction; any contradiction reopens the track per the standing rule. No further optimization experiments.

## 16. What Must NOT Change

Model, checkpoint (+hash), preprocessing, output semantics (`is_metric=False`), affine evaluation protocol, provenance record, train/val/probe ID lists, M10 base checkpoint.

---

## Shivam Handoff

```text
Final ML candidate: M17 (DA-V2-Small frozen + Pearson-adapted 23k head, epoch 6)
Checkpoint: experiments/m17-geonrw-struct-e01/checkpoints/best.pt, SHA256 D7C0BE91…EDAC
ML output semantics: RELATIVE geometric representation (is_metric=False, units None)
Input assumptions: RGB HWC uint8, any H/W (output follows source grid), ImageNet/518 pipeline
Preprocessing: frozen (§10); nodata→NaN; negatives kept
Validity behavior: finite-masked; no confidence channel (affine a/b are eval-only)
Confidence: none
External evidence: probe Pearson 0.37 (6/6 cities improved over M10 0.25); slopes <1 persist
Main limitations: moderate absolute correlation; relief compression; mid-terrain hole; test cities pending
What calibration may safely assume: relative ordering + validity/provenance above
What calibration must NOT assume: metric scale in ML output; uniform cross-city bias; affine-eval MAE as calibrated accuracy
```

## Aryan Handoff

```text
Final ML candidate: M17 (relative height maps; exact checkpoint above)
Input format: RGB HWC uint8 (PNG/JPG now; GeoTIFF ingest is a known gap — no CRS parsing in ML layer)
Output raster dimensions: follow source image grid (out_hw = H/W)
Relative-vs-metric semantics: RELATIVE ONLY until Shivam's calibration stage
Validity mask: finite-pixel mask accompanies every output
Confidence availability: none
What visualization may assume: source-grid relative relief + validity + provenance
What visualization must NOT assume: metric heights, calibrated DSM, checkpoint internals (consume the rDSM/DSM product boundary, not the checkpoint)
```

---

**Prepared by:** Shravan (ML) · **Date:** 2026-09-05 · **Branch:** `feat/shravan-final-ml-freeze`
