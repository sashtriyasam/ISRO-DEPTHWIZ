import { describe, it, expect } from "vitest";
import { resolveInspection } from "./resolver";
import type { SceneArtifact, ElevationData } from "../types/scene";

function createTestArtifact(): SceneArtifact {
  const grid = new Float32Array([0, 1, 2, 3]);
  const elevation: ElevationData = {
    grid,
    width: 2,
    height: 2,
    cellSize: 1,
    unit: "meters",
  };
  const rdsmGrid = new Float32Array([0.5, 1.5, 2.5, 3.5]);
  const rdsm: ElevationData = {
    grid: rdsmGrid,
    width: 2,
    height: 2,
    cellSize: 1,
    unit: "meters",
  };
  return {
    id: "test-001",
    label: "Test Terrain",
    mesh: {
      vertices: new Float32Array([0, 0, 0, 1, 1, 0, 0, 2, 1, 1, 3, 1]),
      indices: new Uint32Array([0, 1, 2, 1, 3, 2]),
      vertexCount: 4,
      indexCount: 6,
    },
    elevation,
    layers: { rdsm },
    metadata: {
      CRS: "TEST",
      bounds: { minX: 0, minY: 0, minZ: 0, maxX: 1, maxY: 3, maxZ: 1 },
      units: { spatial: "meters", elevation: "meters" },
      source: "deterministic-fixture",
    },
  };
}

describe("resolveInspection", () => {
  const artifact = createTestArtifact();

  it("returns null when uv is null", () => {
    const result = resolveInspection(null, { x: 0, y: 0, z: 0 }, artifact, "dsm");
    expect(result).toBeNull();
  });

  it("returns null when position is null", () => {
    const result = resolveInspection({ u: 0, v: 0 }, null, artifact, "dsm");
    expect(result).toBeNull();
  });

  it("returns null when both are null", () => {
    const result = resolveInspection(null, null, artifact, "dsm");
    expect(result).toBeNull();
  });

  it("resolves a point at (0,0) UV to grid cell (0,0)", () => {
    const result = resolveInspection(
      { u: 0, v: 0 },
      { x: 0, y: 0, z: 0 },
      artifact,
      "dsm"
    );
    expect(result).not.toBeNull();
    expect(result!.gridIndex.col).toBe(0);
    expect(result!.gridIndex.row).toBe(0);
    expect(result!.scientific.elevation).toBe(0);
    expect(result!.scientific.rdsm).toBe(0.5);
    expect(result!.uv.u).toBe(0);
    expect(result!.uv.v).toBe(0);
  });

  it("resolves a point at (1,1) UV to grid cell (1,1)", () => {
    const result = resolveInspection(
      { u: 1, v: 1 },
      { x: 1, y: 3, z: 1 },
      artifact,
      "dsm"
    );
    expect(result).not.toBeNull();
    expect(result!.gridIndex.col).toBe(1);
    expect(result!.gridIndex.row).toBe(1);
    expect(result!.scientific.elevation).toBe(3);
    expect(result!.scientific.rdsm).toBe(3.5);
  });

  it("resolves a point at (0.5, 0.5) UV to nearest grid cell", () => {
    const result = resolveInspection(
      { u: 0.5, v: 0.5 },
      { x: 0.5, y: 1.5, z: 0.5 },
      artifact,
      "dsm"
    );
    expect(result).not.toBeNull();
    expect(result!.gridIndex.col).toBe(1);
    expect(result!.gridIndex.row).toBe(1);
    expect(result!.scientific.elevation).toBeCloseTo(3);
  });

  it("preserves artifact ID in result", () => {
    const result = resolveInspection(
      { u: 0, v: 0 },
      { x: 0, y: 0, z: 0 },
      artifact,
      "dsm"
    );
    expect(result!.artifactId).toBe("test-001");
  });

  it("preserves layer ID in result", () => {
    const result = resolveInspection(
      { u: 0, v: 0 },
      { x: 0, y: 0, z: 0 },
      artifact,
      "rdsm"
    );
    expect(result!.layerId).toBe("rdsm");
  });

  it("does not mutate artifact source data", () => {
    const originalElevation = new Float32Array(artifact.elevation!.grid);
    const originalRdsm = new Float32Array(artifact.layers!.rdsm!.grid);

    resolveInspection({ u: 0, v: 0 }, { x: 0, y: 0, z: 0 }, artifact, "dsm");
    resolveInspection({ u: 1, v: 1 }, { x: 1, y: 3, z: 1 }, artifact, "dsm");
    resolveInspection({ u: 0.5, v: 0.5 }, { x: 0.5, y: 1.5, z: 0.5 }, artifact, "dsm");

    for (let i = 0; i < artifact.elevation!.grid.length; i++) {
      expect(artifact.elevation!.grid[i]).toBeCloseTo(originalElevation[i]);
    }
    for (let i = 0; i < artifact.layers!.rdsm!.grid.length; i++) {
      expect(artifact.layers!.rdsm!.grid[i]).toBeCloseTo(originalRdsm[i]);
    }
  });
});
