# DepthWizard — Pipeline Orchestration (Shivam S14)

In-process composition of the validated scientific subsystems. The
layer owns sequencing, state, cancellation, failure propagation and
run metadata — never scientific algorithms.

## Path

```text
Input
  ↓  inspect_input()
Inspect
  ↓  Preprocessor (identity default: explicitly no transformation)
DepthBackend  (any implementation behind the stable contract)
  ↓  CalibrationProvider (injected reference acquisition)
CalibrationResult + target-semantics consistency check
  ↓  create_scientific_height_product()
ScientificHeightProduct
  ↓  rasterize_height_product()
DSMGrid
  ├──→ build_terrain_mesh()      (only if requested)
  └──→ export_geotiff()          (only if a target path is given)
  ↓
Completed
```

`PipelineRunner.run(request) -> PipelineResult` is the whole public
API. Runners are single-use; each run gets a fresh engine context.

## States

The foundation `PipelineState` enum is reused unchanged (no second
enum, no new members): `INPUT_VALIDATED → PREPROCESSING →
INFERENCE_RUNNING → CALIBRATING → DSM_GENERATION → [MESH_GENERATION]
→ [EXPORTING] → COMPLETED`, with `FAILED`/`CANCELLED` reachable from
any active state and no outgoing edges from terminal states. An
explicit transition table (`TRANSITIONS` + `check_transition`)
rejects illegal moves (`FAILED→COMPLETED`, `CANCELLED→COMPLETED`,
skipped dependencies) with `PipelineExecutionError`.

Height-semantics construction runs inside `CALIBRATING` (reference
mapping plus semantic product are one calibration phase); DSM work
starts only with a valid product in hand. `MESH_GENERATION` and
`EXPORTING` are entered only when requested and only while executing
— never claimed without work. State history is deterministic data
(no timestamps); runs open with `INPUT_VALIDATED`, or with `FAILED`
/`CANCELLED` when inspection never succeeded or cancellation came
first.

## Injected boundaries

- **Preprocessing**: `Preprocessor` protocol with a default
  `IdentityPreprocessor` (name `"identity"`) that returns the
  inspection untouched — honest no-op, no resize/normalize/crop
  claims. Real stages plug in later without touching the machine.
- **Calibration**: `CalibrationProvider.calibrate(depth_result)`
  returns a validated `CalibrationResult`. The runner checks
  finiteness, metric target, metre units, request/provider target
  agreement (never silently overridden) and source-checksum
  consistency — without refitting anything. Reference acquisition
  itself (DEM/GCP/benchmark) lives outside orchestration, which is
  why DEM/GCP work remains separate milestones.

## Failures and cancellation

Each stage captures its exception into `PipelineFailure(stage,
error_category, message)`, transitions to `FAILED`, stops, and keeps
every earlier artifact — domain categories (`InvalidInputError`,
`UnsupportedFormatError`, `ModelInferenceError`,
`CalibrationError`, `MeshGenerationError`, `ExportError`) survive
verbatim. `PipelineExecutionError` (new, `pipeline_execution_failure`)
covers runner misuse (reuse) and illegal transitions only — stage
failures stay data, never this type.

`CancellationToken` is cooperative and synchronous: providers or
callbacks call `cancel()`; the runner observes it before/after every
stage (and before optional mesh/export). Cancelled runs keep
completed artifacts, execute nothing further, and never report
`COMPLETED`.

## Reproducibility

Results carry scalar run metadata (input path/checksum, backend
name/version, calibration method/reference/params, target
semantics, mesh/export requests, engine version) plus the artifact
objects themselves. No timestamps-for-appearance, no random IDs, no
machine paths in scientific metadata, no benchmark claims. Same
inputs and providers ⇒ same histories, artifacts and semantically
equivalent exports (byte identity of TIFFs is not promised).

## Geospatial and semantic honesty

The orchestrator performs no geospatial or scientific math: PNGs
stay non-georeferenced, GeoTIFF CRS/transforms flow through
untouched, calibration never creates CRS, and the relative →
calibrated → metric-meaning chain is preserved end to end (never
"model output = metres"). It writes no files except through the
GeoTIFF exporter and creates no run directories, caches or logs.

## Extension and integration

`Calibrator`-style robust methods, real preprocessors, DEM/GCP
providers and future model adapters all plug into the existing
protocols without orchestration changes. The future service layer
calls `run()`; the future artifact adapter consumes
`PipelineResult` artifacts (`PipelineResult → artifacts → adapter →
SceneArtifact`) while the pipeline stays unaware of React, Three.js
and desktop packaging.
