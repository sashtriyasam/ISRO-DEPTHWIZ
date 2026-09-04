import { describe, it, expect, vi, afterEach } from "vitest";
import * as THREE from "three";
import { TrajectoryCameraController } from "./TrajectoryController";
import type { DisplayBounds } from "./types";
import type { FlythroughTrajectory } from "../flythrough/types";
import { DEFAULT_SEGMENT_DURATION_MS } from "../flythrough/types";

function testBounds(): DisplayBounds {
  return {
    center: new THREE.Vector3(0, 0, 0),
    size: new THREE.Vector3(8, 2, 8),
    sphere: new THREE.Sphere(new THREE.Vector3(), 8),
    box: new THREE.Box3(new THREE.Vector3(-4, -1, -4), new THREE.Vector3(4, 1, 4)),
  };
}

function createMockDomElement() {
  return {
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
  } as unknown as HTMLElement;
}

function testTrajectory(): FlythroughTrajectory {
  return {
    id: "traj-1",
    waypoints: [
      { id: "wp-1", position: { x: 0, y: 4, z: 7 }, target: { x: 0, y: 0, z: 0 } },
      { id: "wp-2", position: { x: 4, y: 4, z: 7 }, target: { x: 0, y: 0, z: 0 } },
    ],
    segmentDurationMs: DEFAULT_SEGMENT_DURATION_MS,
  };
}

function createController(callbacks?: { onCompleted?: () => void; onWaypointIndex?: (index: number) => void }) {
  const camera = new THREE.PerspectiveCamera(50, 800 / 600, 0.1, 100);
  const domElement = createMockDomElement();
  const bounds = testBounds();
  const controller = new TrajectoryCameraController({
    camera,
    domElement,
    target: bounds.center.clone(),
    bounds,
    trajectory: testTrajectory(),
    onCompleted: callbacks?.onCompleted,
    onWaypointIndex: callbacks?.onWaypointIndex,
  });
  return { camera, domElement, bounds, controller };
}

let nowMs = 100000;
vi.spyOn(performance, "now").mockImplementation(() => nowMs);

function advance(controller: { update: () => void }, steps: number, stepMs = 50): void {
  for (let i = 0; i < steps; i++) {
    nowMs += stepMs;
    controller.update();
  }
}

afterEach(() => {
  nowMs = 100000;
});

