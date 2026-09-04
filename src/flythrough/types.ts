export interface WaypointPosition {
  x: number;
  y: number;
  z: number;
}

export interface FlythroughWaypoint {
  id: string;
  position: WaypointPosition;
  target: WaypointPosition;
}

export interface FlythroughTrajectory {
  id: string;
  waypoints: readonly FlythroughWaypoint[];
  segmentDurationMs: number;
}

export type PlaybackSpeed = 0.5 | 1 | 2;

export const PLAYBACK_SPEEDS: readonly PlaybackSpeed[] = [0.5, 1, 2];

export const DEFAULT_PLAYBACK_SPEED: PlaybackSpeed = 1;

export const DEFAULT_SEGMENT_DURATION_MS = 3000;

export function isPlaybackSpeed(value: number): value is PlaybackSpeed {
  return (PLAYBACK_SPEEDS as readonly number[]).includes(value);
}

export type PlaybackStatus = "idle" | "ready" | "playing" | "paused" | "completed";

function isFinitePosition(p: WaypointPosition): boolean {
  return Number.isFinite(p.x) && Number.isFinite(p.y) && Number.isFinite(p.z);
}

export function isValidWaypoint(waypoint: FlythroughWaypoint): boolean {
  return (
    typeof waypoint.id === "string" &&
    waypoint.id.length > 0 &&
    isFinitePosition(waypoint.position) &&
    isFinitePosition(waypoint.target)
  );
}

export function isValidTrajectory(trajectory: FlythroughTrajectory): boolean {
  return (
    typeof trajectory.id === "string" &&
    trajectory.id.length > 0 &&
    Number.isFinite(trajectory.segmentDurationMs) &&
    trajectory.segmentDurationMs > 0 &&
    trajectory.waypoints.every(isValidWaypoint)
  );
}

export function canPlayTrajectory(trajectory: FlythroughTrajectory): boolean {
  return isValidTrajectory(trajectory) && trajectory.waypoints.length >= 2;
}

export function trajectoryStatusForCount(count: number): PlaybackStatus {
  if (count >= 2) {
    return "ready";
  }
  return "idle";
}
