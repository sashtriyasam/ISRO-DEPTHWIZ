import { describe, it, expect, vi, afterEach } from "vitest";
import * as THREE from "three";
import { createDeterministicFixture } from "../fixtures/deterministicFixture";
import type { SceneArtifact } from "../types/scene";
import { createLayerMesh, createRgbTexture } from "./layerRenderer";
import { createLayerState } from "./LayerRegistry";
import { attachStagedTexture } from "../artifact/stagedTexture";

/** Two-vertex-wide artifact whose vertices come from pixels 3 and 0 of a 2x2 grid. */
function sparseArtifact(): SceneArtifact {
  const base = createDeterministicFixture();
  return {
    ...base,
    mesh: {
      vertices: new Float32Array([0, 0, 0, 1, 0, 0, 0, 0, 1]),
      indices: new Uint32Array([0, 1, 2]),
      vertexCount: 3,
      indexCount: 3,
      sourceIndices: new Uint32Array([3, 0, 1]),
    },
    elevation: {
      grid: new Float32Array([0, 5, NaN, 10]),
      width: 2,
      height: 2,
      cellSize: 1,
      unit: "meters",
    },
  };
}

afterEach(() => {
  delete (window as unknown as { depthwizard?: unknown }).depthwizard;
  vi.unstubAllGlobals();
});

describe("per-vertex layer colours", () => {
  it("colour each vertex from its own source pixel", () => {
    const group = createLayerMesh(sparseArtifact(), "dsm", "shaded");
    const colors = group!.geometry.getAttribute("color");
    expect(colors.count).toBe(3); // one per vertex, not per grid pixel
    // vertex 0 = pixel 3 (max, 10) and vertex 1 = pixel 0 (min, 0) differ
    expect(colors.getX(0)).not.toBeCloseTo(colors.getX(1));
    for (let i = 0; i < colors.count * 3; i++) {
      expect(Number.isFinite(colors.array[i])).toBe(true);
    }
  });
});

describe("slope layer", () => {
  it("is available only when the backend supplied slope", () => {
    const without = createLayerState(sparseArtifact());
    expect(without.layers.find((l) => l.id === "slope")!.available).toBe(false);
    const artifact = sparseArtifact();
    artifact.layers = {
      slope: { ...artifact.elevation!, grid: new Float32Array([1, 2, 3, NaN]), unit: "degrees" },
    };
    const state = createLayerState(artifact);
    expect(state.layers.find((l) => l.id === "slope")!.available).toBe(true);
    expect(createLayerMesh(artifact, "slope", "shaded")).not.toBeNull();
  });
});

describe("RGB texture", () => {
  it("maps pixel centres onto mesh UVs without flipping", () => {
    const artifact = sparseArtifact();
    artifact.texture = {
      image: { width: 2, height: 2 } as unknown as ImageBitmap,
      width: 2,
      height: 2,
    };
    const texture = createRgbTexture(artifact)!;
    expect(texture.flipY).toBe(false);
    expect(texture.repeat.x).toBeCloseTo(0.5);
    expect(texture.offset.x).toBeCloseTo(0.25);
    const group = createLayerMesh(artifact, "rgb", "shaded")!;
    expect((group.material as THREE.MeshStandardMaterial).map).toBeTruthy();
  });

  it("is attached from the staged PNG through the host", async () => {
    const bitmap = { width: 2, height: 2 };
    vi.stubGlobal("createImageBitmap", vi.fn(async () => bitmap));
    const readStagedFile = vi.fn(async () => ({ bytes: new Uint8Array([137, 80, 78, 71]) }));
    (window as unknown as { depthwizard: unknown }).depthwizard = { readStagedFile };
    const artifact = sparseArtifact();
    artifact.metadata = { ...artifact.metadata, texturePath: "C:/tmp/depthwiz-x/texture.png" };
    const withTexture = await attachStagedTexture(artifact);
    expect(readStagedFile).toHaveBeenCalledWith({ path: "C:/tmp/depthwiz-x/texture.png" });
    expect(withTexture.texture).toEqual({ image: bitmap, width: 2, height: 2 });
  });

  it("leaves the artifact unchanged without a host", async () => {
    const artifact = sparseArtifact();
    artifact.metadata = { ...artifact.metadata, texturePath: "texture.png" };
    expect(await attachStagedTexture(artifact)).toBe(artifact);
  });
});