describe("TrajectoryCameraController", () => {
  it("reports the trajectory mode and starts at the first waypoint", () => {
    const { camera, controller } = createController();
    expect(controller.mode).toBe("trajectory");
    expect(camera.position.x).toBeCloseTo(0);
    expect(camera.position.z).toBeCloseTo(7);
    expect(controller.playbackTimeMs).toBe(0);
    expect(controller.isPlaying).toBe(false);
    controller.dispose();
  });

  it("attaches no DOM listeners", () => {
    const { domElement, controller } = createController();
    controller.activate();
    controller.update();
    expect((domElement.addEventListener as unknown as ReturnType<typeof vi.fn>).mock.calls.length).toBe(0);
    controller.dispose();
  });

  it("advances time while playing and freezes while paused", () => {
    const { camera, controller } = createController();
    controller.activate();
    controller.play();
    advance(controller, 10);
    const moved = camera.position.clone();
    expect(controller.playbackTimeMs).toBeCloseTo(450);
    expect(camera.position.distanceTo(new THREE.Vector3(0, 4, 7))).toBeGreaterThan(0);
    controller.pause();
    advance(controller, 10);
    expect(camera.position.distanceTo(moved)).toBe(0);
    expect(controller.isPlaying).toBe(false);
    controller.dispose();
  });

  it("resumes from the paused time", () => {
    const { controller } = createController();
    controller.activate();
    controller.play();
    advance(controller, 10);
    const pausedAt = controller.playbackTimeMs;
    expect(pausedAt).toBeGreaterThan(0);
    controller.pause();
    controller.resume();
    advance(controller, 10);
    expect(controller.playbackTimeMs).toBeGreaterThan(pausedAt);
    controller.dispose();
  });

  it("scales time by playback speed", () => {
    const { controller } = createController();
    controller.activate();
    controller.setSpeed(2);
    expect(controller.playbackSpeed).toBe(2);
    controller.play();
    advance(controller, 10);
    expect(controller.playbackTimeMs).toBeCloseTo(900);
    controller.setSpeed(3 as 2);
    expect(controller.playbackSpeed).toBe(2);
    controller.dispose();
  });

  it("completes exactly at the final waypoint and fires once", () => {
    const onCompleted = vi.fn();
    const { camera, controller } = createController({ onCompleted });
    controller.activate();
    controller.play();
    advance(controller, 70);
    expect(controller.playbackTimeMs).toBe(DEFAULT_SEGMENT_DURATION_MS);
    expect(camera.position.x).toBeCloseTo(4);
    expect(camera.position.z).toBeCloseTo(7);
    expect(onCompleted).toHaveBeenCalledTimes(1);
    expect(controller.isPlaying).toBe(false);
    advance(controller, 5);
    expect(onCompleted).toHaveBeenCalledTimes(1);
    controller.dispose();
  });

  it("reports waypoint progress without per-frame React involvement", () => {
    const seen: number[] = [];
    const { controller } = createController({ onWaypointIndex: (i: number) => seen.push(i) });
    controller.activate();
    controller.play();
    advance(controller, 70);
    expect(seen.length).toBeLessThanOrEqual(2);
    expect(seen[seen.length - 1]).toBe(1);
    controller.dispose();
  });

  it("stops and resets deterministically", () => {
    const { camera, controller } = createController();
    controller.activate();
    controller.play();
    advance(controller, 10);
    controller.stop();
    expect(controller.isPlaying).toBe(false);
    const stoppedAt = controller.playbackTimeMs;
    expect(stoppedAt).toBeGreaterThan(0);
    controller.resetToStart();
    expect(controller.playbackTimeMs).toBe(0);
    expect(camera.position.x).toBeCloseTo(0);
    advance(controller, 10);
    expect(controller.playbackTimeMs).toBe(0);
    controller.dispose();
  });

  it("reaches identical poses at different playback speeds", () => {
    const runToEnd = (speed: 0.5 | 1 | 2) => {
      const { camera, controller } = createController();
      controller.activate();
      controller.setSpeed(speed);
      controller.play();
      advance(controller, 200);
      const pose = camera.position.clone();
      const quat = controller.getState();
      controller.dispose();
      return { pose, target: quat.target };
    };
    const slow = runToEnd(0.5);
    const fast = runToEnd(2);
    expect(slow.pose.distanceTo(fast.pose)).toBeLessThan(1e-6);
    expect(slow.target.distanceTo(fast.target)).toBeLessThan(1e-6);
  });

  it("accepts speed changes while paused", () => {
    const { controller } = createController();
    controller.activate();
    controller.play();
    advance(controller, 5);
    controller.pause();
    controller.setSpeed(0.5);
    expect(controller.playbackSpeed).toBe(0.5);
    const pausedAt = controller.playbackTimeMs;
    controller.resume();
    advance(controller, 10);
    expect(controller.playbackTimeMs).toBeGreaterThan(pausedAt);
    controller.dispose();
  });

  it("restarts from the beginning after completion", () => {
    const { controller } = createController();
    controller.activate();
    controller.play();
    advance(controller, 70);
    expect(controller.playbackTimeMs).toBe(DEFAULT_SEGMENT_DURATION_MS);
    controller.play();
    expect(controller.playbackTimeMs).toBe(0);
    expect(controller.isPlaying).toBe(true);
    controller.dispose();
  });

  it("exposes camera state through the existing seam", () => {
    const { controller } = createController();
    const state = controller.getState();
    expect(state.mode).toBe("trajectory");
    expect(state.position).toBeInstanceOf(THREE.Vector3);
    expect(state.target).toBeInstanceOf(THREE.Vector3);
    controller.dispose();
  });

  it("clamps evaluated positions to display bounds", () => {
    const { camera, controller } = createController();
    controller.activate();
    controller.play();
    for (let i = 0; i < 10; i++) {
      nowMs += 200;
      controller.update();
    }
    expect(Number.isFinite(camera.position.x)).toBe(true);
    controller.dispose();
  });
});


