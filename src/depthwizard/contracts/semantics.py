"""Scientific semantics: explicit enums, no free-form strings.

These enums prevent future model implementations from leaking
model-specific assumptions (e.g. claiming metric units for
scale-ambiguous output) into the rest of the system.
"""

from enum import Enum


class GeoreferencingLevel(str, Enum):
    """How an input/product is positioned on the Earth (if at all)."""

    NON_GEOREFERENCED = "non_georeferenced"
    GEOREFERENCED_NO_ELEVATION_REFERENCE = "georeferenced_no_elevation_reference"
    GEOREFERENCED_WITH_DEM = "georeferenced_with_dem"
    GEOREFERENCED_WITH_GCP = "georeferenced_with_gcp"


class DepthScale(str, Enum):
    """Scale semantics of a depth estimate.

    RELATIVE: scale-ambiguous (e.g. raw monocular network output).
    METRIC: calibrated to metres. Must never be claimed without
    a calibration reference recorded in provenance.
    """

    RELATIVE = "relative"
    METRIC = "metric"


class ElevationSemantics(str, Enum):
    """What the height-like values in a product actually mean."""

    RELATIVE_DEPTH = "relative_depth"
    RELATIVE_SURFACE_RDSM = "relative_surface_rdsm"
    HEIGHT_AGL_NDSM = "height_agl_ndsm"
    ABSOLUTE_ELEVATION_DSM = "absolute_elevation_dsm"
    # Ground/terrain elevation reference (DEM). Not a surface model:
    # never interchangeable with DSM/AGL meanings without an explicit
    # scientifically valid surface relationship (see S8 docs).
    TERRAIN_ELEVATION = "terrain_elevation"
