# M14 — External Remote-Sensing + Metric-DSM Readiness Audit

**Date:** 2026-09-05 (restructured to full PS-alignment spec; findings from live audit unchanged)
**Author:** Shravan (ML/data)
**Branch:** `feat/shravan-m14-external-readiness`
**Type:** Audit / readiness (no training, no model changes, no data committed)
**References:** M10 seed0 5.8204 m · M11 mean 5.7428 m · M13 5.9323 m (Outcome 2) · M9 6.0206 m · M5 5.1500 m

**M14 answers: what data and target definition do we need to move the GAMUS-trained M10/M11 candidate toward a defensible single-view remote-sensing DSM system for ISRO PS 26175?**

---

## 1. M14 Objective

Move the ML track from "GAMUS adaptation benchmark" toward "can our pipeline generalize to real remote-sensing height data and support the final metric-DSM pipeline" by auditing official external sources, target semantics, the reusable M10/M11 interface, DA3, licenses, and the ML↔calibration boundary — without running training or benchmarks. Outcome: **B** (see §15).

---

## 2. End-Goal Alignment With PS 26175

PS 26175 (`IMG-PROCESS-SAC/SIH-DepthWizard-2026`, README-only — see §5) requires an end-to-end system:

```
Single-view optical RGB (PNG/JPG non-georeferenced, GeoTIFF georeferenced)
  → elevation extraction (relative depth / height representation)
  → scale calibration (scene stats, low-res DEM e.g. SRTM 30 m, semantic priors, or minimal GCPs)
  → rDSM (non-georeferenced) / absolute metric DSM (georeferenced)
  → RGB-textured 3D terrain mesh → interactive flythrough + height/slope analysis
```

Evaluation is **50% DSM accuracy** (RMSE/MAE/correlation vs LiDAR/reference, stability across urban/sparse/hilly/forested) and **50% rendering & UX** (projection accuracy, flythrough, standalone deployment). Consequence for the ML track: optimizing GAMUS val MAE alone is insufficient — every M14 finding below is tied to data semantics, external generalization, calibration interface, or deployability, never to MAE in isolation.

---

## 3. Official Repositories Audited (Live Inspection)

| # | Repository (official) | Revision inspected | License (code) | Role |
|---|----------------------|--------------------|----------------|------|
| 1 | `EarthNets/Dataset4EO` | branch `streaming` (202 commits; builtin list via API) | Apache-2.0 | Streaming lib + 16 builtin RS datasets; depth-bearing entries found |
| 2 | `EarthNets/RSI-MMSegmentation` | `main` (123 commits) | **unknown** (no LICENSE in listing) | GAMUS official code; taxonomy + `XShadow/GAMUS` pointer |
| 3 | `EarthNets/Sat3DGen` (as tasked) | — | — | **404 — does not exist.** Sat3DGen is actually `qianmingduowan/Sat3DGen` (ICLR 2026; see below) |
| 4 | `qianmingduowan/Sat3DGen` (corrected source) | public release + ICLR poster 2026-02-06 + arXiv 2605.14984 | **unknown** (not verified) | Related-work only (satellite→street 3D generation, DSM export as side app) |
| 5 | `ByteDance-Seed/Depth-Anything-3` | `main` (30 commits) | Apache-2.0 (code); **CC BY-NC 4.0: Giant/Large/Nested/Metric-Large**; Apache-2.0: Base/Small/Mono-Large/Metric-Large | Future-benchmark assessment |
| 6 | `DepthAnything/Depth-Anything-V2` | `main` HEAD **`a561b84`** (verified live — our pin is current) | checkpoint Small Apache-2.0 (per M3) | Pin currency check |
| 7 | `IMG-PROCESS-SAC/SIH2026` → `SIH-DepthWizard-2026` | `main` (2 commits, README only) | unknown | PS text; **no reference samples** (blocker §5) |

Supporting read-only sources: `earthflow/GAMUS` HF card, torchgeo `DFC2022` docs/source, IEEE DataPort GeoNRW + DFC2022 pages, NRW open-data portal, `gbaier/geonrw`. Nothing downloaded, cloned, or run for findings.

---

## 4. Dataset4EO Findings

Dataset4EO is a LitData-based streaming library (channel-wise or full-image chunking), **not** a dataset collection itself; its 16 builtins point at HF datasets (`earthflow/earthnets` collection). Depth/height-bearing builtins and only those matter here:

