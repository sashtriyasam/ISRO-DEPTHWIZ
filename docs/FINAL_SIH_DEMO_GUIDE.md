# Final SIH Demo & System Walkthrough Guide — DepthWizard (ISRO PS 26175)

**Target Audience:** SIH Evaluators, ISRO Technical Judges, and Demonstration Presenters  
**System:** DepthWizard — Single-View Height Estimation and 3D Flythrough  
**Version:** `v0.1.0-sih-26175-rc1` (Immutable tag pointer)  
**Canonical Commit SHA:** `24cce9825e66d789fe981063090c09a1c717c4e3` (`24cce98`)  
**Lead Architecture & Release Owner:** Shivam Shelatkar  

---

## 1. Installation & Environment Verification

### Standalone Package & Managed Runtime Architecture
- **Installer Package:** `DepthWizard Setup 1.0.0.exe`
- **File Size:** `115,579,824 bytes` (115.57 MB)
- **Target OS:** Windows 10 / Windows 11 (x64)
- **Authenticode Signature:** Valid (`CN=DepthWizard Release Candidate, O=ISRO DepthWizard Team`, DigiCert RFC 3161 SHA256 Timestamp Responder 2026)
- **Installer SHA-256:** `2A974B514694D79C0B7E72D6F17EE33B2B07A532CDD33207F9D34FFB3452D717`
- **Runtime Strategy:** Electron 35 desktop host + Managed Python 3.11+ virtual environment (`provision_runtime.py`).
- **Checkpoint Policy:** External managed provision (`DW_DAV2_CKPT` / `%APPDATA%\DepthWizard\checkpoints\depth_anything_v2_vits.pth`), SHA-256 verified.

### Step-by-Step Installation Walkthrough
1. **Launch Installer:** Double-click `DepthWizard Setup 1.0.0.exe` on a Windows machine.
2. **Installation Directory:** Installs to `%LOCALAPPDATA%\Programs\depthwizard`.
3. **Managed Environment Verification:**
   - Managed Python virtual environment provisioned via `provision_runtime.py`.
   - Verified local model weights (`depth_anything_v2_vits.pth`).
   - Electron + React + Three.js presentation engine.
4. **Launch Application:** Double-click desktop shortcut `DepthWizard`. Loads with clean status indicators: `Backend: Online (Local IPC)`, `GPU/CPU Model: Ready`, `CRS Engine: Ready`.

---

## 2. Real Single-Image Workflow: Path A vs Path B

DepthWizard enforces strict scientific boundaries between uncalibrated relative height maps (`rDSM`) and georeferenced metric digital surface models (`DSM`).

```
                              [ Single Optical / Satellite Input ]
                                               │
                       ┌───────────────────────┴───────────────────────┐
                       ▼                                               ▼
           [ Path A: Standard Image ]                       [ Path B: GeoTIFF Image ]
             (PNG, JPG, BMP, WEBP)                             (EPSG CRS + Transform)
                       │                                               │
                       ▼                                               ▼
            DA-V2 Small ML Inference                         DA-V2 Small ML Inference
                       │                                               │
                       ▼                                               ▼
             Relative Depth (rDSM)                           Relative Depth (rDSM)
              (metric=false, units=None)                     (preserves CRS & Transform)
                       │                                               │
                       ▼                                               ▼
             Display-Only 3D Mesh                             Reference DEM / GCP Fit
                       │                                               │
                       ▼                                               ▼
             Relative Height Profile                          Calibrated Metric DSM (m)
                                                                       │
                                                                       ▼
                                                             Metric Mesh & 3D Flythrough
```

### Demonstration — Path A: Standard Optical Imagery (PNG / JPG / BMP)
1. **Load Sample Image:** Click **Ingest Image** $\rightarrow$ select `sample_test_data/sample_terrain.jpg` or any standard drone/aerial PNG photo.
2. **Inference Execution:** Backend runs local inference using DA-V2 Small.
3. **Scientific Output:**
   - Output Type: **`rDSM` (Relative Digital Surface Model)**.
   - Scientific Flags: `metric=false`, `units=None`.
   - UI Display: Displays relative height range normalized to $[0.0, 1.0]$ or relative percentage $[0\%, 100\%]$.
   - Boundary Enforcement: UI explicitly displays **"Relative Geometry Only — Metres & Coordinates Disabled (Calibration Required)"**.

