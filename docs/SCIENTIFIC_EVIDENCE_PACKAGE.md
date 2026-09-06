# DepthWizard — Scientific Evidence Package (ISRO PS 26175)

**Lead Architecture & Release Authority:** Shivam Shelatkar  
**Repository State:** `main` at commit `24cce9825e66d789fe981063090c09a1c717c4e3` (`24cce98`)  
**Git Tag:** `v0.1.0-sih-26175-rc1` (Immutable tag target)  

---

## 1. Executive Summary & Scientific Principles

This document provides the formal **Scientific Evidence Package** for **DepthWizard — Single-View Height Estimation and 3D Flythrough (ISRO Problem Statement 26175)**.

### Core Scientific Principles
1. **Engineering Validation $\neq$ Scientific Accuracy**: 100% test suite completion, clean TypeScript compilation, and executable packaging prove software engineering correctness, **not** universal metric accuracy across arbitrary global terrain.
2. **Relative Depth $\neq$ Metric DSM**: Non-georeferenced optical RGB inputs (PNG/JPG) produce **Relative Digital Surface Models (`rDSM`)** in local coordinate frames (`units=None`, `is_metric=False`). Metric claims require explicit reference calibration.
3. **No CRS Invention**: Georeferenced inputs (GeoTIFF) strictly preserve spatial Coordinate Reference Systems (CRS) and affine transformation matrices. Spatial metadata is never fabricated.
4. **Honest Limitations**: Baseline performance, research signals, and known physical boundaries are recorded transparently without unverified claims.

---

## 2. Engineering System Validation vs. Scientific Accuracy

| Dimension | Engineering System Validation | Scientific Accuracy Evidence |
| :--- | :--- | :--- |
| **Scope** | Code correctness, IPC wire protocol, IPC serialization, UI rendering, packaging, error handling | Physical surface elevation accuracy ($m$), $R^2$ correlation, RMSE, MAE against LiDAR/DEM ground truth |
| **Status** | **`PASSED 100%`** | **`RESEARCH BASELINE (EVIDENCE RECORDED)`** |
| **Evidence** | - 549 Python pytest tests passed<br>- 627 Vitest UI tests passed<br>- 0 TypeScript compilation errors<br>- 0 Ruff linter issues<br>- 86 Mypy clean source files<br>- Authenticode signed installer (`2A974B51...`, `115,579,824 bytes`) <br>- Clean machine physical witness trial passed | - 32-tile GAMUS pooled evaluation (MAE 4.40m, RMSE 5.86m, $R^2$ 0.23)<br>- Cross-city probe Pearson correlation: 0.37 (6/6 cities)<br>- Formal external test-city scoring: **`PENDING`** |
| **Claim** | DepthWizard is a stable, offline-capable desktop application host executing deterministic scientific pipelines without synthetic fallback. | Monocular estimation provides relative structural geometry. Metric elevation claims strictly depend on DEM/GCP calibration quality. |

---

## 3. GAMUS Benchmark Evaluation (Research Baseline)

Evaluation harness (`src/depthwizard/evaluation/`) evaluated the shipped monocular depth backbone on 32 pooled satellite/aerial terrain tiles with reference DEM ground truth:

| Metric | Measured Value | Interpretation |
| :--- | :--- | :--- |
| **Mean Absolute Error (MAE)** | **$4.40\,\text{m}$** | Mean absolute vertical deviation across pooled terrain tiles |
| **Root Mean Square Error (RMSE)** | **$5.86\,\text{m}$** | Standard deviation of vertical residuals, highlighting outlier errors |
| **Coefficient of Determination ($R^2$)** | **$0.23$** | Linear correlation between relative predicted depth and true height |
| **Evaluated Sample Size** | **32 Tiles** | Pooled urban, hilly, and sparse vegetative sub-regions |

> **Scientific Assessment:** The GAMUS baseline demonstrates structural relative depth extraction. In absolute terms, an $R^2$ of 0.23 represents an initial research signal, **not** universal SIH-wide validation across all Indian terrain types.

---

## 4. Cross-City Robustness & M17 Research Probe

The ML research track conducted cross-city structural adaptation probes across 6 urban landscapes (GeoNRW probe):

