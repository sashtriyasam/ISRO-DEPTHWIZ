# M14 — External Remote-Sensing + Metric-DSM Readiness Audit

**Date:** 2026-09-05
**Author:** Shravan (ML/data)
**Branch:** `feat/shravan-m14-external-readiness`
**Type:** Audit / readiness (no training, no model changes, no new data committed)

**M14 is an audit milestone. It ends with: what data and target definition do we need to move from the GAMUS-trained M10/M11 candidate toward a defensible single-view remote-sensing DSM system for ISRO PS 26175?**

---

## 1. M14 Objective

Move the ML track from "GAMUS adaptation benchmark" toward "can our pipeline generalize to real remote-sensing height data and support the final metric-DSM pipeline" by auditing official external sources, target semantics, the reusable M10/M11 interface, and the ML↔calibration boundary — without running any training or benchmark yet.

---

## 2. Repository / Data Sources Audited (Live Inspection)

| # | Repository (official) | Revision inspected | License (code) | Role in audit |
|---|----------------------|--------------------|----------------|---------------|
| 1 | `EarthNets/Dataset4EO` | branch `streaming` (202 commits; builtin list via API) | Apache-2.0 | Streaming lib + 16 builtin RS datasets; depth-bearing entries identified |
| 2 | `EarthNets/RSI-MMSegmentation` | `main` (123 commits) | **unknown** (no LICENSE file in listing) | GAMUS official code; confirms class taxonomy + new data location |
| 3 | `ByteDance-Seed/Depth-Anything-3` | `main` (30 commits) | Apache-2.0 (code); **CC BY-NC 4.0 for Giant/Large/Nested/Metric-Large**; Apache-2.0 for Base/Small/Mono-Large/Metric-Large | Future-benchmark assessment |
| 4 | `DepthAnything/Depth-Anything-V2` | `main` HEAD **`a561b84`** (verified live via API — our pin is current) | Code repo; Small checkpoint Apache-2.0 (per M3) | Pin currency check |
| 5 | `IMG-PROCESS-SAC/SIH2026` → `IMG-PROCESS-SAC/SIH-DepthWizard-2026` | `main` (2 commits, README only) | unknown | PS text source; **no reference samples** (blocker) |

Supporting sources (read-only web): `earthflow/GAMUS` HF card, `XShadow/GAMUS` (referenced by RSI-MMSegmentation README), torchgeo `DFC2022` docs/source, IEEE DataPort GeoNRW + DFC2022 pages, NRW open-data portal, `gbaier/geonrw` processing repo. No datasets downloaded; no code cloned except pre-existing local pins.

---

## 3. Dataset Semantics

### 3.1 GAMUS (our development baseline — confirmed)

- RGB optical tiles + AGL height + 7-class labels (Dataset4EO `builtin_datasets/GAMUS/collect_data.py`: `image` uint8 HWC RGB with `assert shape[-1] == 3`; `class` uint8; `height` float16).
- Target treated in M4–M13 as **nDSM/AGL meters** (surface height above ground), 1024×1024 tiles, negatives kept (−5.0 m min observed).
- HF `earthflow/GAMUS`: **CC-BY-4.0**, 5.9k rows (train 1.2k / val 1.6k / test 3.1k), ~80 GB, imagefolder format, ~3.5k downloads/month. Citation: Xiong et al., arXiv:2305.14914. New version at `XShadow/GAMUS` (per RSI-MMSegmentation README; not inspected for license drift — re-verify before use).

### 3.2 GeoNRW — strongest external candidate (partial verification still required)

- From Dataset4EO `builtin_datasets/GeoNRW/collect_data.py`: per-city `*_rgb.jp2` (converted RGB) + `*_seg.tif` (11 classes) + **` *_dem.tif` → `height` float32**, 40 train cities + 3 test cities (`duesseldorf`, `herne`, `neuss`).
- Upstream facts (IEEE DataPort DOI 10.21227/s5xq-b822 + `gbaier/geonrw`): 7,783 triplets 1000×1000, photos resampled 0.1 m → 1 m, **first LiDAR return averaged in 1 m²** → geocoded GeoTIFF/JPEG2000, ~30 GB, free IEEE login required.
- Semantics: first-return LiDAR elevation ≈ **DSM-like surface elevation** — the closest external quantity to GAMUS nDSM/AGL, BUT (a) per-file DSM-vs-DTM status must still be verified (filenames say `_dem`), (b) it is absolute elevation-flavored while GAMUS is above-ground, so direct MAE comparison needs a documented alignment step, (c) 1000² vs our 1024² tiles, (d) German cities = true geographic holdout (never in GAMUS).
- License: `dl-de/by-2.0` (attribution; per IEEE DataPort + gbaier repo). Source orthophotos now under dl-de-zero-2.0; the **compiled GeoNRW triplet license to respect is dl-de/by-2.0** (attribute Baier et al. + NRW open-data program).

