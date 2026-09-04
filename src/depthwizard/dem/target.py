"""Target-grid derivation for DEM alignment (explicit, no guessing).

Builds an S7 ``TargetGrid`` from an already-validated georeferenced
``InputInspection``. Non-georeferenced or transform-less inputs are
refused — a PNG/JPEG stays valid DepthWizard input but can never
request georeferenced DEM alignment, and no georeferencing is
invented for it.
"""

from __future__ import annotations

from depthwizard.contracts.semantics import GeoreferencingLevel
from depthwizard.contracts.spatial import SpatialKind
from depthwizard.errors import GeospatialProcessingError, MissingCRSError
from depthwizard.geospatial.grids import TargetGrid
from depthwizard.ingestion.models import InputInspection


def target_grid_from_inspection(
    inspection: InputInspection,
    *,
    dtype: str = "float32",
    nodata: float = float("nan"),
) -> TargetGrid:
    """Derive an explicit DEM-alignment target from image metadata.

    CRS, transform, dimensions and resolution come from the validated
    inspection; ``dtype``/``nodata`` describe the terrain-float target
    (defaults suit elevation work). Nothing is guessed: missing CRS,
    transform or georeferencing fails explicitly.
    """
    if not isinstance(inspection, InputInspection):
        raise TypeError(
            "target_grid_from_inspection requires an InputInspection; "
            f"got {type(inspection).__name__}"
        )
    if inspection.georeferencing is GeoreferencingLevel.NON_GEOREFERENCED:
        raise MissingCRSError(
            "DEM alignment requires a georeferenced image, but "
            f"{inspection.handle.display_name} is non-georeferenced "
            "(it remains valid DepthWizard input otherwise)"
        )
    details = inspection.spatial.details if inspection.spatial.kind is SpatialKind.PRESENT else None
    if details is None or details.crs is None:
        raise MissingCRSError(
            "DEM alignment requires image CRS metadata, none available for "
            f"{inspection.handle.display_name}"
        )
    if details.transform is None:
        raise GeospatialProcessingError(
            "DEM alignment requires an image affine transform, none available for "
            f"{inspection.handle.display_name}"
        )
    raster_width = details.raster_width or inspection.width
    raster_height = details.raster_height or inspection.height
    return TargetGrid(
        crs=details.crs,
        transform=details.transform,
        width=raster_width,
        height=raster_height,
        dtype=dtype,
        nodata=nodata,
        resolution=details.resolution_gsd,
    )
