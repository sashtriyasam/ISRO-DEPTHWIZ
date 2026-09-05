# DepthWizard — Input Ingestion & Semantic Validation (Shivam S2/S3)

Read-only input inspection. No inference, calibration, DEM alignment,
reprojection, DSM/mesh generation, services or desktop integration.

## Public API

```python
from depthwizard.ingestion import InputHandle, InputInspection, inspect_input

inspection = inspect_input("scene.tif")  # -> InputInspection (frozen)
handle = InputHandle.from_path("photo.jpg")  # identity record only
```

## Supported formats

| Suffixes                     | Detected as | Reader                                | Classification                         |
| ---------------------------- | ----------- | ------------------------------------- | -------------------------------------- |
| `.png`                       | PNG         | Pillow (`Image.open` + forced decode) | `NON_GEOREFERENCED`                    |
| `.jpg`, `.jpeg` (any casing) | JPEG        | Pillow                                | `NON_GEOREFERENCED`                    |
| `.tif`, `.tiff` without CRS  | TIFF        | rasterio (metadata only)              | `NON_GEOREFERENCED`                    |
| `.tif`, `.tiff` with CRS     | TIFF        | rasterio                              | `GEOREFERENCED_NO_ELEVATION_REFERENCE` |

Detection is suffix-hint + content verification: the reader must decode
the file _as the claimed format_ (Pillow auto-detects content, so a
`.jpg` holding PNG bytes is rejected as mislabeled). Files with unknown
suffixes fall back to magic-byte sniffing (PNG/JPEG/TIFF signatures);
anything else raises `UnsupportedFormatError`.

## Semantic classification (conservative by design)

- PNG/JPEG carry image dimensions and checksum only. EXIF/GPS,
  filenames and textual metadata are ignored — no CRS, transform, GSD
  or elevation is ever inferred. Spatial kind: `NOT_APPLICABLE`.
- A georeferenced raster keeps CRS, affine transform (stored in the
  foundation GDAL tag order), bounds, resolution (only when x == y),
  nodata, raster dimensions and source. Spatial kind: `PRESENT`.
- A TIFF _without_ CRS is valid input classified `NON_GEOREFERENCED`
  (spatial kind `UNAVAILABLE`): rasterio's identity fallback transform
  is never mistaken for georeferencing, and no fake EPSG/transform/
  bounds/GSD defaults are invented.
- Inspection alone never yields `GEOREFERENCED_WITH_DEM` or
  `GEOREFERENCED_WITH_GCP`: those require DEM-alignment / GCP-fitting
  evidence from later milestones.

A supported non-georeferenced image is valid input. Absence of
georeferencing is not an ingestion failure. The ingestion layer never
invents spatial or elevation semantics.

## Checksum / reproducibility

Every inspection captures hex SHA-256 over the file bytes, streamed in
64 KiB chunks (never fully loaded for hashing). Pixel arrays are
decoded transiently for validation (Pillow) or never read at all
(rasterio metadata path) and are never stored. Inspection performs no
filesystem writes.

## Mapping to foundation contracts

`InputInspection` reuses `GeoreferencingLevel`, `SpatialContext`
(`SpatialKind`/`SpatialDetails`/`AffineTransform`/`Bounds`) and the
error taxonomy unchanged — no second CRS/transform representation.
The same honesty validators apply (e.g. `NON_GEOREFERENCED` cannot
carry `PRESENT` spatial details).

## Error behavior

- `InvalidInputError`: missing path, directory, empty file, unreadable
  file, corrupt/mislabeled PNG-JPEG-TIFF. Raw Pillow/rasterio
  exceptions are wrapped (chained as context, never leaked as types).
- `UnsupportedFormatError`: PDF, BMP, WEBP, arbitrary binary, unknown
  extension + unknown content.
- `MissingCRSError` is never raised here: no-CRS input is a valid
  state, flagged only when a later geospatial operation requires CRS.
- `MissingElevationReferenceError` is not used: weaker semantics are
  represented by the classification, not by failure.

## Fixtures

All test fixtures are generated programmatically in `tmp_path`
(`tests/ingestion/fixtures.py`: Pillow checker PNG, fixed-quality
JPEG, rasterio `arange` plain/GeoTIFF with EPSG:32643). No binaries
are committed, no downloads, no network, no GPU.

## Deliberately out of scope

Reprojection, resampling, DEM alignment/overlap, elevation extraction,
terrain correction, GCP fitting/validation, registries, caches,
async pipelines, API services, desktop integration.

## Future extension points

`InspectionStatus` (currently `VALID` only), additional
`DetectedFormat` members with matching readers, GCP sidecar support
(new milestone + contract), calibration-reference capture in
`ProductProvenance` from inspection handles.