### 3.3 DFC2022 — terrain reference, NOT nDSM supervision

- From Dataset4EO `builtin_datasets/DFC2022/collect_data.py` (via torchgeo): last image channel → `height` float16, **unit meters**, + optional mask; 16 UrbanAtlas classes.
- Upstream facts (torchgeo docs/source + IEEE DataPort): RGB aerial 0.5 m (~2000²) + **DEM from IGN RGE ALTI at 1 m (~1000²)** + masks, 19 French regions, train/val/test (train 1915 + val 2066 tiles), georeferenced GeoTIFFs.
- Semantics (critical): RGE ALTI is a **bare-earth DTM** (bare-ground topographic surface, sub-metric precision) — **not** a surface/height model. It cannot supervise nDSM directly. Usable as (a) terrain reference for sanity checks, (b) French urban/countryside/sparse imagery for qualitative transfer probes, (c) the DTM half of a future DSM−DTM derivation.
- Friction: RGB/DEM resolution mismatch (0.5 m vs 1 m → resampling required); **IEEE DataPort approved-participant login (gated)**; contest terms + mandatory `grss_dfc_2022` citation.
- Related: DFC30 (Zenodo, CC-BY-4.0) repackages DFC2022 + Copernicus COP30 + FABDEM for DEM super-resolution — noted, not needed.

### 3.4 Other Dataset4EO builtins

DFC2022-adjacent depth content: none — the rest (LoveDA, GID-15, DeepGlobe, LEVIRCD(Plus), So2Sat, PatternNet, ETCI2021, FireRisk, LandCoverAI, Inria, USAVars) are segmentation/classification/change-detection. **No other built-in carries metric height.**

### 3.5 The mandatory distinction

```
monocular camera depth  ≠  nDSM/AGL  ≠  absolute terrain elevation (DTM)  ≠  DSM
```

- GAMUS target: nDSM/AGL (above-ground surface height, meters).
- GeoNRW `_dem`: first-return LiDAR elevation (DSM-like; verify per file).
- DFC2022 RGE ALTI: bare-earth DTM (terrain only; buildings/trees absent by construction).
- DA-V2/DA3 outputs: scale-ambiguous relative depth (camera-frame), or metric depth only with focal length (DA3) — neither is nDSM without adaptation + calibration.

---

## 4. GAMUS vs External Data Comparison

| Source | Input | Target | Target semantics | Units | Resolution | Geo metadata | RGB available | Comparable to GAMUS? |
|--------|-------|--------|------------------|-------|------------|--------------|---------------|----------------------|
| GAMUS | RGB tiles | AGL height | nDSM/AGL | meters | 1024² (tile) | city prefix only | ✓ | self |
| GeoNRW | RGB orthophotos | `_dem.tif` LiDAR 1st-return | DSM-like (verify/file) | meters | 1 m, 1000², geocoded | ✓ GeoTIFF+JP2K | ✓ | **partial** — closest quantity; needs alignment step |
| DFC2022 | RGB aerial | RGE ALTI DEM | bare-earth **DTM** | meters | RGB 0.5 m / DEM 1 m, georeferenced | ✓ GeoTIFF | ✓ | **no (direct)** — terrain reference / probe imagery only |
| SIH2026 repo | none in repo | none in repo | — | — | — | — | — | not applicable (blocker §5) |

---

## 5. SIH2026 Reference-Data Findings (Blocker)

- `IMG-PROCESS-SAC/SIH2026` resolves to **`IMG-PROCESS-SAC/SIH-DepthWizard-2026`**: README-only, 2 commits, 15 stars. It contains the PS 26175 text (GAMUS recommended; SRTM-30 m allowed for scale mapping; rDSM-vs-absolute-DSM pipeline; RMSE/MAE/correlation vs LiDAR across urban/sparse/hilly/forested; 50/50 DSM-accuracy vs rendering-UX weighting) — but **no RGB imagery, no reference DSM/DEM, no samples, no output-format examples, no geospatial conventions**.
- **Blocker (documented, not inferred):** there is no official reference sample to validate against today. PS text explicitly permits SRTM 30 m + any open remote-sensing depth data, so this blocks *validation*, not *development*.

