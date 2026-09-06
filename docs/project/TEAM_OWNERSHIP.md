# DepthWizard — Team Ownership (LOCKED)

SIH 26175 north star. Three workstreams, one shared control plane
(GitHub Project **DepthWizard — SIH 26175**). Ownership is assigned by
this model, never by convenience.

## Shivam — Core / Geospatial / Calibration / DSM / Integration / Release

- Lead architecture (`docs/sih-architecture.md` contract authority)
- Python core software (`src/depthwizard/`)
- Geospatial processing: CRS / transform / spatial validation
- Input ingestion and semantic validation (Path A vs Path B routing)
- DEM / reference integration, GCP support
- Calibration engine (relative → metric mapping, quality checks)
- DSM / rDSM semantics, height semantics, nodata/validity semantics
- Raster alignment, reprojection, reference raster handling
- GeoTIFF export, mesh engine (renderer-independent)
- Pipeline orchestration (`PipelineRunner`, `run_relative_path`)
- Service / integration architecture (transport, local service)
- Benchmark methodology, significance design, reference controls
- Release integration, scientific acceptance, **final merge authority**

Primary tracks: `core`, `geospatial`, `calibration`, `dsm`,
`integration`, `qa`, `release`.

## Shravan — ML / Data / Model / Research / Benchmark

- ML depth model backends behind `DepthBackend`
- Depth Anything V2 integration, inference runtime, provenance
- Dataset engineering (GAMUS manifests, preparation scripts)
- Remote-sensing adaptation, model experiments
- Benchmarks, optimization, model selection
- Scientific evidence (evaluation protocol, significance)
- Deterministic behavior, model loading, checkpoint provenance

Constraint: ML output is **relative geometry only**
(`metric=false`, `units=None`). Metric meaning is assigned
downstream by calibration, never inside the model adapter.

Primary tracks: `ml`, `qa`. Work tagged `type:research` /
`type:experiment` stays on the research side until promoted through
the product path (see `RESEARCH_VS_PRODUCT.md`).

## Aryan — Desktop / 3D / UX / Packaging

- Desktop application (React/TypeScript, `src/`)
- Three.js rendering, terrain visualization, rendering modes
- Camera system (orbit / first-person / aerial), flythrough waypoints
- Project/input workflow, session lifecycle, artifact handling
- Scene creation from `SceneArtifact`, RGB texture projection in viewer
- Height inspection, slope analysis, distance/measurement tools,
  elevation profiles, point inspector, layers
- Visualization UX, scientific metadata display
- Native host boundary, installer, standalone acceptance,
  fresh-machine validation

Primary tracks: `3d`, `desktop`.

## Release Control & Governance (Single-Owner Handoff)

All remaining execution, integration, verification, physical witness, code signing, and release authorization activities are centralized explicitly under **Shivam**. Historical contributions of teammates (Shravan, Aryan) are acknowledged, but no future tasks will be assigned to external owners.

## Rules

1. Cross workstream boundaries only through the canonical contracts.
2. No silent semantic changes in the adapter (no recalibration,
   resampling, reprojection, remeshing, unit changes).
3. No automatic merging of a teammate's branch; review before merge.
4. Final merge authority and release authority: Shivam.
5. All remaining release tasks carry `Owner: Shivam`.

