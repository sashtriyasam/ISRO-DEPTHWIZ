import { describe, it, expect } from "vitest";
import { BackendArtifactSource } from "./source";

describe("BackendArtifactSource", () => {
  it("implements ArtifactSource interface", () => {
    const source = new BackendArtifactSource();
    expect(source.id).toBe("backend-synthetic");
    expect(source.label).toBe("Synthetic Backend");
    expect(typeof source.load).toBe("function");
  });

  it("loads a backend terrain artifact by default", async () => {
    const source = new BackendArtifactSource({ width: 4, height: 4 });
    const artifact = await source.load();
    expect(artifact.id).toBe("backend-synthetic-depth-terrain");
    expect(artifact.elevation).toBeDefined();
    expect(artifact.elevation!.width).toBe(4);
    expect(artifact.elevation!.height).toBe(4);
    expect(artifact.elevation!.grid.length).toBe(16);
    expect(artifact.elevation!.unit).toBe("meters");
    expect(artifact.mesh.vertexCount).toBe(16);
    expect(artifact.mesh.indexCount).toBe(54);
  });

  it("preserves backend terrain metadata", async () => {
    const source = new BackendArtifactSource();
    const artifact = await source.load();
    expect(artifact.metadata.backend).toBeDefined();
    expect(artifact.metadata.backend!.model_name).toBe("synthetic-depth");
    expect(artifact.metadata.backend!.depth_scale).toBe("metric");
    expect(artifact.metadata.backend!.elevation_semantics).toBe("absolute_elevation_dsm");
    expect(artifact.metadata.backend!.calibration_reference).toBe("synthetic-dev-ref");
  });

  it("supports the depth-only mode explicitly", async () => {
    const source = new BackendArtifactSource({ width: 4, height: 4, mode: "depth" });
    const artifact = await source.load();
    expect(artifact.id).toBe("backend-synthetic-depth");
    expect(artifact.metadata.backend?.depth_scale).toBe("relative");
    expect(artifact.metadata.backend?.elevation_semantics).toBe("relative_depth");
    expect(artifact.mesh.vertexCount).toBe(0);
  });

  it("does not fabricate scientific data", async () => {
    const source = new BackendArtifactSource();
    const artifact = await source.load();
    expect(artifact.metadata.backend?.depth_scale).toBe("metric");
    expect(artifact.metadata.backend?.elevation_semantics).toBe("absolute_elevation_dsm");
    expect(artifact.elevation!.unit).toBe("meters");
  });

  it("creates stable artifact identity", async () => {
    const source = new BackendArtifactSource({ width: 8, height: 8 });
    const artifact1 = await source.load();
    const artifact2 = await source.load();
    expect(artifact1.id).toBe(artifact2.id);
  });

  it("returns empty warnings from getWarnings", () => {
    const source = new BackendArtifactSource();
    expect(source.getWarnings()).toEqual([]);
  });
});
