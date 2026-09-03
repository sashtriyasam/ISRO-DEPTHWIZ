# DepthWizard — DEM Terrain Reference (Shivam S8)

Local, offline terrain-elevation references for future control
logic. A DEM provides ground elevation — never surface elevation,
AGL height, or DSM ground truth — and this package constructs no
calibration objects from it.

## Path

```text
Local DEM
 ↓  inspect_dem() (metadata only, explicit metric units declared)
DEMInspection
 ↓  target_grid_from_inspection() (explicit image-derived grid)
TargetGrid + overlap gate (S7, DemMismatchError on disjoint)
 ↓  build_terrain_reference() (S7 align/reproject, owned output)
TerrainReferenceGrid
 ↓  sample_terrain() / sample_terrain_at_world() (nearest, typed)
future control/reference subsystem (NOT this milestone)
```

## Formats and scope

Local GeoTIFF DEMs only (`.tif/.tiff`, single numeric band). No
SRTM/Copernicus/ALOS downloads, no network, no credentials. HGT is
deliberately deferred not for lack of a driver but for lack of
embedded CRS/transform — deriving georeferencing from filenames
would violate the ingestion honesty policy. GTiff is confirmed in
the installed GDAL driver set.

## Inspection

`inspect_dem(path, *, vertical_units)` validates: real file,
GeoTIFF, single uint/int/float band, CRS present (else
`MissingCRSError`), geotransform present and invertible (identity
fallback or degenerate mappings refused), valid bounds/resolution.
Pixel arrays are not loaded at inspection. Vertical units have no
trustworthy in-file encoding in this stack, so metric use always
requires `vertical_units="meters"` — anything else (including
omission) fails; no feet conversion exists. All-invalid sources
surface at build time, where the mask exists to prove it.

## Vertical meaning and units

`vertical_semantics` is always `TERRAIN_ELEVATION` (new enum member;
calibration targets intentionally exclude it, and the S-foundation
stability test records the addition). It is never
`ABSOLUTE_ELEVATION_DSM` or `HEIGHT_AGL_NDSM`. No vertical datum is
invented — the contract has no datum field, so datum stays
unknown/unavailable. Units are explicit metres or nothing.

## Target grids and overlap

`target_grid_from_inspection` derives CRS/transform/dims/resolution
from a validated georeferenced `InputInspection` (float32/NaN
terrain-float defaults); non-georeferenced or transform-less inputs
fail — PNG/JPEG stay valid DepthWizard input but can never request
DEM alignment, and nothing is invented for them. Builds overlap-gate
through S7 (`DemMismatchError` carries both frames) and record
source vs target resolution separately: a 30 m DEM on a 0.5 m grid
is an interpolated surface, never 0.5 m ground truth.

## Alignment and resampling

S7 `align_raster` (nearest default — conservative; bilinear
available for continuous terrain; caller-chosen, recorded, `None`
only for native fast-path copies). Nodata/mask follow repository
policy (valid 0.0, NaN marker, synchronized mask, no zero-fill);
all-invalid sources fail as `InvalidInputError`, uncovered targets
as `DemMismatchError`. Outputs are freshly owned; sources,
inspections and upstream products are never mutated.

## Sampling

Nearest-neighbour only (bilinear explicitly future): integer cells
with pixel-center semantics; world coordinates via S7 (unrounded)
resolved with documented floor (containing-cell) policy;
out-of-bounds and nodata locations yield explicit invalid
`TerrainSample`s — never clamped, wrapped, or invented. Results
carry elevation-or-None, integer and continuous pixel positions,
world coordinates, units and reference id.

## Provenance

Reused `ProductProvenance` plus explicit source/target fields (DEM
id/checksum, source/target CRS and resolutions, resampling). No
acquisition dates, sensors, datums, accuracy or RMSE inventions.

## Boundaries (enforced by test)

- No `CalibrationResult`/`CalibrationSamples` construction, no
  `ScaleOffsetCalibrator`/`apply_calibration` calls, no
  `create_scientific_height_product` — asserted by scanning the
  package sources for those identifiers.
- No `surface − terrain`, no AGL derivation, no DSM claims.
- No GeoTIFF/mesh writing (fixtures stay in `tmp_path` and are never
  committed); no pipeline changes; no frontend changes.
- Terrain ≠ surface ≠ AGL, always and everywhere in this layer.
