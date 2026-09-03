import * as THREE from "three";

export type CameraMode = "orbit";

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

export interface CameraControllerOptions {
  camera: THREE.PerspectiveCamera;
  domElement: HTMLElement;
  target: THREE.Vector3;
  bounds: DisplayBounds;
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
