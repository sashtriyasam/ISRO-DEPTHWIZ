"""Single-band GeoTIFF export for DSM grids (serialization only).

Writes ``DSMGrid`` values, mask, nodata, CRS and transform to a GTiff
file with lossless DEFLATE compression, then verifies by read-back.
No resampling, reprojection, calibration or reinterpretation: export
serializes the existing scientific raster.
"""

from __future__ import annotations

import math
import os
import tempfile
import warnings
from enum import Enum
from pathlib import Path
from typing import Literal

import numpy as np
from pydantic import BaseModel, ConfigDict, Field

from depthwizard.dsm.grid import DSMGrid
from depthwizard.errors import ExportError

#: Metadata namespace for serialized product facts (small stable set).
TAG_NAMESPACE = "depthwizard"

#: Suffixes the exporter accepts (matches the ingestion allow-list).
TIFF_SUFFIXES = frozenset({".tif", ".tiff"})


class Compression(str, Enum):
    """Lossless compression options actually supported (never lossy)."""

    DEFLATE = "deflate"
    NONE = "none"


class ExportOptions(BaseModel):
    """Minimal explicit export configuration (deterministic defaults)."""

    model_config = ConfigDict(frozen=True)

    overwrite: bool = Field(
        default=False,
        description="Allow replacing an existing target (default refuses).",
    )
    compression: Compression = Field(
        default=Compression.DEFLATE,
        description="Lossless DEFLATE (verified) or uncompressed.",
    )


class ExportResult(BaseModel):
    """Verified outcome of a GeoTIFF export (read-back confirmed)."""

    model_config = ConfigDict(frozen=True)

    path: str = Field(description="Export target path as supplied.")
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    dtype: str
    count: Literal[1] = 1
    crs: str | None = None
    transform: tuple[float, ...] | None = None
    nodata: float
    compression: str
    verified: bool = Field(description="True only after read-back verification.")


def _validate_target(path: Path, overwrite: bool) -> None:
    """Validate the destination before any filesystem write occurs."""
    if path.is_dir():
        raise ExportError(f"export target is a directory: {path.name}")
    parent = path.parent
    if str(parent) not in ("", ".") and not parent.is_dir():
        raise ExportError(f"export parent directory does not exist: {parent}")
    if path.suffix.lower() not in TIFF_SUFFIXES:
        raise ExportError(f"export target must use a .tif/.tiff suffix: {path.name}")
    if path.exists() and not overwrite:
        raise ExportError(f"export target already exists (overwrite=False): {path.name}")


def _check_grid_array(grid: DSMGrid) -> None:
    """Verify the grid array honors its own mask before opening output.

    DSMGrid construction enforces this invariant, but attribute-level
    bypasses     (e.g. unvalidated copies) must not reach the writer: an
    infinity serialized as a valid pixel would corrupt the science.
    """
    valid_cells = grid.array[grid.valid_mask]
    if valid_cells.size and not bool(np.isfinite(valid_cells).all()):
        raise ExportError(
            "refusing export: grid array holds non-finite values under "
            "a valid mask (invariant violated before writing)"
        )
    invalid_cells = grid.array[~grid.valid_mask]
    if invalid_cells.size and not bool(np.isnan(invalid_cells).all()):
        raise ExportError(
            "refusing export: masked grid pixels must carry the NaN "
            "nodata marker (invariant violated before writing)"
        )


def _writer_kwargs(grid: DSMGrid, compression: Compression) -> dict[str, object]:
    """Convert the typed profile to Rasterio writer arguments."""
    from rasterio.transform import Affine

    profile = grid.export_profile().to_rasterio_kwargs()
    transform = profile["transform"]
    kwargs: dict[str, object] = {
        "driver": profile["driver"],
        "dtype": profile["dtype"],
        "count": profile["count"],
        "width": profile["width"],
        "height": profile["height"],
        "nodata": profile["nodata"],
    }
    if profile["crs"] is not None:
        kwargs["crs"] = profile["crs"]
    if transform is not None:
        assert isinstance(transform, tuple)
        kwargs["transform"] = Affine.from_gdal(*transform)
    if compression is Compression.DEFLATE:
        kwargs["compress"] = "deflate"
    return kwargs


def _metadata_tags(grid: DSMGrid) -> dict[str, str]:
    """Small stable serialized product facts (not a Pydantic dump)."""
    tags = {
        "semantics": grid.semantics.value,
        "units": grid.units,
        "model_name": grid.depth_model_name,
        "calibration_method": grid.calibration_method,
        "calibration_reference": grid.calibration_reference,
        "engine_version": grid.provenance.software_version or "unknown",
    }
    if grid.source_checksum is not None:
        tags["source_checksum"] = grid.source_checksum
    return tags


