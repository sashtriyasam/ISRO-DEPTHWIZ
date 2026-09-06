# SIH Submission Package — DepthWizard (ISRO PS 26175)

**Project Name:** DepthWizard — Single-View Height Estimation & 3D Flythrough  
**Problem Statement:** ISRO PS 26175 (Smart India Hackathon 2026)  
**Release Tag:** `v0.1.0-sih-26175-rc1` (Immutable tag target)  
**Canonical Commit SHA:** `24cce9825e66d789fe981063090c09a1c717c4e3` (`24cce98`)  
**Lead Architecture & Release Owner:** Shivam Shelatkar (Lead Architect)  
**Team Members:** Shivam (Architecture & Geospatial Core), Shravan (ML & Depth Models), Aryan (Desktop App & 3D Rendering)  

---

## Executive Summary

DepthWizard is a standalone, air-gapped Windows desktop application for estimating height maps from single optical or satellite imagery and performing real-time 3D flythrough visualization. Shipped under release candidate `v0.1.0-sih-26175-rc1`, it enforces strict scientific truthfulness by separating uncalibrated relative height maps (`rDSM`) from georeferenced metric digital surface models (`DSM`) calibrated using reference elevation data or ground control points.

---

## 1. Final Software Architecture

DepthWizard is built as a multi-process architecture consisting of an Electron + React + TypeScript + Three.js host and an IPC-launched Python 3.11+ sidecar service using a managed virtual environment runtime.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           FRONTEND HOST (Electron 35)                   │
│                                                                         │
│   ┌──────────────────────────┐         ┌────────────────────────────┐   │
│   │   React / TypeScript UI  │ ◄─────► │  Three.js 3D Viewport      │   │
│   │   (GIS Controls & HUD)   │         │  (Mesh & Flight Animation) │   │
│   └─────────────┬────────────┘         └──────────────▲─────────────┘   │
└─────────────────┼─────────────────────────────────────┼─────────────────┘
                  │ Child Process StdIO Async IPC       │ WebGL Buffers / Rasters
                  ▼                                     │
┌───────────────────────────────────────────────────────┴─────────────────┐
│                 BACKEND SIDECAR (Managed Python Virtual Env)            │
│                                                                         │
│   ┌──────────────────────────┐         ┌────────────────────────────┐   │
│   │  Ingestion & Geospatial  │ ──────► │   DA-V2 Small ML Inference │   │
│   │  (GDAL / Rasterio / CRS) │         │   (Relative rDSM Engine)   │   │
│   └──────────────────────────┘         └──────────────┬─────────────┘   │
│                                                       │                 │
│   ┌──────────────────────────┐                        ▼                 │
│   │  3D Terrain Mesh Builder │ ◄───────── ┌─────────────────────────┐   │
│   │  (TerrainMesh.build())   │            │   Calibration Engine    │   │
│   └──────────────────────────┘            │   (DEM 30m / GCP OLS)   │   │
│                                           └─────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

### Core Architecture Components
1. **Frontend Presentation Engine (Electron + React + Three.js):**
   - **Framework:** TypeScript 5.7, React 19, Vite 6, Electron 35 (Electron 44.2.0 framework).
   - **3D Graphics Engine:** Three.js WebGL 2.0 rendering engine supporting indexed triangle terrain meshes, custom shader lighting, camera flight path interpolation, and spatial inspection HUD.
2. **Backend Scientific Service (Managed Python Virtual Environment):**
   - **Runtime Strategy:** Managed Python virtual environment (`provision_runtime.py`, `DEPTHWIZARD_PYTHON` / `python` on PATH).
   - **Service Entrypoints:** `scripts/depthwiz_service.py` (control plane) & `scripts/backend_bridge.py` (payload plane).
   - **Geospatial Processing:** Rasterio, NumPy, Pillow, PyProj for coordinate transformations, affine GeoTransforms, and spatial bounds parsing.
   - **Calibration Core:** Ordinary Least Squares (OLS) linear regression model fitting relative depth $H_{\text{rel}}$ against reference 30m DEM (COP-DEM / SRTM) or manual GCPs.
3. **IPC Bridge (`src/backend/bridge.ts`):**
   - Asynchronous JSON-RPC protocol over stdin/stdout.
   - Zero HTTP network dependency — works 100% offline in air-gapped environments.

---

## 2. Installer & Signed Artifact Provenance

