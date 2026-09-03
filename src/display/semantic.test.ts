import { describe, it, expect } from "vitest";
import { applyHeightExaggeration } from "./types";
import type { SceneArtifact } from "../types/scene";

describe("height exaggeration semantic immutability", () => {
  it("does not modify source vertices", () => {
    const source = new Float32Array([1, 2, 3, 4, 5, 6]);
    const result = applyHeightExaggeration(source, 2);
    expect(source[1]).toBe(2);
    expect(source[4]).toBe(5);
    expect(result[1]).toBe(4);
  });

  it("creates independent output array", () => {
    const source = new Float32Array([1, 2, 3]);
    const result = applyHeightExaggeration(source, 2);
    expect(result).not.toBe(source);
  });

  it("scales only Y component", () => {
    const source = new Float32Array([1, 2, 3, 4, 5, 6]);
    const result = applyHeightExaggeration(source, 10);
    expect(result[0]).toBe(1);
    expect(result[1]).toBe(20);
    expect(result[2]).toBe(3);
    expect(result[3]).toBe(4);
    expect(result[4]).toBe(50);
    expect(result[5]).toBe(6);
  });

  it("does not change depth_scale", () => {
    const artifact: SceneArtifact = {
      id: "test",
      label: "test",
      mesh: { vertices: new Float32Array(0), indices: new Uint32Array(0), vertexCount: 0, indexCount: 0 },
      elevation: { grid: new Float32Array([0.5, 0.3]), width: 2, height: 1, cellSize: 1, unit: "relative" },
      metadata: {
        source: "backend",
        units: { spatial: "meters", elevation: "meters" },
        backend: { model_name: "test", depth_scale: "relative", elevation_semantics: "relative_depth", georeferencing: "non_georeferenced" },
      },
    };
    const result = applyHeightExaggeration(artifact.elevation!.grid, 5);
    expect(result[1]).toBeCloseTo(1.5);
    expect(artifact.metadata.backend!.depth_scale).toBe("relative");
  });

  it("does not change elevation_semantics", () => {
    const artifact: SceneArtifact = {
      id: "test",
      label: "test",
      mesh: { vertices: new Float32Array(0), indices: new Uint32Array(0), vertexCount: 0, indexCount: 0 },
      elevation: { grid: new Float32Array([0.5, 0.3]), width: 2, height: 1, cellSize: 1, unit: "relative" },
      metadata: {
        source: "backend",
        units: { spatial: "meters", elevation: "meters" },
        backend: { model_name: "test", depth_scale: "relative", elevation_semantics: "relative_depth", georeferencing: "non_georeferenced" },
      },
    };
    applyHeightExaggeration(artifact.elevation!.grid, 5);
    expect(artifact.metadata.backend!.elevation_semantics).toBe("relative_depth");
  });

  it("does not change units", () => {
    const artifact: SceneArtifact = {
      id: "test",
      label: "test",
      mesh: { vertices: new Float32Array(0), indices: new Uint32Array(0), vertexCount: 0, indexCount: 0 },
      elevation: { grid: new Float32Array([0.5, 0.3]), width: 2, height: 1, cellSize: 1, unit: "relative" },
      metadata: {
        source: "backend",
        units: { spatial: "meters", elevation: "meters" },
        backend: { model_name: "test", depth_scale: "relative", elevation_semantics: "relative_depth", georeferencing: "non_georeferenced" },
      },
    };
    applyHeightExaggeration(artifact.elevation!.grid, 5);
    expect(artifact.elevation!.unit).toBe("relative");
  });

  it("does not change provenance", () => {
    const artifact: SceneArtifact = {
      id: "test",
      label: "test",
      mesh: { vertices: new Float32Array(0), indices: new Uint32Array(0), vertexCount: 0, indexCount: 0 },
      elevation: { grid: new Float32Array([0.5, 0.3]), width: 2, height: 1, cellSize: 1, unit: "relative" },
      metadata: {
        source: "backend",
        units: { spatial: "meters", elevation: "meters" },
        backend: { model_name: "synthetic-depth", depth_scale: "relative", elevation_semantics: "relative_depth", georeferencing: "non_georeferenced" },
      },
    };
    applyHeightExaggeration(artifact.elevation!.grid, 10);
    expect(artifact.metadata.backend!.model_name).toBe("synthetic-depth");
  });
});
