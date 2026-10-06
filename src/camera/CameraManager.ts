import * as THREE from "three";
import type { CameraController, CameraMode, DisplayBounds } from "./types";
import { OrbitCameraController } from "./OrbitController";
import { FirstPersonCameraController } from "./FirstPersonController";
import { AerialCameraController } from "./AerialController";
import { fitClipPlanes } from "./sceneBounds";

export class CameraManager {
  private activeController: CameraController | null = null;
  private camera: THREE.PerspectiveCamera;
  private domElement: HTMLElement;
  private initialPosition: THREE.Vector3;
  private lastBounds: DisplayBounds | null = null;

  constructor(camera: THREE.PerspectiveCamera, domElement: HTMLElement) {
    this.camera = camera;
    this.domElement = domElement;
    this.initialPosition = camera.position.clone();
  }

  setInitial(position: THREE.Vector3, _target: THREE.Vector3): void {
    this.initialPosition = position.clone();
  }

  activateController(controller: CameraController): void {
    if (this.activeController) {
      this.activeController.deactivate();
      this.activeController.dispose();
      this.activeController = null;
    }
    this.activeController = controller;
    this.activeController.activate();
  }

  activate(mode: CameraMode, target: THREE.Vector3, bounds: DisplayBounds): void {
    if (mode === "trajectory") {
      return;
    }
    if (this.activeController) {
      this.activeController.deactivate();
      this.activeController.dispose();
      this.activeController = null;
    }

    fitClipPlanes(this.camera, bounds.sphere.radius);
    this.lastBounds = bounds;
    switch (mode) {
      case "orbit":
        this.activeController = new OrbitCameraController({
          camera: this.camera,
          domElement: this.domElement,
          target,
          bounds,
        });
        break;
      case "first-person":
        this.activeController = new FirstPersonCameraController({
          camera: this.camera,
          domElement: this.domElement,
          target,
          bounds,
        });
        break;
      case "aerial":
        this.activeController = new AerialCameraController({
          camera: this.camera,
          domElement: this.domElement,
          target,
          bounds,
        });
        break;
    }

    this.activeController?.activate();
  }

  update(): void {
    this.activeController?.update();
  }

  resize(width: number, height: number): void {
    this.camera.aspect = width / height;
    this.camera.updateProjectionMatrix();
    this.activeController?.resize(width, height);
  }

  getMode(): CameraMode | null {
    return this.activeController?.mode ?? null;
  }

  getState() {
    return this.activeController?.getState() ?? null;
  }

  frameBounds(bounds: DisplayBounds): void {
    fitClipPlanes(this.camera, bounds.sphere.radius);
    this.lastBounds = bounds;
    this.activeController?.frameBounds(bounds);
  }

  reset(): void {
    if (this.lastBounds && this.activeController?.mode === "orbit") {
      // Reset to the framed view of the loaded scene, not a fixed position.
      this.activeController.frameBounds(this.lastBounds);
      return;
    }
    this.camera.position.copy(this.initialPosition);
    this.activeController?.reset();
  }

  dispose(): void {
    this.activeController?.deactivate();
    this.activeController?.dispose();
    this.activeController = null;
  }
}
