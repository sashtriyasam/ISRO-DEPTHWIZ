import { describe, it, expect } from "vitest";
import { adaptTerrainProduct, validateTerrainProduct } from "./meshAdapter";
import type { BackendTerrainProduct } from "./types";
import { createLayerState } from "../layers/LayerRegistry";
import { applyHeightExaggeration } from "../display/types";

function makeTerrainTransport(): BackendTerrainProduct {
  return {
    kind: "terrain",
    depth_result: {
      model_name: "synthetic-depth",
      model_version: "0.1.0",
      checkpoint_id: null,
      input_resolution: { width: 2, height: 2 },
      output_resolution: { width: 2, height: 2 },
      depth_scale: "relative",
      elevation_semantics: "relative_depth",
      georeferencing: "non_georeferenced",
      depth_values: [0.1, 0.2, 0.3, 0.4],
      spatial: { kind: "not_applicable" },
    },
    dsm: {
      width: 2,
      height: 2,
      dtype: "float32",
      units: "meters",
      semantics: "absolute_elevation_dsm",
      values: [10, 11, 12, 13],
      valid_mask: [true, true, true, true],
      invalid_count: 0,
      nodata: null,
      georeferencing: "non_georeferenced",
      spatial: { kind: "not_applicable" },
    },
    mesh: {
      vertices: [0, 10, 0, 1, 11, 0, 0, 12, 1, 1, 13, 1],
      indices: [0, 2, 1, 1, 2, 3],
      normals: [0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0],
      uvs: [0, 0, 1, 0, 0, 1, 1, 1],
      vertex_source_indices: [0, 1, 2, 3],
      vertex_count: 4,
      triangle_count: 2,
      valid_source_pixels: 4,
      invalid_source_pixels: 0,
      skipped_cells: 0,
      coverage: 1.0,
      frame: "local",
      origin_x: null,
      origin_y: null,
      width: 2,
      height: 2,
      units: "meters",
      semantics: "absolute_elevation_dsm",
      georeferencing: "non_georeferenced",
      spatial: { kind: "not_applicable" },
      depth_model_name: "synthetic-depth",
      depth_model_version: "0.1.0",
      depth_checkpoint_id: null,
      source_input_id: "test.png",
      source_checksum: null,
      calibration_method: "scale_offset",
      calibration_reference: "synthetic-dev-ref",
      calibration_scale: 2.5,
      calibration_offset: 10.0,
      calibration_valid_samples: 5,
    },
  };
}