---

## 6. External Evaluation Strategy (Designed, Not Run)

| Split | Source | Purpose | Contamination status |
|-------|--------|---------|----------------------|
| train | GAMUS train (existing 16/4/4 etc.) | development/adaptation | — |
| validation | 8 DC tiles (frozen) | checkpoint selection | frozen since M5 |
| geographic holdout | M6 manifest val+test (DC/PHL/NYC) | cross-city transfer | frozen; never trained on |
| **external holdout (new)** | **GeoNRW test cities (duesseldorf/herne/neuss)** | true out-of-distribution eval | clean — never in GAMUS, never trained on |
| terrain-reference check | DFC2022 val (DTM) | sanity: terrain plausibility, not nDSM scoring | clean; score separately, never mix with nDSM MAE |

Rules: never optimize against the external holdout (single frozen evaluation per candidate); never pool DFC2022-DTM errors with nDSM errors; re-verify GeoNRW per-file DSM-vs-DTM status during the adaptation stage.

---

## 7. Current M10/M11 Reusability

**Reusable as-is:** `AdaptedDepthModel` (RGB uint8 HWC → meters via inverse `TargetScale`); `GamusAdapter`+`GamusConfig` root resolution; sorted/canonical-split manifest loader; `evaluate_predictions` (finite-mask MAE/RMSE/corr/bins/classes); `m6_geographic` city-grouped evaluator with optional train-stats (`--target-mu/--target-sigma`).

**GAMUS-specific assumptions blocking external use:** filename suffixes (`_RGB/_IMG/_CLS/_AGL.h5`); fixed 1024² tiles; 7-class taxonomy (vs GeoNRW 11, DFC 16 UrbanAtlas); city-prefix IDs; H5-only loading (no GeoTIFF/CRS/geotransform path); fixed 518 preprocessing; µ/σ tied to GAMUS train distribution; no resampling step (DFC2022 0.5 m/1 m mismatch); no DSM−DTM derivation mode.

**Required abstraction gaps (for the adaptation stage, not M14):** generic sample/manifest schema for GeoTIFF+CRS; resolution resampling; taxonomy crosswalk; target-semantics adapter (DSM-like direct vs DTM-referenced eval).

---

## 8. ML ↔ Calibration Boundary

- The PS allows SRTM 30 m or limited GCPs for scale calibration. The repo already encodes the boundary: `DepthResult` is `relative/is_metric=False` by construction; `metric_height()` raises toward calibration; `is_metric=True` requires `calibration_provenance` (Rules A/B, `depth/base.py`).
- **Finding: Shivam's calibration/geospatial subsystem does not exist in the repo yet** (no `calibration/` module; only references). The contract for it exists; the implementation does not.
- Recommended boundary (no subsystem changes in M14): ML side outputs **relative depth** (`DepthResult`) plus, for research, **relative height + optional confidence-ready fields**; **scale, offset, absolute elevation, CRS/geotransform stay with the calibration/geospatial subsystem** (Shivam-owned; review required before integration).

## 9. DA3 Future Benchmark Assessment

