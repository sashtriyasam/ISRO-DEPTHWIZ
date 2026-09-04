import * as THREE from "three";
import type { CameraController, CameraControllerOptions, CameraState, DisplayBounds } from "./types";
import { clampToBounds } from "./FirstPersonController";
import type { FlythroughTrajectory, PlaybackSpeed } from "../flythrough/types";
import { DEFAULT_PLAYBACK_SPEED, isPlaybackSpeed } from "../flythrough/types";
import { evaluateTrajectory, totalDurationMs } from "../flythrough/trajectory";

export interface TrajectoryPlaybackOptions extends CameraControllerOptions {
  trajectory: FlythroughTrajectory;
  speed?: PlaybackSpeed;
  onCompleted?: () => void;
  onWaypointIndex?: (index: number) => void;
}

const MAX_FRAME_DT_MS = 100;

export class TrajectoryCameraController implements CameraController {
  readonly mode = "trajectory" as const;

  private camera: THREE.PerspectiveCamera;
  private bounds: DisplayBounds;
  private trajectory: FlythroughTrajectory;
  private speed: PlaybackSpeed;
  private onCompleted: (() => void) | null;
  private onWaypointIndex: ((index: number) => void) | null;
  private homeTarget: THREE.Vector3;
  private timeMs = 0;
  private playing = false;
  private completedFired = false;
  private lastNowMs: number | null = null;
  private lastIndex = 0;
  private active = false;
  private disposed = false;

  constructor(options: TrajectoryPlaybackOptions) {
    this.camera = options.camera;
    this.bounds = options.bounds;
    this.trajectory = options.trajectory;
    this.speed = options.speed ?? DEFAULT_PLAYBACK_SPEED;
    this.onCompleted = options.onCompleted ?? null;
    this.onWaypointIndex = options.onWaypointIndex ?? null;
    this.homeTarget = options.target.clone();
    this.applyTime(0);
  }

  get playbackTimeMs(): number {
    return this.timeMs;
  }

  get totalMs(): number {
    return totalDurationMs(this.trajectory);
  }

  get isPlaying(): boolean {
    return this.playing;
  }

  get playbackSpeed(): PlaybackSpeed {
    return this.speed;
  }

  setSpeed(speed: PlaybackSpeed): void {
    if (!isPlaybackSpeed(speed)) {
      return;
    }
    this.speed = speed;
  }

  play(): void {
    if (this.disposed) return;
    if (this.timeMs >= this.totalMs) {
      this.timeMs = 0;
      this.completedFired = false;
    }
    this.playing = true;
    this.lastNowMs = null;
  }

  pause(): void {
    this.playing = false;
    this.lastNowMs = null;
  }

  resume(): void {
    if (this.disposed || this.timeMs >= this.totalMs) return;
    this.playing = true;
    this.lastNowMs = null;
  }

  stop(): void {
    this.playing = false;
    this.lastNowMs = null;
  }

  resetToStart(): void {
    this.timeMs = 0;
    this.completedFired = false;
    this.lastIndex = 0;
    this.lastNowMs = null;
    this.applyTime(0);
  }

  private applyTime(timeMs: number): void {
    const pose = evaluateTrajectory(this.trajectory, timeMs);
    if (!pose) return;
    this.camera.position.copy(clampToBounds(pose.position, this.bounds));
    this.camera.quaternion.copy(pose.quaternion);
  }

  private waypointIndexAt(timeMs: number): number {
    const count = this.trajectory.waypoints.length;
    if (count === 0) return -1;
    const duration = this.totalMs;
    if (duration <= 0) return 0;
    const clamped = Math.max(0, Math.min(duration, timeMs));
    return Math.min(Math.floor(clamped / this.trajectory.segmentDurationMs), count - 1);
  }

  activate(): void {
    if (this.disposed || this.active) return;
    this.active = true;
    this.lastNowMs = null;
  }

  deactivate(): void {
    this.active = false;
    this.playing = false;
    this.lastNowMs = null;
  }

  update(): void {
    if (!this.active || this.disposed || !this.playing) return;
    const now = performance.now();
    if (this.lastNowMs === null) {
      this.lastNowMs = now;
      return;
    }
    const dt = Math.max(0, Math.min(MAX_FRAME_DT_MS, now - this.lastNowMs));
    this.lastNowMs = now;
    this.timeMs = Math.min(this.totalMs, this.timeMs + dt * this.speed);
    this.applyTime(this.timeMs);
    const index = this.waypointIndexAt(this.timeMs);
    if (index !== this.lastIndex) {
      this.lastIndex = index;
      this.onWaypointIndex?.(index);
    }
    if (this.timeMs >= this.totalMs) {
      this.playing = false;
      if (!this.completedFired) {
        this.completedFired = true;
        this.onCompleted?.();
      }
    }
  }

  resize(width: number, height: number): void {
    this.camera.aspect = width / height;
    this.camera.updateProjectionMatrix();
  }

  getState(): CameraState {
    const forward = new THREE.Vector3(0, 0, -1).applyQuaternion(this.camera.quaternion);
    return {
      mode: this.mode,
      position: this.camera.position.clone(),
      target: this.camera.position.clone().add(forward),
      distance: this.camera.position.distanceTo(this.homeTarget),
    };
  }

  setState(state: CameraState): void {
    this.camera.position.copy(state.position);
    this.camera.lookAt(state.target);
  }

  frameBounds(bounds: DisplayBounds): void {
    this.bounds = bounds;
  }

  reset(): void {
    this.resetToStart();
  }

  dispose(): void {
    if (this.disposed) return;
    this.deactivate();
    this.onCompleted = null;
    this.onWaypointIndex = null;
    this.disposed = true;
  }
}
