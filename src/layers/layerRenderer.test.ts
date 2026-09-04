import { describe, it, expect, vi } from "vitest";
import * as THREE from "three";
import { createLayerMesh, disposeLayerMesh } from "./layerRenderer";
import { createDeterministicFixture } from "../fixtures/deterministicFixture";
import { DEFAULT_RENDERING_MODE, RENDERING_MODES, isRenderingMode } from "./types";
import type { SceneArtifact } from "../types/scene";

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

describe("rendering mode registry", () => {
  it("declares shaded, wireframe, and combined modes with a shaded default", () => {
    expect(RENDERING_MODES).toEqual(["shaded", "wireframe", "shaded-wireframe"]);
    expect(DEFAULT_RENDERING_MODE).toBe("shaded");
    expect(isRenderingMode("shaded")).toBe(true);
    expect(isRenderingMode("shaded-wireframe")).toBe(true);
    expect(isRenderingMode("raytraced")).toBe(false);
  });
});

describe("shaded mode", () => {
  it("renders the surface without an overlay", () => {
    const artifact = createDeterministicFixture();
    const group = createLayerMesh(artifact, "dsm", "shaded")!;
    expect(group.wireframe).toBeUndefined();
    expect((group.material as THREE.MeshStandardMaterial).wireframe).toBe(false);
    expect((group.material as THREE.MeshStandardMaterial).vertexColors).toBe(true);
    disposeLayerMesh(group);
  });

  it("preserves backend normals instead of recomputing them", () => {
    const artifact = createDeterministicFixture();
    const group = createLayerMesh(artifact, "dsm", "shaded")!;
    const normals = group.geometry.getAttribute("normal") as THREE.BufferAttribute;
    expect(normals.count).toBe(artifact.mesh.vertexCount);
    for (let i = 0; i < artifact.mesh.normals!.length; i++) {
      expect(normals.array[i]).toBeCloseTo(artifact.mesh.normals![i]);
    }
    disposeLayerMesh(group);
  });
});

describe("wireframe mode", () => {
  it("uses native wireframe material without overlay geometry", () => {
    const artifact = createDeterministicFixture();
    const group = createLayerMesh(artifact, "dsm", "wireframe")!;
    expect((group.material as THREE.MeshStandardMaterial).wireframe).toBe(true);
    expect(group.wireframe).toBeUndefined();
    expect((group.material as THREE.MeshStandardMaterial).vertexColors).toBe(true);
    disposeLayerMesh(group);
  });

  it("shares the same position attribute as shaded mode", () => {
    const artifact = createDeterministicFixture();
    const shaded = createLayerMesh(artifact, "dsm", "shaded")!;
    const wire = createLayerMesh(artifact, "dsm", "wireframe")!;
    const a = shaded.geometry.getAttribute("position") as THREE.BufferAttribute;
    const b = wire.geometry.getAttribute("position") as THREE.BufferAttribute;
    expect(a.count).toBe(b.count);
    for (let i = 0; i < a.array.length; i++) {
      expect(a.array[i]).toBe(b.array[i]);
    }
    disposeLayerMesh(shaded);
    disposeLayerMesh(wire);
  });
});

describe("combined mode", () => {
  it("aligns the overlay with the surface mesh", () => {
    const artifact = createDeterministicFixture();
    const group = createLayerMesh(artifact, "dsm", "shaded-wireframe")!;
    expect(group.wireframe).toBeDefined();
    expect((group.material as THREE.MeshStandardMaterial).wireframe).toBe(false);
    const surface = group.geometry.getAttribute("position") as THREE.BufferAttribute;
    const overlay = group.wireframe!.geometry.getAttribute("position") as THREE.BufferAttribute;
    expect(overlay.count).toBeGreaterThan(0);
    const surfaceSet = new Set<number>();
    for (let i = 0; i < surface.array.length; i++) {
      surfaceSet.add(surface.array[i]);
    }
    for (let i = 0; i < overlay.array.length; i++) {
      expect(surfaceSet.has(overlay.array[i])).toBe(true);
    }
    disposeLayerMesh(group);
  });

  it("marks only the surface mesh as pickable", () => {
    const artifact = createDeterministicFixture();
    const group = createLayerMesh(artifact, "dsm", "shaded-wireframe")!;
    expect(group.mesh.userData.pickable).toBe(true);
    expect(group.wireframe!.userData.pickable).toBe(false);
    disposeLayerMesh(group);
  });
});

