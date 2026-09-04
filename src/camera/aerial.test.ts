import { describe, it, expect, vi } from "vitest";
import * as THREE from "three";
import { AerialCameraController, aerialDistanceForBounds } from "./AerialController";
import type { DisplayBounds } from "./types";

function testBounds(size = 8, height = 2): DisplayBounds {
  const half = size / 2;
  return {
    center: new THREE.Vector3(0, 0, 0),
    size: new THREE.Vector3(size, height, size),
    sphere: new THREE.Sphere(new THREE.Vector3(), size),
    box: new THREE.Box3(new THREE.Vector3(-half, -1, -half), new THREE.Vector3(half, 1, half)),
  };
}

function createMockDomElement() {
  return {
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    clientWidth: 800,
    clientHeight: 600,
    ownerDocument: { defaultView: null },
    getRootNode: () => ({ addEventListener: vi.fn(), removeEventListener: vi.fn() }),
    style: { touchAction: "" },
    tagName: "DIV",
    getBoundingClientRect: () => ({ left: 0, top: 0, width: 800, height: 600 }),
  } as unknown as HTMLElement;
}

function createController(size = 8) {
  const camera = new THREE.PerspectiveCamera(50, 800 / 600, 0.1, 100);
  camera.position.set(6, 5, 6);
  const domElement = createMockDomElement();
  const bounds = testBounds(size);
  const controller = new AerialCameraController({
    camera,
    domElement,
    target: bounds.center.clone(),
    bounds,
  });
  return { camera, domElement, bounds, controller };
}

describe("aerialDistanceForBounds", () => {
  it("scales with scene size without hardcoding", () => {
    const near = aerialDistanceForBounds(testBounds(4), 50);
    const far = aerialDistanceForBounds(testBounds(16), 50);
    expect(far).toBeGreaterThan(near);
    expect(near).toBeGreaterThan(0);
  });
});

describe("AerialCameraController", () => {
  it("starts above the scene looking at the center", () => {
    const { camera, bounds, controller } = createController();
    expect(controller.mode).toBe("aerial");
    expect(camera.position.y).toBeGreaterThan(bounds.center.y + bounds.size.x);
    const state = controller.getState();
    expect(state.mode).toBe("aerial");
    expect(state.target.distanceTo(bounds.center)).toBeLessThan(1e-6);
    controller.dispose();
  });

  it("clamps the polar angle for overview inspection", () => {
    const { controller } = createController();
    const inner = controller as unknown as {
      inner: { controls: { maxPolarAngle: number } };
    };
    expect(inner.inner.controls.maxPolarAngle).toBeLessThan(Math.PI / 2);
    controller.dispose();
  });

  it("adapts framing to new bounds", () => {
    const { camera, controller } = createController(8);
    const before = camera.position.clone();
    controller.frameBounds(testBounds(24));
    expect(camera.position.distanceTo(before)).toBeGreaterThan(0);
    expect(camera.position.y).toBeGreaterThan(12);
    controller.dispose();
  });

  it("adapts to vertically exaggerated display bounds", () => {
    const flat = testBounds(8, 2);
    const exaggerated = testBounds(8, 20);
    const first = createController();
    first.controller.frameBounds(flat);
    const flatY = first.camera.position.y;
    first.controller.dispose();
    const second = createController();
    second.controller.frameBounds(exaggerated);
    expect(second.camera.position.y).toBeGreaterThan(flatY);
    second.controller.dispose();
  });

  it("resets to the aerial pose", () => {
    const { camera, controller } = createController();
    const initial = camera.position.clone();
    camera.position.set(1, 1, 1);
    controller.reset();
    expect(camera.position.distanceTo(initial)).toBeLessThan(1e-6);
    controller.dispose();
  });

  it("activates, updates, and disposes cleanly", () => {
    const { controller } = createController();
    expect(() => {
      controller.activate();
      controller.update();
      controller.deactivate();
      controller.dispose();
    }).not.toThrow();
  });
});
