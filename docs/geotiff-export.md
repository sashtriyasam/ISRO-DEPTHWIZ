# DepthWizard — GeoTIFF Export (Shivam S12)

Single-band file serialization of validated DSM grids. Export writes
bytes; it never improves or reinterprets the science.

## API

```python
export_geotiff(grid, path, options=None) -> ExportResult
```

- `grid: DSMGrid` — the only accepted raster input (no raw arrays,
  no re-rasterization at this layer).
- `path` — `.tif`/`.tiff` target (matches the ingestion allow-list).
- `options: ExportOptions` — `overwrite=False` default,
  `compression=deflate` default. Minimal by design: no driver-option
  grab-bag.

## What the exporter does

1. Validates types, destination (parent exists, not a directory,
   `.tif/.tiff` suffix, existing target refused unless
   `overwrite=True`) and grid-array invariants — all before any write.
2. Converts `DSMProfile.to_rasterio_kwargs()` into Rasterio writer
   arguments (6-tuple GDAL-order transform → `Affine.from_gdal`).
3. Writes band 1 verbatim, writes the explicit 8-bit dataset mask
   (`255` valid / `0` invalid) via `write_mask`, and stores a small
   stable `depthwizard`-namespaced tag set: semantics, units,
   model_name, calibration_method, calibration_reference,
   source_checksum (when known), engine_version. No Pydantic dumps,
   no blobs.
4. Writes to a temp file in the destination directory, closes it,
   re-verifies by read-back, then atomically `os.replace`s the
   target. Temp files are removed on any failure; an existing target
   is never truncated before success (validated first, replaced last).
   Existing files plus `overwrite=False` raise `ExportError` with the
   original bytes untouched.

## Read-back verification (mandatory, always on)

Every export reopens its output and checks dimensions, count,
dtype, CRS (string + structured equality where present), transform
(native-order comparison against `Affine.from_gdal` reconstruction),
NaN nodata, exact data equality (`equal_nan`), and mask equality
against `valid_mask`. Any mismatch raises `ExportError` and the
target is not installed.

## Nodata and mask

NaN marker + authoritative mask, exactly as the DSM contract:
valid `0.0` stays `0.0`/valid; NaN/±inf (including float32 downcast
overflow) stay invalid/NaN. The exporter additionally guards the
writer boundary: arrays violating the mask invariant are refused
with `ExportError` instead of serializing corrupt science.

## Georeferencing

CRS and transform are written exactly as profiled — no conversion,
no axis swaps. Absent spatial metadata yields an honestly
unreferenced raster (CRS None), which is valid output.

## Compression

Lossless `DEFLATE` by default, verified in read-back profile tags
(rasterio 1.5.1 / GDAL 3.12.4). A float `predictor` was probed and
found to be silently dropped by this stack, so it is deliberately
not requested — no unverified claims. `Compression.NONE` writes
uncompressed (verified `compress` key absent). Lossy/JPEG compression
is never an option.

## Determinism and immutability

Same grid + options ⇒ semantically equivalent outputs (exact data
and mask equality verified across double exports; byte identity is
not promised and not required). Sources (`DSMGrid`, product,
calibration, spatial) are never mutated — verified by test.

## Errors

`ExportError` for: existing target, missing parent, directory
target, bad suffix, writer failures, verification failures,
invariant violations, all-invalid grids. `TypeError` for wrong
input/options types. No `CalibrationError`/`MissingCRS*` misuse;
raw Rasterio exceptions are chained, never the public contract.

## Provenance

Authoritative contracts stay in Python; the file carries the small
tag set above plus standard GTiff structural metadata (CRS,
transform, nodata, compression). No datums, scores, timestamps or
coordinates are fabricated.

## Non-goals (explicit)

No DEM/reprojection/resampling/GCP/calibration/inference/mesh/API/
desktop/COG-multiband work. COG optimization, if ever wanted, is a
separate product decision — this milestone writes plain GTiff.
