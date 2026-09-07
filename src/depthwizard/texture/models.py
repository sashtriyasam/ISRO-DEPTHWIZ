"""RGB texture projection contract (mapping, not rendering).

``TextureProjection`` records that a source optical image maps onto a
generated mesh: source identity, pixel dimensions, colour
interpretation, UV coverage and preserved georeferencing.  It never
alters mesh scientific coordinates — texturing is a mapping claim,
and display conversion belongs to the renderer.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from depthwizard.contracts.provenance import ProductProvenance
from depthwizard.contracts.semantics import GeoreferencingLevel
from depthwizard.contracts.spatial import SpatialContext, SpatialKind
from depthwizard.errors import InvalidInputError
from depthwizard.mesh.models import TerrainMesh


class ColourInterpretation(str, Enum):
    """Source colour layouts actually supported (no placeholders)."""

    RGB_UINT8 = "rgb_uint8"


class TextureProjection(BaseModel):
    """Validated mapping between a source image and a terrain mesh."""

    model_config = ConfigDict(frozen=True)

    source_input_id: str = Field(min_length=1)
    source_checksum: str | None = None
    image_width: int = Field(gt=0)
    image_height: int = Field(gt=0)
    colour: ColourInterpretation
    mesh_width: int = Field(gt=0, description="Mesh source raster width (must match image).")
    mesh_height: int = Field(gt=0, description="Mesh source raster height (must match image).")
    uv_coverage: float = Field(
        ge=0.0, le=1.0, description="Share of mesh vertices carrying valid UVs."
    )
    georeferencing: GeoreferencingLevel = Field(description="Preserved, never upgraded.")
    spatial: SpatialContext = Field(description="Preserved mesh spatial context.")
    depth_model_name: str = Field(min_length=1)
    source_mesh_checksum: str | None = Field(
        default=None, description="Checksum of the mesh product, when known."
    )
    provenance: ProductProvenance = Field(description="Reused mesh provenance.")

    @model_validator(mode="after")
    def _check_projection_honesty(self) -> TextureProjection:
        if (self.image_width, self.image_height) != (self.mesh_width, self.mesh_height):
            raise ValueError(
                f"image dimensions ({self.image_width}x{self.image_height}) must match "
                f"mesh source dimensions ({self.mesh_width}x{self.mesh_height})"
            )
        if self.georeferencing is GeoreferencingLevel.NON_GEOREFERENCED:
            if self.spatial.kind is SpatialKind.PRESENT:
                raise ValueError("NON_GEOREFERENCED projection must not carry PRESENT details")
        return self


def project_texture(
    mesh: TerrainMesh,
    source_input_id: str,
    image_width: int,
    image_height: int,
    colour: ColourInterpretation,
    source_checksum: str | None = None,
) -> TextureProjection:
    """Bind a source image to a mesh as a validated texture mapping.

    Verifies dimension agreement, UV validity and georeferencing
    preservation.  The mesh is never mutated.  Colour interpretation
    is declared explicitly by the caller — never inferred.
    """
    if not isinstance(mesh, TerrainMesh):
        raise InvalidInputError(
            f"project_texture requires a TerrainMesh, got {type(mesh).__name__}"
        )
    if not isinstance(source_input_id, str) or not source_input_id.strip():
        raise InvalidInputError("source_input_id must be a non-empty string")
    if not isinstance(colour, ColourInterpretation):
        raise InvalidInputError(f"colour must be an explicit ColourInterpretation; got {colour!r}")
    if image_width <= 0 or image_height <= 0:
        raise InvalidInputError("image dimensions must be positive")

    import numpy as np

    uvs = np.asarray(mesh.uvs)
    finite = bool(np.isfinite(uvs).all())
    in_range = bool(((uvs >= 0.0) & (uvs <= 1.0)).all())
    if not (finite and in_range):
        raise InvalidInputError("mesh UVs must be finite values in [0, 1]")
    coverage = float(uvs.shape[0] / mesh.vertex_count) if mesh.vertex_count else 0.0

    return TextureProjection(
        source_input_id=source_input_id,
        source_checksum=source_checksum,
        image_width=image_width,
        image_height=image_height,
        colour=colour,
        mesh_width=mesh.width,
        mesh_height=mesh.height,
        uv_coverage=coverage,
        georeferencing=mesh.georeferencing,
        spatial=mesh.spatial,
        depth_model_name=mesh.depth_model_name,
        source_mesh_checksum=mesh.source_checksum,
        provenance=mesh.provenance,
    )
