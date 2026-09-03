import { describe, it, expect } from "vitest";
import * as THREE from "three";
import { computeDisplayBounds, computeFrameCameraPosition } from "./sceneBounds";

describe("computeDisplayBounds", () => {
  it("computes bounds from mesh objects", () => {
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute("position", new THREE.Float32BufferAttribute([
      -1, 0, -1,
       1, 0, -1,
      -1, 0,  1,
       1, 0,  1,
    ], 3));
    const mesh = new THREE.Mesh(geometry);
    const bounds = computeDisplayBounds([mesh]);

    expect(bounds.center.x).toBeCloseTo(0);
    expect(bounds.center.y).toBeCloseTo(0);
    expect(bounds.center.z).toBeCloseTo(0);
    expect(bounds.size.x).toBeCloseTo(2);
    expect(bounds.size.z).toBeCloseTo(2);
  });

  it("returns fallback bounds for empty input", () => {
    const bounds = computeDisplayBounds([]);
    expect(bounds.center.x).toBe(0);
    expect(bounds.size.x).toBe(2);
  });
});

describe("computeFrameCameraPosition", () => {
  it("returns position and target", () => {
    const bounds = {
      center: new THREE.Vector3(0, 0, 0),
      size: new THREE.Vector3(2, 1, 2),
      sphere: new THREE.Sphere(new THREE.Vector3(), 1.5),
      box: new THREE.Box3(new THREE.Vector3(-1, -0.5, -1), new THREE.Vector3(1, 0.5, 1)),
    };
    const result = computeFrameCameraPosition(bounds, 50, 16 / 9);
    expect(result.position).toBeInstanceOf(THREE.Vector3);
    expect(result.target).toBeInstanceOf(THREE.Vector3);
    expect(result.position.length()).toBeGreaterThan(0);
  });
});
