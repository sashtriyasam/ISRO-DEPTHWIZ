"""Shared model-input loader: band order, 16-bit scaling, nodata validity."""

from pathlib import Path
from typing import Any

import numpy as np
import pytest

from depthwizard.backends.depth_anything_v2 import DepthAnythingV2Backend
from depthwizard.calibration.selection import DevCalibrationProvider
from depthwizard.contracts.semantics import ElevationSemantics
from depthwizard.dsm.rasterize import rasterize_height_product
from depthwizard.height.factory import create_scientific_height_product
from depthwizard.ingestion.api import inspect_input
from depthwizard.ingestion.pixels import load_model_rgb

CRS = "EPSG:32643"


def _write_tiff(
    path: Path,
    data: np.ndarray,
    nodata: float | None = None,
    colorinterp: list[str] | None = None,
) -> Path:
    import rasterio
    from rasterio.enums import ColorInterp
    from rasterio.transform import Affine

    count, height, width = data.shape
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=height,
        width=width,
        count=count,
        dtype=str(data.dtype),
        crs=CRS,
        transform=Affine(1.0, 0.0, 500000.0, 0.0, -1.0, 2000000.0),
        nodata=nodata,
    ) as dst:
        dst.write(data)
        if colorinterp is not None:
            dst.colorinterp = [ColorInterp[name] for name in colorinterp]
    return path


def test_uint16_is_stretched_not_wrapped(tmp_path: Path) -> None:
    ramp = np.linspace(0, 4000, 64, dtype=np.uint16).reshape(8, 8)
    data = np.stack([ramp, ramp, ramp])
    loaded = load_model_rgb(inspect_input(_write_tiff(tmp_path / "u16.tif", data)))
    red = loaded.rgb[:, :, 0].astype(int).ravel()
    # A modulo-256 wrap would make the ramp non-monotonic.
    assert np.all(np.diff(red) >= 0)
    assert red.min() == 0 and red.max() == 255
    assert "percentile" in loaded.scaling


def test_declared_bgr_band_order_is_respected(tmp_path: Path) -> None:
    blue = np.full((4, 4), 10, dtype=np.uint8)
    green = np.full((4, 4), 20, dtype=np.uint8)
    red = np.full((4, 4), 30, dtype=np.uint8)
    path = _write_tiff(
        tmp_path / "bgr.tif", np.stack([blue, green, red]), colorinterp=["blue", "green", "red"]
    )
    loaded = load_model_rgb(inspect_input(path))
    assert tuple(loaded.rgb[0, 0]) == (30, 20, 10)
    assert "declared" in loaded.bands


def test_nodata_pixels_are_invalid(tmp_path: Path) -> None:
    data = np.full((3, 4, 4), 100, dtype=np.uint8)
    data[:, 0, :] = 0
    loaded = load_model_rgb(inspect_input(_write_tiff(tmp_path / "nd.tif", data, nodata=0)))
    assert not loaded.valid[0].any()
    assert loaded.valid[1:].all()
    mask = loaded.valid_mask_tuple()
    assert mask is not None and mask.count(False) == 4


def test_png_alpha_zero_is_invalid(tmp_path: Path) -> None:
    from PIL import Image

    rgba = np.full((4, 4, 4), 200, dtype=np.uint8)
    rgba[0, 0, 3] = 0
    Image.fromarray(rgba, "RGBA").save(tmp_path / "a.png")
    loaded = load_model_rgb(inspect_input(tmp_path / "a.png"))
    assert not loaded.valid[0, 0]
    assert int(loaded.valid.sum()) == 15


def test_sixteen_bit_png_is_stretched(tmp_path: Path) -> None:
    from PIL import Image

    gray = np.linspace(0, 60000, 16, dtype=np.uint16).reshape(4, 4)
    Image.fromarray(gray).save(tmp_path / "g16.png")
    loaded = load_model_rgb(inspect_input(tmp_path / "g16.png"))
    assert loaded.rgb.dtype == np.uint8
    assert loaded.rgb[..., 0].max() == 255


class _RampModel:
    def __init__(self, encoder_config: dict[str, Any]) -> None:
        pass

    def infer_image(self, bgr: Any, input_size: int) -> Any:
        h, w = bgr.shape[:2]
        return np.arange(h * w, dtype=np.float32).reshape(h, w)


def test_nodata_never_becomes_dsm_data(tmp_path: Path) -> None:
    data = np.full((3, 4, 4), 100, dtype=np.uint8)
    data[:, :, 0] = 0
    inspection = inspect_input(_write_tiff(tmp_path / "scene.tif", data, nodata=0))
    ckpt = tmp_path / "fake.pth"
    ckpt.write_bytes(b"x")
    depth = DepthAnythingV2Backend(checkpoint=ckpt, model_factory=_RampModel).estimate_depth(
        inspection
    )
    assert depth.valid_mask is not None
    assert depth.preprocessing["invalid_input_pixels"] == "4"
    target = ElevationSemantics.ABSOLUTE_ELEVATION_DSM
    calibration = DevCalibrationProvider(target).calibrate(depth)
    assert calibration.valid_samples == 12
    grid = rasterize_height_product(create_scientific_height_product(depth, calibration, target))
    assert not grid.valid_mask[:, 0].any()
    assert grid.invalid_count == 4
    assert np.isnan(grid.array[:, 0]).all()


def test_two_band_non_alpha_tiff_is_refused(tmp_path: Path) -> None:
    from depthwizard.errors import InvalidInputError

    data = np.ones((2, 4, 4), dtype=np.uint8)
    with pytest.raises(InvalidInputError, match="2 bands"):
        load_model_rgb(inspect_input(_write_tiff(tmp_path / "two.tif", data)))
