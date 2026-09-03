import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import type { CameraController, CameraControllerOptions, CameraState, DisplayBounds } from "./types";
import { computeFrameCameraPosition } from "./sceneBounds";

const MIN_DISTANCE = 0.5;
const MAX_DISTANCE = 50;

export class OrbitCameraController implements CameraController {
  readonly mode = "orbit" as const;

  private controls: OrbitControls;
  private camera: THREE.PerspectiveCamera;
  private initialState: { position: THREE.Vector3; target: THREE.Vector3 };

  constructor(options: CameraControllerOptions) {
    this.camera = options.camera;
    this.controls = new OrbitControls(options.camera, options.domElement);

    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.08;
    this.controls.rotateSpeed = 0.8;
    this.controls.zoomSpeed = 1.0;
    this.controls.panSpeed = 0.8;
    this.controls.minDistance = MIN_DISTANCE;
    this.controls.maxDistance = MAX_DISTANCE;
    this.controls.maxPolarAngle = Math.PI * 0.85;
    this.controls.minPolarAngle = 0.05;
    this.controls.target.copy(options.target);
    this.controls.update();

    this.initialState = {
      position: options.camera.position.clone(),
      target: options.target.clone(),
    };
  }

  activate(): void {
    this.controls.enabled = true;
  }

  deactivate(): void {
    this.controls.enabled = false;
  }

  update(): void {
    this.controls.update();
  }

  resize(width: number, height: number): void {
    this.camera.aspect = width / height;
    this.camera.updateProjectionMatrix();
  }

  getState(): CameraState {
    return {
      mode: this.mode,
      position: this.camera.position.clone(),
      target: this.controls.target.clone(),
      distance: this.camera.position.distanceTo(this.controls.target),
    };
  }

  setState(state: CameraState): void {
    this.camera.position.copy(state.position);
    this.controls.target.copy(state.target);
    this.controls.update();
  }

  frameBounds(bounds: DisplayBounds): void {
    const { position, target } = computeFrameCameraPosition(
      { center: bounds.center, size: bounds.size, sphere: bounds.sphere, box: bounds.box },
      this.camera.fov,
      this.camera.aspect
    );
    this.camera.position.copy(position);
    this.controls.target.copy(target);
    this.controls.update();
  }

  reset(): void {
    this.camera.position.copy(this.initialState.position);
    this.controls.target.copy(this.initialState.target);
    this.controls.update();
  }

  dispose(): void {
    this.controls.dispose();
  }
}
