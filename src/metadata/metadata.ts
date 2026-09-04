import type { SceneArtifact, SceneMetadata } from "../types/scene";
import type { LayerId } from "../layers/types";

export const NOT_AVAILABLE = "Not available";

export interface MetadataRow {
  label: string;
  value: string;
  title?: string;
}

export interface MetadataSection {
  id: "product" | "spatial" | "calibration" | "provenance" | "input";
  title: string;
  rows: MetadataRow[];
}

export function semanticLabel(semantics: string | undefined): string {
  switch (semantics) {
    case "absolute_elevation_dsm":
      return "Absolute elevation (DSM)";
    case "height_agl_ndsm":
      return "Height above ground (AGL)";
    case "relative_surface_rdsm":
      return "Relative surface (rDSM)";
    case "relative_depth":
      return "Relative depth";
    case undefined:
      return NOT_AVAILABLE;
    default:
      return semantics;
  }
}

export function unitLabel(unit: string | undefined | null): string {
  if (unit === undefined || unit === null || unit === "") {
    return NOT_AVAILABLE;
  }
  return unit;
}

export function georeferencingLabel(value: string | undefined): string {
  switch (value) {
    case "non_georeferenced":
      return "Non-georeferenced";
    case "georeferenced_no_elevation_reference":
      return "Georeferenced (no elevation reference)";
    case "georeferenced_with_dem":
      return "Georeferenced (DEM)";
    case "georeferenced_with_gcp":
      return "Georeferenced (GCP)";
    case undefined:
      return NOT_AVAILABLE;
    default:
      return value;
  }
}

export function sourceStatusLabel(metadata: SceneMetadata): string {
  if (metadata.source === "deterministic-fixture") {
    return "Development fixture";
  }
  const model = metadata.backend?.model_name;
  if (model === "synthetic-depth") {
    return "Synthetic Development Backend";
  }
  return model ? `Backend model (${model})` : "Backend";
}

export function formatScalar(value: number | undefined | null): string {
  if (value === undefined || value === null) {
    return NOT_AVAILABLE;
  }
  if (Number.isNaN(value)) {
    return "NaN (nodata marker)";
  }
  return String(value);
}

export function formatChecksum(checksum: string | undefined | null): { short: string; full?: string } {
  if (!checksum) {
    return { short: NOT_AVAILABLE };
  }
  if (checksum.length <= 16) {
    return { short: checksum };
  }
  return { short: `${checksum.slice(0, 12)}…`, full: checksum };
}

export function formatAffine(affine: [number, number, number, number, number, number]): string {
  const [a, b, c, d, e, f] = affine;
  return `${a}, ${b}, ${c} / ${d}, ${e}, ${f}`;
}

export interface ActiveGrid {
  kindLabel: string;
  width: number;
  height: number;
  unit: string;
}

export function activeGrid(artifact: SceneArtifact, layerId: LayerId): ActiveGrid | null {
  if (layerId === "rdsm" || layerId === "agl") {
    const payload = layerId === "rdsm" ? artifact.layers?.rdsm : artifact.layers?.agl;
    if (!payload) {
      return null;
    }
    return {
      kindLabel: layerId === "rdsm" ? "Relative surface (rDSM)" : "Height above ground (AGL)",
      width: payload.width,
      height: payload.height,
      unit: payload.unit,
    };
  }
  if (!artifact.elevation) {
    return null;
  }
  return {
    kindLabel: semanticLabel(artifact.metadata.backend?.elevation_semantics),
    width: artifact.elevation.width,
    height: artifact.elevation.height,
    unit: artifact.elevation.unit,
  };
}

function row(label: string, value: string, title?: string): MetadataRow {
  return title ? { label, value, title } : { label, value };
}

