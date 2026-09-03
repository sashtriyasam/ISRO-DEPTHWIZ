import type {
  SceneArtifact,
  SceneMetadata,
  ElevationData,
  BoundingBox3D,
} from "../types/scene";
import type {
  BackendTerrainProduct,
  BackendTerrainMeshTransport,
  BackendDsmTransport,
  BackendSpatialDetails,
} from "./types";
import type { AdapterError } from "./adapter";
import { mapBackendTransform } from "./adapter";

export interface MeshAdapterResult {
  success: boolean;
  artifact?: SceneArtifact;
  errors: AdapterError[];
  warnings: string[];
}

const METRIC_SEMANTICS = new Set([
  "height_agl_ndsm",
  "absolute_elevation_dsm",
]);

function isFiniteNumber(v: unknown): v is number {
  return typeof v === "number" && Number.isFinite(v);
}

function validateDsm(dsm: BackendTerrainProduct["dsm"]): AdapterError[] {
  const errors: AdapterError[] = [];
  if (!dsm || typeof dsm !== "object") {
    return [{ code: "MISSING_DSM", message: "terrain product requires a dsm section" }];
  }
  if (!Number.isInteger(dsm.width) || dsm.width <= 0) {
    errors.push({ code: "INVALID_DSM_WIDTH", message: "dsm.width must be a positive integer", field: "dsm.width" });
  }
  if (!Number.isInteger(dsm.height) || dsm.height <= 0) {
    errors.push({ code: "INVALID_DSM_HEIGHT", message: "dsm.height must be a positive integer", field: "dsm.height" });
  }
  const expected = dsm.width * dsm.height;
  if (!Array.isArray(dsm.values)) {
    errors.push({ code: "MISSING_DSM_VALUES", message: "dsm.values is required", field: "dsm.values" });
  } else if (dsm.values.length !== expected) {
    errors.push({
      code: "DSM_VALUES_LENGTH_MISMATCH",
      message: `dsm.values length ${dsm.values.length} != expected ${expected}`,
      field: "dsm.values",
    });
  } else {
    for (let i = 0; i < dsm.values.length; i++) {
      const v = dsm.values[i];
      if (v !== null && !isFiniteNumber(v)) {
        errors.push({ code: "INVALID_DSM_VALUE", message: `dsm.values[${i}] must be finite or null`, field: "dsm.values" });
        break;
      }
    }
  }
  if (!Array.isArray(dsm.valid_mask)) {
    errors.push({ code: "MISSING_DSM_MASK", message: "dsm.valid_mask is required", field: "dsm.valid_mask" });
  } else if (dsm.valid_mask.length !== expected) {
    errors.push({
      code: "DSM_MASK_LENGTH_MISMATCH",
      message: `dsm.valid_mask length ${dsm.valid_mask.length} != expected ${expected}`,
      field: "dsm.valid_mask",
    });
  }
  if (dsm.units !== "meters") {
    errors.push({ code: "DSM_UNITS_MISMATCH", message: "backend DSM must declare units='meters'", field: "dsm.units" });
  }
  if (!METRIC_SEMANTICS.has(dsm.semantics)) {
    errors.push({
      code: "DSM_SEMANTICS_MISMATCH",
      message: `backend DSM requires a metric meaning, got '${dsm.semantics}'`,
      field: "dsm.semantics",
    });
  }
  return errors;
}