### Demonstration — Path B: Single-View Satellite Imagery (GeoTIFF)
1. **Load GeoTIFF Image:** Click **Ingest Image** $\rightarrow$ select `sample_test_data/sample_geotiff.tif`.
2. **Spatial Metadata Extraction:**
   - Preserves Coordinate Reference System (e.g., `EPSG:32643` - WGS 84 / UTM Zone 43N).
   - Preserves 6-parameter GeoTransform affine matrix $[x_{0}, dx, rx, y_{0}, ry, dy]$.
   - Preserves pixel resolution and spatial bounding box.
3. **Inference Execution:** Backend runs local inference on normalized satellite band rasters.
4. **Initial State:** Produces spatial `rDSM` preserving CRS and transform metadata.

---

## 3. Calibration Engine: Reference DEM & GCP Alignment

To convert relative `rDSM` into absolute metric `DSM` ($m$), DepthWizard applies linear regression against reference elevation data.

### Option 3A: Reference DEM 30m Calibration (Automatic / Semi-Automatic)
1. **Trigger Calibration:** Open **Calibration Panel** $\rightarrow$ select **Reference DEM Calibration (COP-DEM 30m / SRTM)**.
2. **Overlap Resampling:** Backend samples overlapping elevation points between relative `rDSM` grid $H_{\text{rel}}$ and reference DEM grid $H_{\text{dem}}$.
3. **OLS Regression Fit:** Solves linear scale ($s$) and translation shift ($t$):
   $$H_{\text{metric}}(x, y) = s \cdot H_{\text{rel}}(x, y) + t$$
4. **Validation Metrics Output:**
   - Scale factor $s$ (e.g., $s = 42.15$)
   - Offset shift $t$ (e.g., $t = 210.40\text{ m}$)
   - Calibration Residual RMSE (e.g., $\text{RMSE} = 1.42\text{ m}$)
5. **Output Product:** Generates calibrated metric **`DSM`** in GeoTIFF format with metadata tag `metric=true`, `units=metres`.

### Option 3B: Ground Control Point (GCP) Calibration (Interactive Manual)
1. **Add GCPs:** Click 3 or more prominent ground features in the image.
2. **Compute Fit:** Click **Apply GCP Calibration**.
3. **Residual Verification:** Displays per-GCP residual errors ($\Delta z_i$).

---

## 4. 3D Mesh Generation & Texture Mapping

DepthWizard converts height rasters into real-time renderable 3D triangular surface meshes.

1. **Mesh Construction (`TerrainMesh.build()`):**
   - Converts `rDSM` or `DSM` 2D grid into 3D vertex positions $(X, Y, Z)$.
   - Dynamic Level of Detail (LOD) decimation optimizes polycount for WebGL rendering.
   - Nodata values are masked to prevent geometric spikes or infinite depth tears.
2. **Ortho-Texture Mapping:**
   - Original RGB image is projected onto the 3D surface mesh using normalized UV coordinate mapping ($u = x / W, v = y / H$).
   - Bilinear texture sampling ensures crisp terrain and building façade rendering during close-up camera passes.
3. **Height Exaggeration Display:**
   - Interactive height exaggeration slider ($0.5\times$ to $5.0\times$) enables visual accentuation of subtle terrain relief.
   - **Scientific Boundary Notice:** UI clearly states **"Height Exaggeration is Display-Only — Scientific Measurements Remain Unaltered"**.

---

## 5. Spatial Analysis Suite

DepthWizard provides interactive GIS analysis tools directly within the 3D viewport.

### 1. Point Elevation Query
- **Action:** Click anywhere on the 3D terrain surface.
- **Output:** Inspector HUD with Relative Height ($H_{\text{rel}}$) or Absolute Elevation ($Z_{\text{metric}}$ in metres) + Spatial Coordinates.