| Parameter | Specification / Evidence |
| :--- | :--- |
| **Signed Installer Name** | `DepthWizard Setup 1.0.0.exe` |
| **File Size** | `115,579,824 bytes` (115.57 MB) |
| **Exact SHA-256 Hash** | `2A974B514694D79C0B7E72D6F17EE33B2B07A532CDD33207F9D34FFB3452D717` |
| **Authenticode Signature** | **VALID** (`CN=DepthWizard Release Candidate, O=ISRO DepthWizard Team`) |
| **Timestamp Authority** | DigiCert RFC 3161 SHA256 Timestamp Responder (2026) |
| **Installation Path** | `%LOCALAPPDATA%\Programs\depthwizard` |
| **Runtime Architecture** | Managed Python 3.11+ virtual environment (`provision_runtime.py`) |
| **Model Checkpoint Policy** | External managed provision (`DW_DAV2_CKPT` / `%APPDATA%\DepthWizard\checkpoints\depth_anything_v2_vits.pth`) |
| **GitHub Release Link** | [DepthWizard v0.1.0-sih-26175-rc1 Release](https://github.com/sashtriyasam/ISRO-DEPTHWIZ/releases/tag/v0.1.0-sih-26175-rc1) |

---

## 3. Comprehensive Documentation Registry

The codebase contains exhaustive, canonical documentation detailing every facet of system design, scientific methodology, and acceptance gates:

- **Master Plan & Architecture:** [`docs/project/MASTER_PLAN.md`](file:///d:/SIH%20DEPH%20WIZARD/docs/project/MASTER_PLAN.md)
- **Scientific Evidence Package:** [`docs/SCIENTIFIC_EVIDENCE_PACKAGE.md`](file:///d:/SIH%20DEPH%20WIZARD/docs/SCIENTIFIC_EVIDENCE_PACKAGE.md)
- **Release Artifact Record:** [`docs/RELEASE_ARTIFACT_RECORD.md`](file:///d:/SIH%20DEPH%20WIZARD/docs/RELEASE_ARTIFACT_RECORD.md)
- **Final Release Gate Audit:** [`docs/final-release-gate.md`](file:///d:/SIH%20DEPH%20WIZARD/docs/final-release-gate.md)
- **Final SIH Compliance Audit:** [`docs/final-sih-compliance.md`](file:///d:/SIH%20DEPH%20WIZARD/docs/final-sih-compliance.md)
- **Final SIH Demo Guide:** [`docs/FINAL_SIH_DEMO_GUIDE.md`](file:///d:/SIH%20DEPH%20WIZARD/docs/FINAL_SIH_DEMO_GUIDE.md)
- **Geospatial Specifications:** [`docs/geospatial.md`](file:///d:/SIH%20DEPH%20WIZARD/docs/geospatial.md)
- **DSM Engine Specifications:** [`docs/dsm-engine.md`](file:///d:/SIH%20DEPH%20WIZARD/docs/dsm-engine.md)
- **Calibration Methodology:** [`docs/calibration.md`](file:///d:/SIH%20DEPH%20WIZARD/docs/calibration.md)
- **Mesh Engine & Flythrough:** [`docs/mesh-engine.md`](file:///d:/SIH%20DEPH%20WIZARD/docs/mesh-engine.md), [`docs/flythrough.md`](file:///d:/SIH%20DEPH%20WIZARD/docs/flythrough.md)

---

## 4. Scientific Methodology

DepthWizard adheres strictly to geospatial principles, preventing false claims of metric accuracy without empirical reference calibration.

### Dual-Path Processing Framework

#### Path A: Standard Imagery (PNG / JPG / BMP)
- **Input:** Single uncalibrated optical image.
- **Inference:** Depth-Anything-V2 Small extracts structural relative depth.
- **Scientific Contract:** Output is classified as **`rDSM` (Relative Digital Surface Model)** with `metric=false` and `units=None`.
- **UI Policy:** Displays relative scale $[0.0, 1.0]$. Metres, absolute elevations, and spatial coordinate grids are explicitly disabled.

#### Path B: Single-View Satellite Imagery (GeoTIFF)
- **Input:** Single satellite GeoTIFF containing EPSG CRS and affine GeoTransform matrix.
- **Inference:** ML backend predicts structural relative depth map $H_{\text{rel}}$ while preserving spatial metadata.
- **Calibration Engine:** Aligns $H_{\text{rel}}$ against reference 30m DEM (COP-DEM/SRTM) or manual GCPs via Ordinary Least Squares (OLS) regression:
  $$H_{\text{metric}}(x, y) = s \cdot H_{\text{rel}}(x, y) + t$$
- **Scientific Contract:** Produces calibrated **`DSM` (Digital Surface Model)** with `metric=true`, `units=metres`, spatial CRS, GeoTransform, and residual RMSE validation metrics.

---

## 5. Model Provenance & ML System

### Shipped Product Model: Depth-Anything-V2 Small (`DA-V2 Small`)
- **Weight File:** `depth_anything_v2_vits.pth`
- **Parameter Count:** $\approx 24.8\text{M}$ parameters (ViT-Small backbone)
- **Licensing:** Apache 2.0 (commercial & research friendly)
- **Role:** Primary inference backend shipped in the production desktop application.

### Research Candidate: M17 (`m17_candidate.pth`)
- **Status:** Frozen research candidate (documented in [`docs/final-ml-candidate.md`](file:///d:/SIH%20DEPH%20WIZARD/docs/final-ml-candidate.md) and [`docs/m17-product-promotion.md`](file:///d:/SIH%20DEPH%20WIZARD/docs/m17-product-promotion.md)).
- **Integrity Checksum:** SHA-256 `D7C0BE9127FAFAC5F4C2D207E3626D335AF148A8CBB7489A10EE8C7F7DA4EDAC`
- **Promotion Decision:** Kept as research candidate pending formal test-city benchmark scoring; DA-V2 Small retained for shipped RC1 build due to verified backend stability.

---

## 6. Evaluation & Scientific Validation Results

### 1. GAMUS 32-Tile Ground Truth Baseline
Evaluated on 32 high-resolution aerial LiDAR tiles from the GAMUS benchmark dataset:
- **Mean Absolute Error (MAE):** $4.40\text{ m}$
- **Root Mean Squared Error (RMSE):** $5.86\text{ m}$
- **Coefficient of Determination ($R^2$):** $0.23$
- **Interpretation:** Demonstrates structural relative depth extraction from single optical views. Reflects realistic single-view ambiguity prior to stereo/multi-view integration.

### 2. GeoNRW Cross-City Probe Evaluation
Evaluated across 6 German urban landscapes (Aachen, Bonn, Cologne, Düsseldorf, Essen, Wuppertal):
- **Probe Finding:** **Observed cross-city probe improvement; not a generalization proof.** (Pearson $r = 0.37$).

### 3. Automated Software Verification
- **Pytest Backend Test Suite:** **549 passed**, 0 failed, 4 skipped.
- **Vitest Frontend Test Suite:** **627 passed**, 0 failed.
- **TypeScript Typecheck:** 0 errors.
- **Ruff Linter & Formatter:** 0 errors.

---

## 7. Known Scientific Limitations & Future Scope

In accordance with scientific truthfulness, DepthWizard explicitly documents remaining limitations:

1. **Single-View Ambiguity:** Single optical images lack absolute scale. Metric heights require reference DEM (30m) or GCP calibration.
2. **Solar-Shadow Height Extraction:** Solar-shadow height extraction was investigated but explicitly excluded from shipped RC1 product scope (`docs/ps-solar-shadow-gap.md`).
3. **Multi-View Stereo:** DepthWizard processes single views. True multi-view photogrammetry is out of scope for PS 26175 single-view requirements.
4. **Generalization Claim Policy:** All implemented PS capabilities in the defined acceptance matrix were verified; scientific generalization/accuracy beyond the tested evidence is not claimed.

---

## 8. Demonstration Workflow Overview

1. **Fresh Install:** Run `DepthWizard Setup 1.0.0.exe` on clean Windows 10/11 machine.
2. **Path A Ingestion:** Load `sample_terrain.jpg` $\rightarrow$ inspect `rDSM` ($[0, 1]$ relative scale).
3. **Path B Ingestion:** Load `sample_geotiff.tif` $\rightarrow$ inspect preserved CRS and transform.
4. **DEM Calibration:** Run 30m DEM alignment $\rightarrow$ obtain calibrated metric `DSM` ($m$) with scale $s$, shift $t$, and RMSE.
5. **3D Mesh & Texture:** View 3D surface mesh with projected satellite UV ortho-texture.
6. **Spatial Analysis:** Perform point elevation query, 2D profile slicing, building height delta ($\Delta h$), and 3D volume calculation.
7. **Flythrough Animation:** Execute first-person flight controls (`WASD`) and automated spline camera flythrough.
8. **Failure Rejection:** Attempt loading invalid format $\rightarrow$ observe safe rejection modal.
9. **Offline Test:** Disconnect network $\rightarrow$ verify 100% functionality without internet connection.

---

## 9. Release Notes (`v0.1.0-sih-26175-rc1`)

```markdown
# DepthWizard v0.1.0-sih-26175-rc1 (Release Candidate 1)

Official Release Candidate 1 for ISRO Problem Statement 26175 (Single-View Height Estimation and 3D Flythrough).

## Key Deliverables
- Executable: `DepthWizard Setup 1.0.0.exe` (115,579,824 bytes / 115.57 MB)
- Commit SHA: `24cce9825e66d789fe981063090c09a1c717c4e3`
- Authenticode Signature: Valid (DigiCert RFC 3161 SHA256 Timestamped)
- Shipped ML Model: Depth-Anything-V2 Small (ViT-Small, Apache 2.0)
- Calibration Engine: Reference DEM 30m / GCP OLS Linear Regression
- Rendering Engine: Electron 35 + React 19 + Three.js WebGL Flythrough
- Operating Environment: Standalone Managed-Venv Air-Gapped Windows Desktop Bundle
```
