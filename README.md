# DepthWizard — ISRO DEPTH WIZARD (SIH 26175)

**Single-View Height Estimation and 3D Flythrough**

## Overview

DepthWizard is a scientific desktop application for single-view height estimation from monocular images using Depth Anything V2, with geospatial calibration, DSM generation, terrain mesh export, and interactive 3D flythrough.

**SIH Problem Statement:** 26175

## Quick Start

```bash
# Install dependencies
npm install

# Development (React + Vite)
npm run dev

# Production build (React + Electron)
npm run build:electron

# Windows installer (NSIS)
npm run electron:build:win

# Portable build
npm run electron:build:portable
```

## Python Scientific Engine

The canonical Python engine lives in `src/depthwizard/` — contracts, ingestion, depth backends, calibration, height semantics, DSM/mesh raster engines, GeoTIFF export, geospatial primitives, DEM references, reference controls, pipeline orchestration, local service, and managed runtime provisioning.

```bash
# Python tests
python -m pytest

# Lint & format
python -m ruff check src tests
python -m ruff format --check src tests

# Type checking
python -m mypy src tests
```

## Architecture

```
Electron Native Host (Aryan)
├── Renderer: React 19 + Three.js (Vite)
├── Preload: contextBridge (8 IPC methods)
├── Main: Electron 44.2.0 (sandboxed, CSP)
│   ├── Python resolution: DEPTHWIZARD_PYTHON → PATH
│   ├── Checkpoint resolution: DW_DAV2_CKPT → %APPDATA%/DepthWizard/checkpoints/
│   ├── Service lifecycle: spawn/kill depthwiz_service.py
│   └── IPC: getHostCapabilities, executeService, etc.
└── child_process.spawn()
    ↓
Python Service (depthwiz_service.py)
├── LocalService (wire contract v1)
├── PipelineRunner (full chain + path variants)
├── DepthBackend Protocol
│   ├── synthetic-depth (always available)
│   └── depth-anything-v2-small (conditional)
├── Calibration: ScaleOffsetCalibrator
├── DSM: DSMGrid (metric, calibrated, nodata=NaN)
├── Mesh: TerrainMesh (local + georeferenced coords)
├── Export: GeoTIFF (prepare-only)
└── Contracts: Artifacts, Provenance, Semantics, Spatial
```

## Two Operating Modes

### Mode A: Relative (PNG/JPG)

```
InputInspection (NON_GEOREFERENCED)
    → DepthBackend.estimate_depth()
    → DepthResult(RELATIVE, units=None)
    → RelativeSurfaceGrid → RelativeTerrainMesh (frame=LOCAL)
    → Desktop viewer (display-only height exaggeration)
```

### Mode B: Metric (GeoTIFF + Calibration)

```
InputInspection (GEOREFERENCED with CRS + transform)
    → DepthBackend.estimate_depth() (still RELATIVE)
    → DEM reference → CalibrationSamples (GCP/DEM, meters)
    → ScaleOffsetCalibrator → CalibrationResult
    → ScientificHeightProduct (AGL / ABSOLUTE_ELEVATION_DSM, meters)
    → DSMGrid → TerrainMesh (CRS preserved) → GeoTIFF export
```

## Runtime Provisioning (S18)

```bash
# Core (non-ML)
python scripts/provision_runtime.py --runtime-dir <dir> --mode core

# Full DA-V2 (requires network for pip/git/fetch)
python scripts/provision_runtime.py --runtime-dir <dir> --mode dav2 \
    --checkpoint-src <verified-file>  # or --fetch-checkpoint
```

Output: JSON status (`ready`, `core_ready`, `dav2_ready`, `service_launch_ready`, `offline_ready`)

## Runtime Check (S17)

```bash
python scripts/runtime_check.py [--checkpoint PATH] [--device NAME] [--require-dav2] [--pretty]
```

Checks: interpreter version, core/DA-V2 deps, upstream revision, checkpoint SHA256, service importability.

## Model Provenance

| Element           | Value                                                              |
| ----------------- | ------------------------------------------------------------------ |
| Model             | Depth Anything V2 Small                                            |
| Upstream Repo     | `DepthAnything/Depth-Anything-V2`                                  |
| Upstream Revision | `a561b849ebae10a6f5ef49e26c83cbbcd36c71bf` (pinned)                |
| Checkpoint        | `depth_anything_v2_vits.pth`                                       |
| Checkpoint SHA256 | `715fade13be8f229f8a70cc02066f656f2423a59effd0579197bbf57860e1378` |
| Output Semantics  | RELATIVE (`units=None`, `DepthScale.RELATIVE`)                     |
| License           | Apache-2.0                                                         |

**Checkpoint is external** — never committed, SHA-verified, placed in `%APPDATA%/DepthWizard/checkpoints/`.

## Scientific Boundaries

- **Relative depth ≠ metric DSM** — metric requires explicit calibration
- **PNG/JPG: relative only** — never invent CRS, coordinates, metres
- **GeoTIFF: CRS/transform preserved** — metric only when justified
- **DEM ≠ DSM ≠ AGL** — distinct semantics enforced
- **Height exaggeration = display-only** — never alters scientific data
- **Integration adapter transparent** — no recalibration, resampling, reprojection

## Documentation

- `docs/final-release-status.md` — Complete release audit
- `docs/final-release-gate.md` — 17-gate release matrix
- `docs/native-host.md` — Electron architecture
- `docs/installer-strategy.md` — NSIS packaging
- `docs/runtime-provisioning.md` — Managed runtime contract
- `docs/native-runtime-packaging.md` — Runtime packaging contract
- `docs/release-blockers.md` — P0/P1/P2/INFO classification
- `docs/native-release-acceptance.md` — 33 automated PASS, 13 requires hardware

## Project Control

- **North Star:** SIH Problem Statement 26175
- **Team:** Shivam (architecture/Python/release), Shravan (ML), Aryan (desktop/UX)
- **GitHub Project:** DepthWizard — SIH 26175
- **AGENTS.md** — Ownership, workflow, scientific rules

## Release Status

**Current:** RELEASE CANDIDATE — PHYSICAL WITNESS REQUIRED

All automated gates PASS. Requires:

1. Physical Windows acceptance (clean VM + display + checkpoint)
2. Shravan final ML candidate frozen with evidence
3. Code signing for production

See `docs/final-release-status.md` and `docs/final-release-gate.md` for full audit.