- **GeoNRW** (`*_rgb.jp2` → RGB; `*_seg.tif` → 11 classes; `*_dem.tif` → `height` float32): 40 train + 3 test cities (`duesseldorf`, `herne`, `neuss`). Upstream (IEEE DataPort DOI 10.21227/s5xq-b822; `gbaier/geonrw`): 7,783 triplets 1000×1000, photos 0.1 m → 1 m, **first LiDAR return averaged per 1 m²**, geocoded GeoTIFF/JPEG2000, ~30 GB, free IEEE login gate. First-return ⇒ DSM-like. License **dl-de/by-2.0** (attribution).
- **DFC2022** (via torchgeo): last image channel → `height` float16, unit meters, + optional mask; 16 UrbanAtlas classes. Upstream: RGB aerial **0.5 m** (~2000²) + **DEM from IGN RGE ALTI at 1 m** (~1000²) + masks, 19 French regions, train/val/test georeferenced GeoTIFFs. **RGE ALTI is bare-earth DTM** (bare-ground surface, sub-metric) — terrain reference, not nDSM supervision. RGB/DEM resolution mismatch ⇒ resampling required. **IEEE DataPort approved-participant gate** + mandatory `grss_dfc_2022` citation. (Related: DFC30 on Zenodo, CC-BY-4.0, repackages DFC2022 + COP30 + FABDEM for DEM-SR — noted only.)
- **GAMUS** builtin: `image` uint8 HWC RGB (asserted 3-ch) + `class` uint8 + `height` float16 AGL — confirms our nDSM reading.
- The other 12 builtins (LoveDA, GID-15, DeepGlobe, LEVIRCD(Plus), So2Sat, PatternNet, ETCI2021, FireRisk, LandCoverAI, Inria, USAVars) are segmentation/classification/change-detection — **no metric height**.

---

## 5. SIH2026 Findings (Blocker)

`IMG-PROCESS-SAC/SIH2026` resolves to `SIH-DepthWizard-2026`: README-only, 2 commits. It carries the full PS 26175 text (GAMUS recommended; **SRTM 30 m explicitly allowed** for scale mapping; rDSM-vs-absolute-DSM split; RMSE/MAE/correlation vs LiDAR across urban/sparse/hilly/forested; 50/50 DSM-vs-rendering weighting) but **no RGB imagery, reference DSM/DEM, samples, output examples, or geospatial conventions**. Blocker for *validation*, not development (the PS permits any open remote-sensing depth data + SRTM).

---

## 6. Target-Semantics Comparison (Mandatory Distinction)

```
monocular camera depth  ≠  relative monocular depth  ≠  nDSM/AGL  ≠  DSM  ≠  DTM  ≠  absolute elevation
```

| Source | Input | Target | Physical meaning | Units | Resolution | Geo metadata | Comparable to GAMUS? |
|--------|-------|--------|------------------|-------|------------|--------------|----------------------|
| GAMUS | RGB tiles | AGL height | nDSM/AGL | meters | 1024² tile | city prefix only | reference |
| GeoNRW | RGB orthophotos | `_dem.tif` 1st-return LiDAR | DSM-like (**verify per file**) | meters | 1 m, 1000², geocoded | ✓ GeoTIFF+JP2K | **partial** — closest quantity; needs alignment step |
| DFC2022 | RGB aerial | RGE ALTI DEM | bare-earth **DTM** | meters | RGB 0.5 m / DEM 1 m, georeferenced | ✓ GeoTIFF | **no (direct)** — terrain reference / probe imagery only |
| DA-V2 output | RGB | relative depth | scale-ambiguous camera depth | relative | source size | none | no (needs adaptation+calibration) |
| DA3-Metric output | RGB + focal | metric depth | camera depth in meters | meters | source size | none | partial (needs focal; unproven on aerial) |
| SIH2026 repo | — | — | — | — | — | — | n/a (blocker) |

---

## 7. External Benchmark Strategy (Designed, Not Run)

| Split | Source | Purpose | Independence |
|-------|--------|---------|--------------|
| train | GAMUS train (existing) | adaptation | — |
| validation | 8 DC tiles (frozen since M5) | checkpoint selection | frozen |
| geographic holdout | M6 manifest val+test | cross-city transfer | frozen; never trained on |
| **external holdout (new)** | **GeoNRW test cities (duesseldorf/herne/neuss)** | true out-of-distribution eval | clean — never in GAMUS, never trained on |
| terrain-reference check | DFC2022 val DTM | terrain plausibility only | clean; never pooled with nDSM errors |

Rules: one frozen evaluation per candidate on the external holdout (no tuning on it); never mix DTM errors with nDSM MAE; re-verify GeoNRW per-file DSM status during adaptation. Do not run it in M14.

---

## 8. M10/M11 Reusability Audit

**Reusable as-is:** `AdaptedDepthModel` (RGB uint8 HWC → meters via inverse `TargetScale`); `GamusAdapter`+`GamusConfig`; sorted/canonical-split manifest loader; `evaluate_predictions` (finite-mask MAE/RMSE/corr/bins/classes); `m6_geographic` city-grouped evaluator with optional train stats.

