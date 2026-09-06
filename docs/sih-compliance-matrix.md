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
| 3   | **Solar shadow geometry/trigonometry**             | **NOT IMPLEMENTED** — No solar geometry analysis, shadow detection, or trigonometric height extraction from shadows         | No implementation found in `src/depthwizard/`                                               | **MISSING**         | Shivam       | **YES** (core PS requirement)        | Implement solar geometry pipeline: shadow detection → solar angle computation → trigonometric height estimation |
| 4   | **3D neural rendering**                            | Three.js renderer displays mesh with RGB texture projection; **NOT neural rendering** (uses traditional rasterization)      | `src/components/`, `src/display/`, `src/viewer/`                                            | **PARTIAL**         | Aryan        | **YES** (PS says "neural rendering") | Implement neural radiance field (NeRF) or 3D Gaussian splatting renderer; or clarify PS interpretation          |
| 5   | **3D cityscape reconstruction**                    | Mesh generation from DSM (`TerrainMesh.build()`); texture projection via UV mapping; flythrough camera                      | `src/depthwizard/mesh/build.py`, `src/components/FlythroughPanel/`                          | **PARTIAL**         | Aryan/Shivam | **PARTIAL**                          | Full city-scale reconstruction not demonstrated; limited to single tile                                         |
| 6   | **Height estimation**                              | Relative depth (Mode A) + explicit calibration → metric DSM (Mode B); `ScientificHeightProduct` with AGL/absolute semantics | `src/depthwizard/height/product.py`, `src/depthwizard/calibration/calibrator.py`            | **PASS** (contract) | Shivam       | No (contract)                        | Physical validation with real calibration needed                                                                |
| 7   | **Flythrough generation**                          | `FlythroughPanel` with waypoint-based camera trajectory; orbit/first-person/aerial modes                                    | `src/components/FlythroughPanel/`, `src/camera/`                                            | **PASS**            | Aryan        | No                                   | None                                                                                                            |
| 8   | **Single-view**                                    | Architecture processes single input image (PNG/JPG/GeoTIFF)                                                                 | `InputInspection` single file                                                               | **PASS**            | Shivam       | No                                   | None                                                                                                            |
| 9   | **Satellite imagery**                              | GeoTIFF with CRS/transform supported; PNG/JPG for non-geo                                                                   | `InputInspection` supports GeoTIFF/PNG/JPG                                                  | **PASS**            | Shivam       | No                                   | None                                                                                                            |

---

## Critical Gaps Analysis

### Gap 1: Solar Shadow Geometry / Trigonometry (MISSING)

**PS Text:** "monocular depth foundation model with solar shadow geometry/trigonometry"
**Current:** Only DA-V2 relative depth → metric via calibration. No solar angle computation, shadow detection, or trigonometric height from shadows.
**Impact:** Core PS requirement not met. DepthWizard uses ML depth + calibration, not solar geometry.

### Gap 2: 3D Neural Rendering (PARTIAL)

**PS Text:** "3D neural rendering"
**Current:** Three.js rasterization with UV texture mapping. No NeRF, 3D Gaussian Splatting, or neural radiance fields.
**Impact:** Terminology mismatch. If PS requires neural rendering (NeRF/GS), this is a gap.

### Gap 3: 3D Cityscape Reconstruction (PARTIAL)

**PS Text:** "3D cityscape reconstruction"
**Current:** Single-tile mesh from single image. No multi-view, no city-scale reconstruction, no building segmentation.

---

## Compliance Summary

| Category          | PASS    | PARTIAL | MISSING | BLOCKED |
| ----------------- | ------- | ------- | ------- | ------- |
| Core Requirements | 5       | 2       | 2       | 0       |
| **Overall**       | **5/9** | **2/9** | **2/9** | **0/9** |

**Compliance Score:** 55% PASS

---

## Release Blocker Classification

| Gap                                 | Severity | Classification                                      |
| ----------------------------------- | -------- | --------------------------------------------------- |
| Solar geometry/trigonometry missing | P0       | **Release Blocker** (core PS requirement)           |
| Neural rendering not implemented    | P1       | **Release Blocker** if PS requires neural rendering |
| City-scale reconstruction           | P2       | Gap (single-tile only)                              |
| Final ML candidate                  | P0       | **Release Blocker** (G15)                           |
| Physical Windows acceptance         | P0       | **Release Blocker** (G2, G10, G14)                  |

---

## Requirement Closure Review (2026-09-06)

| Requirement                        | Interpretation                                                                     | Current implementation                                   | Evidence                                                                                                    | Gap                                                         | Classification              | Minimum implementation                                                                                     | Owner        |
| ---------------------------------- | ---------------------------------------------------------------------------------- | -------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------- | --------------------------- | ---------------------------------------------------------------------------------------------------------- | ------------ |
| Solar-shadow geometry/trigonometry | Per-structure heights from shadow length + solar angles, as calibration references | None (0 matches in `src/`)                               | Verified search + `docs/ps-solar-shadow-closure.md` §§1–12                                                  | Full chain absent                                           | **C — MAJOR NEW SUBSYSTEM** | New `depthwizard.solar` package feeding `CalibrationSamples`; tests per closure §14                        | Shivam       |
| 3D neural rendering                | Learned scene representation + neural view synthesis                               | Three.js rasterization only (0 neural matches in `src/`) | Verified search + `docs/ps-neural-rendering-closure.md` §§1–4; in-repo PS sources contain no neural wording | Representation + synthesizer + GPU/packaging program absent | **C — MAJOR NEW SUBSYSTEM** | Per-scene fit + versioned artifact + WebGL/WASM renderer + held-out metrics; or accept rasterization claim | Aryan/Shivam |

**Decision:** **C for both** — from evidence, not impression. No implementation started (closure analysis only).

## Required Actions for SIH Compliance

| Action                                                                                                                                                                                          | Owner        | Timeline                    |
| ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------ | --------------------------- |
| Accept or reject the solar C-classification; if accepted, scope `depthwizard.solar` as a separate program (`docs/ps-solar-shadow-closure.md` §14)                                               | Shivam       | Required for SIH compliance |
| Accept or reject the neural-rendering C-classification; if binding, scope the NeRF/GS program (`docs/ps-neural-rendering-closure.md` §5) or record rasterization as the accepted interpretation | Aryan/Shivam | Required for SIH compliance |
| Document single-tile vs city-scale scope limitation                                                                                                                                             | Aryan/Shivam | Documentation               |
| Freeze final ML candidate with solar-aware model                                                                                                                                                | Shravan      | Required for SIH compliance |

---

**End of SIH Compliance Matrix.** This audit reflects actual repository state at `809801d`.