function validateMesh(mesh: BackendTerrainMeshTransport, dsm: BackendDsmTransport): AdapterError[] {
  const errors: AdapterError[] = [];
  if (!mesh || typeof mesh !== "object") {
    return [{ code: "MISSING_MESH", message: "terrain product requires a mesh section" }];
  }
  if (!Number.isInteger(mesh.vertex_count) || mesh.vertex_count <= 0) {
    errors.push({ code: "INVALID_VERTEX_COUNT", message: "mesh.vertex_count must be a positive integer", field: "mesh.vertex_count" });
  }
  if (!Number.isInteger(mesh.triangle_count) || mesh.triangle_count <= 0) {
    errors.push({ code: "INVALID_TRIANGLE_COUNT", message: "mesh.triangle_count must be a positive integer", field: "mesh.triangle_count" });
  }
  if (!Array.isArray(mesh.vertices) || mesh.vertices.length !== 3 * mesh.vertex_count) {
    errors.push({
      code: "MESH_VERTICES_LENGTH_MISMATCH",
      message: `mesh.vertices length must equal 3 * vertex_count (${3 * mesh.vertex_count})`,
      field: "mesh.vertices",
    });
  } else if (!mesh.vertices.every(isFiniteNumber)) {
    errors.push({ code: "INVALID_MESH_VERTICES", message: "mesh.vertices must all be finite", field: "mesh.vertices" });
  }
  if (!Array.isArray(mesh.normals) || mesh.normals.length !== 3 * mesh.vertex_count) {
    errors.push({
      code: "MESH_NORMALS_LENGTH_MISMATCH",
      message: `mesh.normals length must equal 3 * vertex_count (${3 * mesh.vertex_count})`,
      field: "mesh.normals",
    });
  } else if (!mesh.normals.every(isFiniteNumber)) {
    errors.push({ code: "INVALID_MESH_NORMALS", message: "mesh.normals must all be finite", field: "mesh.normals" });
  }
  if (!Array.isArray(mesh.uvs) || mesh.uvs.length !== 2 * mesh.vertex_count) {
    errors.push({
      code: "MESH_UVS_LENGTH_MISMATCH",
      message: `mesh.uvs length must equal 2 * vertex_count (${2 * mesh.vertex_count})`,
      field: "mesh.uvs",
    });
  } else if (!mesh.uvs.every((v) => isFiniteNumber(v) && v >= 0 && v <= 1)) {
    errors.push({ code: "INVALID_MESH_UVS", message: "mesh.uvs must lie in [0, 1]", field: "mesh.uvs" });
  }
  if (!Array.isArray(mesh.indices) || mesh.indices.length !== 3 * mesh.triangle_count) {
    errors.push({
      code: "MESH_INDICES_LENGTH_MISMATCH",
      message: `mesh.indices length must equal 3 * triangle_count (${3 * mesh.triangle_count})`,
      field: "mesh.indices",
    });
  } else if (!mesh.indices.every((v) => Number.isInteger(v) && v >= 0 && v < mesh.vertex_count)) {
    errors.push({ code: "INVALID_MESH_INDICES", message: "mesh.indices must lie in [0, vertex_count)", field: "mesh.indices" });
  }
  if (!Array.isArray(mesh.vertex_source_indices) || mesh.vertex_source_indices.length !== mesh.vertex_count) {
    errors.push({
      code: "MESH_SOURCE_INDICES_LENGTH_MISMATCH",
      message: "mesh.vertex_source_indices must map every vertex to a pixel",
      field: "mesh.vertex_source_indices",
    });
  }
  if (mesh.units !== "meters") {
    errors.push({ code: "MESH_UNITS_MISMATCH", message: "backend mesh must declare units='meters'", field: "mesh.units" });
  }
  if (!METRIC_SEMANTICS.has(mesh.semantics)) {
    errors.push({
      code: "MESH_SEMANTICS_MISMATCH",
      message: `backend mesh requires a metric meaning, got '${mesh.semantics}'`,
      field: "mesh.semantics",
    });
  }
  if (mesh.frame !== "georeferenced_local" && mesh.frame !== "local") {
    errors.push({ code: "INVALID_MESH_FRAME", message: `mesh.frame must be a known frame, got '${mesh.frame}'`, field: "mesh.frame" });
  }
  if ((mesh.origin_x === null) !== (mesh.origin_y === null)) {
    errors.push({ code: "INVALID_MESH_ORIGIN", message: "mesh origin must be fully set or fully absent", field: "mesh.origin" });
  }
  if (mesh.frame === "georeferenced_local" && mesh.origin_x === null) {
    errors.push({ code: "MISSING_MESH_ORIGIN", message: "georeferenced-local mesh requires a stored origin", field: "mesh.origin" });
  }
  if (!isFiniteNumber(mesh.coverage) || mesh.coverage < 0 || mesh.coverage > 1) {
    errors.push({ code: "INVALID_MESH_COVERAGE", message: "mesh.coverage must lie in [0, 1]", field: "mesh.coverage" });
  }
  if (mesh.width !== dsm.width || mesh.height !== dsm.height) {
    errors.push({ code: "MESH_DSM_DIMENSION_MISMATCH", message: "mesh dimensions must match dsm dimensions", field: "mesh.dimensions" });
  }
  if (mesh.semantics !== dsm.semantics) {
    errors.push({ code: "MESH_DSM_SEMANTICS_MISMATCH", message: "mesh semantics must match dsm semantics", field: "mesh.semantics" });
  }
  return errors;
}

