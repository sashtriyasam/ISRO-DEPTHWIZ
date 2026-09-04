import { describe, it, expect, vi } from "vitest";
import * as THREE from "three";
import { CameraManager } from "./CameraManager";
import { TrajectoryCameraController } from "./TrajectoryController";
import { DEFAULT_SEGMENT_DURATION_MS } from "../flythrough/types";
import { CAMERA_MODES, MANUAL_CAMERA_MODES, isCameraMode } from "./types";

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

function testBounds() {
  return {
    center: new THREE.Vector3(0, 0, 0),
    size: new THREE.Vector3(8, 2, 8),
    sphere: new THREE.Sphere(new THREE.Vector3(), 8),
    box: new THREE.Box3(new THREE.Vector3(-4, -1, -4), new THREE.Vector3(4, 1, 4)),
  };
}

describe("camera modes", () => {
  it("declares orbit, first-person, aerial, and trajectory modes", () => {
    expect(CAMERA_MODES).toEqual(["orbit", "first-person", "aerial", "trajectory"]);
    expect(isCameraMode("orbit")).toBe(true);
    expect(isCameraMode("first-person")).toBe(true);
    expect(isCameraMode("aerial")).toBe(true);
    expect(isCameraMode("cinematic")).toBe(false);
  });
});

describe("mode switching", () => {
  it("cycles orbit → first-person → aerial → orbit with cleanup", () => {
    const camera = new THREE.PerspectiveCamera(50, 800 / 600, 0.1, 100);
    const domElement = createMockDomElement();
    const manager = new CameraManager(camera, domElement);
    const bounds = testBounds();
    try {
      manager.activate("orbit", bounds.center.clone(), bounds);
      expect(manager.getMode()).toBe("orbit");
      manager.activate("first-person", bounds.center.clone(), bounds);
      expect(manager.getMode()).toBe("first-person");
      manager.activate("aerial", bounds.center.clone(), bounds);
      expect(manager.getMode()).toBe("aerial");
      manager.activate("orbit", bounds.center.clone(), bounds);
      expect(manager.getMode()).toBe("orbit");
      const remove = domElement.removeEventListener as unknown as ReturnType<typeof vi.fn>;
      expect(remove.mock.calls.length).toBeGreaterThan(0);
    } finally {
      manager.dispose();
    }
  });

  it("delegates frame, reset, and state in every mode", () => {
    const camera = new THREE.PerspectiveCamera(50, 800 / 600, 0.1, 100);
    const domElement = createMockDomElement();
    const manager = new CameraManager(camera, domElement);
    const bounds = testBounds();
    try {
      for (const mode of MANUAL_CAMERA_MODES) {
        manager.activate(mode, bounds.center.clone(), bounds);
        expect(() => manager.frameBounds(bounds)).not.toThrow();
        expect(() => manager.reset()).not.toThrow();
        expect(() => manager.update()).not.toThrow();
        const state = manager.getState();
        expect(state).not.toBeNull();
        expect(state!.mode).toBe(mode);
      }
    } finally {
      manager.dispose();
    }
  });

  it("keeps the active controller when trajectory is requested without data", () => {
    const camera = new THREE.PerspectiveCamera(50, 800 / 600, 0.1, 100);
    const domElement = createMockDomElement();
    const manager = new CameraManager(camera, domElement);
    const bounds = testBounds();
    try {
      manager.activate("orbit", bounds.center.clone(), bounds);
      manager.activate("trajectory", bounds.center.clone(), bounds);
      expect(manager.getMode()).toBe("orbit");
    } finally {
      manager.dispose();
    }
  });

  it("injects trajectory controllers through the same seam", () => {
    const camera = new THREE.PerspectiveCamera(50, 800 / 600, 0.1, 100);
    const domElement = createMockDomElement();
    const manager = new CameraManager(camera, domElement);
    const bounds = testBounds();
    try {
      manager.activate("orbit", bounds.center.clone(), bounds);
      expect(manager.getMode()).toBe("orbit");
      const controller = new TrajectoryCameraController({
        camera,
        domElement,
        target: bounds.center.clone(),
        bounds,
        trajectory: {
          id: "traj-1",
          waypoints: [
            { id: "wp-1", position: { x: 0, y: 4, z: 7 }, target: { x: 0, y: 0, z: 0 } },
            { id: "wp-2", position: { x: 4, y: 4, z: 7 }, target: { x: 0, y: 0, z: 0 } },
          ],
          segmentDurationMs: DEFAULT_SEGMENT_DURATION_MS,
        },
      });
      manager.activateController(controller);
      expect(manager.getMode()).toBe("trajectory");
      expect(() => manager.update()).not.toThrow();
      manager.activate("orbit", bounds.center.clone(), bounds);
      expect(manager.getMode()).toBe("orbit");
      const remove = domElement.removeEventListener as unknown as ReturnType<typeof vi.fn>;
      expect(remove.mock.calls.length).toBeGreaterThan(0);
    } finally {
      manager.dispose();
    }
  });

  it("uses fresh bounds after artifact replacement in every mode", () => {
    const camera = new THREE.PerspectiveCamera(50, 800 / 600, 0.1, 100);
    const domElement = createMockDomElement();
    const manager = new CameraManager(camera, domElement);
    try {
      for (const mode of MANUAL_CAMERA_MODES) {
        manager.activate(mode, new THREE.Vector3(), testBounds());
        const before = camera.position.clone();
        const bigger = {
          center: new THREE.Vector3(10, 2, 10),
          size: new THREE.Vector3(40, 10, 40),
          sphere: new THREE.Sphere(new THREE.Vector3(10, 2, 10), 40),
          box: new THREE.Box3(new THREE.Vector3(-10, -3, -10), new THREE.Vector3(30, 7, 30)),
        };
        manager.frameBounds(bigger);
        expect(camera.position.distanceTo(before)).toBeGreaterThan(0);
      }
    } finally {
      manager.dispose();
    }
  });
});