| Model Candidate | Probe Pearson Correlation (6/6 Cities) | Scientific Finding |
| :--- | :--- | :--- |
| **M10 Baseline** | $0.25$ | Historical ML milestone |
| **M17 Structural Head** | **$0.37$** | **Observed cross-city probe improvement; not a generalization proof.** Frozen research candidate (`best.pt`, SHA-256 `D7C0BE91...`). |
| **Formal External Test Cities** | **`PENDING / BLOCKED`** | Awaiting formal labeled dataset access |

> **Governance Policy:** M17 remains frozen in the research track per `docs/project/RESEARCH_VS_PRODUCT.md`. It is not promoted to the shipped product backend without formal external test-city scoring and product integration tests.

---

## 5. Calibration Methodology & Height Products

To convert scale-ambiguous relative depth $z_{\text{rel}}$ into metric height $z_{\text{metric}}$ in metres ($m$), DepthWizard employs the `ScaleOffsetCalibrator` engine ([`src/depthwizard/calibration/calibrator.py`](file:///d:/SIH%20DEPH%20WIZARD/src/depthwizard/calibration/calibrator.py)):

### Mathematical Model
$$z_{\text{metric}}(x, y) = s \cdot z_{\text{rel}}(x, y) + o$$

Where:
- $s$: Dimensional scale factor ($\text{metres} / \text{depth\_unit}$)
- $o$: Vertical datum offset ($\text{metres}$)

### Parameter Fitting
Optimal parameters $(s^*, o^*)$ are estimated via Ordinary Least Squares (OLS) minimization over $N \ge 3$ valid reference control points $(z_{\text{ref}, i}, z_{\text{rel}, i})$:

$$\min_{s, o} \sum_{i=1}^N \left( z_{\text{ref}, i} - (s \cdot z_{\text{rel}, i} + o) \right)^2$$

### Validity Constraints
- **Uncalibrated Output (Path A)**: `RelativeSurfaceGrid` ($z \in [0, 1]$, `units=None`, `LOCAL` frame). Zero fabricated CRS or metric units.
- **Calibrated Product (Path B)**: `ScientificHeightProduct` ($z \in \mathbb{R}$, `units='m'`). Preserves original GeoTIFF CRS (e.g., `EPSG:32643`) and $6 \times 1$ affine transformation matrix.

---

## 6. Reproducibility & Provenance Engine

DepthWizard guarantees 100% deterministic reproducibility across execution environments.

### Pinned Model & System Provenance
- **Shipped Product Backend**: `DepthAnythingV2Backend` (`depth-anything-v2-small`)
- **Upstream Repository**: `DepthAnything/Depth-Anything-V2`
- **Pinned Upstream Revision**: `a561b849ebae10a6f5ef49e26c83cbbcd36c71bf` (Git HEAD)
- **Shipped Checkpoint SHA-256**: `715FADE13BE8F229F8A70CC02066F656F2423A59EFFD0579197BBF57860E1378`
- **M17 Checkpoint SHA-256**: `D7C0BE9127FAFAC5F4C2D207E3626D335AF148A8CBB7489A10EE8C7F7DA4EDAC`
- **Signed Installer SHA-256**: `2A974B514694D79C0B7E72D6F17EE33B2B07A532CDD33207F9D34FFB3452D717` (`115,579,824 bytes`)

---

## 7. Known Scientific & Physical Limitations

1. **Monocular Scale Ambiguity**: Single RGB images contain inherent scale-depth ambiguity. Path A outputs are strictly relative until calibrated against reference DEMs or Ground Control Points.
2. **Dense Vegetative Canopy**: Monocular optical depth measures top-of-canopy reflective surface (Digital Surface Model), not ground elevation (Digital Elevation Model).
3. **Solar Angle & Shadow Extraction**: Solar-shadow height extraction was investigated but explicitly excluded from shipped RC1 product scope (`docs/ps-solar-shadow-gap.md`).
4. **Display Exaggeration Isolation**: UI height exaggeration ($\times 0.1 \dots \times 5.0$) is strictly display-only in the Three.js vertex shader and never mutates underlying scientific elevation rasters.
