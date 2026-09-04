import type { SceneArtifact, SceneMetadata, ElevationData, GeoTransform, BoundingBox3D } from "../types/scene";
import type {
  BackendDepthResult,
  BackendSpatialDetails,
  BackendCalibrationResult,
} from "./types";
import { mapSpatialDetails, applyProvenance } from "./spatialMeta";

export interface AdapterError {
  code: string;
  message: string;
  field?: string;
}

export interface AdapterResult {
  success: boolean;
  artifact?: SceneArtifact;
  errors: AdapterError[];
  warnings: string[];
}

function mapGeoreferencingToFrontend(
  georeferencing: BackendDepthResult["georeferencing"]
): "deterministic-fixture" | "backend" {
  switch (georeferencing) {
    case "non_georeferenced":
      return "backend";
    case "georeferenced_no_elevation_reference":
    case "georeferenced_with_dem":
    case "georeferenced_with_gcp":
      return "backend";
    default:
      return "backend";
  }
}

function mapTransform(details: BackendSpatialDetails): GeoTransform | undefined {
  if (!details.transform) return undefined;
  return {
    originX: details.transform.a,
    originY: details.transform.d,
    pixelWidth: details.transform.b,
    pixelHeight: details.transform.e,
    rotation: details.transform.c !== 0 || details.transform.f !== 0 ? undefined : undefined,
  };
}

export const mapBackendTransform = mapTransform;

function mapBounds(details: BackendSpatialDetails): BoundingBox3D | undefined {
  if (!details.bounds) return undefined;
  return {
    minX: details.bounds.min_x,
    minY: details.bounds.min_y,
    minZ: 0,
    maxX: details.bounds.max_x,
    maxY: details.bounds.max_y,
    maxZ: 0,
  };
}

function createElevationFromDepthValues(
  depthValues: number[],
  width: number,
  height: number,
  depthScale: BackendDepthResult["depth_scale"]
): ElevationData {
  const grid = new Float32Array(depthValues.length);
  for (let i = 0; i < depthValues.length; i++) {
    grid[i] = depthValues[i];
  }
  return {
    grid,
    width,
    height,
    cellSize: 1,
    unit: depthScale === "metric" ? "meters" : "relative",
  };
}

function validateBackendResult(result: BackendDepthResult): AdapterError[] {
  const errors: AdapterError[] = [];

  if (!result.model_name || result.model_name.length === 0) {
    errors.push({ code: "MISSING_MODEL_NAME", message: "model_name is required" });
  }

  if (!result.output_resolution) {
    errors.push({ code: "MISSING_OUTPUT_RESOLUTION", message: "output_resolution is required" });
  } else {
    if (result.output_resolution.width <= 0) {
      errors.push({ code: "INVALID_WIDTH", message: "output_resolution.width must be > 0", field: "output_resolution.width" });
    }
    if (result.output_resolution.height <= 0) {
      errors.push({ code: "INVALID_HEIGHT", message: "output_resolution.height must be > 0", field: "output_resolution.height" });
    }
  }

  if (!result.depth_values) {
    errors.push({ code: "MISSING_DEPTH_VALUES", message: "depth_values is required" });
  } else if (result.output_resolution) {
    const expected = result.output_resolution.width * result.output_resolution.height;
    if (result.depth_values.length !== expected) {
      errors.push({
        code: "DEPTH_VALUES_LENGTH_MISMATCH",
        message: `depth_values length ${result.depth_values.length} != expected ${expected}`,
        field: "depth_values",
      });
    }
  }

  if (!result.depth_scale) {
    errors.push({ code: "MISSING_DEPTH_SCALE", message: "depth_scale is required" });
  } else if (result.depth_scale !== "relative" && result.depth_scale !== "metric") {
    errors.push({ code: "INVALID_DEPTH_SCALE", message: `depth_scale must be 'relative' or 'metric', got '${result.depth_scale}'` });
  }

  if (!result.elevation_semantics) {
    errors.push({ code: "MISSING_ELEVATION_SEMANTICS", message: "elevation_semantics is required" });
  }

  if (!result.spatial) {
    errors.push({ code: "MISSING_SPATIAL", message: "spatial context is required" });
  }

  if (result.depth_scale === "metric" && result.units !== "meters") {
    errors.push({ code: "METRIC_UNITS_MISMATCH", message: "METRIC depth_scale requires units='meters'" });
  }

  if (result.depth_scale === "relative" && result.units === "meters") {
    errors.push({ code: "RELATIVE_UNITS_MISMATCH", message: "RELATIVE depth_scale must not claim units='meters'" });
  }

  if (result.confidence_values && result.output_resolution) {
    const expected = result.output_resolution.width * result.output_resolution.height;
    if (result.confidence_values.length !== expected) {
      errors.push({
        code: "CONFIDENCE_VALUES_LENGTH_MISMATCH",
        message: `confidence_values length ${result.confidence_values.length} != expected ${expected}`,
        field: "confidence_values",
      });
    }
  }

  if (result.valid_mask && result.output_resolution) {
    const expected = result.output_resolution.width * result.output_resolution.height;
    if (result.valid_mask.length !== expected) {
      errors.push({
        code: "VALID_MASK_LENGTH_MISMATCH",
        message: `valid_mask length ${result.valid_mask.length} != expected ${expected}`,
        field: "valid_mask",
      });
    }
  }

  return errors;
}

