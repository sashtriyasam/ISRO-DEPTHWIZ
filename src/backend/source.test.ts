import { describe, it, expect } from "vitest";
import { BackendArtifactSource } from "./source";

describe("BackendArtifactSource", () => {
  it("implements ArtifactSource interface", () => {
    const source = new BackendArtifactSource();
    expect(source.id).toBe("backend-synthetic");
    expect(source.label).toBe("Synthetic Backend");
    expect(typeof source.load).toBe("function");
  });

  it("loads an artifact from the Python backend", async () => {
    const source = new BackendArtifactSource({ width: 4, height: 4 });
    const artifact = await source.load();
    expect(artifact.id).toBe("backend-synthetic-depth");
    expect(artifact.elevation).toBeDefined();
    expect(artifact.elevation!.width).toBe(4);
    expect(artifact.elevation!.height).toBe(4);
    expect(artifact.elevation!.grid.length).toBe(16);
  });

  it("preserves backend metadata", async () => {
    const source = new BackendArtifactSource();
    const artifact = await source.load();
    expect(artifact.metadata.backend).toBeDefined();
    expect(artifact.metadata.backend!.model_name).toBe("synthetic-depth");
    expect(artifact.metadata.backend!.depth_scale).toBe("relative");
  });

  it("does not fabricate scientific data", async () => {
    const source = new BackendArtifactSource();
    const artifact = await source.load();
    expect(artifact.metadata.backend?.depth_scale).toBe("relative");
    expect(artifact.metadata.backend?.elevation_semantics).toBe("relative_depth");
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
