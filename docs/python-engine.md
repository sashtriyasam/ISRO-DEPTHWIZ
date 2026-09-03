# DepthWizard — Python Scientific Engine Foundation (Shivam)

Foundation-only. No inference, no DEM download, no GCP fitting, no
calibration math, no DSM raster generation, no meshing, no services.

## Purpose

`src/depthwizard/` is the stable backend contract layer everything else
builds on: ingestion, depth inference, calibration, DSM, mesh and
orchestration. Frontend code is untouched and never imported.

## Layout

```text
src/depthwizard/
├── __init__.py            # package marker, re-exports __version__
├── version.py             # single source of truth (0.1.0)
├── errors.py              # backend error taxonomy (codes for UI/API use)
└── contracts/
    ├── semantics.py       # GeoreferencingLevel / DepthScale / ElevationSemantics
    ├── spatial.py         # SpatialKind + SpatialDetails (no CRS math)
    ├── provenance.py      # ProductProvenance (unknown stays None)
    ├── artifacts.py       # ImageResolution / DepthResult / DepthBackend
    └── pipeline.py        # PipelineState (states only, no engine)
```

Packaging: `pyproject.toml` (setuptools, `src/` layout,
`requires-python = ">=3.11"`). Runtime dependency: `pydantic>=2.0,<3`
only — justified as the contract-boundary validator (invalid
`DepthResult` construction fails loudly instead of leaking bad science
downstream). Dev: `pytest`, `mypy` (strict), `ruff`.

## Scientific semantics

- `NON_GEOREFERENCED` — plain PNG/JPG. No CRS, no metres. Ever.
- `GEOREFERENCED_NO_ELEVATION_REFERENCE` — positioned, but no trustworthy
  elevation reference. Must not be sold as absolute terrain elevation.
- `GEOREFERENCED_WITH_DEM` / `GEOREFERENCED_WITH_GCP` — elevation claims
  allowed only with provenance naming the DEM/GCP reference.
- `DepthScale.RELATIVE` vs `METRIC` enforced by validators:
  `METRIC` requires `units="meters"`; `RELATIVE` rejects it.
- `SpatialKind` makes "present / unavailable / not applicable" explicit;
  `PRESENT` requires at least one of CRS/transform/bounds.

## Backend ↔ frontend boundary

Scientific engine owns: elevation values, AGL/rDSM/DSM semantics,
geospatial coordinates, CRS, transforms, scientific metadata.
Desktop app owns: display transforms, camera, interaction, rendering,
UI state. Height exaggeration is a presentation transform only
(`DEFAULT_DISPLAY_TRANSFORM` in `src/types/scene.ts`) and must never
mutate scientific elevation.

Conceptual mapping to Aryan's `SceneArtifact`:

| Backend (this package)             | Frontend `SceneArtifact`            |
| ---------------------------------- | ----------------------------------- |
| `DepthResult` + future DSM product | `elevation.grid/width/height`       |
| `SpatialDetails` (CRS/transform)   | `metadata.CRS/transform/bounds`     |
| `ProductProvenance`                | `metadata.source/description`       |
| future mesh product                | `mesh.vertices/indices/normals/uvs` |

The Python engine never imports TypeScript/Three.js/React and the
frontend never imports Python. Exchange happens via serialized
artifacts in later integration tasks.

## Why models stay behind `DepthBackend`

`DepthBackend` is a `Protocol`: any model (Depth Anything V2/V3,
Sat3DGen-derived, future ISRO-specific) implements `estimate_depth`
returning the same `DepthResult`. Model names, checkpoints and
preprocessing live in data fields, never in the type system, so
swapping backends cannot silently change unit or CRS semantics.

## Future subsystem ownership (not implemented)

ingestion → depth backend → relative geometry → calibration →
height product → DSM → mesh → desktop viewer. Each gets its own
module/package in a later task, conforming to these contracts.