function computeBounds(vertices: number[]): BoundingBox3D {
  let minX = Infinity;
  let minY = Infinity;
  let minZ = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  let maxZ = -Infinity;
  for (let i = 0; i < vertices.length; i += 3) {
    const x = vertices[i];
    const y = vertices[i + 1];
    const z = vertices[i + 2];
    if (x < minX) minX = x;
    if (y < minY) minY = y;
    if (z < minZ) minZ = z;
    if (x > maxX) maxX = x;
    if (y > maxY) maxY = y;
    if (z > maxZ) maxZ = z;
  }
  return { minX, minY, minZ, maxX, maxY, maxZ };
}

export function validateTerrainProduct(product: BackendTerrainProduct): AdapterError[] {
  if (!product || typeof product !== "object") {
    return [{ code: "INVALID_TERRAIN_PRODUCT", message: "terrain product must be an object" }];
  }
  if (product.kind !== "terrain") {
    return [{ code: "INVALID_TERRAIN_KIND", message: `terrain product kind must be 'terrain', got '${(product as { kind?: unknown }).kind}'` }];
  }
  const errors = validateDsm(product.dsm);
  errors.push(...validateMesh(product.mesh, product.dsm));
  return errors;
}

export function adaptTerrainProduct(product: BackendTerrainProduct): MeshAdapterResult {
  const warnings: string[] = [];
  const errors = validateTerrainProduct(product);
  if (errors.length > 0) {
    return { success: false, errors, warnings };
  }

  const { dsm, mesh, depth_result } = product;

  const grid = new Float32Array(dsm.values.length);
  for (let i = 0; i < dsm.values.length; i++) {
    const v = dsm.values[i];
    grid[i] = v === null ? NaN : v;
  }
  const elevation: ElevationData = {
    grid,
    width: dsm.width,
    height: dsm.height,
    cellSize: 1,
    unit: "meters",
    ...(dsm.invalid_count > 0 ? { noDataValue: NaN } : {}),
  };

  // Backend TerrainMesh vertices are [x, elevation, z] with Y as the
  // vertical axis — identical to the frontend convention (X/Z
  // horizontal, Y vertical). No axis conversion is performed; values
  // are copied verbatim into renderer-ready typed arrays.
  const vertices = new Float32Array(mesh.vertices);
  const normals = new Float32Array(mesh.normals);
  const uvs = new Float32Array(mesh.uvs);
  const indices = new Uint32Array(mesh.indices);

  const bounds = computeBounds(mesh.vertices);

  const spatialDetails: BackendSpatialDetails | undefined =
    mesh.spatial.kind === "present" ? mesh.spatial.details ?? undefined : undefined;
  const transform = spatialDetails ? mapBackendTransform(spatialDetails) : undefined;
  const crs = spatialDetails?.crs ?? undefined;

  const backend: SceneMetadata["backend"] = {
    model_name: mesh.depth_model_name,
    depth_scale: "metric",
    elevation_semantics: mesh.semantics,
    georeferencing: mesh.georeferencing,
    calibration_method: mesh.calibration_method,
    calibration_reference: mesh.calibration_reference,
  };
  if (mesh.depth_model_version) backend.model_version = mesh.depth_model_version;

  const metadata: SceneMetadata = {
    source: "backend",
    units: { spatial: "meters", elevation: "meters" },
    backend,
    bounds,
  };
  if (crs) metadata.CRS = crs;
  if (transform) metadata.transform = transform;

  warnings.push(
    `Backend terrain mesh: ${mesh.vertex_count} vertices, ${mesh.triangle_count} triangles (frame: ${mesh.frame})`
  );
  warnings.push(
    `Calibrated via ${mesh.calibration_method}: scale=${mesh.calibration_scale}, offset=${mesh.calibration_offset} (reference: ${mesh.calibration_reference})`
  );
  if (dsm.invalid_count > 0) {
    warnings.push(`${dsm.invalid_count} DSM pixels are nodata (holes are never bridged)`);
  }

  const artifact: SceneArtifact = {
    id: `backend-${mesh.depth_model_name}-terrain`,
    label: `${mesh.depth_model_name} terrain${mesh.depth_model_version ? ` v${mesh.depth_model_version}` : ""}`,
    mesh: {
      vertices,
      indices,
      normals,
      uvs,
      vertexCount: mesh.vertex_count,
      indexCount: mesh.indices.length,
    },
    elevation,
    metadata,
  };

  void depth_result;

  return { success: true, artifact, errors: [], warnings };
}
