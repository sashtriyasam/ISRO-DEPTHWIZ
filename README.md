# DepthWizard — ISRO SIH 26175

[![Release](https://img.shields.io/badge/Release-v1.3.1-success.svg)](https://github.com/sashtriyasam/ISRO-DEPTHWIZ/releases/tag/v1.3.1)
[![CI](https://github.com/sashtriyasam/ISRO-DEPTHWIZ/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/sashtriyasam/ISRO-DEPTHWIZ/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](#testing--scientific-verification)
[![Desktop](https://img.shields.io/badge/Desktop-Electron_+_React_19_+_Three.js-blue.svg)](#system-architecture)

> **Single-View Height Estimation and 3D Flythrough**  
> **Problem Statement ID:** 26175  
> **Organization:** Indian Space Research Organisation (ISRO), Department of Space / SAC  
> **Theme:** Disaster Management / Urban Planning / Reconnaissance  
> **Release tag:** `v1.3.1` (`63a41f6`)

---

## Executive Summary

**DepthWizard** is an end-to-end scientific software suite designed for the Indian Space Research Organisation (ISRO) to convert single-view optical RGB satellite imagery into relative surface models, reference-calibrated Digital Surface Models (DSMs), and interactive 3D terrain flythrough assets. Measured accuracy is reported in [Evaluation Metrics](#evaluation-metrics-isro-ps-26175-criteria); it is a research baseline, not a validated precision claim.

- **Path A (Non-Georeferenced PNG/JPG)**: Converts raw optical images into a **Relative Digital Surface Model (`rDSM`)** in the local coordinate frame (`units=None`) without fabricating spatial metadata, CRS, or metric units.
- **Path B (Georeferenced GeoTIFF + reference)**: Converts relative depth into a **metric DSM (`DSMGrid`)** in metres ($m$) only when the user attaches a reference — a DEM GeoTIFF (absolute elevation) or a GCP CSV (`elevation` or `height_agl`) — preserving CRS and affine transform. Without a reference the app stays relative; metres are never fabricated.
- **3D Texture Projection & Interactive Flythrough**: Drapes the input's RGB pixels (as the model saw them) over the terrain mesh in React 19 + Three.js + Electron, with Orbit, First-Person and aerial controls, waypoint flythrough, a slope layer (projected metric CRS only), height inspection and GeoTIFF export of the DSM.

### Unreleased (after v1.3.1)
- **Truthful calibration**: metric output requires a DEM/GCP reference; the synthetic dev calibration is test-only (`DW_DEV_CALIBRATION=1`). Weak fits (R² < 0.25) are flagged.
- **Input handling**: one nodata-aware loader (16-bit stretch, declared band order, nodata/alpha masks); inputs above 8 MP are refused with tiling advice.
- **Satellite tiling**: tiles are aligned into one relative frame before blending.
- **One inference per Generate**, working LOD meshes, live progress, Cancel that stops Python.
- **Delivered**: RGB texture, slope layer, DSM GeoTIFF export; solar cues returned (never invented sun angles).
- **Installer**: `setup_backend.bat` provisions a managed runtime with the DA-V2 model; checkpoints are SHA-verified and loaded weights-only.

### Recent Enhancements (v1.3.1)
- **Satellite / Orthophoto Backend**: `SatelliteDepthBackend` (`depth-anything-v2-satellite`) — DA-V2 Small fine-tuned on GAMUS (smoke run, **no accuracy evaluation yet**; never auto-selected over DA-V2 Small). Checkpoint-gated via `DW_DAV2_SAT_CKPT`; output remains **relative** depth only.
- **Flat-Depth Variance Check**: Pipeline warns when depth output variance is near zero (std/mean ratio below 1e-6), catching model failures on uniform imagery (e.g. map screenshots).
- **Satellite Training Pipeline**: `scripts/train_satellite_adaptation.py` — Scale-Invariant + Gradient loss fine-tuning on GAMUS orthophoto + nDSM/AGL.

### Prior Highlights (v1.2.0)
- **Calibration Method Selection**: OLS (`scale_offset`), robust Huber (`scale_offset_huber`), and piecewise-linear (`piecewise_linear`) via UI and service API.
- **FileBasedCalibrationProvider**: File-backed calibration profiles.
- **Mesh LOD Control**: Selectable mesh detail levels (strided lattice of the full grid).
- **Semantic Preprocessing**: Library stubs only — **not wired into the app**.
- **DepthAnything V2 Large**: Available when checkpoint present, with fallback to smaller backends.

### Known limitations
- Accuracy is a research baseline (see Evaluation Metrics); external test-city scoring is pending and the satellite fine-tune is unevaluated.
- Products travel to the desktop as JSON, so one run is limited to about 8 MP (`DW_MAX_INPUT_PIXELS`); larger scenes must be tiled.
- Semantic preprocessing and mosaicking exist as library code only.
- Solar-shadow heights are returned as an independent cross-check, not fused into the DSM.
- GCPs are given in pixel coordinates; contours and reference-overlay layers are not implemented.

> **Scope & Compliance Policy:** All implemented PS capabilities in the defined acceptance matrix were verified; scientific generalization/accuracy beyond the tested evidence is not claimed. Relative depth is not metric DSM without calibration evidence.

---

## ISRO Problem Statement 26175 Matrix & Verification

| Requirement | Implementation Component | Status & Verification Evidence |
| :--- | :--- | :--- |
| **1. Single-View Optical RGB Input** | `InputInspection`, `load_model_rgb` ([src/depthwizard/ingestion/](src/depthwizard/ingestion)) | **PASS** — PNG, JPG, GeoTIFF up to 8 MP per run; 16-bit stretch, declared band order, nodata/alpha masks. |
| **2. Non-Georeferenced Relative DSM (rDSM)** | `RelativeSurfaceGrid` ([src/depthwizard/rdsm/](src/depthwizard/rdsm)) | **PASS** — Relative height model (`units=None`, `LOCAL` frame). Zero fabricated CRS or metres. |
| **3. Georeferenced Metric DSM (DSM)** | `ScientificHeightProduct` ([src/depthwizard/dsm/](src/depthwizard/dsm)) | **PASS (needs a reference)** — Metric DSM in metres only from a user-supplied DEM/GCP reference, preserving CRS and affine transform. Accuracy: see Evaluation Metrics. |
| **4. Pretrained Monocular Depth Engine** | `DepthAnythingV2Backend`, `SatelliteDepthBackend` | **PASS** — DA-V2 Small provisioned by `setup_backend.bat`; Large / satellite when their verified checkpoints are present. M17 stays research-only (not offered). |
| **5. Scale Calibration Module** | `ScaleOffsetCalibrator`, `HuberScaleOffsetCalibrator`, `PiecewiseLinearCalibrator`, `select_calibration_provider` ([src/depthwizard/calibration/](src/depthwizard/calibration)) | **PASS** — DEM (absolute elevation targets only) or GCP CSV references; OLS, robust Huber, continuous piecewise spline; weak fits flagged. |
| **6. Optical Texture Projection** | Service texture + `createRgbTexture` ([src/layers/layerRenderer.ts](src/layers/layerRenderer.ts)) | **PASS** — The model-input RGB is draped on the mesh with pixel-centre UVs (RGB layer). |
| **7. Real-Time 3D Rendering** | Three.js 0.177 + React 19 + Electron 44.2.0 | **PASS** — Display mesh capped at 1M vertices (DSM stays full resolution). |
| **8. First-Person & Aerial Flythrough** | `src/camera/` & `src/flythrough/` | **PASS** — Orbit, First-Person aerial camera, waypoint trajectory player. |
| **9. Height & Slope Analysis** | `compute_slope` ([src/depthwizard/dsm/slope.py](src/depthwizard/dsm/slope.py)), profile, measurement | **PASS** — Inspector, profile, measurement with explicit units (m / px), slope layer for projected metric CRSs, DSM GeoTIFF export. |
| **10. Standalone Application Deployment** | electron-builder.yml & provision_runtime.py | **PASS (installer)** — Unsigned NSIS Installer (`forceCodeSigning: false`). Clean-machine witness passed for the signed RC1 installer (`v0.1.0-sih-26175-rc1`, see [docs/RELEASE_ARTIFACT_RECORD.md](docs/RELEASE_ARTIFACT_RECORD.md)); the v1.3.1 witness is **pending**. |

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                      DEPTHWIZARD STANDALONE APPLICATION                         │
├─────────────────────────────────────────────────────────────────────────────────┤
│  Electron Native Host (Main + Preload + Sandboxed IPC)                          │
│  ├── Renderer: React 19 + Three.js 0.177 (Vite)                                 │
│  ├── Viewport & Flythrough: Orbit/First-Person/Aerial Navigation + Waypoints    │
│  ├── Measurement & Tools: Point Inspector, Height/Slope Profile, Exaggeration  │
│  ├── Workspace Controls: Backend auto-selection, calibration method, mesh LOD   │
│  └── Preload Bridge: ContextBridge IPC (8 service methods)                      │
│       ↓                                                                         │
│  Managed Python Scientific Service (depthwiz_service.py)                        │
│  ├── Ingestion & Geospatial: InputInspection, CRS & Affine Preservation         │
│  ├── Depth Backends: DA-V2 (Small/Large), SatelliteDepthBackend, M17            │
│  ├── Calibration Engine: ScaleOffsetCalibrator, HuberScaleOffsetCalibrator,     │
│  │   PiecewiseLinearCalibrator                                                  │
│  ├── Semantic Preprocessing: Optional RGB-guided depth refinement               │
│  ├── Products: RelativeSurfaceGrid (Path A) / ScientificHeightProduct (Path B)   │
│  ├── Analytics: SlopeGrid (degree computation), flat-depth variance warning     │
│  ├── Mesh & Texture: TerrainMesh generation, adaptive LOD decimation,           │
│  │   TextureProjection mapping                                                  │
│  └── Export: GeoTIFF export (prepare-only, zero CRS invention)                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Download & Installation

### Standalone Windows Installer
Download the standalone installer directly from the GitHub release:
- **Download Installer**: [DepthWizard Setup v1.3.1.exe](https://github.com/sashtriyasam/ISRO-DEPTHWIZ/releases/download/v1.3.1/DepthWizard.Setup.1.3.1.exe)
- **Installer SHA-256**: `b858dc52d5d8bcd17a24b4f5b1d1ff9a0eccab738c6bb3d7cad53136cf5bcf40`
- **Authenticode Signature**: Not signed (`forceCodeSigning: false`)
- **Clean Machine Physical Witness**: Pending install verification for `v1.3.1`

---

## Testing & Scientific Verification

### Python Core Engine
```bash
# Execute the Python suite (opt-in heavy models skipped by default)
python -m pytest tests/

# Code quality & typing checks
python -m ruff check src tests
python -m ruff format --check src tests
python -m mypy --python-version 3.12 src
```

### Desktop UI & Vitest Integration
```bash
# Run TypeScript compilation check (0 errors)
npm run typecheck

# Run the Vitest suite
npm run test
```

### Key Test Areas
- `tests/backends/test_satellite.py` — Satellite backend contract, tiling, provenance
- `tests/pipeline/test_flat_detection.py` — Flat-depth variance warning
- `tests/semantics/test_classifier.py` — Semantic classifier unit tests
- `tests/pipeline/test_chain.py` — Semantic preprocessing integration tests
- `tests/service/test_execute.py` — LOD mesh and calibration method service tests
- `tests/integration/test_dav2_bridge.py` — Backend bridge integration tests

---

## Evaluation Metrics (ISRO PS 26175 Criteria)

1. **DSM Estimation Accuracy (50%)**:
   - Automated benchmark harness (`src/depthwizard/evaluation/`) evaluates **RMSE**, **MAE**, and **$R^2$ correlation** against reference LiDAR/DEM ground truth across urban, sparse, hilly, and forested landscapes.
   - **Measured so far (DA-V2 Small, calibrated):** 32-tile GAMUS pooled MAE 4.40 m, RMSE 5.86 m, $R^2$ 0.23; cross-city macro $R^2$ ≈ 0.09 ([docs/gamus-cross-city-expanded.md](docs/gamus-cross-city-expanded.md)). Formal external test-city scoring is **pending**. The satellite fine-tune has no accuracy evaluation yet.
   - Reference Dataset: Compatible with [ISRO SAC SIH Reference Dataset](https://github.com/IMG-PROCESS-SAC/SIH2026/).

2. **Visualization & UX (50%)**:
   - High visual fidelity with real-time Three.js mesh rasterization.
   - Seamless first-person and aerial waypoint navigation.
   - Idempotent offline deployment with managed Python runtime.
   - User-selectable calibration methods and mesh LOD levels for optimized workflows.

---

## License & Team Ownership

- **Lead Architecture & Release Authority**: Shivam Shelatkar
- **ML & Depth Backbone Engineering**: Shravan
- **Desktop Application & Rendering**: Aryan
- **Repository**: [https://github.com/sashtriyasam/ISRO-DEPTHWIZ](https://github.com/sashtriyasam/ISRO-DEPTHWIZ)
- **License**: Apache-2.0
