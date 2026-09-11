# SIH Problem Statement 26175 — Compliance Matrix

**DepthWizard — Single-View Height Estimation and 3D Flythrough**

**Audit Date:** 2026-09-06  
**Auditor:** Shivam (Architecture Authority)  
**Source of Truth:** Actual repository code, tests, and documentation at `main` (`809801d`)

---

## SIH PS 26175 Requirements vs Implementation

| #   | PS Requirement                                     | Current Implementation                                                                                                      | Evidence                                                                                    | Status              | Owner        | Release Blocker                      | Required Action                                                                                                 |
| --- | -------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------- | ------------------- | ------------ | ------------------------------------ | --------------------------------------------------------------------------------------------------------------- |
| 1   | **Single optical monocular satellite image input** | `InputInspection` validates PNG/JPG/GeoTIFF; `ingestion/api.py` handles single-view input                                   | `src/depthwizard/ingestion/api.py`, `tests/ingestion/test_supported.py`                     | **PASS**            | Shivam       | No                                   | None                                                                                                            |
| 2   | **Monocular depth foundation model**               | `DepthAnythingV2Backend` implements `DepthBackend` protocol; DA-V2 Small frozen inference                                   | `src/depthwizard/backends/depth_anything_v2.py`, `tests/backends/test_depth_anything_v2.py` | **PASS**            | Shivam       | No                                   | None                                                                                                            |
| 3   | **Solar shadow geometry/trigonometry**             | depthwizard.solar package: sun angle resolver, Otsu shadow detector, trig height kernel, pipeline stage (Python); frontend UI panel and service-API wiring pending | src/depthwizard/solar/, 	ests/solar/ (29 passed); no SolarShadowPanel.tsx; solar constraints not fed into calibration samples in production code | **PARTIAL**        | Shivam       | **P0 Release Blocker** (frontend UI missing) | Wire SolarShadowPanel.tsx into the frontend; feed solar constraints into calibration samples via the service API |
| 4   | **3D neural rendering**                            | Textured-mesh PBR visualization (`MeshStandardMaterial` + scene lighting); honest mode label `"Photorealistic (Textured Mesh)"` | `src/layers/types.ts`, `src/viewer/Viewer.tsx`, `src/layers/layerRenderer.ts`               | **PASS** (accepted) | Aryan        | No                                   | None (NeRF not in in-repo contract)                                                                             |
| 5   | **3D cityscape reconstruction**                    | `TerrainMesh.build()` for single tiles + `depthwizard.mosaic` multi-tile DSM stitching for city-scale GeoTIFF collections  | `src/depthwizard/mesh/`, `src/depthwizard/mosaic/`, `tests/mosaic/` (4 passed)              | **PASS**            | Shivam/Aryan | No                                   | None                                                                                                            |
| 6   | **Height estimation**                              | Relative depth (Mode A) + explicit calibration → metric DSM (Mode B); `ScientificHeightProduct` with AGL/absolute semantics | `src/depthwizard/height/product.py`, `src/depthwizard/calibration/calibrator.py`            | **PASS** (contract) | Shivam       | No (contract)                        | None                                                                                                            |
| 7   | **Flythrough generation**                          | `FlythroughPanel` with waypoint-based camera trajectory; orbit/first-person/aerial modes                                    | `src/components/FlythroughPanel/`, `src/camera/`                                            | **PASS**            | Aryan        | No                                   | None                                                                                                            |
| 8   | **Single-view**                                    | Architecture processes single input image (PNG/JPG/GeoTIFF)                                                                 | `InputInspection` single file                                                               | **PASS**            | Shivam       | No                                   | None                                                                                                            |
| 9   | **Satellite imagery**                              | GeoTIFF with CRS/transform supported; PNG/JPG for non-geo                                                                   | `InputInspection` supports GeoTIFF/PNG/JPG                                                  | **PASS**            | Shivam       | No                                   | None                                                                                                            |

---

## Critical Gaps Analysis (PARTIAL — Python Implemented, Frontend Pending)

### Gap 1: Solar Shadow Geometry / Trigonometry (PARTIAL)

**Implementation:** Python pipeline implemented in src/depthwizard/solar/ (29 tests passing). Resolves sun angles from image metadata or explicit supply, segments shadow regions via Otsu luminance thresholding, and estimates building heights via trigonometry. Integrated into PipelineRunner. **Frontend UI panel (SolarShadowPanel.tsx) is NOT present**, and solar constraints are computed but **not fed into calibration samples** in production code. The frontend service-API wiring remains incomplete.