export function adaptBackendResult(result: BackendDepthResult): AdapterResult {
  const warnings: string[] = [];
  const errors = validateBackendResult(result);

  if (errors.length > 0) {
    return { success: false, errors, warnings };
  }

  const width = result.output_resolution.width;
  const height = result.output_resolution.height;

  const elevation = createElevationFromDepthValues(result.depth_values, width, height, result.depth_scale);

  const spatialDetails = result.spatial.kind === "present" ? result.spatial.details : undefined;
  const transform = spatialDetails ? mapTransform(spatialDetails) : undefined;
  const bounds = spatialDetails ? mapBounds(spatialDetails) : undefined;
  const crs = spatialDetails?.crs ?? undefined;

  const source = mapGeoreferencingToFrontend(result.georeferencing);

  const backend: SceneMetadata["backend"] = {
    model_name: result.model_name,
    depth_scale: result.depth_scale,
    elevation_semantics: result.elevation_semantics,
    georeferencing: result.georeferencing,
  };
  if (result.model_version) backend.model_version = result.model_version;
  applyProvenance(backend, result.provenance);

  const metadata: SceneArtifact["metadata"] = {
    source,
    units: {
      spatial: "meters",
      elevation: "meters",
    },
    backend,
  };

  if (crs) metadata.CRS = crs;
  if (transform) metadata.transform = transform;
  if (bounds) metadata.bounds = bounds;
  const extraSpatial = spatialDetails ? mapSpatialDetails(spatialDetails) : undefined;
  if (extraSpatial) metadata.spatialDetails = extraSpatial;

  if (result.depth_scale === "relative") {
    warnings.push("Depth values are RELATIVE — not calibrated to metres");
  }

  if (result.elevation_semantics === "relative_depth") {
    warnings.push("Elevation semantics are relative_depth — not absolute elevation");
  }

  const artifact: SceneArtifact = {
    id: `backend-${result.model_name}`,
    label: `${result.model_name}${result.model_version ? ` v${result.model_version}` : ""}`,
    mesh: {
      vertices: new Float32Array(0),
      indices: new Uint32Array(0),
      vertexCount: 0,
      indexCount: 0,
    },
    elevation,
    metadata,
  };

  return { success: true, artifact, errors: [], warnings };
}

export function adaptCalibratedResult(
  result: BackendDepthResult,
  calibration: BackendCalibrationResult
): AdapterResult {
  const warnings: string[] = [];
  const errors = validateBackendResult(result);

  if (errors.length > 0) {
    return { success: false, errors, warnings };
  }

  const width = result.output_resolution.width;
  const height = result.output_resolution.height;

  const calibratedValues = new Float32Array(result.depth_values.length);
  for (let i = 0; i < result.depth_values.length; i++) {
    calibratedValues[i] = calibration.scale * result.depth_values[i] + calibration.offset;
  }

  const elevation: ElevationData = {
    grid: calibratedValues,
    width,
    height,
    cellSize: 1,
    unit: result.depth_scale === "metric" ? "meters" : "relative",
  };

  const spatialDetails = result.spatial.kind === "present" ? result.spatial.details : undefined;
  const transform = spatialDetails ? mapTransform(spatialDetails) : undefined;
  const bounds = spatialDetails ? mapBounds(spatialDetails) : undefined;
  const crs = spatialDetails?.crs ?? undefined;

  const backend: SceneMetadata["backend"] = {
    model_name: result.model_name,
    depth_scale: result.depth_scale,
    elevation_semantics: result.elevation_semantics,
    georeferencing: result.georeferencing,
    calibration_method: calibration.method,
    calibration_reference: calibration.reference_id,
    calibration_scale: calibration.scale,
    calibration_offset: calibration.offset,
  };
  if (result.model_version) backend.model_version = result.model_version;
  applyProvenance(backend, result.provenance);

  const metadata: SceneArtifact["metadata"] = {
    source: "backend",
    units: {
      spatial: "meters",
      elevation: "meters",
    },
    backend,
  };

  if (crs) metadata.CRS = crs;
  if (transform) metadata.transform = transform;
  if (bounds) metadata.bounds = bounds;
  const extraSpatial = spatialDetails ? mapSpatialDetails(spatialDetails) : undefined;
  if (extraSpatial) metadata.spatialDetails = extraSpatial;

  warnings.push(`Calibrated via ${calibration.method}: scale=${calibration.scale}, offset=${calibration.offset}`);
  warnings.push(`Calibration RMSE: ${calibration.rmse}, R²: ${calibration.r_squared}`);

  const artifact: SceneArtifact = {
    id: `backend-${result.model_name}-calibrated`,
    label: `${result.model_name} (calibrated)`,
    mesh: {
      vertices: new Float32Array(0),
      indices: new Uint32Array(0),
      vertexCount: 0,
      indexCount: 0,
    },
    elevation,
    metadata,
  };

  return { success: true, artifact, errors: [], warnings };
}
