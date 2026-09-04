import { describe, it, expect } from "vitest";
import * as THREE from "three";
import {
  buildPreviewGroup,
  disposePreviewGroup,
  PREVIEW_COMPLETED_COLOR,
  PREVIEW_FUTURE_COLOR,
  PREVIEW_START_COLOR,
  PREVIEW_END_COLOR,
  PREVIEW_MIDDLE_COLOR,
} from "./preview";
import type { WaypointPosition } from "./types";

function points(): WaypointPosition[] {
  return [
    { x: 0, y: 4, z: 7 },
    { x: 4, y: 4, z: 7 },
    { x: 8, y: 4, z: 7 },
  ];
}

describe("buildPreviewGroup", () => {
  it("returns null below two waypoints", () => {
    expect(buildPreviewGroup([], 0, 0.1)).toBeNull();
    expect(buildPreviewGroup([points()[0]], 0, 0.1)).toBeNull();
  });

  it("splits completed and future route segments", () => {
    const built = buildPreviewGroup(points(), 1, 0.1)!;
    expect(built.waypointCount).toBe(3);
    const lines = built.group.children.filter(
      (child): child is THREE.Line => child instanceof THREE.Line
    );
    expect(lines).toHaveLength(2);
    const colors = lines.map((line) => (line.material as THREE.LineBasicMaterial).color.getHex());
    expect(colors).toContain(PREVIEW_COMPLETED_COLOR);
    expect(colors).toContain(PREVIEW_FUTURE_COLOR);
    disposePreviewGroup(built.group);
  });

  it("marks start, end, and current waypoints distinctly", () => {
    const built = buildPreviewGroup(points(), 1, 0.1)!;
    const markers = built.group.children.filter(
      (child): child is THREE.Mesh => child instanceof THREE.Mesh
    );
    expect(markers).toHaveLength(3);
    const colors = markers.map((marker) => (marker.material as THREE.MeshBasicMaterial).color.getHex());
    expect(colors[0]).toBe(PREVIEW_START_COLOR);
    expect(colors[1]).toBe(PREVIEW_MIDDLE_COLOR);
    expect(colors[2]).toBe(PREVIEW_END_COLOR);
    expect(markers[1].scale.x).toBeGreaterThan(markers[0].scale.x);
    disposePreviewGroup(built.group);
  });

  it("marks every preview object non-pickable", () => {
    const built = buildPreviewGroup(points(), 0, 0.1)!;
    built.group.traverse((child) => {
      expect(child.userData.pickable === true).toBe(false);
    });
    disposePreviewGroup(built.group);
  });

  it("disposes every owned geometry and material", () => {
    const built = buildPreviewGroup(points(), 2, 0.1)!;
    const geometries = new Set<THREE.BufferGeometry>();
    const materials = new Set<THREE.Material>();
    built.group.traverse((child) => {
      if (child instanceof THREE.Line || child instanceof THREE.Mesh) {
        geometries.add(child.geometry);
        const material = child.material as THREE.Material;
        materials.add(material);
      }
    });
    expect(geometries.size).toBeGreaterThan(0);
    const geometrySpies = [...geometries].map((geometry) => {
      let calls = 0;
      const original = geometry.dispose.bind(geometry);
      geometry.dispose = () => {
        calls += 1;
        original();
      };
      return () => calls;
    });
    disposePreviewGroup(built.group);
    for (const calls of geometrySpies) {
      expect(calls()).toBe(1);
    }
    expect(materials.size).toBeGreaterThan(0);
  });
});
