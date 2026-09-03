# DepthWizard — Scientific Reference Controls (Shivam S8.x)

The only sanctioned bridge between DEM terrain references and the
calibration engine. Relative predictions plus explicit surface
controls (plus DEM terrain for AGL) become auditable metric
reference pairs — as `CalibrationSamples`, never as fitted results.

## Path

```text
Relative prediction (DepthResult, untouched)
        +
Explicit surface control (caller-supplied, metres)
        +
Optional DEM terrain control (sampled, metres)
        ↓  build_reference_control() — fail-fast, no fitting
ReferenceControlPoint
        ↓  build_calibration_samples() (order preserved, no fitting)
CalibrationSamples
        ↓  future S9 fitting (not here)
```

## The two valid references

- **Absolute elevation**: `reference = surface_elevation_m`,
  target `ABSOLUTE_ELEVATION_DSM`. The DEM is not required and is
  never substituted; when supplied it is sampled contextually only.
- **AGL / nDSM-style**: `reference = surface_elevation_m −
terrain_elevation_m`, target `HEIGHT_AGL_NDSM`. The DEM supplies
  terrain at the same location; the model prediction is never part
  of the subtraction.

The prohibited shortcut — `relative depth → DEM elevation` — cannot
be expressed: builders have no path that treats terrain as surface,
and a source-scanning test asserts the production package never
references `ScaleOffsetCalibrator`, `apply_calibration`,
`create_scientific_height_product` or `CalibrationResult`.

## Controls and coordinates

`SurfaceElevationControl` carries one authoritative space
(`PIXEL` with integer row/col, or `WORLD` with finite x/y in an
explicit-or-source CRS) plus optional secondary coordinates that
are consistency-checked (documented 1e-6 relative/absolute
tolerance) rather than silently preferred. Predictions come from the
actual `DepthResult` cell — exact, unmodified, still relative;
invalid or non-finite cells fail fast. World placement reuses S7
(`world_to_pixel`, floor containing-cell rule); pixel centers map
through the source transform. Non-georeferenced inputs accept pixel
controls but refuse world controls (`MissingCRSError` — no CRS
invented); cross-CRS controls fail instead of being reprojected.

## Terrain handling

AGL requires a terrain grid (`MissingElevationReferenceError`
otherwise) and a valid sample at the control location
(`DemMismatchError` on nodata/out-of-coverage). Values stay
untouched; negative AGL is preserved, never clamped (it signals
mismatch worth investigating). Source and target resolutions ride
along in grid metadata — interpolated terrain is never presented
as fine ground truth.

## Batches and provenance

`build_calibration_samples` preserves caller order, rejects empty
batches, duplicate ids and mixed targets, and links each point to
its prediction/surface/terrain sources (ids, checksums where
present — never fabricated). Minimum-count enforcement stays in S9
fitting: two-point batches construct fine and fail only at fit time
(tested), keeping layer responsibilities separate.

## Units, semantics, errors

Metres everywhere (surface, terrain, reference); feet and unitless
values rejected at the boundary. Targets restricted to the two
metric height meanings. Structural/location problems use
`InvalidInputError`/`MissingCRSError`/`GeospatialProcessingError`/
`DemMismatchError`; scientific-precondition violations
(non-metric targets, metric-claiming depth, non-finite references)
use `CalibrationError`. Production code constructs no calibration
results and creates no height products.

## Future provider

A later integration step wraps `DepthResult + SurfaceControlSet +
TerrainReferenceGrid → CalibrationSamples → ScaleOffsetCalibrator →
CalibrationResult` as an injectable `CalibrationProvider`. Neither
the S14 pipeline nor the S9 engine changes for that — the seam
already exists.
