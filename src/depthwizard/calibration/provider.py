"""Production calibration providers (DEM, GCP, file-based references).

A ``CalibrationProvider`` acquires paired predicted/reference samples
and fits a calibrator. This module ships a single production provider
that reads local DEM GeoTIFFs or GCP CSVs; future acquisition
subsystems can implement the same protocol.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from depthwizard.calibration.calibrator import (
    MIN_VALID_SAMPLES,
    Calibrator,
    ScaleOffsetCalibrator,
)
from depthwizard.calibration.models import (
    CalibrationMethod,
    CalibrationResult,
    CalibrationSamples,
)
from depthwizard.contracts.artifacts import DepthResult
from depthwizard.contracts.semantics import ElevationSemantics
from depthwizard.contracts.spatial import SpatialDetails
from depthwizard.dem.build import build_terrain_reference
from depthwizard.dem.inspect import inspect_dem
from depthwizard.dem.models import DEMInspection
from depthwizard.errors import CalibrationError, InsufficientGCPsError
from depthwizard.geospatial.grids import TargetGrid
from depthwizard.ingestion.models import InputInspection


def _depth_valid(depth_result: DepthResult, height: int, width: int) -> NDArray[np.bool_]:
    """Depth validity as a 2D mask (input nodata/alpha never calibrates)."""
    if depth_result.valid_mask is None:
        return np.ones((height, width), dtype=bool)
    return np.asarray(depth_result.valid_mask, dtype=bool).reshape(height, width)


#: Upper bound on DEM pixel pairs per fit (ample for an affine/spline fit).
MAX_DEM_SAMPLES = 250_000


def _pixel_size(details: SpatialDetails) -> float | None:
    """Pixel size from the GDAL-order transform (b = width, f = height)."""
    if details.transform is None:
        return details.resolution_gsd
    return math.sqrt(abs(details.transform.b * details.transform.f))


def _ground_resolution(crs: str | None, resolution: float | None, details: SpatialDetails) -> float:
    """Pixel size in metres (degrees converted at the scene's latitude)."""
    from depthwizard.geospatial.crs import crs_is_projected_metric

    if resolution is None or not math.isfinite(resolution) or resolution <= 0:
        raise CalibrationError("raster resolution unknown; cannot size the DEM footprint")
    if crs_is_projected_metric(crs):
        return float(resolution)
    # Geographic degrees: metres per degree at the scene centre latitude.
    latitude = 0.0
    if details.bounds is not None and details.crs is not None:
        from rasterio.warp import transform_bounds

        _, south, _, north = transform_bounds(
            details.crs,
            "EPSG:4326",
            details.bounds.min_x,
            details.bounds.min_y,
            details.bounds.max_x,
            details.bounds.max_y,
        )
        latitude = (south + north) / 2.0
    metres_per_degree = 111_320.0 * math.sqrt(max(math.cos(math.radians(latitude)), 1e-6))
    return float(float(resolution) * metres_per_degree)


class FileBasedCalibrationProvider:
    """Production calibration provider using local DEM or GCP references.

    The provider is intentionally stateless between ``prepare()`` and
    ``calibrate()``: the pipeline runner calls ``prepare(inspection)``
    and then ``calibrate(depth_result)`` in the calibrating stage. A
    provider without a reference path refuses to calibrate: metric
    values are never fabricated from a synthetic rule.
    """

    def __init__(
        self,
        reference_path: str | None = None,
        target: ElevationSemantics = ElevationSemantics.HEIGHT_AGL_NDSM,
        calibrator: Calibrator | None = None,
        method: CalibrationMethod | None = None,
        reference_label: str | None = None,
        dem_vertical_units: str = "meters",
    ) -> None:
        """Configure reference source and target semantics."""
        self._reference_path = reference_path
        self._target = target
        self._calibrator = calibrator if calibrator is not None else ScaleOffsetCalibrator()
        self._method = method
        self._reference_label = reference_label
        # GeoTIFF carries no trustworthy vertical-unit tag: DEM references are
        # declared metres (true for SRTM, Copernicus and national DEMs).
        self._dem_vertical_units = dem_vertical_units
        self._inspection: InputInspection | None = None
        self.warnings: list[str] = []

    def prepare(self, inspection: InputInspection | None = None) -> None:
        """Store inspection for spatial alignment during calibration."""
        self._inspection = inspection

    @property
    def name(self) -> str:
        """Stable provider name for run metadata."""
        if self._reference_path:
            return f"file-based:{Path(self._reference_path).name}"
        return "file-based:none"

    def calibrate(self, depth_result: DepthResult) -> CalibrationResult:
        """Fit calibration from the configured DEM or GCP reference file."""
        if not self._reference_path:
            raise CalibrationError(
                "Metric output requires a calibration reference (DEM GeoTIFF or "
                "GCP CSV); none was provided."
            )

        path = Path(self._reference_path)
        suffix = path.suffix.lower()
        if suffix in (".tif", ".tiff"):
            return self._calibrate_from_dem(depth_result, path)
        if suffix == ".csv":
            return self._calibrate_from_gcps(depth_result, path)

        raise CalibrationError(
            f"Unsupported reference format: {suffix} (expected .tif/.tiff or .csv)"
        )

    def _calibrate_from_dem(self, depth_result: DepthResult, path: Path) -> CalibrationResult:
        """Align DEM to depth grid and fit calibration from terrain samples."""
        if self._target is not ElevationSemantics.ABSOLUTE_ELEVATION_DSM:
            raise CalibrationError(
                "a DEM reference holds absolute terrain elevations, so it can only "
                f"calibrate '{ElevationSemantics.ABSOLUTE_ELEVATION_DSM.value}'; "
                f"'{self._target.value}' needs height-above-ground references "
                "(e.g. a GCP CSV with a height_agl column)"
            )
        if self._inspection is None or self._inspection.spatial.details is None:
            raise CalibrationError("DEM calibration requires a georeferenced input inspection")

        details = self._inspection.spatial.details
        if details.transform is None or details.crs is None:
            raise CalibrationError("DEM calibration requires CRS and transform in input inspection")

        target = TargetGrid(
            crs=details.crs,
            transform=details.transform,
            width=depth_result.output_resolution.width,
            height=depth_result.output_resolution.height,
            dtype="float32",
            nodata=float("nan"),
            resolution=details.resolution_gsd,
        )

        dem_inspection = inspect_dem(path, vertical_units=self._dem_vertical_units)
        if self._method is CalibrationMethod.DEM_ANCHORED:
            return self._dem_anchored(depth_result, dem_inspection, target, details)
        terrain = build_terrain_reference(dem_inspection, target)

        depth_array: NDArray[np.float32] = np.asarray(
            depth_result.depth_values, dtype=np.float32
        ).reshape(target.height, target.width)

        usable = terrain.valid_mask & _depth_valid(depth_result, target.height, target.width)
        predicted = depth_array[usable]
        reference = terrain.array[usable]
        if predicted.size > MAX_DEM_SAMPLES:
            # Evenly spaced deterministic subsample: a multi-megapixel DEM
            # overlap would otherwise be fitted pair by pair in pure Python.
            picks = np.unique(np.linspace(0, predicted.size - 1, MAX_DEM_SAMPLES).round())
            index = picks.astype(np.int64)
            predicted = predicted[index]
            reference = reference[index]

        if predicted.size < MIN_VALID_SAMPLES:
            raise CalibrationError(
                f"Insufficient valid terrain samples for calibration: "
                f"{int(predicted.size)} valid pixels (need >= {MIN_VALID_SAMPLES})"
            )

        samples = CalibrationSamples(
            predicted_values=tuple(predicted.tolist()),
            reference_values=tuple(reference.tolist()),
            reference_id=terrain.source_dem_id,
            reference_units="meters",
            target_semantics=self._target,
            source_checksum=depth_result.provenance.input_checksum,
        )
        return self._calibrator.calibrate(samples)

    def _calibrate_from_gcps(self, depth_result: DepthResult, path: Path) -> CalibrationResult:
        """Sample depth at GCP pixel locations and fit calibration."""
        if self._inspection is None or self._inspection.spatial.details is None:
            raise CalibrationError("GCP calibration requires a georeferenced input inspection")

        gcps, column = self._read_gcps(path)
        expected = _GCP_COLUMN_FOR_TARGET.get(self._target)
        if column != expected:
            raise CalibrationError(
                f"GCP file provides '{column}' values but the target "
                f"'{self._target.value}' needs a '{expected}' column"
            )
        if len(gcps) < MIN_VALID_SAMPLES:
            raise InsufficientGCPsError(
                f"Too few GCPs for calibration: {len(gcps)} (need >= {MIN_VALID_SAMPLES})"
            )

        depth_array: NDArray[np.float32] = np.asarray(
            depth_result.depth_values, dtype=np.float32
        ).reshape(
            depth_result.output_resolution.height,
            depth_result.output_resolution.width,
        )

        depth_valid = _depth_valid(depth_result, depth_array.shape[0], depth_array.shape[1])
        predicted: list[float] = []
        reference: list[float] = []
        for gcp in gcps:
            row = int(round(gcp["row"]))
            col = int(round(gcp["col"]))
            in_bounds = 0 <= row < depth_array.shape[0] and 0 <= col < depth_array.shape[1]
            if in_bounds and depth_valid[row, col]:
                predicted.append(float(depth_array[row, col]))
                reference.append(gcp["value"])

        if len(predicted) < MIN_VALID_SAMPLES:
            raise InsufficientGCPsError(
                f"Too few valid GCP samples after bounds check: "
                f"{len(predicted)} (need >= {MIN_VALID_SAMPLES})"
            )

        samples = CalibrationSamples(
            predicted_values=tuple(predicted),
            reference_values=tuple(reference),
            reference_id=path.name,
            reference_units="meters",
            target_semantics=self._target,
            source_checksum=depth_result.provenance.input_checksum,
        )
        return self._calibrator.calibrate(samples)

    def _dem_anchored(
        self,
        depth_result: DepthResult,
        dem_inspection: DEMInspection,
        target: TargetGrid,
        details: SpatialDetails,
    ) -> CalibrationResult:
        """Fuse the DEM (absolute terrain) with model detail (see calibration.fusion)."""
        from depthwizard.calibration.fusion import dem_anchored_calibration, dem_pixels_in_image
        from depthwizard.geospatial.warp import ResamplingMethod

        terrain = build_terrain_reference(
            dem_inspection, target, resampling=ResamplingMethod.BILINEAR
        )
        k = dem_pixels_in_image(
            _ground_resolution(dem_inspection.crs, dem_inspection.resolution, details),
            _ground_resolution(details.crs, _pixel_size(details), details),
        )
        relative: NDArray[np.float64] = np.asarray(
            depth_result.depth_values, dtype=np.float64
        ).reshape(target.height, target.width)
        result, notes = dem_anchored_calibration(
            relative,
            _depth_valid(depth_result, target.height, target.width),
            np.asarray(terrain.array, dtype=np.float64),
            np.asarray(terrain.valid_mask, dtype=bool),
            k,
            reference_id=self._reference_label or terrain.source_dem_id,
            target=self._target,
            source_checksum=depth_result.provenance.input_checksum,
        )
        self.warnings.extend(notes)
        return result

    @staticmethod
    def _read_gcps(path: str | Path) -> tuple[list[dict[str, float]], str]:
        """Read a GCP CSV: ``pixel_col, pixel_row`` plus ``elevation`` or ``height_agl``.

        Returns the control points and which value column was used. Malformed
        files raise :class:`CalibrationError` naming the problem and row.
        """
        import csv

        try:
            with open(path, newline="", encoding="utf-8-sig") as handle:
                reader = csv.DictReader(handle)
                fields = {name.strip().lower(): name for name in (reader.fieldnames or [])}
                value_columns = [c for c in ("elevation", "height_agl") if c in fields]
                missing = [c for c in ("pixel_col", "pixel_row") if c not in fields]
                if missing or len(value_columns) != 1:
                    raise CalibrationError(
                        "GCP CSV needs columns pixel_col, pixel_row and exactly one of "
                        f"elevation / height_agl; got {sorted(fields)}"
                    )
                column = value_columns[0]
                gcps: list[dict[str, float]] = []
                for line, row in enumerate(reader, start=2):
                    try:
                        gcps.append(
                            {
                                "col": float(row[fields["pixel_col"]]),
                                "row": float(row[fields["pixel_row"]]),
                                "value": float(row[fields[column]]),
                            }
                        )
                    except (TypeError, ValueError) as exc:
                        raise CalibrationError(f"GCP CSV row {line} is not numeric: {exc}") from exc
        except (OSError, UnicodeDecodeError, csv.Error) as exc:
            raise CalibrationError(f"GCP CSV unreadable: {exc}") from exc
        return gcps, column


#: Which GCP value column backs each metric target.
_GCP_COLUMN_FOR_TARGET = {
    ElevationSemantics.ABSOLUTE_ELEVATION_DSM: "elevation",
    ElevationSemantics.HEIGHT_AGL_NDSM: "height_agl",
}
