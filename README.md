# DepthWizard — ISRO SIH 26175

[![Release](https://img.shields.io/badge/Release-v1.2.0-success.svg)](https://github.com/sashtriyasam/ISRO-DEPTHWIZ/releases/tag/v1.2.0)
[![Build & Test](https://img.shields.io/badge/CI-Passed_100%25-brightgreen.svg)](https://github.com/sashtriyasam/ISRO-DEPTHWIZ/actions)
[![Python](https://img.shields.io/badge/Python-3.12_|_685_Tests_Passed-success.svg)](#python-scientific-engine)
[![Frontend](https://img.shields.io/badge/Desktop-Electron_+_React_19_+_Three.js_|_631_Tests_Passed-success.svg)](#interactive-3d-visualization--flythrough)

> **Single-View Height Estimation and 3D Flythrough**  
> **Problem Statement ID:** 26175  
> **Organization:** Indian Space Research Organisation (ISRO), Department of Space / SAC  
> **Theme:** Disaster Management / Urban Planning / Reconnaissance  
> **Canonical Main Commit SHA:** `093eef8`

---

## 🌟 Executive Summary

**DepthWizard** is an end-to-end scientific software suite designed for the Indian Space Research Organisation (ISRO) to convert single-view optical RGB satellite imagery into high-precision Digital Elevation Models (DEMs), Digital Surface Models (DSMs), and interactive 3D terrain flythrough assets.

- **Path A (Non-Georeferenced PNG/JPG)**: Converts raw optical images into a **Relative Digital Surface Model (`rDSM`)** in the local coordinate frame (`units=None`) without fabricating spatial metadata, CRS, or metric units.
- **Path B (Georeferenced GeoTIFF)**: Converts relative depth maps into an **Absolute Metric Digital Surface Model (`DSMGrid`)** with height in metres ($m$) using low-resolution reference DEMs (e.g., SRTM 30m) or Ground Control Points (GCPs), strictly preserving spatial CRS and affine transformation.
- **3D Texture Projection & Interactive Flythrough**: Projects original optical RGB textures onto generated 3D terrain meshes rendered via React 19 + Three.js + Electron, supporting Orbit, First-Person aerial controls, Waypoint Flythrough playback, slope degree calculation (`SlopeGrid`), and height inspection.

### 🆕 Recent Enhancements (v1.2.0)
- **Calibration Method Selection**: Users can now choose between OLS (`scale_offset`), robust Huber (`scale_offset_huber`), and piecewise-linear (`piecewise_linear`) calibration methods via the UI and service API.
- **FileBasedCalibrationProvider**: File-backed calibration provider for loading calibration parameters from external files, enabling persistent and reusable calibration profiles.
- **Mesh LOD Control**: Selectable mesh detail levels (`1`, `1,4,16`, `1,2,4,8,16`) enable performance-optimized terrain rendering. The pipeline now supports adaptive mesh decimation via vertex clustering.
- **Semantic Preprocessing**: Optional semantic-aware depth refinement can be injected into the pipeline. Implementations include rule-based terrain classification and bilateral/SAM refinement stubs.
- **DepthAnything V2 Large**: The scientific engine now supports the DA-V2 Large backbone (`depth-anything-v2-large`) when its checkpoint is available, with automatic fallback to smaller backends.

> **Scope & Compliance Policy:** All implemented PS capabilities in the defined acceptance matrix were verified; scientific generalization/accuracy beyond the tested evidence is not claimed.

---

## 🌟 ISRO Problem Statement 26175 Matrix & Verification

| Requirement | Implementation Component | Status & Verification Evidence |
| :--- | :--- | :--- |
| **1. Single-View Optical RGB Input** | `InputInspection` ([src/depthwizard/ingestion/](file:///d:/SIH%20DEPH%20WIZARD/src/depthwizard/ingestion)) | **PASS** — Accepts PNG, JPG, and GeoTIFF. Validates checksums & georeferencing. |
| **2. Non-Georeferenced Relative DSM (rDSM)** | `RelativeSurfaceGrid` ([src/depthwizard/rdsm/](file:///d:/SIH%20DEPH%20WIZARD/src/depthwizard/rdsm)) | **PASS** — Relative height model (`units=None`, `LOCAL` frame). Zero fabricated CRS or metres. |
| **3. Georeferenced Metric DSM (DSM)** | `ScientificHeightProduct` ([src/depthwizard/dsm/](file:///d:/SIH%20DEPH%20WIZARD/src/depthwizard/dsm)) | **PASS** — Calibrated metric DSM in metres ($m$), preserving original CRS and affine bounds. |
| **4. Pretrained Monocular Depth Engine** | `DepthAnythingV2Backend` & `M17DepthBackend` | **PASS** — Canonical `DepthBackend` protocol (DA-V2 Small shipped; DA-V2 Large available when checkpoint present; M17 research candidate). |
| **5. Scale Calibration Module** | `ScaleOffsetCalibrator`, `HuberScaleOffsetCalibrator`, `PiecewiseLinearCalibrator` ([src/depthwizard/calibration/](file:///d:/SIH%20DEPH%20WIZARD/src/depthwizard/calibration)) | **PASS** — Calibrates depth via DEM (SRTM 30m) or GCP reference controls with selectable robust methods. |
| **6. Optical Texture Projection** | `TextureProjection` ([src/depthwizard/texture/](file:///d:/SIH%20DEPH%20WIZARD/src/depthwizard/texture)) | **PASS** — Binds optical RGB texture to 3D terrain mesh UVs. |
| **7. Real-Time 3D Rendering** | Three.js 0.177 + React 19 + Electron 44.2.0 | **PASS** — Clean TypeScript compilation & 631 passing Vitest tests. |
| **8. First-Person & Aerial Flythrough** | `src/camera/` & `src/flythrough/` | **PASS** — Orbit, First-Person aerial camera, waypoint trajectory player. |
| **9. Height & Slope Analysis** | `SlopeGrid` ([src/depthwizard/dsm/slope.py](file:///d:/SIH%20DEPH%20WIZARD/src/depthwizard/dsm/slope.py)) | **PASS** — Point inspector, profile sampler, slope degree calculation, height exaggeration. |
| **10. Standalone Application Deployment** | electron-builder.yml & provision_runtime.py | **PASS** — Unsigned NSIS Installer (orceCodeSigning: false); clean machine physical witness trial passed. |

---

## 🏗️ System Architecture

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
│  ├── Depth Backends: DepthAnythingV2Backend (Small + Large), M17DepthBackend    │
│  ├── Calibration Engine: ScaleOffsetCalibrator, HuberScaleOffsetCalibrator,     │
│  │   PiecewiseLinearCalibrator                                                  │
│  ├── Semantic Preprocessing: Optional RGB-guided depth refinement               │
│  ├── Products: RelativeSurfaceGrid (Path A) / ScientificHeightProduct (Path B)   │
│  ├── Analytics: SlopeGrid (degree computation)                                  │
│  ├── Mesh & Texture: TerrainMesh generation, adaptive LOD decimation,           │
│  │   TextureProjection mapping                                                  │
│  └── Export: GeoTIFF export (prepare-only, zero CRS invention)                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Download & Installation

### Standalone Windows Installer
Download the standalone installer directly from the GitHub release:
- **Download Installer**: [DepthWizard Setup v1.2.0.exe](https://github.com/sashtriyasam/ISRO-DEPTHWIZ/releases/download/v1.2.0/DepthWizard.Setup.1.2.0.exe)
- **Installer SHA-256**: e10691c38d2c6bc2c9a3d6d40904bfbd3cec7cd07fb58e4001e8dafec222729
- **Authenticode Signature**: Not signed (orceCodeSigning: false)
- **Clean Machine Physical Witness**: `PASSED` (Verification items verified)

---

## 🧪 Testing & Scientific Verification

### Python Core Engine
```bash
# Execute all 685 Python tests (7 skipped opt-in heavy models)
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

# Run Vitest test suite (631 passed)
npm run test
```

### Key Test Files Added in rc2
- `tests/semantics/test_classifier.py` — Semantic classifier unit tests
- `tests/pipeline/test_chain.py` — Semantic preprocessing integration tests
- `tests/service/test_execute.py` — LOD mesh and calibration method service tests
- `tests/integration/test_dav2_bridge.py` — Backend bridge integration tests

---

## 📈 Evaluation Metrics (ISRO PS 26175 Criteria)

1. **DSM Estimation Accuracy (50%)**:
   - Automated benchmark harness (`src/depthwizard/evaluation/`) evaluates **RMSE**, **MAE**, and **$R^2$ correlation** against reference LiDAR/DEM ground truth across urban, sparse, hilly, and forested landscapes.
   - Reference Dataset: Compatible with [ISRO SAC SIH Reference Dataset](https://github.com/IMG-PROCESS-SAC/SIH2026/).

2. **Visualization & UX (50%)**:
   - High visual fidelity with real-time Three.js mesh rasterization.
   - Seamless first-person and aerial waypoint navigation.
   - Idempotent offline deployment with managed Python runtime.
   - User-selectable calibration methods and mesh LOD levels for optimized workflows.

---

## 📄 License & Team Ownership

- **Lead Architecture & Release Authority**: Shivam Shelatkar
- **ML & Depth Backbone Engineering**: Shravan
- **Desktop Application & Rendering**: Aryan
- **Repository**: [https://github.com/sashtriyasam/ISRO-DEPTHWIZ](https://github.com/sashtriyasam/ISRO-DEPTHWIZ)
- **License**: Apache-2.0