- Repo: Apache-2.0; 30 commits; CUDA + xformers required (our lab runs CPU — Giant-class inference not executable here); no training code (inference + benchmark pipeline + Gradio/CLI).
- Checkpoints: Giant/Large/**Nested/Metric-Large = CC BY-NC 4.0** (non-commercial — excluded from SIH-deployable path); **Base/Small/Mono-Large/Metric-Large = Apache-2.0**.
- Semantics: main series = relative/multi-view/pose/3DGS; `DA3METRIC-LARGE` (0.35B, Apache-2.0) does monocular metric depth but requires **focal length** (`metric = focal·output/300`) — unavailable for arbitrary PNG/JPG uploads; Nested outputs meters but is NC-licensed.
- Remote-sensing relevance: **unproven** — public benchmarks are indoor/street (HiRoom, ETH3D, DTU, 7Scenes, ScanNet++); no aerial/RS evaluation published.
- **Decision: benchmark later.** Triggers for revisiting: (a) GPU access, (b) a georeferenced eval set with known intrinsics (for DA3METRIC-LARGE, Apache-2.0), (c) after the GeoNRW adaptation stage gives a baseline to beat. DA3 changes nothing about the GAMUS→DSM target-semantics gap today.

## 10. License / Provenance

| Item | License | Source / revision | Constraint |
|------|---------|-------------------|------------|
| GAMUS data (`earthflow/GAMUS`) | **CC-BY-4.0** | HF card (5.9k rows, 80 GB); paper Xiong et al. 2023 | attribution; commercial OK |
| GAMUS code (RSI-MMSegmentation) | **unknown** (no LICENSE in listing) | `main`, 123 commits; new data `XShadow/GAMUS` | re-verify before vendoring; watch `XShadow` license drift |
| Dataset4EO code | Apache-2.0 | branch `streaming` | OK |
| GeoNRW triplets | **dl-de/by-2.0** (attribution) | IEEE DataPort DOI 10.21227/s5xq-b822; free login gate | attribute Baier et al. + NRW program |
| DFC2022 data | contest terms (gated) | IEEE DataPort, approved-participant login | cite `grss_dfc_2022`; registration required |
| DA-V2 Small ckpt | Apache-2.0 | `depth-anything/Depth-Anything-V2-Small`, pin 03876f86; upstream HEAD verified `a561b84` | OK (current M10 basis) |
| DA3 code | Apache-2.0 | `ByteDance-Seed/Depth-Anything-3`, `main` | OK |
| DA3 Giant/Large/Nested/Metric-Large | **CC BY-NC 4.0** | model cards | **excluded** from deployable path |
| DA3 Base/Small/Mono/Metric-Large | Apache-2.0 | model cards | eligible for future benchmark |
| SRTM 30 m (PS-allowed) | public/open (USGS/NASA; verify tile terms at fetch time) | PS README allowance | re-verify at download |

Nothing selected on metric alone; all deployable-path items above are permissive except the flagged NC/gated ones.

## 11. Decision Matrix

| Candidate | RGB | Metric target | Remote sensing | Geo metadata | Landscape diversity | Scale-compatible | License | Recommendation |
|-----------|----:|--------------:|---------------:|-------------:|--------------------:|-----------------:|--------:|----------------|
| GAMUS | ✓ | ✓ (nDSM/AGL) | ✓ | partial (city tags) | partial (3 US cities) | ✓ (training scale) | CC-BY-4.0 | **Development baseline (keep)** |
| GeoNRW | ✓ | partial (DSM-like; verify/file) | ✓ | ✓ (geocoded) | ✓ (40+3 DE cities; urban/forest/agri/water) | partial (needs alignment) | dl-de/by-2.0 | **External holdout + adaptation target** |
| DFC2022 | ✓ | no (bare-earth DTM) | ✓ | ✓ (georeferenced) | ✓ (19 FR regions; urban/countryside/coast) | no (terrain only) | gated + citation | **Terrain-reference / probe only** |
| SIH2026 repo data | — | — | — | — | — | — | — | **Blocker: no samples published** |
| DA3-Metric-Large | n/a (model) | partial (needs focal) | unproven | n/a | — | partial | Apache-2.0 | **Benchmark later** |
| DA3 Giant/Nested | n/a (model) | ✓ (Nested, meters) | unproven | n/a | — | no (NC license) | CC BY-NC 4.0 | **Excluded from deployable path** |

Legend: ✓ confirmed · partial = usable with a documented adaptation step · no/blocker as stated. Nothing fabricated; unknowns marked in §§3–5.

## 12. Gaps / Blockers

1. **No SIH reference samples** (blocker for validation, not development).
2. **GeoNRW per-file DSM-vs-DTM verification** not yet done (the single fact gating direct comparability).
3. **No GeoTIFF/CRS adapter** in the ML track (gap list §7).
4. **No taxonomy crosswalk** (GAMUS 7 vs GeoNRW 11 vs UrbanAtlas 16).
5. **Calibration subsystem unimplemented** (contract exists; Shivam-owned).
6. **No GPU path** for Giant-class models (CPU lab).
7. IEEE DataPort gates (free login; DFC2022 needs approved participation).

## 13. Recommended Next ML Milestone

**Outcome B: dataset exists (GeoNRW) but semantics/resolution/taxonomy require a controlled adaptation stage before benchmarking.**

ONE next milestone: **M15 = GeoNRW target-alignment + frozen-M10 zero-shot external eval (report-only, no training)** — (a) verify per-file DSM-vs-DSM status on a small triplet sample, (b) add a minimal GeoTIFF-capable adapter + documented meter-alignment step, (c) run the frozen M10 candidate once on GeoNRW test cities and report MAE/RMSE/corr/bins with the comparability caveats. Do NOT start it here.

---

*Evidence: all URLs/revisions above were inspected live for this audit; values marked partial/unknown are explicitly so. No datasets downloaded, no models run, no code changed for findings (report-only milestone).*