describe("mode switching stability", () => {
  it("cycles modes repeatedly without leaking", () => {
    const artifact = createDeterministicFixture();
    const modes = ["shaded", "wireframe", "shaded-wireframe", "shaded", "wireframe"] as const;
    for (const mode of modes) {
      const group = createLayerMesh(artifact, "dsm", mode)!;
      const geometrySpy = vi.spyOn(group.geometry, "dispose");
      const materialSpy = vi.spyOn(group.material, "dispose");
      disposeLayerMesh(group);
      expect(geometrySpy).toHaveBeenCalledOnce();
      expect(materialSpy).toHaveBeenCalledOnce();
    }
  });

  it("builds independent resources per mode", () => {
    const artifact = createDeterministicFixture();
    const first = createLayerMesh(artifact, "dsm", "shaded")!;
    const second = createLayerMesh(artifact, "dsm", "wireframe")!;
    expect(first.geometry).not.toBe(second.geometry);
    expect(first.material).not.toBe(second.material);
    disposeLayerMesh(first);
    disposeLayerMesh(second);
  });

  it("rejects unsupported layers without leaking geometry", () => {
    const artifact = createDeterministicFixture();
    expect(createLayerMesh(artifact, "slope", "shaded")).toBeNull();
    expect(createLayerMesh(artifact, "slope", "wireframe")).toBeNull();
    expect(createLayerMesh(artifact, "slope", "shaded-wireframe")).toBeNull();
  });
});

describe("rendering mode data safety", () => {
  it("never mutates artifact vertices across modes", () => {
    const artifact = createDeterministicFixture();
    const before = Array.from(artifact.mesh.vertices);
    const gridBefore = Array.from(artifact.elevation!.grid);
    for (const mode of ["shaded", "wireframe", "shaded-wireframe"] as const) {
      const group = createLayerMesh(artifact, "dsm", mode)!;
      disposeLayerMesh(group);
    }
    expect(Array.from(artifact.mesh.vertices)).toEqual(before);
    expect(Array.from(artifact.elevation!.grid)).toEqual(gridBefore);
  });

  it("bakes no display scale into geometry", () => {
    const artifact = createDeterministicFixture();
    for (const mode of ["shaded", "wireframe", "shaded-wireframe"] as const) {
      const group = createLayerMesh(artifact, "dsm", mode)!;
      const position = group.geometry.getAttribute("position") as THREE.BufferAttribute;
      for (let i = 0; i < position.array.length; i++) {
        expect(position.array[i]).toBe(artifact.mesh.vertices[i]);
      }
      disposeLayerMesh(group);
    }
  });

  it("works for every available fixture layer", () => {
    const artifact = createDeterministicFixture();
    for (const layerId of ["dsm", "rdsm", "agl"] as const) {
      for (const mode of ["shaded", "wireframe", "shaded-wireframe"] as const) {
        const group = createLayerMesh(artifact, layerId, mode);
        expect(group).not.toBeNull();
        disposeLayerMesh(group!);
      }
    }
  });

  it("keeps the wireframe layer mode-independent", () => {
    const artifact = createDeterministicFixture();
    for (const mode of ["shaded", "wireframe", "shaded-wireframe"] as const) {
      const group = createLayerMesh(artifact, "wireframe", mode)!;
      expect((group.material as THREE.MeshStandardMaterial).wireframe).toBe(true);
      expect(group.wireframe).toBeUndefined();
      disposeLayerMesh(group);
    }
  });

  it("leaves inspection inputs untouched", async () => {
    const { resolveInspection } = await import("../inspection/resolver");
    const artifact: SceneArtifact = createDeterministicFixture();
    const gridBefore = Array.from(artifact.elevation!.grid);
    for (const mode of ["shaded", "wireframe", "shaded-wireframe"] as const) {
      const group = createLayerMesh(artifact, "dsm", mode)!;
      const result = resolveInspection({ u: 0.5, v: 0.5 }, { x: 0, y: 0, z: 0 }, artifact, "dsm");
      expect(result).not.toBeNull();
      disposeLayerMesh(group);
    }
    expect(Array.from(artifact.elevation!.grid)).toEqual(gridBefore);
  });
});
