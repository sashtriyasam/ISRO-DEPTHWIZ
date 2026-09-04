import { describe, it, expect, vi, afterEach } from "vitest";
import * as THREE from "three";
import {
  FirstPersonCameraController,
  applyLookDelta,
  forwardVector,
  rightVector,
  inputFromCodes,
  baseSpeedForBounds,
  computeDisplacement,
  clampToBounds,
  startPoseForBounds,
  yawPitchForLookAt,
  isFirstPersonKey,
  FP_MAX_PITCH,
} from "./FirstPersonController";
import type { DisplayBounds } from "./types";

function testBounds(size = 8): DisplayBounds {
  const half = size / 2;
  return {
    center: new THREE.Vector3(0, 0, 0),
    size: new THREE.Vector3(size, size / 4, size),
    sphere: new THREE.Sphere(new THREE.Vector3(), size),
    box: new THREE.Box3(new THREE.Vector3(-half, -1, -half), new THREE.Vector3(half, 1, half)),
  };
}

function createMockDomElement() {
  return {
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
  } as unknown as HTMLElement;
}

function createController(size = 8) {
  const camera = new THREE.PerspectiveCamera(50, 800 / 600, 0.1, 100);
  const domElement = createMockDomElement();
  const bounds = testBounds(size);
  const controller = new FirstPersonCameraController({ camera, domElement, target: bounds.center.clone(), bounds });
  return { camera, domElement, bounds, controller };
}

afterEach(() => {
  window.dispatchEvent(new KeyboardEvent("keyup", { code: "KeyW" }));
});

describe("first-person look math", () => {
  it("turns right with positive horizontal drag", () => {
    const next = applyLookDelta(0, 0, 100, 0);
    expect(next.yaw).toBeLessThan(0);
    expect(next.pitch).toBe(0);
  });

  it("looks up with negative vertical drag and clamps pitch", () => {
    const next = applyLookDelta(0, 0, 0, -10000);
    expect(next.pitch).toBeCloseTo(FP_MAX_PITCH);
    const down = applyLookDelta(0, 0, 0, 10000);
    expect(down.pitch).toBeCloseTo(-FP_MAX_PITCH);
  });

  it("faces negative Z at zero yaw and pitch", () => {
    const forward = forwardVector(0, 0);
    expect(forward.x).toBeCloseTo(0);
    expect(forward.y).toBeCloseTo(0);
    expect(forward.z).toBeCloseTo(-1);
    const right = rightVector(0);
    expect(right.x).toBeCloseTo(1);
    expect(right.z).toBeCloseTo(0);
  });

  it("recovers yaw and pitch from a look-at", () => {
    const position = new THREE.Vector3(0, 4, 7);
    const target = new THREE.Vector3(0, 0, 0);
    const { yaw, pitch } = yawPitchForLookAt(position, target);
    const forward = forwardVector(yaw, pitch);
    const expected = target.clone().sub(position).normalize();
    expect(forward.x).toBeCloseTo(expected.x);
    expect(forward.y).toBeCloseTo(expected.y);
    expect(forward.z).toBeCloseTo(expected.z);
  });

  it("maps key codes to movement intents", () => {
    const input = inputFromCodes(new Set(["KeyW", "KeyA", "ShiftLeft"]));
    expect(input.forward).toBe(true);
    expect(input.left).toBe(true);
    expect(input.boost).toBe(true);
    expect(input.up).toBe(false);
    expect(isFirstPersonKey("KeyW")).toBe(true);
    expect(isFirstPersonKey("Space")).toBe(false);
    expect(isFirstPersonKey("Escape")).toBe(false);
  });
});