describe("adaptTerrainProduct", () => {
  it("converts a valid terrain product to a SceneArtifact", () => {
    const result = adaptTerrainProduct(makeTerrainTransport());
    expect(result.success).toBe(true);
    expect(result.artifact).toBeDefined();
    expect(result.artifact!.id).toBe("backend-synthetic-depth-terrain");
    expect(result.artifact!.metadata.source).toBe("backend");
  });

  it("populates mesh from backend vertices/indices/normals/uvs", () => {
    const result = adaptTerrainProduct(makeTerrainTransport());
    const mesh = result.artifact!.mesh;
    expect(mesh.vertexCount).toBe(4);
    expect(mesh.indexCount).toBe(6);
    expect(Array.from(mesh.vertices)).toEqual([0, 10, 0, 1, 11, 0, 0, 12, 1, 1, 13, 1]);
    expect(Array.from(mesh.indices)).toEqual([0, 2, 1, 1, 2, 3]);
    expect(mesh.normals).toBeDefined();
    expect(mesh.uvs).toBeDefined();
  });

  it("preserves DSM values in the elevation grid", () => {
    const result = adaptTerrainProduct(makeTerrainTransport());
    const elevation = result.artifact!.elevation!;
    expect(elevation.width).toBe(2);
    expect(elevation.height).toBe(2);
    expect(Array.from(elevation.grid)).toEqual([10, 11, 12, 13]);
    expect(elevation.unit).toBe("meters");
  });

  it("keeps vertex Y identical to DSM elevation (no axis swap)", () => {
    const product = makeTerrainTransport();
    const result = adaptTerrainProduct(product);
    const mesh = result.artifact!.mesh;
    const grid = result.artifact!.elevation!.grid;
    for (let v = 0; v < mesh.vertexCount; v++) {
      const pixel = product.mesh.vertex_source_indices[v];
      expect(mesh.vertices[v * 3 + 1]).toBe(grid[pixel]);
    }
  });

  it("computes bounds from backend vertices", () => {
    const result = adaptTerrainProduct(makeTerrainTransport());
    const bounds = result.artifact!.metadata.bounds!;
    expect(bounds.minX).toBe(0);
    expect(bounds.maxX).toBe(1);
    expect(bounds.minY).toBe(10);
    expect(bounds.maxY).toBe(13);
    expect(bounds.minZ).toBe(0);
    expect(bounds.maxZ).toBe(1);
  });

  it("records metric semantics and calibration provenance", () => {
    const result = adaptTerrainProduct(makeTerrainTransport());
    const backend = result.artifact!.metadata.backend!;
    expect(backend.depth_scale).toBe("metric");
    expect(backend.elevation_semantics).toBe("absolute_elevation_dsm");
    expect(backend.calibration_method).toBe("scale_offset");
    expect(backend.calibration_reference).toBe("synthetic-dev-ref");
  });

  it("maps the terrain layer to DSM", () => {
    const result = adaptTerrainProduct(makeTerrainTransport());
    const layerState = createLayerState(result.artifact!);
    const dsm = layerState.layers.find((l) => l.id === "dsm");
    expect(dsm!.available).toBe(true);
    expect(dsm!.label).toBe("DSM");
  });

  it("does not mutate the transport arrays", () => {
    const product = makeTerrainTransport();
    const before = JSON.stringify(product);
    adaptTerrainProduct(product);
    expect(JSON.stringify(product)).toBe(before);
  });

  it("height exaggeration leaves backend mesh source data unchanged", () => {
    const result = adaptTerrainProduct(makeTerrainTransport());
    const mesh = result.artifact!.mesh;
    const original = Array.from(mesh.vertices);
    applyHeightExaggeration(mesh.vertices, 10);
    expect(Array.from(mesh.vertices)).toEqual(original);
    expect(result.artifact!.metadata.backend!.depth_scale).toBe("metric");
    expect(result.artifact!.metadata.backend!.elevation_semantics).toBe("absolute_elevation_dsm");
  });

  it("rejects vertex/index length mismatches", () => {
    const bad = makeTerrainTransport();
    bad.mesh.vertices = [0, 10, 0];
    const result = adaptTerrainProduct(bad);
    expect(result.success).toBe(false);
    expect(result.errors.some((e) => e.code === "MESH_VERTICES_LENGTH_MISMATCH")).toBe(true);
  });

  it("rejects out-of-range indices", () => {
    const bad = makeTerrainTransport();
    bad.mesh.indices = [0, 2, 99, 1, 2, 3];
    const result = adaptTerrainProduct(bad);
    expect(result.success).toBe(false);
    expect(result.errors.some((e) => e.code === "INVALID_MESH_INDICES")).toBe(true);
  });

  it("rejects non-metric mesh units", () => {
    const bad = makeTerrainTransport();
    bad.mesh.units = "relative";
    const result = adaptTerrainProduct(bad);
    expect(result.success).toBe(false);
    expect(result.errors.some((e) => e.code === "MESH_UNITS_MISMATCH")).toBe(true);
  });

  it("rejects non-metric mesh semantics", () => {
    const bad = makeTerrainTransport();
    bad.mesh.semantics = "relative_depth";
    const result = adaptTerrainProduct(bad);
    expect(result.success).toBe(false);
    expect(result.errors.some((e) => e.code === "MESH_SEMANTICS_MISMATCH")).toBe(true);
  });

  it("rejects mesh/dsm dimension mismatches", () => {
    const bad = makeTerrainTransport();
    bad.mesh.width = 4;
    const result = adaptTerrainProduct(bad);
    expect(result.success).toBe(false);
    expect(result.errors.some((e) => e.code === "MESH_DSM_DIMENSION_MISMATCH")).toBe(true);
  });

  it("rejects dsm value length mismatches", () => {
    const bad = makeTerrainTransport();
    bad.dsm.values = [10, 11];
    const result = adaptTerrainProduct(bad);
    expect(result.success).toBe(false);
    expect(result.errors.some((e) => e.code === "DSM_VALUES_LENGTH_MISMATCH")).toBe(true);
  });

  it("rejects a missing mesh section", () => {
    const bad = makeTerrainTransport() as unknown as Record<string, unknown>;
    delete bad.mesh;
    const result = validateTerrainProduct(bad as unknown as BackendTerrainProduct);
    expect(result.some((e) => e.code === "MISSING_MESH")).toBe(true);
  });

  it("rejects a wrong product kind", () => {
    const bad = makeTerrainTransport() as unknown as Record<string, unknown>;
    bad.kind = "depth";
    const result = validateTerrainProduct(bad as unknown as BackendTerrainProduct);
    expect(result.some((e) => e.code === "INVALID_TERRAIN_KIND")).toBe(true);
  });
});
