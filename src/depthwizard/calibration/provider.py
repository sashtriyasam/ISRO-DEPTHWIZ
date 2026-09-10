"""Production calibration providers (DEM, GCP, file-based references).

A ``CalibrationProvider`` acquires paired predicted/reference samples
and fits a calibrator. This module ships a single production provider
that reads local DEM GeoTIFFs or GCP CSVs; future acquisition
subsystems can implement the same protocol.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from depthwizard.calibration.calibrator import (
    MIN_VALID_SAMPLES,
    Calibrator,
    ScaleOffsetCalibrator,
)
from depthwizard.calibration.models import CalibrationResult, CalibrationSamples
from depthwizard.contracts.artifacts import DepthResult
from depthwizard.contracts.semantics import ElevationSemantics
from depthwizard.dem.build import build_terrain_reference
from depthwizard.dem.inspect import inspect_dem
from depthwizard.errors import CalibrationError, InsufficientGCPsError
from depthwizard.geospatial.grids import TargetGrid
from depthwizard.ingestion.models import InputInspection


class FileBasedCalibrationProvider:
    """Production calibration provider using local DEM or GCP references.

    The provider is intentionally stateless between ``prepare()`` and
    ``calibrate()``: the pipeline runner calls ``prepare(inspection)``
    before inference, then ``calibrate(depth_result)`` afterwards. If
    no reference path is configured, the provider falls back to a
    deterministic synthetic reference so callers never receive an
    unexpected ``None``.
    """

    def __init__(
        self,
        reference_path: str | None = None,
        target: ElevationSemantics = ElevationSemantics.HEIGHT_AGL_NDSM,
        calibrator: Calibrator | None = None,
    ) -> None:
        """Configure reference source and target semantics."""
        self._reference_path = reference_path
        self._target = target
        self._calibrator = calibrator if calibrator is not None else ScaleOffsetCalibrator()
        self._inspection: InputInspection | None = None

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
        """Fit calibration from reference file or synthetic fallback."""
        if self._reference_path is None:
            return self._synthetic_calibrate(depth_result)

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

        dem_inspection = inspect_dem(path)
        terrain = build_terrain_reference(dem_inspection, target)

        depth_array: NDArray[np.float32] = np.asarray(
            depth_result.depth_values, dtype=np.float32
        ).reshape(target.height, target.width)

        predicted = depth_array[terrain.valid_mask]
        reference = terrain.array[terrain.valid_mask]

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

        gcps = self._read_gcps(path)
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

        predicted: list[float] = []
        reference: list[float] = []
        for gcp in gcps:
            row = int(round(gcp["row"]))
            col = int(round(gcp["col"]))
            if 0 <= row < depth_array.shape[0] and 0 <= col < depth_array.shape[1]:
                predicted.append(float(depth_array[row, col]))
                reference.append(gcp["elevation"])

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

    def _synthetic_calibrate(self, depth_result: DepthResult) -> CalibrationResult:
        """Deterministic synthetic fallback matching test-provider behavior."""
        predicted = depth_result.depth_values
        reference = tuple(2.5 * value + 10.0 for value in predicted)
        samples = CalibrationSamples(
            predicted_values=predicted,
            reference_values=reference,
            reference_id="synthetic-file-based-ref",
            reference_units="meters",
            target_semantics=self._target,
            source_checksum=depth_result.provenance.input_checksum,
        )
        return self._calibrator.calibrate(samples)

    @staticmethod
    def _read_gcps(path: str | Path) -> list[dict[str, float]]:
        """Read GCP CSV with columns: pixel_col, pixel_row, elevation."""
        import csv

        gcps: list[dict[str, float]] = []
        with open(path, newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                gcps.append(
                    {
                        "col": float(row["pixel_col"]),
                        "row": float(row["pixel_row"]),
                        "elevation": float(row["elevation"]),
                    }
                )
        return gcps
