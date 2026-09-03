"""Tiny deterministic fixture builders for ingestion tests.

Provenance: every fixture is generated programmatically in ``tmp_path``
at test time — no binaries are checked in, nothing is downloaded, no
network or GPU is involved.

- PNG/JPEG fixtures: Pillow, fixed sizes/modes, deterministic pixels.
  (JPEG bytes are encoder-version dependent; tests assert in-run
  determinism and metadata, never golden hashes across environments.)
- TIFF fixtures: rasterio GTiff driver + numpy ``arange`` grids.
  Plain TIFF carries no CRS/transform (identity fallback ignored by the
  reader). GeoTIFF fixture uses EPSG:32643 with a fixed affine
  transform and nodata=0.
"""

from __future__ import annotations

import warnings
from pathlib import Path

PNG_SIZE = (8, 6)
JPEG_SIZE = (10, 7)
TIFF_SIZE = (5, 4)  # (width, height)
GEO_CRS = "EPSG:32643"
# Affine(col-scale, row-skew, x-origin, col-skew, row-scale, y-origin).
GEO_TRANSFORM = (0.5, 0.0, 100.0, 0.0, -0.5, 200.0)


def make_png(path: Path) -> Path:
    """Write an 8x6 RGB PNG with a deterministic checker pattern."""
    from PIL import Image

    width, height = PNG_SIZE
    img = Image.new("RGB", (width, height))
    pixels = img.load()
    assert pixels is not None
    for row in range(height):
        for col in range(width):
            v = 255 if (row + col) % 2 == 0 else 0
            pixels[col, row] = (v, (col * 32) % 256, (row * 40) % 256)
    img.save(path, format="PNG")
    return path


def make_jpeg(path: Path) -> Path:
    """Write a 10x7 RGB JPEG with fixed quality settings."""
    from PIL import Image

    width, height = JPEG_SIZE
    img = Image.new("RGB", (width, height), color=(10, 120, 200))
    img.save(path, format="JPEG", quality=90, subsampling=0)
    return path


def make_plain_tiff(path: Path) -> Path:
    """Write a 5x4 single-band uint8 TIFF with no georeferencing."""
    import numpy as np
    import rasterio
    from rasterio.errors import NotGeoreferencedWarning

    width, height = TIFF_SIZE
    grid = np.arange(width * height, dtype="uint8").reshape(height, width)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", NotGeoreferencedWarning)
        with rasterio.open(
            path,
            "w",
            driver="GTiff",
            height=height,
            width=width,
            count=1,
            dtype="uint8",
        ) as dst:
            dst.write(grid, 1)
    return path


def make_geotiff(path: Path) -> Path:
    """Write a 5x4 two-band uint8 GeoTIFF (EPSG:32643, nodata=0)."""
    import numpy as np
    import rasterio
    from rasterio.crs import CRS
    from rasterio.transform import Affine

    width, height = TIFF_SIZE
    grid = np.arange(width * height, dtype="uint8").reshape(height, width)
    transform = Affine(*GEO_TRANSFORM)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=height,
        width=width,
        count=2,
        dtype="uint8",
        crs=CRS.from_string(GEO_CRS),
        transform=transform,
        nodata=0,
    ) as dst:
        dst.write(grid, 1)
        dst.write(grid, 2)
    return path