describe("first-person movement math", () => {
  it("derives base speed from display bounds", () => {
    expect(baseSpeedForBounds(testBounds(8))).toBeCloseTo(8 * 0.6);
    expect(baseSpeedForBounds(testBounds(0))).toBeCloseTo(0.6);
  });

  it("moves forward at speed over time", () => {
    const displacement = computeDisplacement(
      { forward: true, back: false, left: false, right: false, up: false, down: false, boost: false },
      0, 0, 4.8, 0.1
    );
    expect(displacement.length()).toBeCloseTo(0.48);
    expect(displacement.z).toBeLessThan(0);
  });

  it("normalizes diagonal movement and applies boost", () => {
    const plain = computeDisplacement(
      { forward: true, back: false, left: false, right: true, up: false, down: false, boost: false },
      0, 0, 4.8, 0.1
    );
    expect(plain.length()).toBeCloseTo(0.48);
    const boosted = computeDisplacement(
      { forward: true, back: false, left: false, right: false, up: false, down: false, boost: true },
      0, 0, 4.8, 0.1
    );
    expect(boosted.length()).toBeCloseTo(0.48 * 3);
  });

  it("clamps large time steps and stays still without input", () => {
    const idle = computeDisplacement(
      { forward: false, back: false, left: false, right: false, up: false, down: false, boost: false },
      0, 0, 4.8, 0.1
    );
    expect(idle.length()).toBe(0);
    const jump = computeDisplacement(
      { forward: true, back: false, left: false, right: false, up: false, down: false, boost: false },
      0, 0, 4.8, 10
    );
    expect(jump.length()).toBeCloseTo(4.8 * 0.1);
  });

  it("clamps positions to expanded display bounds", () => {
    const bounds = testBounds(8);
    const inside = new THREE.Vector3(0, 0, 0);
    expect(clampToBounds(inside, bounds)).toEqual(inside);
    const far = new THREE.Vector3(1000, 1000, 1000);
    const clamped = clampToBounds(far, bounds);
    expect(clamped.x).toBeLessThan(1000);
    expect(clamped.y).toBeLessThan(1000);
  });

  it("computes deterministic start poses above the center", () => {
    const bounds = testBounds(8);
    const first = startPoseForBounds(bounds);
    const second = startPoseForBounds(bounds);
    expect(first.position).toEqual(second.position);
    expect(first.target).toEqual(bounds.center);
    expect(first.position.y).toBeGreaterThan(bounds.center.y);
  });
});

describe("FirstPersonCameraController lifecycle", () => {
  it("starts posed toward the scene center", () => {
    const { camera, bounds, controller } = createController();
    expect(controller.mode).toBe("first-person");
    const state = controller.getState();
    expect(state.mode).toBe("first-person");
    expect(camera.position.y).toBeGreaterThan(bounds.center.y);
    controller.dispose();
  });

  it("attaches listeners on activate and removes them on deactivate", () => {
    const { domElement, controller } = createController();
    const add = domElement.addEventListener as unknown as ReturnType<typeof vi.fn>;
    const remove = domElement.removeEventListener as unknown as ReturnType<typeof vi.fn>;
    controller.activate();
    const addsAfterFirst = add.mock.calls.length;
    expect(addsAfterFirst).toBeGreaterThan(0);
    controller.activate();
    expect(add.mock.calls.length).toBe(addsAfterFirst);
    controller.deactivate();
    expect(remove.mock.calls.length).toBe(addsAfterFirst);
    controller.dispose();
  });

  it("moves with held keys through the update cycle", () => {
    const { camera, controller } = createController();
    controller.activate();
    const before = camera.position.clone();
    window.dispatchEvent(new KeyboardEvent("keydown", { code: "KeyW" }));
    controller.update(1000);
    controller.update(1100);
    expect(camera.position.distanceTo(before)).toBeGreaterThan(0);
    window.dispatchEvent(new KeyboardEvent("keyup", { code: "KeyW" }));
    controller.dispose();
  });

  it("ignores Escape (exit is owned by the application)", () => {
    const { camera, controller } = createController();
    controller.activate();
    const before = camera.position.clone();
    window.dispatchEvent(new KeyboardEvent("keydown", { code: "Escape" }));
    controller.update(1000);
    controller.update(1100);
    expect(camera.position.distanceTo(before)).toBe(0);
    controller.dispose();
  });

  it("does nothing before activation", () => {
    const { camera, controller } = createController();
    const before = camera.position.clone();
    window.dispatchEvent(new KeyboardEvent("keydown", { code: "KeyW" }));
    controller.update(1000);
    controller.update(1100);
    expect(camera.position.distanceTo(before)).toBe(0);
    window.dispatchEvent(new KeyboardEvent("keyup", { code: "KeyW" }));
    controller.dispose();
  });

  it("clamps speed multipliers and restores pose on reset", () => {
    const { camera, controller } = createController();
    controller.setSpeedMultiplier(100);
    expect(controller.getSpeedMultiplier()).toBe(10);
    controller.setSpeedMultiplier(NaN);
    expect(controller.getSpeedMultiplier()).toBe(1);
    const initial = camera.position.clone();
    camera.position.set(50, 50, 50);
    controller.reset();
    expect(camera.position.distanceTo(initial)).toBeLessThan(1e-6);
    controller.dispose();
  });

  it("adapts to new bounds and disposes idempotently", () => {
    const { camera, controller } = createController(8);
    controller.frameBounds(testBounds(20));
    expect(camera.position.y).toBeGreaterThan(4);
    controller.dispose();
    expect(() => controller.dispose()).not.toThrow();
    expect(() => controller.update()).not.toThrow();
  });
});