**GAMUS-specific assumptions blocking external use:** filename suffixes (`_RGB/_IMG/_CLS/_AGL.h5`); fixed 1024² tiles; 7-class taxonomy (vs GeoNRW 11, UrbanAtlas 16); city-prefix IDs; H5-only loading; **zero GeoTIFF/CRS/geotransform/rasterio/GDAL handling anywhere in `src/`** (verified by search — the GeoTIFF path gap is total); fixed 518 preprocessing; µ/σ tied to GAMUS train; no resampling (DFC2022 0.5 m/1 m); no DSM−DTM derivation mode.

**Gaps for the adaptation stage (documented, not implemented):** generic GeoTIFF+CRS sample/manifest schema; resampling; taxonomy crosswalk; target-semantics adapter (direct DSM-like vs DTM-referenced eval).

---

## 9. ML ↔ Calibration Boundary (ML Output Contract)

Proposed eventual contract (no implementation in M14):

```
RGB image → ML inference → { relative depth/height map, validity mask,
                             optional confidence, model provenance }
Calibration/geospatial layer → { metric scale/offset + CRS/transform } → metric DSM
```

The repo already encodes this boundary: `DepthResult` is `relative/is_metric=False` by construction; `metric_height()` raises toward calibration; `is_metric=True` requires `calibration_provenance` (Rules A/B, `depth/base.py`). **Finding: Shivam's calibration/geospatial subsystem does not exist in the repo yet** (no `calibration/` module) — the contract exists, the implementation does not. ML outputs relative depth/height (+ validity mask + provenance); scale/offset/absolute elevation/CRS stay with Shivam's side. **Shivam review required** before any interface change (AGENTS.md shared-interface rule) or integration.

---

## 10. GeoTIFF vs PNG/JPG Processing Paths

- **Path A (PNG/JPG → rDSM):** supported at the inference layer today — `DepthBackend.infer` consumes HWC uint8 RGB and returns source-sized relative depth; the M10 head path consumes the same. Missing only product plumbing (relative-height export + mesh handoff), which sits with the visualization track.
- **Path B (GeoTIFF → metric DSM):** **not supported end-to-end.** No GeoTIFF ingest, no CRS/geotransform parsing, no DEM/GCP calibration, no metric-DSM writer exists in the repo. Do not pretend otherwise: the only metric outputs in the tree are research-only (`gamus-ndsm-agl-metric … not calibrated elevation`).
- 3D texture/mesh/flythrough on either path is Aryan's track (out of ML scope; Sat3DGen noted below as related work for that track, not ML height).

---

## 11. DA3 Assessment — **BENCHMARK LATER**

