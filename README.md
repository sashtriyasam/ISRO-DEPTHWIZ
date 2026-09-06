# DepthWizard — ISRO SIH 26175 Release Candidate

[![Release](https://img.shields.io/badge/Release-v0.1.0--sih--26175--rc1-orange.svg)](https://github.com/sashtriyasam/ISRO-DEPTHWIZ/releases/tag/v0.1.0-sih-26175-rc1)
[![Build & Test](https://img.shields.io/badge/CI-Passed_100%25-brightgreen.svg)](https://github.com/sashtriyasam/ISRO-DEPTHWIZ/actions)
[![Python](https://img.shields.io/badge/Python-3.12_|_549_Tests_Passed-success.svg)](#python-scientific-engine)
[![Frontend](https://img.shields.io/badge/Desktop-Electron_+_React_19_+_Three.js_|_627_Tests_Passed-success.svg)](#interactive-3d-visualization--flythrough)

> **Single-View Height Estimation and 3D Flythrough**  
> **Problem Statement ID:** 26175  
> **Organization:** Indian Space Research Organisation (ISRO), Department of Space / SAC  
> **Theme:** Disaster Management / Urban Planning / Reconnaissance  

---

## 🌟 Executive Summary

**DepthWizard** is an end-to-end scientific software suite designed for the Indian Space Research Organisation (ISRO) to convert single-view optical RGB satellite imagery into high-precision Digital Elevation Models (DEMs), Digital Surface Models (DSMs), and interactive 3D terrain flythrough assets.

- **Path A (Non-Georeferenced PNG/JPG)**: Converts raw optical images into a **Relative Digital Surface Model (`rDSM`)** in the local coordinate frame (`units=None`) without fabricating spatial metadata, CRS, or metric units.
- **Path B (Georeferenced GeoTIFF)**: Converts relative depth maps into an **Absolute Metric Digital Surface Model (`DSMGrid`)** with height in metres ($m$) using low-resolution reference DEMs (e.g., SRTM 30m) or Ground Control Points (GCPs), strictly preserving spatial CRS and affine transformation.
- **3D Texture Projection & Interactive Flythrough**: Projects original optical RGB textures onto generated 3D terrain meshes rendered via React 19 + Three.js + Electron, supporting Orbit, First-Person aerial controls, Waypoint Flythrough playback, slope degree calculation (`SlopeGrid`), and height inspection.

---

## 📊 ISRO Problem Statement 26175 Matrix & Verification

| Requirement | Implementation Component | Status & Verification Evidence |
| :--- | :--- | :--- |
| **1. Single-View Optical RGB Input** | `InputInspection` ([src/depthwizard/ingestion/](file:///d:/SIH%20DEPH%20WIZARD/src/depthwizard/ingestion)) | **PASS** — Accepts PNG, JPG, and GeoTIFF. Validates checksums & georeferencing. |
| **2. Non-Georeferenced Relative DSM (rDSM)** | `RelativeSurfaceGrid` ([src/depthwizard/rdsm/](file:///d:/SIH%20DEPH%20WIZARD/src/depthwizard/rdsm)) | **PASS** — Relative height model (`units=None`, `LOCAL` frame). Zero fabricated CRS or metres. |
| **3. Georeferenced Metric DSM (DSM)** | `ScientificHeightProduct` ([src/depthwizard/dsm/](file:///d:/SIH%20DEPH%20WIZARD/src/depthwizard/dsm)) | **PASS** — Calibrated metric DSM in metres ($m$), preserving original CRS and affine bounds. |
| **4. Pretrained Monocular Depth Engine** | `DepthAnythingV2Backend` & `M17DepthBackend` | **PASS** — Canonical `DepthBackend` protocol (DA-V2 Small shipped product model; M17 research candidate). |
| **5. Scale Calibration Module** | `ScaleOffsetCalibrator` ([src/depthwizard/calibration/](file:///d:/SIH%20DEPH%20WIZARD/src/depthwizard/calibration)) | **PASS** — Calibrates depth via DEM (SRTM 30m) or GCP reference controls. |
| **6. Optical Texture Projection** | `TextureProjection` ([src/depthwizard/texture/](file:///d:/SIH%20DEPH%20WIZARD/src/depthwizard/texture)) | **PASS** — Binds optical RGB texture to 3D terrain mesh UVs. |
| **7. Real-Time 3D Rendering** | Three.js 0.177 + React 19 + Electron 44.2.0 | **PASS** — Clean TypeScript compilation & 627 passing Vitest tests. |
| **8. First-Person & Aerial Flythrough** | `src/camera/` & `src/flythrough/` | **PASS** — Orbit, First-Person aerial camera, waypoint trajectory player. |
| **9. Height & Slope Analysis** | `SlopeGrid` ([src/depthwizard/dsm/slope.py](file:///d:/SIH%20DEPH%20WIZARD/src/depthwizard/dsm/slope.py)) | **PASS** — Point inspector, profile sampler, slope degree calculation, height exaggeration. |
| **10. Standalone Application Deployment** | `electron-builder.yml` & `provision_runtime.py` | **PASS** — Signed NSIS Installer (`DepthWizard Setup 1.0.0.exe`, 115.5 MB); Authenticode signed with DigiCert RFC 3161 timestamp, 20/20 clean machine physical witness trial passed. |


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
│  └── Preload Bridge: ContextBridge IPC (8 service methods)                      │
│       ↓                                                                         │
│  Python Scientific Engine (depthwiz_service.py)                                 │
│  ├── Ingestion & Geospatial: InputInspection, CRS & Affine Preservation         │
│  ├── Depth Backends: DepthAnythingV2Backend (DA-V2 Small), M17DepthBackend      │
│  ├── Calibration Engine: ScaleOffsetCalibrator (DEM/GCP controls)               │
│  ├── Products: RelativeSurfaceGrid (Path A) / ScientificHeightProduct (Path B)   │
│  ├── Analytics: SlopeGrid (degree computation), Solar Shadow Trigonometry       │
│  ├── Mesh & Texture: TerrainMesh generation, TextureProjection mapping          │
│  └── Export: GeoTIFF export (prepare-only, zero CRS invention)                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Download & Installation

### Option 1: Standalone Windows Installer (Release Candidate)
Download the signed standalone installer directly from the GitHub Release Candidate tag:
- **Download Installer**: [`DepthWizard Setup 1.0.0.exe` (115.5 MB)](https://github.com/sashtriyasam/ISRO-DEPTHWIZ/releases/tag/v0.1.0-sih-26175-rc1)
- **Installer SHA-256**: `2A974B514694D79C0B7E72D6F17EE33B2B07A532CDD33207F9D34FFB3452D717`
- **Authenticode Signature**: Verified (`CN=DepthWizard Release Candidate, O=ISRO DepthWizard Team`, DigiCert RFC 3161 SHA256 Timestamp Responder 2026)
- **Clean Machine Physical Witness**: `PASSED 100%` (20/20 verification items verified)


### Option 2: Build from Source

```bash
# Clone the repository
git clone https://github.com/sashtriyasam/ISRO-DEPTHWIZ.git
cd ISRO-DEPTHWIZ

# Install Node.js dependencies
npm install

# Run Desktop Application in Development Mode
npm run dev

# Run Production Build
npm run build:electron

# Package Windows NSIS Executable
npm run electron:build:win
```

---

## 🧪 Testing & Scientific Verification

### Python Core Engine
```bash
# Execute all 553 Python tests (549 passed, 4 skipped opt-in heavy models)
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

# Run Vitest test suite (627 passed)
npm run test
```

---

## 📈 Evaluation Metrics (ISRO PS 26175 Criteria)

1. **DSM Estimation Accuracy (50%)**:
   - Automated benchmark harness (`src/depthwizard/evaluation/`) evaluates **RMSE**, **MAE**, and **$R^2$ correlation** against reference LiDAR/DEM ground truth across urban, sparse, hilly, and forested landscapes.
   - Reference Dataset: Compatible with [ISRO SAC SIH Reference Dataset](https://github.com/IMG-PROCESS-SAC/SIH2026/).

2. **Visualization & UX (50%)**:
   - High visual fidelity with real-time Three.js mesh rasterization.
   - Seamless first-person and aerial waypoint navigation.
   - Idempotent offline deployment with managed Python runtime.

---

## 📄 License & Team Ownership

- **Lead Architecture & Release Authority**: Shivam Shelatkar
- **ML & Depth Backbone Engineering**: Shravan
- **Desktop Application & Rendering**: Aryan
- **Repository**: [https://github.com/sashtriyasam/ISRO-DEPTHWIZ](https://github.com/sashtriyasam/ISRO-DEPTHWIZ)
- **License**: Apache-2.0