def _verify_written(target: Path, grid: DSMGrid) -> None:
    """Reopen the output and verify persisted state (raises ExportError)."""
    import rasterio
    from rasterio.errors import NotGeoreferencedWarning

    def failure(reason: str) -> ExportError:
        return ExportError(f"read-back verification failed for {target.name}: {reason}")

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", NotGeoreferencedWarning)
        try:
            dataset = rasterio.open(target)
        except Exception as exc:
            raise failure(f"cannot reopen output: {exc}") from exc
        with dataset:
            if dataset.count != 1:
                raise failure(f"count {dataset.count} != 1")
            if dataset.width != grid.width or dataset.height != grid.height:
                raise failure(
                    f"dimensions {(dataset.width, dataset.height)} != {(grid.width, grid.height)}"
                )
            if dataset.dtypes[0] != grid.dtype:
                raise failure(f"dtype {dataset.dtypes[0]} != {grid.dtype}")
            read_crs = None if dataset.crs is None else dataset.crs.to_string()
            if read_crs != grid.export_profile().crs:
                raise failure(f"CRS {read_crs!r} mismatch")
            profile_transform = grid.export_profile().transform
            if profile_transform is not None:
                from rasterio.transform import Affine

                gt = profile_transform
                expected = tuple(Affine.from_gdal(gt[0], gt[1], gt[2], gt[3], gt[4], gt[5]))[:6]
                if tuple(dataset.transform)[:6] != expected:
                    raise failure(f"transform {tuple(dataset.transform)[:6]!r} != {expected!r}")
            nodata = dataset.nodata
            if nodata is None or not math.isnan(float(nodata)):
                raise failure(f"nodata {nodata!r} is not NaN")
            data = dataset.read(1)
            if not bool(np.array_equal(data, grid.array, equal_nan=True)):
                raise failure("data values differ from grid array")
            mask = dataset.read_masks(1)
            expected_mask = (grid.valid_mask.astype("uint8")) * 255
            if not bool((mask == expected_mask).all()):
                raise failure("dataset mask differs from grid valid_mask")


def export_geotiff(
    grid: DSMGrid,
    path: str | Path,
    options: ExportOptions | None = None,
) -> ExportResult:
    """Export a DSM grid to a single-band GeoTIFF with verification.

    Writes to a temporary file in the destination directory and
    atomically replaces the target only after a successful write plus
    read-back verification. Never mutates the source grid. Existing
    targets are refused unless ``overwrite=True``.
    """
    import rasterio
    from rasterio.errors import NotGeoreferencedWarning

    if not isinstance(grid, DSMGrid):
        raise TypeError(f"export_geotiff requires a DSMGrid; got {type(grid).__name__}")
    opts = options if options is not None else ExportOptions()
    if not isinstance(opts, ExportOptions):
        raise TypeError(f"export_geotiff options must be ExportOptions; got {type(opts).__name__}")
    target = Path(path)
    _validate_target(target, opts.overwrite)
    if grid.invalid_count == grid.width * grid.height:
        raise ExportError("refusing to export an all-invalid grid (no valid pixels)")
    _check_grid_array(grid)
    kwargs = _writer_kwargs(grid, opts.compression)
    parent = target.parent if str(target.parent) not in ("", ".") else Path(".")
    tmp_handle = tempfile.NamedTemporaryFile(
        delete=False, dir=parent, prefix=target.stem + ".", suffix=target.suffix
    )
    tmp_path = Path(tmp_handle.name)
    tmp_handle.close()
    replaced = False
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", NotGeoreferencedWarning)
            try:
                with rasterio.open(tmp_path, "w", **kwargs) as dataset:
                    dataset.write(grid.array, 1)
                    dataset.write_mask((grid.valid_mask.astype("uint8")) * 255)
                    dataset.update_tags(ns=TAG_NAMESPACE, **_metadata_tags(grid))
            except Exception as exc:
                raise ExportError(f"GeoTIFF write failed for {target.name}: {exc}") from exc
        _verify_written(tmp_path, grid)
        os.replace(tmp_path, target)
        replaced = True
    finally:
        if not replaced and tmp_path.exists():
            tmp_path.unlink()
    profile = grid.export_profile()
    return ExportResult(
        path=str(target),
        width=grid.width,
        height=grid.height,
        dtype=grid.dtype,
        crs=profile.crs,
        transform=profile.transform,
        nodata=grid.nodata,
        compression=opts.compression.value,
        verified=True,
    )
