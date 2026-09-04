import { describe, it, expect } from "vitest";
import * as THREE from "three";
import {
  canPlayTrajectory,
  isPlaybackSpeed,
  isValidTrajectory,
  isValidWaypoint,
  trajectoryStatusForCount,
  DEFAULT_PLAYBACK_SPEED,
  DEFAULT_SEGMENT_DURATION_MS,
  PLAYBACK_SPEEDS,
  type FlythroughTrajectory,
} from "./types";
import {
  evaluateTrajectory,
  previewPoints,
  totalDurationMs,
  waypointIndexAt,
} from "./trajectory";

function waypoint(id: string, x: number, tx = 0, ty = 0, tz = 0) {
  return { id, position: { x, y: 4, z: 6 }, target: { x: tx, y: ty, z: tz } };
}

function trajectory(count: number): FlythroughTrajectory {
  const waypoints = Array.from({ length: count }, (_, i) => waypoint(`wp-${i + 1}`, i * 4));
  return { id: "traj-1", waypoints, segmentDurationMs: DEFAULT_SEGMENT_DURATION_MS };
}

describe("waypoint and trajectory validation", () => {
  it("accepts finite waypoints with ids", () => {
    expect(isValidWaypoint(waypoint("wp-1", 0))).toBe(true);
    expect(isValidWaypoint({ ...waypoint("wp-1", 0), id: "" })).toBe(false);
    expect(
      isValidWaypoint({ ...waypoint("wp-1", 0), position: { x: NaN, y: 0, z: 0 } })
    ).toBe(false);
  });

  it("validates trajectory structure", () => {
    expect(isValidTrajectory(trajectory(3))).toBe(true);
    expect(isValidTrajectory({ ...trajectory(2), segmentDurationMs: 0 })).toBe(false);
    expect(isValidTrajectory({ ...trajectory(2), segmentDurationMs: -5 })).toBe(false);
    expect(isValidTrajectory({ ...trajectory(2), id: "" })).toBe(false);
  });

  it("gates playback on two valid waypoints", () => {
    expect(canPlayTrajectory(trajectory(0))).toBe(false);
    expect(canPlayTrajectory(trajectory(1))).toBe(false);
    expect(canPlayTrajectory(trajectory(2))).toBe(true);
    expect(trajectoryStatusForCount(0)).toBe("idle");
    expect(trajectoryStatusForCount(1)).toBe("idle");
    expect(trajectoryStatusForCount(2)).toBe("ready");
  });

  it("restricts speeds to the typed set", () => {
    expect(PLAYBACK_SPEEDS).toEqual([0.5, 1, 2]);
    expect(DEFAULT_PLAYBACK_SPEED).toBe(1);
    expect(isPlaybackSpeed(1)).toBe(true);
    expect(isPlaybackSpeed(0.5)).toBe(true);
    expect(isPlaybackSpeed(3)).toBe(false);
    expect(isPlaybackSpeed(NaN)).toBe(false);
  });

  it("derives duration from segment count", () => {
    expect(totalDurationMs(trajectory(0))).toBe(0);
    expect(totalDurationMs(trajectory(1))).toBe(0);
    expect(totalDurationMs(trajectory(3))).toBe(2 * DEFAULT_SEGMENT_DURATION_MS);
  });
});

describe("evaluateTrajectory", () => {
  it("returns null below two waypoints", () => {
    expect(evaluateTrajectory(trajectory(0), 0)).toBeNull();
    expect(evaluateTrajectory(trajectory(1), 100)).toBeNull();
  });

  it("hits endpoints exactly without overshoot", () => {
    const traj = trajectory(2);
    const start = evaluateTrajectory(traj, 0)!;
    expect(start.position.x).toBeCloseTo(0);
    const end = evaluateTrajectory(traj, totalDurationMs(traj))!;
    expect(end.position.x).toBeCloseTo(4);
    const beyond = evaluateTrajectory(traj, totalDurationMs(traj) + 5000)!;
    expect(beyond.position.x).toBeCloseTo(4);
    const before = evaluateTrajectory(traj, -100)!;
    expect(before.position.x).toBeCloseTo(0);
  });

  it("interpolates linearly at segment midpoints", () => {
    const traj = trajectory(2);
    const mid = evaluateTrajectory(traj, DEFAULT_SEGMENT_DURATION_MS / 2)!;
    expect(mid.position.x).toBeCloseTo(2);
    expect(mid.position.y).toBeCloseTo(4);
    expect(mid.position.z).toBeCloseTo(6);
  });

  it("is deterministic for the same time", () => {
    const traj = trajectory(3);
    const first = evaluateTrajectory(traj, 1234)!;
    const second = evaluateTrajectory(traj, 1234)!;
    expect(first.position.distanceTo(second.position)).toBe(0);
    expect(first.quaternion.angleTo(second.quaternion)).toBe(0);
  });

  it("keeps orientation continuous across samples", () => {
    const traj = trajectory(3);
    const duration = totalDurationMs(traj);
    let previous: THREE.Quaternion | null = null;
    for (let i = 0; i <= 20; i++) {
      const pose = evaluateTrajectory(traj, (duration * i) / 20)!;
      expect(pose.quaternion.length()).toBeCloseTo(1);
      if (previous) {
        expect(pose.quaternion.angleTo(previous)).toBeLessThan(0.6);
      }
      previous = pose.quaternion;
    }
  });

  it("orients the camera toward each waypoint target", () => {
    const traj: FlythroughTrajectory = {
      id: "traj-look",
      waypoints: [
        { id: "wp-1", position: { x: 0, y: 5, z: 10 }, target: { x: 0, y: 0, z: 0 } },
        { id: "wp-2", position: { x: 0, y: 5, z: 10 }, target: { x: 0, y: 0, z: 0 } },
      ],
      segmentDurationMs: DEFAULT_SEGMENT_DURATION_MS,
    };
    const pose = evaluateTrajectory(traj, 0)!;
    const forward = new THREE.Vector3(0, 0, -1).applyQuaternion(pose.quaternion);
    const expected = new THREE.Vector3(0, -5, -10).normalize();
    expect(forward.distanceTo(expected)).toBeLessThan(1e-6);
  });

  it("reports waypoint indices along the path", () => {
    const traj = trajectory(3);
    expect(waypointIndexAt(traj, 0)).toBe(0);
    expect(waypointIndexAt(traj, DEFAULT_SEGMENT_DURATION_MS * 1.5)).toBe(1);
    expect(waypointIndexAt(traj, totalDurationMs(traj))).toBe(2);
    expect(waypointIndexAt(trajectory(0), 0)).toBe(-1);
  });

  it("exposes preview points matching waypoint positions", () => {
    const points = previewPoints(trajectory(2));
    expect(points).toHaveLength(2);
    expect(points[0].x).toBe(0);
    expect(points[1].x).toBe(4);
  });
});
