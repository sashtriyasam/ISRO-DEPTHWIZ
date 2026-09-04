import * as THREE from "three";
import { OrbitCameraController } from "./OrbitController";
import type { CameraController, CameraControllerOptions, CameraState, DisplayBounds } from "./types";

const AERIAL_DIRECTION = new THREE.Vector3(0.18, 1, 0.18);
const AERIAL_MAX_POLAR_ANGLE = 0.5;

export function aerialDistanceForBounds(bounds: DisplayBounds, fovDegrees: number): number {
  const maxDim = Math.max(bounds.size.x, bounds.size.y, bounds.size.z, 1);
  const fovRad = (fovDegrees * Math.PI) / 180;
  return ((maxDim / 2) / Math.tan(fovRad / 2)) * 1.6;
}

export class AerialCameraController implements CameraController {
  readonly mode = "aerial" as const;

  private inner: OrbitCameraController;
  private lastBounds: DisplayBounds;

  constructor(options: CameraControllerOptions) {
    const distance = aerialDistanceForBounds(options.bounds, options.camera.fov);
    this.inner = new OrbitCameraController({
      ...options,
      controls: {
        ...(options.controls ?? {}),
        maxPolarAngle: options.controls?.maxPolarAngle ?? AERIAL_MAX_POLAR_ANGLE,
        minDistance: options.controls?.minDistance ?? Math.max(0.5, distance * 0.15),
        maxDistance: options.controls?.maxDistance ?? Math.max(50, distance * 2.5),
      },
      initialDirection: options.initialDirection ?? AERIAL_DIRECTION,
    });
    this.lastBounds = options.bounds;
    this.frameBounds(options.bounds);
  }

  activate(): void {
    this.inner.activate();
  }

  deactivate(): void {
    this.inner.deactivate();
  }

  update(): void {
    this.inner.update();
  }

  resize(width: number, height: number): void {
    this.inner.resize(width, height);
  }

  getState(): CameraState {
    const state = this.inner.getState();
    return { ...state, mode: this.mode };
  }

  setState(state: CameraState): void {
    this.inner.setState(state);
  }

  frameBounds(bounds: DisplayBounds): void {
    this.lastBounds = bounds;
    this.inner.frameBounds(bounds);
  }

  reset(): void {
    this.frameBounds(this.lastBounds);
  }

  dispose(): void {
    this.inner.dispose();
  }
}
