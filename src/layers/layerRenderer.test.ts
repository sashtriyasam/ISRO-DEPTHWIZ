import { describe, it, expect, vi } from "vitest";
import * as THREE from "three";
import { createLayerMesh, disposeLayerMesh } from "./layerRenderer";
import { createDeterministicFixture } from "../fixtures/deterministicFixture";

describe("layer mesh lifecycle", () => {
  it("builds renderer-ready geometry from artifact mesh data", () => {
    const artifact = createDeterministicFixture();
    const group = createLayerMesh(artifact, "dsm");
    expect(group).not.toBeNull();
    const position = group!.geometry.getAttribute("position") as THREE.BufferAttribute;
    expect(position.count).toBe(artifact.mesh.vertexCount);
    expect(group!.geometry.getIndex()!.count).toBe(artifact.mesh.indexCount);
    disposeLayerMesh(group!);
  });

  it("disposes geometry and materials on replacement", () => {
    const artifact = createDeterministicFixture();
    const group = createLayerMesh(artifact, "dsm")!;
    const geometrySpy = vi.spyOn(group.geometry, "dispose");
    const materialSpy = vi.spyOn(group.material, "dispose");
    disposeLayerMesh(group);
    expect(geometrySpy).toHaveBeenCalled();
    expect(materialSpy).toHaveBeenCalled();
  });

  it("disposes wireframe resources too", () => {
    const artifact = createDeterministicFixture();
    const group = createLayerMesh(artifact, "dsm")!;
    expect(group.wireframe).toBeDefined();
    const wireGeometrySpy = vi.spyOn(group.wireframe!.geometry, "dispose");
    disposeLayerMesh(group);
    expect(wireGeometrySpy).toHaveBeenCalled();
  });
});
