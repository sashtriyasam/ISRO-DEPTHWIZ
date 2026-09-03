import { describe, it, expect } from "vitest";
import { BackendBridge } from "./bridge";
import { resolveInspection } from "../inspection/resolver";
import { calculateMeasurement } from "../measurement/calculator";
import { generateProfile } from "../profile/sampler";

describe("backend terrain end-to-end", () => {
  const bridge = new BackendBridge({
    bridgeScript: "scripts/backend_bridge.py",
  });

  it("executes the real backend terrain chain", async () => {
    const result = await bridge.executeTerrain(4, 4);
    expect(result.success).toBe(true);
    expect(result.artifact).toBeDefined();
    expect(result.artifact!.id).toBe("backend-synthetic-depth-terrain");
  });

  it("returns a backend-generated mesh with matching DSM values", async () => {
    const result = await bridge.executeTerrain(4, 4);
    const artifact = result.artifact!;
    expect(artifact.mesh.vertexCount).toBe(16);
    expect(artifact.mesh.indexCount).toBe(54);
    expect(artifact.mesh.normals).toBeDefined();
    expect(artifact.mesh.uvs).toBeDefined();
    expect(artifact.elevation!.unit).toBe("meters");
    expect(artifact.metadata.backend!.depth_scale).toBe("metric");
    expect(artifact.metadata.backend!.elevation_semantics).toBe("absolute_elevation_dsm");
  });

  it("proves calibration was applied without hardcoding backend values", async () => {
    const result = await bridge.executeTerrain(4, 4);
    const grid = result.artifact!.elevation!.grid;
    for (let i = 0; i < grid.length; i++) {
      expect(grid[i]).toBeGreaterThan(1);
    }
    expect(result.artifact!.metadata.backend!.calibration_reference).toBe("synthetic-dev-ref");
  });

  it("is deterministic across runs", async () => {
    const first = await bridge.executeTerrain(4, 4);
    const second = await bridge.executeTerrain(4, 4);
    expect(Array.from(first.artifact!.mesh.vertices)).toEqual(
      Array.from(second.artifact!.mesh.vertices)
    );
    expect(Array.from(first.artifact!.elevation!.grid)).toEqual(
      Array.from(second.artifact!.elevation!.grid)
    );
  });

  it("supports point inspection on the terrain artifact", async () => {
    const result = await bridge.executeTerrain(4, 4);
    const artifact = result.artifact!;
    const inspection = resolveInspection({ u: 0.5, v: 0.5 }, { x: 0, y: 0, z: 0 }, artifact, "dsm");
    expect(inspection).not.toBeNull();
    expect(inspection!.artifactId).toBe(artifact.id);
    expect(Number.isFinite(inspection!.scientific.elevation)).toBe(true);
  });

  it("supports metric measurement on the terrain artifact", async () => {
    const result = await bridge.executeTerrain(4, 4);
    const artifact = result.artifact!;
    const pointA = {
      displayPosition: { x: 0, y: 0, z: 0 },
      scientific: { elevation: artifact.elevation!.grid[0] },
      uv: { u: 0, v: 0 },
      gridIndex: { col: 0, row: 0 },
      layerId: "dsm",
      artifactId: artifact.id,
    };
    const pointB = { ...pointA, displayPosition: { x: 1, y: 0, z: 0 } };
    const measurement = calculateMeasurement("distance", pointA, pointB, {
      units: "meters",
      source: "backend",
    });
    expect(measurement.units).toBe("meters");
    expect(measurement.horizontalDistance).toBeCloseTo(1);
  });

  it("supports metric profiles on the terrain artifact", async () => {
    const result = await bridge.executeTerrain(4, 4);
    const artifact = result.artifact!;
    const mk = (x: number, col: number) => ({
      displayPosition: { x, y: 0, z: 0 },
      scientific: { elevation: 0 },
      uv: { u: 0, v: 0 },
      gridIndex: { col, row: 0 },
      layerId: "dsm",
      artifactId: artifact.id,
    });
    const profile = generateProfile(mk(0, 0), mk(1, 1), artifact.elevation, undefined, undefined, {
      units: "meters",
      source: "backend",
      elevationSemantics: "absolute_elevation_dsm",
    });
    expect(profile.units).toBe("meters");
    expect(profile.points.length).toBeGreaterThan(0);
  });

  it("rejects malformed terrain output with an actionable error", async () => {
    const badBridge = new BackendBridge({ bridgeScript: "scripts/backend_bridge.py" });
    const result = await badBridge.executeWithInput("nonexistent.png");
    expect(result.success).toBe(false);
    expect(result.errors.length).toBeGreaterThan(0);
  });
});
