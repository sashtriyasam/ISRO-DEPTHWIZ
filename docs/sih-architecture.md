# DepthWizard SIH 26175 — Canonical System Architecture

DepthWizard is a standalone end-to-end software system converting
single-view optical remote-sensing imagery into relative or metric
elevation products and an interactive 3D flythrough — not a model
implementation, benchmark, library, or viewer alone.

## End-to-end flow

```text
SINGLE-VIEW OPTICAL RGB
        ↓
InputInspection (CRS/transform validated or declared absent)
        ↓
┌───────┴────────┐
│                │
NON-GEOREFERENCED          GEOREFERENCED
PNG / JPG                  GeoTIFF
│                          │
▼                          ▼
ML relative geometry       ML relative geometry
│                          │
▼                          ▼
rDSM path                  DEM / GCP / reference acquisition
│                          │
│                          ▼
│                   explicit calibration
│                          │
│                          ▼
│                   METRIC HEIGHT
│                          │
└────────┬─────────────────┘
         ▼
  FINAL DSM PRODUCT (metric) / rDSM (relative)
         ▼
  TERRAIN / SURFACE MESH (+ source RGB UVs)
         ▼
  INTERACTIVE 3D VIEWER
         ▼
  STANDALONE DESKTOP SOFTWARE
```

## Ownership boundary

```text
Shravan / ML            RGB → relative geometric representation
                        (metric=false, units=None; validity +
                        optional confidence; model provenance)
Shivam / Geospatial     CRS, transform, bounds, GSD, grids, nodata,
+ Calibration           DEM/GCP ingestion, controls, relative→metric
                        mapping, height/DSM semantics, export,
                        provenance, evaluation methodology
Aryan / Desktop         transport consumption, rendering, interaction,
+ Visualization         native host, installer, standalone acceptance
+ Packaging
```

## ML contract (frozen shape, M14 informs fields only)

`DepthBackend.estimate_depth(inspection) → DepthResult`: relative
values, validity, optional confidence, preprocessing record, model
identity, spatial passthrough, provenance. This already matches the
M14-proposed ML output contract; no rewrite needed. Undecided pending
M14: precise external target semantics (DSM vs nDSM/AGL vs DTM per
dataset) — carried as explicit `ElevationSemantics`, never inferred.

## Product boundaries

- **Relative** (`DepthResult` → `RelativeSurfaceGrid` → relative mesh,
  `LOCAL` frame, units absent): for non-georeferenced input and for
  every pre-calibration stage. Never metres, never CRS-invented.
- **Metric** (`CalibrationResult` → `ScientificHeightProduct` →
  `DSMGrid` → `TerrainMesh`, metres, preserved CRS/transform):
  exists only after explicit calibration against validated DEM/GCP/
  reference controls. Source linkage is checksum-enforced.

## Mode paths

- **Mode A (PNG/JPG → rDSM → mesh → viewer):** `run_relative_path`
  (inspect → infer → rasterize → triangulate). No calibration, no
  metric claims; mesh UVs + source identity flow for RGB texture
  projection (viewer texturing: Aryan track).
- **Mode B (GeoTIFF → metric DSM → mesh → viewer):**
  `PipelineRunner` with DEM/GCP-derived `CalibrationProvider`
  (`controls.build_reference_control` + `build_calibration_samples`);
  CRS/transform preserved end to end.

## Desktop contract

Python artifacts → `depthwizard.integration` transport (metric-only
terrain validation; relative depth validated separately) →
`SceneArtifact` (elevation grid + mesh + metadata/provenance) →
Three.js viewer → native host (pending) → installer (pending).

## Evidence status

S19/S19.1/S20/S21 (GAMUS, frozen DA-V2 Small): 32-tile pooled MAE
4.40 m / RMSE 5.86 m / R² 0.23; DC−PHL MAE gap 3.31 [2.36, 4.40].
Pipeline-valid and honestly poor in absolute terms — a research
signal, not SIH validation. Broader urban/sparse/hilly/forested
evidence, GPU behaviour, and packaged acceptance remain open.

## Frozen / research / blocked

- Frozen: depth interface, relative/metric boundary, calibration
  engine shape, geospatial validators, transport contract, eval
  protocol mechanics.
- Under research (Shravan): M14 target-semantics audit, external
  benchmark, DA-V3 decision, adaptation — behind `DepthBackend`,
  no geospatial rewrite required.
- Blocked on evidence: SIH-wide accuracy; packaged native host +
  installer (Aryan); checkpoint distribution channel.
