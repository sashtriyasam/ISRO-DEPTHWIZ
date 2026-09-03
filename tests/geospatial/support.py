"""Tiny deterministic geospatial fixtures (programmatic, offline)."""

import numpy as np

from depthwizard.contracts.spatial import AffineTransform
from depthwizard.geospatial.grids import TargetGrid

#: North-up UTM-like fixture: origin (100, 200), 0.5-unit pixels.
NORTH_UP = AffineTransform(a=100.0, b=0.5, c=0.0, d=200.0, e=0.0, f=-0.5)

#: South-up variant (positive y pixel size).
SOUTH_UP = AffineTransform(a=10.0, b=2.0, c=0.0, d=20.0, e=0.0, f=2.0)

#: Rotated/skewedvariant.
ROTATED = AffineTransform(a=0.0, b=1.0, c=0.5, d=0.0, e=-0.5, f=1.0)

#: Singular (zero determinant) transform.
SINGULAR = AffineTransform(a=0.0, b=1.0, c=2.0, d=0.0, e=2.0, f=4.0)

CRS_UTM = "EPSG:32643"
CRS_WGS84 = "EPSG:4326"


def utm_grid(width: int = 5, height: int = 4, dtype: str = "float32") -> TargetGrid:
    """Target grid on the north-up UTM-like fixture."""
    return TargetGrid(
        crs=CRS_UTM,
        transform=NORTH_UP,
        width=width,
        height=height,
        dtype=dtype,
        nodata=float("nan"),
        resolution=0.5,
    )


def wgs84_target_from_utm(width: int, height: int) -> TargetGrid:
    """Explicit WGS84 target grid derived via GDAL suggested output (test setup)."""
    from rasterio.crs import CRS
    from rasterio.warp import calculate_default_transform

    from depthwizard.contracts.spatial import AffineTransform as ContractAffine

    dst_transform, dst_width, dst_height = calculate_default_transform(
        CRS.from_string(CRS_UTM),
        CRS.from_string(CRS_WGS84),
        width,
        height,
        left=100.0,
        bottom=198.0,
        right=102.5,
        top=200.0,
    )
    a, b, c, d, e, f, _, _, _ = tuple(dst_transform)
    return TargetGrid(
        crs=CRS_WGS84,
        transform=ContractAffine(a=c, b=a, c=b, d=f, e=d, f=e),
        width=dst_width,
        height=dst_height,
        dtype="float32",
        nodata=float("nan"),
    )


def ramp_array(width: int, height: int, dtype: str = "float32") -> np.ndarray:
    """Deterministic finite ramp with an exact valid zero at (0, 0)."""
    grid = np.arange(width * height, dtype=np.float64).reshape(height, width)
    return grid.astype(dtype)


def assert_grids_equal(first: TargetGrid, second: TargetGrid) -> None:
    """Compare grids field-wise (NaN nodata never equals itself)."""
    assert first.crs == second.crs
    assert first.transform == second.transform
    assert (first.width, first.height) == (second.width, second.height)
    assert first.dtype == second.dtype
    assert first.resolution == second.resolution
    assert (first.nodata != first.nodata) and (second.nodata != second.nodata)
