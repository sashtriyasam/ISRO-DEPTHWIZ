import * as THREE from "three";
import type { CameraController, CameraControllerOptions, CameraState, DisplayBounds } from "./types";

export const FP_SENSITIVITY = 0.0035;
export const FP_MAX_PITCH = 1.45;
export const FP_BASE_SPEED_FACTOR = 0.6;
export const FP_BOOST_MULTIPLIER = 3;
export const FP_MAX_DT = 0.1;

const FORWARD_KEYS = new Set(["KeyW"]);
const BACK_KEYS = new Set(["KeyS"]);
const LEFT_KEYS = new Set(["KeyA"]);
const RIGHT_KEYS = new Set(["KeyD"]);
const UP_KEYS = new Set(["KeyE"]);
const DOWN_KEYS = new Set(["KeyQ"]);
const BOOST_KEYS = new Set(["ShiftLeft", "ShiftRight"]);
const HANDLED_CODES = new Set([...FORWARD_KEYS, ...BACK_KEYS, ...LEFT_KEYS, ...RIGHT_KEYS, ...UP_KEYS, ...DOWN_KEYS, ...BOOST_KEYS]);

export function isFirstPersonKey(code: string): boolean {
  return HANDLED_CODES.has(code);
}

export function applyLookDelta(yaw: number, pitch: number, dx: number, dy: number): { yaw: number; pitch: number } {
  const nextPitch = Math.max(-FP_MAX_PITCH, Math.min(FP_MAX_PITCH, pitch - dy * FP_SENSITIVITY));
  return { yaw: yaw - dx * FP_SENSITIVITY, pitch: nextPitch };
}

export function forwardVector(yaw: number, pitch: number): THREE.Vector3 {
  const cosPitch = Math.cos(pitch);
  return new THREE.Vector3(
    -Math.sin(yaw) * cosPitch,
    Math.sin(pitch),
    -Math.cos(yaw) * cosPitch
  );
}

export function rightVector(yaw: number): THREE.Vector3 {
  return new THREE.Vector3(Math.cos(yaw), 0, -Math.sin(yaw));
}

export interface FirstPersonInput {
  forward: boolean;
  back: boolean;
  left: boolean;
  right: boolean;
  up: boolean;
  down: boolean;
  boost: boolean;
}

export function inputFromCodes(codes: Set<string>): FirstPersonInput {
  const has = (keys: Set<string>): boolean => {
    for (const code of keys) {
      if (codes.has(code)) {
        return true;
      }
    }
    return false;
  };
  return {
    forward: has(FORWARD_KEYS),
    back: has(BACK_KEYS),
    left: has(LEFT_KEYS),
    right: has(RIGHT_KEYS),
    up: has(UP_KEYS),
    down: has(DOWN_KEYS),
    boost: has(BOOST_KEYS),
  };
}

export function baseSpeedForBounds(bounds: DisplayBounds): number {
  const reference = Math.max(bounds.size.x, bounds.size.y, bounds.size.z, 1);
  return reference * FP_BASE_SPEED_FACTOR;
}

export function computeDisplacement(
  input: FirstPersonInput,
  yaw: number,
  pitch: number,
  speed: number,
  dt: number
): THREE.Vector3 {
  const displacement = new THREE.Vector3();
  if (input.forward) displacement.add(forwardVector(yaw, pitch));
  if (input.back) displacement.sub(forwardVector(yaw, pitch));
  if (input.right) displacement.add(rightVector(yaw));
  if (input.left) displacement.sub(rightVector(yaw));
  if (input.up) displacement.y += 1;
  if (input.down) displacement.y -= 1;
  if (displacement.lengthSq() === 0) {
    return displacement;
  }
  displacement.normalize();
  const boost = input.boost ? FP_BOOST_MULTIPLIER : 1;
  const clampedDt = Math.max(0, Math.min(FP_MAX_DT, dt));
  return displacement.multiplyScalar(speed * boost * clampedDt);
}

