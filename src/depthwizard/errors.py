"""Backend/scientific error taxonomy (foundation only).

Each error carries a stable machine-readable ``code`` so future
API/UI layers can propagate categories without parsing messages.
No subsystem operations are implemented here.
"""


class DepthWizardError(Exception):
    """Base class for all DepthWizard backend errors."""

    code = "depthwizard_error"


class InvalidInputError(DepthWizardError):
    """Input fails validation (bad shape, empty file, corrupt header, ...)."""

    code = "invalid_input"


class MissingCRSError(DepthWizardError):
    """Operation required a CRS but none was available."""

    code = "missing_crs"


class MissingElevationReferenceError(DepthWizardError):
    """No trustworthy elevation reference (DEM/GCP) for the requested product."""

    code = "missing_elevation_reference"


class DemMismatchError(DepthWizardError):
    """DEM does not cover/align with the input (extent, resolution, CRS)."""

    code = "dem_mismatch"


class InsufficientGCPsError(DepthWizardError):
    """Too few or poorly distributed ground control points for fitting."""

    code = "insufficient_gcps"


class UnsupportedFormatError(DepthWizardError):
    """Input/output format is not supported by the engine."""

    code = "unsupported_format"


class ModelInferenceError(DepthWizardError):
    """Depth backend failed during inference (checkpoint, runtime, OOM, ...)."""

    code = "model_inference_failure"


class CalibrationError(DepthWizardError):
    """Relative-to-metric calibration failed."""

    code = "calibration_failure"


class MeshGenerationError(DepthWizardError):
    """Mesh extraction/triangulation failed."""

    code = "mesh_generation_failure"


class ExportError(DepthWizardError):
    """Product export/serialization failed."""

    code = "export_failure"


class PipelineExecutionError(DepthWizardError):
    """Pipeline orchestration contract violated (reuse, illegal transition).

    Stage work failures are reported as data in PipelineResult, not via
    this error; it covers runner misuse and state-machine violations.
    """

    code = "pipeline_execution_failure"
