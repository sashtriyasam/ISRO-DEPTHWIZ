import { describe, it, expect } from "vitest";
import { adaptTerrainProduct } from "../backend/meshAdapter";
import type { BackendTerrainProduct } from "../backend/types";
import { ArtifactTransportFailure } from "./types";
import { resolveTerrainArtifact } from "./resolver";
import { verifyBundle } from "./verify";

function minimalBundle(): {
  response: Parameters<typeof verifyBundle>[0]["response"];
  terrain: BackendTerrainProduct;
} {
  const terrain: BackendTerrainProduct = {
    kind: "terrain",
    depth_result: {
      model_name: "synthetic-depth",
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
      source_input_id: "tile.png",
      source_checksum: "abc",
      calibration_method: "scale_offset",
      calibration_reference: "synthetic-dev-ref",
      calibration_scale: 2.5,
      calibration_offset: 10.0,
      calibration_valid_samples: 5,
    },
  };
  return {
    terrain,
    response: {
      contract_version: "1",
      success: true,
      final_state: "completed",
      states: ["completed"],
      failure: null,
      artifacts: [
        {
          kind: "mesh",
          available: true,
          persisted: false,
          path: null,
          semantics: "absolute_elevation_dsm",
          units: "meters",
          width: 2,
          height: 2,
          georeferenced: false,
        },
      ],
      summary: {
        input_path: "tile.png",
        input_checksum: "abc",
        backend_name: "synthetic-depth",
        backend_version: "0.1.0",
        calibration_method: "scale_offset",
        calibration_reference: "synthetic-dev-ref",
        target_semantics: "absolute_elevation_dsm",
        mesh_requested: true,
        geotiff_path: null,
        engine_version: "0.1.0",
      },
    },
  };
}

describe("resolveTerrainArtifact", () => {
  it("resolves a verified bundle to a SceneArtifact", () => {
    const artifact = resolveTerrainArtifact(minimalBundle());
    expect(artifact.id).toBe("backend-synthetic-depth-terrain");
    expect(artifact.mesh.vertexCount).toBe(4);
    expect(artifact.metadata.backend?.depth_scale).toBe("metric");
  });

  it("rejects unverified bundles before adaptation", () => {
    const bundle = minimalBundle();
    bundle.response.artifacts = [];
    try {
      resolveTerrainArtifact(bundle);
      expect.fail("should have thrown");
    } catch (err) {
      expect((err as ArtifactTransportFailure).transportError.code).toBe("ARTIFACT_UNAVAILABLE");
    }
  });

  it("rejects non-metric mesh semantics before any artifact exists", () => {
    const bundle = minimalBundle();
    bundle.terrain.mesh.semantics = "relative_depth";
    bundle.terrain.dsm.semantics = "relative_depth";
    bundle.response.summary.target_semantics = "relative_depth";
    const descriptor = bundle.response.artifacts.find((a) => a.kind === "mesh");
    if (descriptor) {
      descriptor.semantics = "relative_depth";
    }
    try {
      resolveTerrainArtifact(bundle);
      expect.fail("should have thrown");
    } catch (err) {
      expect(err).toBeInstanceOf(ArtifactTransportFailure);
      expect((err as ArtifactTransportFailure).transportError.code).toBe("RESOLUTION_FAILED");
    }
  });

  it("rejects malformed payloads with adapter detail", () => {
    const bundle = minimalBundle();
    bundle.terrain.mesh.vertices = [0, 10];
    try {
      resolveTerrainArtifact(bundle);
      expect.fail("should have thrown");
    } catch (err) {
      expect((err as ArtifactTransportFailure).transportError.code).toBe("RESOLUTION_FAILED");
    }
  });

  it("does not mutate the bundle", () => {
    const bundle = minimalBundle();
    const before = JSON.stringify(bundle);
    resolveTerrainArtifact(bundle);
    expect(JSON.stringify(bundle)).toBe(before);
  });

  it("agrees with the standalone adapter on valid payloads", () => {
    const bundle = minimalBundle();
    const direct = adaptTerrainProduct(bundle.terrain);
    const resolved = resolveTerrainArtifact(bundle);
    expect(direct.success).toBe(true);
    expect(Array.from(resolved.mesh.vertices)).toEqual(
      Array.from(direct.artifact!.mesh.vertices)
    );
  });
});