### Gap 2: 3D Neural Rendering (ACCEPTED INTERPRETATION)

**Implementation:** PBR textured-mesh rendering with `MeshStandardMaterial` and directional scene lighting. The phrase "3D neural rendering" does not appear in any in-repo authoritative source; classical textured-mesh PBR rasterization is the accepted, transparently documented implementation.

### Gap 3: 3D Cityscape Reconstruction (RESOLVED)

**Implementation:** Single-tile terrain mesh generation plus `depthwizard.mosaic` multi-tile DSM stitching (`stitch_dsm_grids()`) for city-scale GeoTIFF collections.

---

## Compliance Summary

| Category          | PASS     | PARTIAL | MISSING | BLOCKED |
| ----------------- | -------- | ------- | ------- | ------- |
| Core Requirements | 8        | 1       | 0       | 0       |
| **Overall**       | **8/9**  | **1/9** | **0/9** | **0/9** |

**Compliance Score:** 89% (8 core PASS + 1 PARTIAL — solar shadow Python implemented, frontend UI and service-API integration pending)

---

## Release Blocker Classification

| Gap                                 | Severity | Classification                                      |
| ----------------------------------- | -------- | --------------------------------------------------- |
| Solar geometry/trigonometry frontend UI missing | P0       | **Release Blocker** (core PS requirement; Python engine works, frontend panel + service-API wiring pending) |
| Neural rendering not implemented    | P1       | **Release Blocker** if PS requires neural rendering |
| City-scale reconstruction           | P2       | Gap (single-tile only)                              |
| Final ML candidate                  | P0       | **Release Blocker** (G15)                           |
| Physical Windows acceptance         | P0       | **Release Blocker** (G2, G10, G14)                  |

---

## Requirement Closure Review (2026-09-06)

| Requirement                        | Interpretation                                                                     | Current implementation                                   | Evidence                                                                                                    | Gap                                                         | Classification              | Minimum implementation                                                                                     | Owner        |
| ---------------------------------- | ---------------------------------------------------------------------------------- | -------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------- | --------------------------- | ---------------------------------------------------------------------------------------------------------- | ------------ |
| Solar-shadow geometry/trigonometry | Per-structure heights from shadow length + solar angles, as calibration references | Python depthwizard.solar package implemented (29 tests); no SolarShadowPanel.tsx; solar constraints not wired into calibration samples | src/depthwizard/solar/, 	ests/solar/; verified absence of frontend panel and service-API wiring        | Frontend UI panel and calibration-sample wiring absent     | **C — MAJOR NEW SUBSYSTEM** (frontend integration incomplete) | Wire SolarShadowPanel.tsx and feed solar constraints into CalibrationSamples via the service API      | Shivam       |
| 3D neural rendering                | Learned scene representation + neural view synthesis                               | Three.js rasterization only (0 neural matches in `src/`) | Verified search + `docs/ps-neural-rendering-closure.md` §§1–4; in-repo PS sources contain no neural wording | Representation + synthesizer + GPU/packaging program absent | **C — MAJOR NEW SUBSYSTEM** | Per-scene fit + versioned artifact + WebGL/WASM renderer + held-out metrics; or accept rasterization claim | Aryan/Shivam |

**Decision:** Solar remains **C — MAJOR NEW SUBSYSTEM** because the frontend UI panel and service-API calibration wiring are incomplete, despite the Python engine being implemented and tested. Neural rendering remains **C** — from evidence, not impression. No implementation started (closure analysis only).

## Required Actions for SIH Compliance

| Action                                                                                                                                                                                          | Owner        | Timeline                    |
| ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------ | --------------------------- |
| Accept or reject the solar C-classification; if accepted, scope depthwizard.solar as a separate program (docs/ps-solar-shadow-closure.md §14); complete frontend SolarShadowPanel.tsx and calibration-sample wiring              | Shivam       | Required for SIH compliance |
| Accept or reject the neural-rendering C-classification; if binding, scope the NeRF/GS program (`docs/ps-neural-rendering-closure.md` §5) or record rasterization as the accepted interpretation | Aryan/Shivam | Required for SIH compliance |
| Document single-tile vs city-scale scope limitation                                                                                                                                             | Aryan/Shivam | Documentation               |
| Freeze final ML candidate with solar-aware model                                                                                                                                                | Shravan      | Required for SIH compliance |

---

**End of SIH Compliance Matrix.** This audit reflects actual repository state at `809801d`.
