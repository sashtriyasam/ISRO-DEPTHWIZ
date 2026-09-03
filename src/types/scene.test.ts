import { describe, it, expect } from "vitest";
import type { SceneArtifact, DisplayTransform } from "../types/scene";
import { DEFAULT_DISPLAY_TRANSFORM } from "../types/scene";
import { createDeterministicFixture } from "../fixtures/deterministicFixture";

describe("SceneArtifact contract", () => {
  const artifact: SceneArtifact = createDeterministicFixture();

  it("has required top-level fields", () => {
    expect(typeof artifact.id).toBe("string");
    expect(typeof artifact.label).toBe("string");
    expect(artifact.mesh).toBeDefined();
    expect(artifact.metadata).toBeDefined();
  });

  it("mesh has typed arrays", () => {
    expect(artifact.mesh.vertices).toBeInstanceOf(Float32Array);
    expect(artifact.mesh.indices).toBeInstanceOf(Uint32Array);
    expect(typeof artifact.mesh.vertexCount).toBe("number");
    expect(typeof artifact.mesh.indexCount).toBe("number");
  });

  it("metadata has correct units", () => {
    expect(artifact.metadata.units.spatial).toBe("meters");
    expect(artifact.metadata.units.elevation).toBe("meters");
  });

  it("source is deterministic-fixture", () => {
    expect(artifact.metadata.source).toBe("deterministic-fixture");
  });

  it("DEFAULT_DISPLAY_TRANSFORM has heightExaggeration 1.0", () => {
    const dt: DisplayTransform = DEFAULT_DISPLAY_TRANSFORM;
    expect(dt.heightExaggeration).toBe(1.0);
  });
});