export function clampToBounds(position: THREE.Vector3, bounds: DisplayBounds): THREE.Vector3 {
  const margin = Math.max(bounds.size.x, bounds.size.y, bounds.size.z, 1) * 0.5;
  const min = bounds.box.min.clone().add(new THREE.Vector3(-margin, -margin, -margin));
  const max = bounds.box.max.clone().add(new THREE.Vector3(margin, margin, margin));
  return new THREE.Vector3(
    Math.max(min.x, Math.min(max.x, position.x)),
    Math.max(min.y, Math.min(max.y, position.y)),
    Math.max(min.z, Math.min(max.z, position.z))
  );
}

export function startPoseForBounds(bounds: DisplayBounds): { position: THREE.Vector3; target: THREE.Vector3 } {
  const maxDim = Math.max(bounds.size.x, bounds.size.y, bounds.size.z, 1);
  const position = bounds.center.clone().add(new THREE.Vector3(0, maxDim * 0.55, maxDim * 0.85));
  return { position, target: bounds.center.clone() };
}

export function yawPitchForLookAt(position: THREE.Vector3, target: THREE.Vector3): { yaw: number; pitch: number } {
  const dir = target.clone().sub(position);
  const length = dir.length() || 1;
  dir.divideScalar(length);
  return {
    yaw: Math.atan2(-dir.x, -dir.z),
    pitch: Math.asin(Math.max(-1, Math.min(1, dir.y))),
  };
}

export interface FirstPersonOptions extends CameraControllerOptions {
  speedMultiplier?: number;
}

function clampSpeedMultiplier(value: number): number {
  if (!Number.isFinite(value)) {
    return 1;
  }
  return Math.max(0.1, Math.min(10, value));
}

export class FirstPersonCameraController implements CameraController {
  readonly mode = "first-person" as const;

  private camera: THREE.PerspectiveCamera;
  private domElement: HTMLElement;
  private bounds: DisplayBounds;
  private baseSpeed: number;
  private speedMultiplier: number;
  private yaw: number;
  private pitch: number;
  private keys = new Set<string>();
  private dragging = false;
  private lastPointer = { x: 0, y: 0 };
  private lastUpdateMs: number | null = null;
  private initialPose: { position: THREE.Vector3; target: THREE.Vector3 };
  private active = false;
  private disposed = false;

  constructor(options: FirstPersonOptions) {
    this.camera = options.camera;
    this.domElement = options.domElement;
    this.bounds = options.bounds;
    this.baseSpeed = baseSpeedForBounds(options.bounds);
    this.speedMultiplier = clampSpeedMultiplier(options.speedMultiplier ?? 1);
    this.initialPose = startPoseForBounds(options.bounds);
    const angles = yawPitchForLookAt(this.initialPose.position, this.initialPose.target);
    this.yaw = angles.yaw;
    this.pitch = angles.pitch;
    this.camera.position.copy(this.initialPose.position);
    this.applyOrientation();
  }

  setSpeedMultiplier(value: number): void {
    this.speedMultiplier = clampSpeedMultiplier(value);
  }

  getSpeedMultiplier(): number {
    return this.speedMultiplier;
  }

  get baseSpeedValue(): number {
    return this.baseSpeed;
  }

  private applyOrientation(): void {
    const forward = forwardVector(this.yaw, this.pitch);
    this.camera.lookAt(this.camera.position.clone().add(forward));
  }

  private onPointerDown = (event: PointerEvent): void => {
    if (!this.active || this.disposed) return;
    if (event.button !== 0 && event.pointerType === "mouse") return;
    this.dragging = true;
    this.lastPointer = { x: event.clientX, y: event.clientY };
  };

  private onPointerMove = (event: PointerEvent): void => {
    if (!this.active || this.disposed || !this.dragging) return;
    const dx = event.clientX - this.lastPointer.x;
    const dy = event.clientY - this.lastPointer.y;
    this.lastPointer = { x: event.clientX, y: event.clientY };
    const next = applyLookDelta(this.yaw, this.pitch, dx, dy);
    this.yaw = next.yaw;
    this.pitch = next.pitch;
    this.applyOrientation();
  };

