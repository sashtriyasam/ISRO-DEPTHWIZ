# DepthWizard — Geospatial Processing Foundation (Shivam S7)

Reusable raster-coordinate mathematics for future DEM/reference
work. No DEM acquisition, no GCP extraction, no science — primitives.

## Path

```text
Image / Raster
      ↓  CRS + transform validation
Spatial Validation
      ↓  overlap / grid compatibility
Reprojection / Alignment (explicit target grids)
      ↓  Aligned Reference Raster
future DEM/reference subsystem (S8)
```

## Backing libraries

rasterio 1.5.1 + GDAL 3.12.4 (already direct runtime dependencies)
provide CRS parsing/comparison, affine math, bounds helpers and the
warp engine; NumPy provides array ops. No pyproj (rasterio/GDAL
covers CRS fully — verified absent from the environment), no Shapely
(rectangular overlap needs only interval math), no GDAL-direct calls,
no vendored code. Upstream API verified: `rasterio.warp.reproject`
(ndarray signature, nodata, resampling flags),
`transform_bounds` (densified edges), `calculate_default_transform`,
`rasterio.transform` affine ops, `rasterio.crs.CRS` structured
equality. One behavioral finding is honored, not worked around:
`array_bounds` assumes north-up ordering, so bounds here project all
four cell corners explicitly with min/max normalization (correct for
north-up, south-up and rotated grids alike).

## Contracts reused, not duplicated

CRS identifiers, `AffineTransform` (GDAL order), `Bounds`,
`SpatialKind` and `GeoreferencingLevel` come from the foundation.
`TargetGrid` (CRS mandatory, affine, dims, dtype, nodata, optional
resolution) is the one new spatial grid description — needed because
alignment targets are meaning-free grids, not DSM products.

## Pixel/world

`pixel_to_world` (CENTER adds the documented 0.5 offset, CORNER does
not — never mixed) and `world_to_pixel` (continuous coordinates, no
rounding; callers choose indexing policy) both go through the
trustworthy `Affine` inverse (`~`), converted from contract order by
`to_affine`. Transforms are finiteness-checked; singular
(zero-determinant) mappings fail via `require_invertible` instead of
returning bogus coordinates. No fake identity transforms.

## CRS policy

`parse_crs` / `crs_equal` use structured comparison (EPSG code vs
WKT of the same system compare equal); invalid identifiers raise
`GeospatialProcessingError`. Missing CRS fails only operations that
need one, via the existing `MissingCRSError` — non-georeferenced
rasters stay valid inputs, and pixel-local conversions never require
CRS. A single compact `GeospatialProcessingError`
(`geospatial_processing_failure`) covers the rest; no per-helper
hierarchy, no `ExportError`/`CalibrationError` misuse.

## Overlap and compatibility

`calculate_overlap` intersects in a common frame: same structured
CRS compares directly; differing CRS transforms the second bounds
explicitly first (raw degrees and metres are never compared).
Missing CRS on either side fails. Edge-touching (zero-area contact)
is not intersection — DEM work needs shared pixels. Results carry
intersects flag, overlap bounds + frame, area and unambiguous
geometric coverage fractions (never "confidence").

`check_grid_compatibility` compares dims, structured CRS, all six
affine parameters (rel_tol=1e-9 — millimetre-level at 1e6
magnitudes, documented) and resolution when known, returning reasons
instead of a bare boolean. `classify_alignment` decides
COMPATIBLE / REPROJECTABLE / INCOMPATIBLE (invalid CRS metadata
yields INCOMPATIBLE).

## Reprojection and alignment

`reproject_array` wraps `rasterio.warp.reproject` onto
caller-specified `TargetGrid`s (no silent resolution changes):
nearest default (conservative — never invents values), bilinear
available for continuous fields, caller-chosen per call. Nodata NaN
initializes uncovered pixels; the valid mask derives from output
finiteness (valid 0.0 preserved, NaN stays invalid, no zero-fill);
dtype is preserved (no silent downcasts); sources are never mutated
and outputs are freshly owned. `align_raster` adds the honest
fast path: identical grids return an owned copy with warping
bypassed (recorded, not hidden).

## Units, meaning, provenance

Horizontal units are CRS-dependent and never claimed; vertical
values pass through per the resampling policy (resampling changes
sampling, not meaning — documented, never called lossless).
Reprojection outputs echo their target grid plus source CRS,
resampling used, and optional source-provenance passthrough reusing
`ProductProvenance` (no second system, no timestamps, no accuracy
inventions).

## Deliberately absent

DEM providers, SRTM/Copernicus downloads, GCP extraction, network
access, reprojection guessing, resampling-algorithm zoos, Dask/GPU —
and any CRS math inside calibration, pipeline, service, DSM or mesh
layers. S8 consumes: inspect source → validate CRS → overlap vs
image → choose target grid → reproject/align → sample reference
terrain.

**Geospatial processing changes coordinate/grid representation; it
does not automatically change the scientific meaning of elevation
values.**