- Code Apache-2.0, 30 commits; CUDA + xformers required (lab is CPU — Giant-class not executable here); inference + benchmark pipeline + Gradio/CLI; **no training code**.
- Checkpoints: Giant/Large/**Nested/Metric-Large = CC BY-NC 4.0** (excluded from SIH-deployable path); **Base/Small/Mono-Large/Metric-Large = Apache-2.0**.
- Semantics: main series relative/multi-view/pose/3DGS; `DA3METRIC-LARGE` (0.35B, Apache-2.0) gives monocular metric depth only with **focal length** (`metric = focal·output/300`) — unavailable for arbitrary uploads; Nested outputs meters but is NC-licensed.
- Remote-sensing relevance **unproven** (benchmarks: HiRoom, ETH3D, DTU, 7Scenes, ScanNet++ — indoor/street, no aerial).
- Revisit triggers: (a) GPU access, (b) a georeferenced eval set with known intrinsics, (c) a GeoNRW baseline to beat. Changes nothing about the GAMUS→DSM semantics gap today.
- **Sat3DGen correction:** `EarthNets/Sat3DGen` **404s — it is not an EarthNets repo.** The real project is `qianmingduowan/Sat3DGen` (ICLR 2026, satellite→street 3D generation, tri-plane NeRF, DSM export as an unsupervised side-app on VIGOR, 8×H20 training, license unverified). Notably it uses **DA-V2 relative depth as its satellite-view prior** (validates our backbone choice). Verdict: related work for the 3D/flythrough track, **not** an ML height benchmark.

---

## 12. License / Provenance

| Item | License | Source / revision | Constraint |
|------|---------|-------------------|------------|
| GAMUS data (`earthflow/GAMUS`) | **CC-BY-4.0** | HF card (5.9k rows: 1.2k/1.6k/3.1k; ~80 GB) | attribution; commercial OK |
| GAMUS code (RSI-MMSegmentation) | **unknown** (no LICENSE in listing) | `main`, 123 commits; new data `XShadow/GAMUS` | re-verify before vendoring; watch license drift |
| Dataset4EO code | Apache-2.0 | branch `streaming` | OK |
| GeoNRW triplets | **dl-de/by-2.0** | IEEE DataPort DOI 10.21227/s5xq-b822; free-login gate | attribute Baier et al. + NRW program |
| DFC2022 data | contest terms (gated) | IEEE DataPort; approved-participant login | cite `grss_dfc_2022`; registration |
| DA-V2 Small ckpt | Apache-2.0 | pin 03876f86; upstream HEAD verified `a561b84` | OK (M10 basis) |
| DA3 code | Apache-2.0 | `ByteDance-Seed/Depth-Anything-3` | OK |
| DA3 Giant/Large/Nested/Metric-Large | **CC BY-NC 4.0** | model cards | **excluded** from deployable path |
| DA3 Base/Small/Mono/Metric-Large | Apache-2.0 | model cards | eligible for future benchmark |
| Sat3DGen code/weights | **unknown** | `qianmingduowan/Sat3DGen`, HF `qian43/Sat3DGen` | verify before any use |
| SRTM 30 m (PS-allowed) | public/open (verify tile terms at fetch) | PS README allowance | re-verify at download |

---

## 13. Decision Matrix

| Candidate | RGB | Remote Sensing | Metric Target | Target Comparable to GAMUS | Geo Metadata | Geographic Diversity | License | External Eval Ready | Decision |
|-----------|----:|---------------:|--------------:|---------------------------:|-------------:|---------------------:|--------:|--------------------:|----------|
| GAMUS | CONFIRMED | CONFIRMED | CONFIRMED (nDSM/AGL) | Reference | PARTIAL (city tags) | PARTIAL (3 US cities) | CC-BY-4.0 | CONFIRMED (internal) | Development |
| GeoNRW | CONFIRMED | CONFIRMED | PARTIAL (DSM-like; verify/file) | PARTIAL (needs alignment) | CONFIRMED (geocoded) | CONFIRMED (40+3 DE cities) | dl-de/by-2.0 | PARTIAL (needs adapter) | **Adaptation target** |
| DFC2022 | CONFIRMED | CONFIRMED | NOT APPLICABLE (bare-earth DTM) | NOT APPLICABLE (terrain only) | CONFIRMED (georeferenced) | CONFIRMED (19 FR regions) | gated + citation | PARTIAL (probe only) | **Terrain reference** |
| SIH2026 repo data | UNKNOWN (none found) | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | NOT APPLICABLE | **Blocker** |
| DA3-Metric-Large | NOT APPLICABLE (model) | UNKNOWN (unproven) | PARTIAL (needs focal) | PARTIAL | NOT APPLICABLE | — | Apache-2.0 | PARTIAL (needs GPU+intrinsics) | **Later** |
| DA3 Giant/Nested | NOT APPLICABLE (model) | UNKNOWN (unproven) | CONFIRMED (Nested, meters) | PARTIAL | NOT APPLICABLE | — | CC BY-NC 4.0 | NOT APPLICABLE | **Excluded** |
| Sat3DGen | NOT APPLICABLE (3D-gen) | CONFIRMED (satellite→street) | UNKNOWN (unsupervised DSM app) | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | NOT APPLICABLE | **Related work only** |

---

## 14. Current Gaps / Blockers

1. **No SIH reference samples** (validation blocker, not development blocker).
2. **GeoNRW per-file DSM-vs-DTM verification** outstanding — gates direct comparability.
3. **No GeoTIFF/CRS adapter** in the ML track (§8 gap list).
4. **No taxonomy crosswalk** (7 vs 11 vs 16).
5. **Calibration subsystem unimplemented** (contract exists; Shivam-owned).
6. **No GPU path** for Giant-class models (CPU lab).
7. IEEE DataPort gates (free login; DFC2022 approved participation).

---

## 15. Recommended Next Milestone

**Outcome B: useful external data exists (GeoNRW), but target semantics/resolution/taxonomy require a controlled adaptation stage before benchmarking.**

ONE next milestone: **M15 = GeoNRW target-alignment + frozen-M10 zero-shot external eval (report-only, no training)** — (a) verify per-file DSM status on a small triplet sample, (b) add a minimal GeoTIFF-capable adapter + documented meter-alignment step, (c) run the frozen M10 candidate once on GeoNRW test cities and report MAE/RMSE/corr/bins with the comparability caveats. Do NOT start it here.

---

*Evidence: all URLs/revisions above were inspected live for this audit (2026-09-05); values marked partial/unknown are explicitly so. No datasets downloaded, no models run, no code changed for findings. Prior M14 commit `5e899e6` established the core audit; this revision adds the PS-alignment framing, Sat3DGen correction, GeoTIFF-path and calibration-readiness analysis, and the ML output contract — conclusions unchanged (Outcome B).*
