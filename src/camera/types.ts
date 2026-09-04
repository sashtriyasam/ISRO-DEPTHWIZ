import * as THREE from "three";

export type ManualCameraMode = "orbit" | "first-person" | "aerial";

export const MANUAL_CAMERA_MODES: readonly ManualCameraMode[] = [
  "orbit",
  "first-person",
  "aerial",
];

export type CameraMode = ManualCameraMode | "trajectory";

export const CAMERA_MODES: readonly CameraMode[] = [...MANUAL_CAMERA_MODES, "trajectory"];

export function isCameraMode(value: string): value is CameraMode {
  return (CAMERA_MODES as readonly string[]).includes(value);
}

export interface CameraState {
  mode: CameraMode;
  position: THREE.Vector3;
  target: THREE.Vector3;
  distance: number;
}

export interface DisplayBounds {
  center: THREE.Vector3;
  size: THREE.Vector3;
  sphere: THREE.Sphere;
  box: THREE.Box3;
}

export interface OrbitControlsTuning {
  minDistance?: number;
  maxDistance?: number;
  minPolarAngle?: number;
  maxPolarAngle?: number;
  rotateSpeed?: number;
  zoomSpeed?: number;
  panSpeed?: number;
}

export interface CameraControllerOptions {
  camera: THREE.PerspectiveCamera;
  domElement: HTMLElement;
  target: THREE.Vector3;
  bounds: DisplayBounds;
  controls?: OrbitControlsTuning;
  initialDirection?: THREE.Vector3;
}

export interface CameraController {
  readonly mode: CameraMode;
  activate(): void;
  deactivate(): void;
  update(): void;
  resize(width: number, height: number): void;
  getState(): CameraState;
  setState(state: CameraState): void;
  frameBounds(bounds: DisplayBounds): void;
  reset(): void;
  dispose(): void;
}
