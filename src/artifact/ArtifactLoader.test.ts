import { describe, it, expect } from "vitest";
import { ArtifactLoader } from "./ArtifactLoader";
import { FixtureSource } from "./FixtureSource";
import type { ArtifactSource } from "./types";

describe("ArtifactLoader", () => {
  it("loads artifact from FixtureSource", async () => {
    const loader = new ArtifactLoader();
    const source = new FixtureSource();
    const result = await loader.load(source);

    expect(result.artifact).toBeDefined();
    expect(result.artifact.id).toBe("dev-fixture-001");
    expect(result.source).toBe(source);
  });

  it("tracks current source", async () => {
    const loader = new ArtifactLoader();
    expect(loader.getCurrentSource()).toBeNull();

    const source = new FixtureSource();
    await loader.load(source);
    expect(loader.getCurrentSource()).toBe(source);
  });

  it("clears source on cancel", async () => {
    const loader = new ArtifactLoader();
    const source = new FixtureSource();
    await loader.load(source);
    loader.cancel();
    expect(loader.getCurrentSource()).toBeNull();
  });

  it("throws ArtifactError on failure", async () => {
    const loader = new ArtifactLoader();
    const failingSource: ArtifactSource = {
      id: "failing",
      label: "Failing",
      load: async () => { throw new Error("test failure"); },
    };

    try {
      await loader.load(failingSource);
      expect.fail("should have thrown");
    } catch (err: any) {
      expect(err.message).toBe("test failure");
      expect(err.source).toBe(failingSource);
    }
  });
});

describe("FixtureSource", () => {
  it("loads deterministic fixture", async () => {
    const source = new FixtureSource();
    const artifact = await source.load();

    expect(artifact.id).toBe("dev-fixture-001");
    expect(artifact.metadata.source).toBe("deterministic-fixture");
    expect(artifact.mesh.vertexCount).toBe(64);
  });

  it("has correct id and label", () => {
    const source = new FixtureSource();
    expect(source.id).toBe("deterministic-fixture");
    expect(source.label).toBe("Development Fixture");
  });
});
