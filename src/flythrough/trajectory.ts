import * as THREE from "three";
import type { FlythroughTrajectory } from "./types";

export interface EvaluatedPose {
  position: THREE.Vector3;
  quaternion: THREE.Quaternion;
}

const UP = new THREE.Vector3(0, 1, 0);

function orientationForSegment(from: THREE.Vector3, to: THREE.Vector3): THREE.Quaternion {
  const matrix = new THREE.Matrix4().lookAt(from, to, UP);
  return new THREE.Quaternion().setFromRotationMatrix(matrix);
}

export function totalDurationMs(trajectory: FlythroughTrajectory): number {
  const segments = Math.max(0, trajectory.waypoints.length - 1);
  return segments * trajectory.segmentDurationMs;
}

export function waypointIndexAt(trajectory: FlythroughTrajectory, timeMs: number): number {
  const count = trajectory.waypoints.length;
  if (count === 0) {
    return -1;
  }
  if (count === 1 || trajectory.segmentDurationMs <= 0) {
    return 0;
  }
  const clamped = Math.max(0, Math.min(totalDurationMs(trajectory), timeMs));
  const index = Math.floor(clamped / trajectory.segmentDurationMs);
  return Math.min(index, count - 1);
}

export function evaluateTrajectory(
  trajectory: FlythroughTrajectory,
  timeMs: number
): EvaluatedPose | null {
  const waypoints = trajectory.waypoints;
  if (waypoints.length < 2 || !(trajectory.segmentDurationMs > 0)) {
    return null;
  }
  const duration = totalDurationMs(trajectory);
  const clamped = Math.max(0, Math.min(duration, timeMs));
  const rawIndex = Math.floor(clamped / trajectory.segmentDurationMs);
  const index = Math.min(rawIndex, waypoints.length - 2);
  const u = Math.max(0, Math.min(1, (clamped - index * trajectory.segmentDurationMs) / trajectory.segmentDurationMs));

  const a = waypoints[index];
  const b = waypoints[index + 1];
  const aPos = new THREE.Vector3(a.position.x, a.position.y, a.position.z);
  const bPos = new THREE.Vector3(b.position.x, b.position.y, b.position.z);
  const position = aPos.clone().lerp(bPos, u);

  const aTarget = new THREE.Vector3(a.target.x, a.target.y, a.target.z);
  const bTarget = new THREE.Vector3(b.target.x, b.target.y, b.target.z);
  const aQuat = orientationForSegment(aPos, aTarget);
  const bQuat = orientationForSegment(bPos, bTarget);
  const quaternion = aQuat.clone().slerp(bQuat, u);

  return { position, quaternion };
}

export function previewPoints(trajectory: FlythroughTrajectory): THREE.Vector3[] {
  return trajectory.waypoints.map(
    (w) => new THREE.Vector3(w.position.x, w.position.y, w.position.z)
  );
}