export function describeArtifact(
  artifact: SceneArtifact,
  activeLayerId: LayerId
): MetadataSection[] {
  const metadata = artifact.metadata;
  const backend = metadata.backend;
  const spatial = metadata.spatialDetails;
  const sections: MetadataSection[] = [];

  const grid = activeGrid(artifact, activeLayerId);
  const productRows: MetadataRow[] = [
    row("Product", grid ? grid.kindLabel : semanticLabel(backend?.elevation_semantics)),
    row("Scale", backend ? backend.depth_scale : NOT_AVAILABLE),
    row("Units", grid ? unitLabel(grid.unit) : NOT_AVAILABLE),
    row("Artifact", artifact.id, artifact.id),
  ];
  if (grid) {
    productRows.push(row("Grid", `${grid.width}×${grid.height} (${unitLabel(grid.unit)})`));
  }
  sections.push({ id: "product", title: "Product", rows: productRows });

  const spatialRows: MetadataRow[] = [
    row("CRS", metadata.CRS ?? NOT_AVAILABLE, metadata.CRS),
    row("Reference", georeferencingLabel(backend?.georeferencing)),
    row("GSD", formatScalar(spatial?.gsd)),
  ];
  if (spatial?.rasterWidth !== undefined && spatial?.rasterHeight !== undefined) {
    spatialRows.push(row("Raster", `${spatial.rasterWidth}×${spatial.rasterHeight}`));
  }
  spatialRows.push(row("Nodata", formatScalar(spatial?.nodata)));
  if (spatial?.affine) {
    spatialRows.push(
      row("Affine", formatAffine(spatial.affine), "Backend affine (GDAL order): x = a + b·col + c·row; y = d + e·col + f·row")
    );
  } else if (metadata.transform) {
    const t = metadata.transform;
    spatialRows.push(
      row(
        "Grid transform",
        `origin (${t.originX}, ${t.originY}), pixel ${t.pixelWidth}×${t.pixelHeight}`,
        "Display grid transform derived from backend metadata"
      )
    );
  } else {
    spatialRows.push(row("Transform", NOT_AVAILABLE));
  }
  if (spatial?.spatialBounds) {
    const b = spatial.spatialBounds;
    spatialRows.push(row("Spatial bounds", `X [${b.minX}, ${b.maxX}] Y [${b.minY}, ${b.maxY}]`));
  }
  if (metadata.bounds) {
    const b = metadata.bounds;
    spatialRows.push(
      row(
        "Display bounds",
        `X [${b.minX}, ${b.maxX}] Y [${b.minY}, ${b.maxY}] Z [${b.minZ}, ${b.maxZ}]`,
        "Three.js scene coordinates, not spatial coordinates"
      )
    );
  }
  sections.push({ id: "spatial", title: "Spatial", rows: spatialRows });

  if (
    backend &&
    (backend.calibration_method !== undefined ||
      backend.calibration_reference !== undefined ||
      backend.calibration_scale !== undefined ||
      backend.calibration_offset !== undefined)
  ) {
    sections.push({
      id: "calibration",
      title: "Calibration",
      rows: [
        row("Method", backend.calibration_method ?? NOT_AVAILABLE),
        row("Reference", backend.calibration_reference ?? NOT_AVAILABLE),
        row("Scale", formatScalar(backend.calibration_scale)),
        row("Offset", formatScalar(backend.calibration_offset)),
      ],
    });
  }

  const provenanceRows: MetadataRow[] = [
    row(
      "Backend",
      backend
        ? `${backend.model_name}${backend.model_version ? ` ${backend.model_version}` : ""}`
        : NOT_AVAILABLE
    ),
    row("Source", sourceStatusLabel(metadata)),
  ];
  if (backend?.software_version) {
    provenanceRows.push(row("Software", backend.software_version));
  }
  if (backend?.semantic_meaning) {
    provenanceRows.push(row("Meaning", backend.semantic_meaning));
  }
  sections.push({ id: "provenance", title: "Provenance", rows: provenanceRows });

  const checksum = formatChecksum(backend?.input_checksum);
  sections.push({
    id: "input",
    title: "Input",
    rows: [
      row("File", backend?.input_id ?? artifact.label, backend?.input_id),
      row("Checksum", checksum.short, checksum.full),
    ],
  });

  return sections;
}