  private onPointerUp = (): void => {
    this.dragging = false;
  };

  private onKeyDown = (event: KeyboardEvent): void => {
    if (!this.active || this.disposed) return;
    if (!isFirstPersonKey(event.code)) return;
    event.preventDefault();
    this.keys.add(event.code);
  };

  private onKeyUp = (event: KeyboardEvent): void => {
    this.keys.delete(event.code);
  };

  activate(): void {
    if (this.disposed || this.active) return;
    this.active = true;
    this.lastUpdateMs = null;
    this.domElement.addEventListener("pointerdown", this.onPointerDown);
    this.domElement.addEventListener("pointermove", this.onPointerMove);
    this.domElement.addEventListener("pointerup", this.onPointerUp);
    this.domElement.addEventListener("pointercancel", this.onPointerUp);
    window.addEventListener("keydown", this.onKeyDown);
    window.addEventListener("keyup", this.onKeyUp);
  }

  deactivate(): void {
    if (!this.active) return;
    this.active = false;
    this.dragging = false;
    this.keys.clear();
    this.domElement.removeEventListener("pointerdown", this.onPointerDown);
    this.domElement.removeEventListener("pointermove", this.onPointerMove);
    this.domElement.removeEventListener("pointerup", this.onPointerUp);
    this.domElement.removeEventListener("pointercancel", this.onPointerUp);
    window.removeEventListener("keydown", this.onKeyDown);
    window.removeEventListener("keyup", this.onKeyUp);
  }

  update(nowMs?: number): void {
    if (!this.active || this.disposed) return;
    const now = nowMs ?? performance.now();
    if (this.lastUpdateMs === null) {
      this.lastUpdateMs = now;
      return;
    }
    const dt = (now - this.lastUpdateMs) / 1000;
    this.lastUpdateMs = now;
    const displacement = computeDisplacement(
      inputFromCodes(this.keys),
      this.yaw,
      this.pitch,
      this.baseSpeed * this.speedMultiplier,
      dt
    );
    if (displacement.lengthSq() > 0) {
      this.camera.position.add(displacement);
      this.camera.position.copy(clampToBounds(this.camera.position, this.bounds));
    }
  }

  resize(width: number, height: number): void {
    this.camera.aspect = width / height;
    this.camera.updateProjectionMatrix();
  }

  getState(): CameraState {
    const forward = forwardVector(this.yaw, this.pitch);
    return {
      mode: this.mode,
      position: this.camera.position.clone(),
      target: this.camera.position.clone().add(forward),
      distance: this.camera.position.distanceTo(this.initialPose.target),
    };
  }

  setState(state: CameraState): void {
    this.camera.position.copy(state.position);
    const angles = yawPitchForLookAt(state.position, state.target);
    this.yaw = angles.yaw;
    this.pitch = angles.pitch;
    this.applyOrientation();
  }

  frameBounds(bounds: DisplayBounds): void {
    this.bounds = bounds;
    this.baseSpeed = baseSpeedForBounds(bounds);
    this.initialPose = startPoseForBounds(bounds);
    this.camera.position.copy(this.initialPose.position);
    const angles = yawPitchForLookAt(this.initialPose.position, this.initialPose.target);
    this.yaw = angles.yaw;
    this.pitch = angles.pitch;
    this.applyOrientation();
  }

  reset(): void {
    this.camera.position.copy(this.initialPose.position);
    const angles = yawPitchForLookAt(this.initialPose.position, this.initialPose.target);
    this.yaw = angles.yaw;
    this.pitch = angles.pitch;
    this.applyOrientation();
  }

  dispose(): void {
    if (this.disposed) return;
    this.deactivate();
    this.disposed = true;
  }
}
