# DepthWizard — DSM Raster Engine (Shivam S11)

In-memory raster representation of scientific height products.
No file writing, no DEM, no reprojection, no resampling, no meshes.

## Path

```text
ScientificHeightProduct (row-major metric values + meaning)
        ↓  rasterize_height_product() — 1:1, representation only
DSMGrid  (explicit (height, width) float array + validity mask)
        ↓  grid.export_profile()
DSMProfile  (future-writer metadata: driver/dtype/count/dims/CRS/transform/nodata)
        ↓  (S12 exporter — not this milestone)
future GeoTIFF
```

## Representation

Single band: band 1 holds the scientific height/elevation values.
Arrays are explicitly 2D `(height, width)`, C-order (row-major),
matching `DepthResult` / `ScientificHeightProduct` layout — never
transposed, flattened, resized, interpolated or rescaled. The
resampling policy is `NO_RESAMPLING`, always, this milestone.

Default storage dtype is `float32` (standard DSM interchange);
`float64` is available via `RasterizeOptions` and preserves full
source precision. `RasterizeOptions` carries only dtype + policy —
no over-engineered configuration.

## Nodata policy

- Nodata marker: NaN (`NODATA`), documented constant.
- Finite values stay valid — a valid `0.0` remains `0.0` and masked
  valid. Zero is never conflated with nodata.
- Non-finite sources (NaN, ±inf, including float64→float32 downcast
  overflow, which is explicitly masked rather than warned about)
  become NaN-marked invalid pixels.
- The dedicated `valid_mask` (bool, True = valid) is authoritative;
  `invalid_count` always equals the masked pixel count (validated).
- No invented replacements (never 0), no silent clipping.
- All pixels invalid → explicit `InvalidInputError` with counts
  (never `ExportError` — nothing is exported).

## Ownership

Controlled immutability: the model is frozen and factories hand out
freshly allocated arrays, so grids are independent of each other and
of the source product. Consumers treat arrays as read-only (copy
before mutating). `ScientificHeightProduct`, `CalibrationResult`
and `DepthResult` are never mutated.

## Geospatial preservation

Georeferencing level, CRS, transform, bounds, dimensions and
resolution pass through untouched from the product's spatial
context. Non-georeferenced sources yield CRS-less/transform-less
grids and profiles — rasterization never creates georeferencing.
No CRS math, reprojection, alignment or overlap logic lives here.

## Profile preparation

`DSMProfile` mirrors the Rasterio profile fields the future writer
needs (driver `GTiff`, dtype, count 1, width, height, CRS, 6-tuple
GDAL-order transform, nodata) without opening any file — not even
via `rasterio.open(..., "w")`. `to_rasterio_kwargs()` returns
plain-data kwargs; the exporter converts the transform tuple to the
writer's affine type. CRS/transform appear only when the source
spatial details actually contain them (a transform without CRS is
refused as an orphan). Current grids are single in-memory arrays:
profiles record `tiled: false`; no chunked/Dask/cloud machinery.

## Provenance and meaning

Units, semantics, depth identity, calibration scalars, source
linkage and the full product provenance pass through unchanged —
rasterization is representation, never reinterpretation or another
calibration. No timestamps, datums, scores or coordinates are
fabricated.

## Dependencies

NumPy became a **direct runtime dependency** in this milestone
(`numpy>=1.24`, BSD-3-Clause): `DSMGrid` array storage is production
code, and relying on the previous transitive-via-rasterio accident
would be dishonest. It was already dev-declared and installed
(2.5.0 verified); the declaration now matches reality. No SciPy,
scikit-learn, PyTorch, OpenCV or GDAL-direct additions. Rasterio
profile conventions follow its official quickstart (driver, dims,
count, dtype, CRS, transform, nodata) as previously inspected; no
third-party code copied.

## Downstream

```text
DSMGrid
   ↓  future mesh/artifact adapter (explicit, separate milestone)
Aryan SceneArtifact / DSM layer (elevation grid + metadata.backend)
```

Aryan's `adaptBackendResult`/`adaptCalibratedResult` already consume
serialized backend-shaped payloads into `SceneArtifact` with
`metadata.backend` origin info; the DSM exporter + adapter will feed
that path when built. Nothing in this milestone touches the frontend.