### 2. 2D Elevation Profile Tool
- **Action:** Draw cross-section line from point $A$ to point $B$ across building or ridge.
- **Output:** Interactive 2D graph displaying Distance ($m$) vs Height ($m$), calculating max slope ($^\circ$), min elevation, and peak height.

### 3. Object & Building Height Measurement
- **Action:** Click building base $P_1$, then click building roof $P_2$.
- **Output:** Calculates exact height difference: $\Delta h = |Z_{P2} - Z_{P1}|$.

### 4. 3D Volumetric Analysis
- **Action:** Draw bounding polygon around a hill, heap, or excavation zone.
- **Output:** Numerical integration of volume above reference baseline ($V = \iint (Z(x,y) - Z_{\text{base}}) \, dx\,dy$).

---

## 6. Interactive 3D Flythrough & Camera Navigation

The Three.js rendering engine provides camera controls tailored for single-image 3D visualization.

1. **Navigation Controls:**
   - **Orbit Mode:** Left-click + drag to rotate $360^\circ$.
   - **Pan Mode:** Right-click + drag to translate across terrain.
   - **Flythrough Mode:** Press `WASD` / Arrow keys for first-person aerial flight simulation.
2. **Automated Camera Flight Paths:**
   - **Add Waypoints:** Click **Record Waypoint** at key visual angles.
   - **Play Flythrough:** Click **Play Flight Animation**. Camera interpolates along Catmull-Rom spline trajectory.
   - **Speed Multiplier:** Adjust flight velocity ($0.5\times$ to $3.0\times$).
3. **Return-to-Home:** One-click reset restores top-down north-oriented nadir view.

---

## 7. Robust Failure Handling & Edge Case Protection

DepthWizard gracefully handles corrupt, missing, or malformed inputs without application crashes.

| Scenario / Edge Case | System Reaction & User Guidance |
| :--- | :--- |
| **Invalid File Format** (`.txt`, `.exe`, corrupted image) | UI presents error modal: *"Unsupported input file format. Please provide valid PNG, JPG, or GeoTIFF imagery."* Rejects ingestion safely. |
| **Corrupt / Missing GeoTIFF Tags** | System detects missing CRS/GeoTransform. Displays warning: *"Spatial tags unreadable. Falling back to Path A Relative Mode (rDSM)."* |
| **Singular / Collinear GCP Selection** | Calibration engine catches rank-deficient OLS matrix ($A^T A$). Displays alert: *"GCPs are collinear or insufficient. Minimum 3 non-collinear points required."* |
| **Extreme Nodata / Cloud Cover** | Nodata regions are transparently masked in mesh generation; slope and volume queries ignore nodata pixels without NaN propagation. |
| **Model Memory OOM / Large Image** | Sliding window strategy handles large satellite scenes without exceeding system RAM. |

---

## 8. Offline & Air-Gapped Operation Verification

DepthWizard is engineered for zero-connectivity ISRO operational environments.

1. **Air-Gapped Test:** Disconnect network adapter (disable Wi-Fi and Ethernet).
2. **Full Pipeline Execution:**
   - Image Ingestion $\rightarrow$ PASS
   - Local DA-V2 Model Inference $\rightarrow$ PASS
   - DEM/GCP Calibration $\rightarrow$ PASS
   - 3D Mesh Generation & UV Texturing $\rightarrow$ PASS
   - Flythrough & Volumetric Queries $\rightarrow$ PASS
3. **Zero Telemetry Guarantee:** 0 outbound HTTP/HTTPS connections attempted. All weights, scripts, and DEM fallback grids are loaded exclusively from local disk.

---

## 9. Summary for SIH Evaluators

DepthWizard satisfies implemented core requirements of **ISRO Problem Statement 26175**:
- **Single-View Height Estimation:** Structural relative depth extraction via DA-V2 Small.
- **Geospatial Calibration:** DEM/GCP linear regression translating relative maps to metric GeoTIFF DSMs.
- **Interactive 3D Flythrough:** WebGL mesh visualization and automated camera trajectory simulation.
- **Deployment & Compliance:** Authenticode-signed installer (`115,579,824 bytes`), managed Python venv strategy, air-gapped operation. Generalization beyond tested evidence is not claimed.
