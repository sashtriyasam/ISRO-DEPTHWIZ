import { useEffect, useRef, useImperativeHandle, forwardRef, useCallback } from "react";
import * as THREE from "three";
import type { SceneArtifact } from "../types/scene";
import type { LayerId } from "../layers/types";
import type { ExaggerationLevel } from "../display/types";
import type { InspectionResult } from "../inspection/types";
import type { MeasurementPoint } from "../measurement/types";
import { createLayerMesh, disposeLayerMesh } from "../layers/layerRenderer";
import type { RenderingMode } from "../layers/types";
import { CameraManager } from "../camera/CameraManager";
import { TrajectoryCameraController } from "../camera/TrajectoryController";
import { computeDisplayBounds } from "../camera/sceneBounds";
import type { CameraMode, DisplayBounds } from "../camera/types";
import type { FlythroughTrajectory, PlaybackSpeed, WaypointPosition } from "../flythrough/types";
import { buildPreviewGroup, disposePreviewGroup } from "../flythrough/preview";
import { resolveInspection } from "../inspection/resolver";

type InteractionMode = "inspect" | "measure" | "profile";

interface ViewerProps {
  scene: SceneArtifact;
  layerId: LayerId;
  verticalScale: ExaggerationLevel;
  interactionMode: InteractionMode;
  onCameraReady?: (manager: CameraManager) => void;
  onPointSelected?: (result: InspectionResult | null) => void;
  onMeasurementPointSelected?: (point: MeasurementPoint | null) => void;
  onProfilePointSelected?: (point: MeasurementPoint | null) => void;
}

export interface ViewerHandle {
  getCameraManager: () => CameraManager | null;
  loadArtifact: (artifact: SceneArtifact) => void;
  setCameraMode: (mode: CameraMode) => void;
  getCameraMode: () => CameraMode;
  setRenderingMode: (mode: RenderingMode) => void;
  getRenderingMode: () => RenderingMode;
  startFlythrough: (
    trajectory: FlythroughTrajectory,
    options?: {
      speed?: PlaybackSpeed;
      onCompleted?: () => void;
      onWaypointIndex?: (index: number) => void;
    }
  ) => boolean;
  pauseFlythrough: () => void;
  resumeFlythrough: () => void;
  stopFlythrough: () => void;
  resetFlythrough: () => void;
  setFlythroughSpeed: (speed: PlaybackSpeed) => void;
  setFlythroughPreview: (points: WaypointPosition[] | null, currentIndex?: number) => void;
  clearSelection: () => void;
  clearMeasurementGraphics: () => void;
  clearProfileGraphics: () => void;
}

interface MeshGroup {
  mesh: THREE.Mesh;
  wireframe?: THREE.LineSegments;
  geometry: THREE.BufferGeometry;
  material: THREE.Material;
}

export const Viewer = forwardRef<ViewerHandle, ViewerProps>(function Viewer({ scene, layerId, verticalScale, interactionMode, onCameraReady, onPointSelected, onMeasurementPointSelected, onProfilePointSelected }, ref) {
  const containerRef = useRef<HTMLDivElement>(null);
  const stateRef = useRef<{
    renderer: THREE.WebGLRenderer | null;
    camera: THREE.PerspectiveCamera | null;
    threeScene: THREE.Scene | null;
    cameraManager: CameraManager | null;
    currentLayerId: LayerId | null;
    currentMeshGroup: MeshGroup | null;
    selectionMarker: THREE.Mesh | null;
    selectionRing: THREE.Mesh | null;
    measurementMarkerA: THREE.Mesh | null;
    measurementMarkerB: THREE.Mesh | null;
    measurementLine: THREE.Line | null;
    profileMarkerA: THREE.Mesh | null;
    profileMarkerB: THREE.Mesh | null;
    profileLine: THREE.Line | null;
    currentArtifact: SceneArtifact | null;
    animationId: number;
    disposed: boolean;
    onPointSelectedRef: ((result: InspectionResult | null) => void) | null;
    onMeasurementPointSelectedRef: ((point: MeasurementPoint | null) => void) | null;
    onProfilePointSelectedRef: ((point: MeasurementPoint | null) => void) | null;
    interactionModeRef: InteractionMode;
    verticalScaleRef: number;
    cameraModeRef: CameraMode;
    renderingModeRef: RenderingMode;
    lastBoundsRef: DisplayBounds | null;
    trajectoryControllerRef: TrajectoryCameraController | null;
    previewGroupRef: THREE.Group | null;
    previousCameraModeRef: CameraMode;
  }>({
    renderer: null,
    camera: null,
    threeScene: null,
    cameraManager: null,
    currentLayerId: null,
    currentMeshGroup: null,
    selectionMarker: null,
    selectionRing: null,
    measurementMarkerA: null,
    measurementMarkerB: null,
    measurementLine: null,
    profileMarkerA: null,
    profileMarkerB: null,
    profileLine: null,
    currentArtifact: null,
    animationId: 0,
    disposed: false,
    onPointSelectedRef: null,
    onMeasurementPointSelectedRef: null,
    onProfilePointSelectedRef: null,
    interactionModeRef: "inspect",
    verticalScaleRef: 1,
    cameraModeRef: "orbit",
    renderingModeRef: "textured",
    lastBoundsRef: null,
    trajectoryControllerRef: null,
    previewGroupRef: null,
    previousCameraModeRef: "orbit",
  });

  const handlePointerDown = useCallback((event: PointerEvent) => {
    const state = stateRef.current;
    if (state.disposed || !state.camera || !state.threeScene || !state.currentMeshGroup || !state.currentArtifact) return;
    if (state.cameraModeRef === "first-person" || state.cameraModeRef === "trajectory") return;

    const container = containerRef.current;
    if (!container) return;

    const rect = container.getBoundingClientRect();
    const x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    const y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

    const raycaster = new THREE.Raycaster();
    raycaster.setFromCamera(new THREE.Vector2(x, y), state.camera);

    const intersects = raycaster.intersectObject(state.currentMeshGroup.mesh, false);
    if (intersects.length === 0) {
      if (state.interactionModeRef === "inspect") {
        if (state.selectionMarker && state.threeScene) {
          state.threeScene.remove(state.selectionMarker);
          state.selectionMarker = null;
        }
        if (state.selectionRing && state.threeScene) {
          state.threeScene.remove(state.selectionRing);
          state.selectionRing = null;
        }
        state.onPointSelectedRef?.(null);
      } else if (state.interactionModeRef === "measure") {
        state.onMeasurementPointSelectedRef?.(null);
      } else {
        state.onProfilePointSelectedRef?.(null);
      }
      return;
    }

    const hit = intersects[0];
    const uv = (hit as THREE.Intersection & { uv?: THREE.Vector2 }).uv;
    const point = hit.point;
    const vscale = state.verticalScaleRef;

    const inspectionResult = resolveInspection(
      uv ? { u: uv.x, v: uv.y } : null,
      { x: point.x, y: point.y / vscale, z: point.z },
      state.currentArtifact,
      state.currentLayerId ?? "dsm"
    );

    if (!inspectionResult) return;

    if (state.interactionModeRef === "inspect") {
      if (!state.selectionMarker) {
        const markerGeometry = new THREE.SphereGeometry(0.05, 16, 16);
        const markerMaterial = new THREE.MeshBasicMaterial({ color: 0xff4444 });
        state.selectionMarker = new THREE.Mesh(markerGeometry, markerMaterial);
        state.threeScene.add(state.selectionMarker);
      }

      if (!state.selectionRing) {
        const ringGeometry = new THREE.RingGeometry(0.08, 0.12, 32);
        const ringMaterial = new THREE.MeshBasicMaterial({
          color: 0xff6666,
          side: THREE.DoubleSide,
          transparent: true,
          opacity: 0.6,
        });
        state.selectionRing = new THREE.Mesh(ringGeometry, ringMaterial);
        state.selectionRing.rotation.x = -Math.PI / 2;
        state.threeScene.add(state.selectionRing);
      }

      state.selectionMarker.position.set(
        inspectionResult.position.x,
        inspectionResult.position.y * vscale,
        inspectionResult.position.z
      );
      state.selectionRing.position.set(
        inspectionResult.position.x,
        inspectionResult.position.y * vscale + 0.01,
        inspectionResult.position.z
      );

      state.onPointSelectedRef?.(inspectionResult);
    } else {
      const measurementPoint: MeasurementPoint = {
        displayPosition: inspectionResult.position,
        scientific: inspectionResult.scientific,
        uv: inspectionResult.uv,
        gridIndex: inspectionResult.gridIndex,
        layerId: inspectionResult.layerId,
        artifactId: inspectionResult.artifactId,
      };
      if (state.interactionModeRef === "measure") {
        state.onMeasurementPointSelectedRef?.(measurementPoint);
      } else {
        state.onProfilePointSelectedRef?.(measurementPoint);
      }
    }
  }, []);

  useImperativeHandle(ref, () => ({
    getCameraManager: () => stateRef.current.cameraManager,
    getCameraMode: () => stateRef.current.cameraModeRef,
    setCameraMode: (mode: CameraMode) => {
      const state = stateRef.current;
      if (state.disposed || !state.cameraManager || !state.lastBoundsRef) return;
      state.cameraModeRef = mode;
      const bounds = state.lastBoundsRef;
      state.cameraManager.activate(mode, bounds.center.clone(), {
        center: bounds.center.clone(),
        size: bounds.size.clone(),
        sphere: bounds.sphere.clone(),
        box: bounds.box.clone(),
      });
    },
    loadArtifact: (artifact: SceneArtifact) => {
      const state = stateRef.current;
      if (state.disposed || !state.threeScene || !state.cameraManager) return;

      if (state.currentMeshGroup) {
        state.threeScene.remove(state.currentMeshGroup.mesh);
        if (state.currentMeshGroup.wireframe) {
          state.threeScene.remove(state.currentMeshGroup.wireframe);
        }
        disposeLayerMesh(state.currentMeshGroup);
        state.currentMeshGroup = null;
      }

      if (state.selectionMarker) {
        state.threeScene.remove(state.selectionMarker);
        state.selectionMarker = null;
      }
      if (state.selectionRing) {
        state.threeScene.remove(state.selectionRing);
        state.selectionRing = null;
      }

      clearMeasurementGraphics(state);
      clearProfileGraphics(state);

      state.currentArtifact = artifact;

      const meshGroup = replaceMeshGroup(state, artifact, state.currentLayerId ?? "dsm");
      if (meshGroup) {
        const bounds = computeScaledBounds(meshGroup.mesh, state.verticalScaleRef);
        state.lastBoundsRef = {
          center: bounds.center.clone(),
          size: bounds.size.clone(),
          sphere: bounds.sphere.clone(),
          box: bounds.box.clone(),
        };
        state.cameraManager.frameBounds(bounds);
      }
    },
    getRenderingMode: () => stateRef.current.renderingModeRef,
    setRenderingMode: (mode: RenderingMode) => {
      const state = stateRef.current;
      if (state.disposed || !state.threeScene || !state.currentArtifact) return;
      state.renderingModeRef = mode;
      replaceMeshGroup(state, state.currentArtifact, state.currentLayerId ?? "dsm");
    },
    startFlythrough: (trajectory, options) => {
      const state = stateRef.current;
      const container = containerRef.current;
      if (state.disposed || !state.cameraManager || !state.lastBoundsRef || !container) return false;
      if (trajectory.waypoints.length < 2) return false;
      if (state.cameraModeRef !== "trajectory") {
        state.previousCameraModeRef = state.cameraModeRef;
      }
      const bounds = state.lastBoundsRef;
      const controller = new TrajectoryCameraController({
        camera: state.camera!,
        domElement: container,
        target: bounds.center.clone(),
        bounds: {
          center: bounds.center.clone(),
          size: bounds.size.clone(),
          sphere: bounds.sphere.clone(),
          box: bounds.box.clone(),
        },
        trajectory,
        speed: options?.speed,
        onCompleted: options?.onCompleted,
        onWaypointIndex: options?.onWaypointIndex,
      });
      state.cameraManager.activateController(controller);
      state.trajectoryControllerRef = controller;
      state.cameraModeRef = "trajectory";
      controller.play();
      return true;
    },
    pauseFlythrough: () => {
      stateRef.current.trajectoryControllerRef?.pause();
    },
    resumeFlythrough: () => {
      stateRef.current.trajectoryControllerRef?.resume();
    },
    resetFlythrough: () => {
      stateRef.current.trajectoryControllerRef?.resetToStart();
    },
    stopFlythrough: () => {
      const state = stateRef.current;
      const controller = state.trajectoryControllerRef;
      state.trajectoryControllerRef = null;
      if (!controller || state.disposed || !state.cameraManager || !state.lastBoundsRef) return;
      controller.stop();
      const restore = state.previousCameraModeRef;
      state.cameraModeRef = restore;
      const bounds = state.lastBoundsRef;
      state.cameraManager.activate(restore, bounds.center.clone(), {
        center: bounds.center.clone(),
        size: bounds.size.clone(),
        sphere: bounds.sphere.clone(),
        box: bounds.box.clone(),
      });
    },
    setFlythroughSpeed: (speed: PlaybackSpeed) => {
      stateRef.current.trajectoryControllerRef?.setSpeed(speed);
    },
    setFlythroughPreview: (points: WaypointPosition[] | null, currentIndex = 0) => {
      const state = stateRef.current;
      if (state.disposed || !state.threeScene) return;
      setPreviewLine(state, points, currentIndex);
    },
    clearSelection: () => {
      const state = stateRef.current;
      if (state.selectionMarker && state.threeScene) {
        state.threeScene.remove(state.selectionMarker);
        state.selectionMarker = null;
      }
      if (state.selectionRing && state.threeScene) {
        state.threeScene.remove(state.selectionRing);
        state.selectionRing = null;
      }
      state.onPointSelectedRef?.(null);
    },
    clearMeasurementGraphics: () => {
      clearMeasurementGraphics(stateRef.current);
    },
    clearProfileGraphics: () => {
      clearProfileGraphics(stateRef.current);
    },
  }));

  useEffect(() => {
    stateRef.current.onPointSelectedRef = onPointSelected ?? null;
  }, [onPointSelected]);

  useEffect(() => {
    stateRef.current.onMeasurementPointSelectedRef = onMeasurementPointSelected ?? null;
  }, [onMeasurementPointSelected]);

  useEffect(() => {
    stateRef.current.onProfilePointSelectedRef = onProfilePointSelected ?? null;
  }, [onProfilePointSelected]);

  useEffect(() => {
    stateRef.current.interactionModeRef = interactionMode;
  }, [interactionMode]);

  useEffect(() => {
    stateRef.current.verticalScaleRef = verticalScale;
  }, [verticalScale]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const state = stateRef.current;
    state.disposed = false;

    const width = container.clientWidth;
    const height = container.clientHeight;

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setClearColor(0x0f1117);
    container.appendChild(renderer.domElement);
    state.renderer = renderer;

    const camera = new THREE.PerspectiveCamera(50, width / height, 0.1, 100);
    camera.position.set(6, 5, 6);
    camera.lookAt(0, 0, 0);
    state.camera = camera;

    const threeScene = new THREE.Scene();
    state.threeScene = threeScene;

    const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
    threeScene.add(ambientLight);
    const dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
    dirLight.position.set(1, 2, 1);
    threeScene.add(dirLight);

    const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
    directionalLight.position.set(5, 8, 5);
    directionalLight.lookAt(0, 0, 0);
    threeScene.add(directionalLight);

    const hemisphereLight = new THREE.HemisphereLight(0x87ceeb, 0x362a28, 0.3);
    threeScene.add(hemisphereLight);

    state.currentArtifact = scene;

    if (replaceMeshGroup(state, scene, layerId)) {
      state.currentLayerId = layerId;
    }
    const group = state.currentMeshGroup;

      const bounds = group ? computeScaledBounds(group.mesh, verticalScale) : computeDisplayBounds([]);
      state.lastBoundsRef = {
        center: bounds.center.clone(),
        size: bounds.size.clone(),
        sphere: bounds.sphere.clone(),
        box: bounds.box.clone(),
      };
      const cameraManager = new CameraManager(camera, renderer.domElement);
    cameraManager.setInitial(
      new THREE.Vector3(6, 5, 6),
      bounds.center.clone()
    );
    cameraManager.activate("orbit", bounds.center, {
      center: bounds.center,
      size: bounds.size,
      sphere: bounds.sphere,
      box: bounds.box,
    });
    state.cameraManager = cameraManager;

    onCameraReady?.(cameraManager);

    container.addEventListener("pointerdown", handlePointerDown);

    function onResize() {
      if (state.disposed || !container) return;
      const w = container.clientWidth;
      const h = container.clientHeight;
      cameraManager.resize(w, h);
      renderer.setSize(w, h);
    }

    window.addEventListener("resize", onResize);

    function animate() {
      if (state.disposed) return;
      state.animationId = requestAnimationFrame(animate);
      cameraManager.update();
      renderer.render(threeScene, camera);
    }
    state.animationId = requestAnimationFrame(animate);

    return () => {
      state.disposed = true;
      cancelAnimationFrame(state.animationId);
      window.removeEventListener("resize", onResize);
      container.removeEventListener("pointerdown", handlePointerDown);

      cameraManager.dispose();

      if (state.selectionMarker) {
        (state.selectionMarker.material as THREE.Material).dispose();
        state.selectionMarker.geometry.dispose();
      }
      if (state.selectionRing) {
        (state.selectionRing.material as THREE.Material).dispose();
        state.selectionRing.geometry.dispose();
      }

      clearMeasurementGraphics(state);
      clearProfileGraphics(state);

      if (state.currentMeshGroup) {
        disposeLayerMesh(state.currentMeshGroup);
        state.currentMeshGroup = null;
      }

      if (state.previewGroupRef) {
        if (state.previewGroupRef.parent) {
          state.previewGroupRef.parent.remove(state.previewGroupRef);
        }
        disposePreviewGroup(state.previewGroupRef);
        state.previewGroupRef = null;
      }
      state.trajectoryControllerRef = null;

      renderer.dispose();

      if (renderer.domElement.parentElement) {
        renderer.domElement.parentElement.removeChild(renderer.domElement);
      }

      state.renderer = null;
      state.camera = null;
      state.threeScene = null;
      state.cameraManager = null;
      state.selectionMarker = null;
      state.selectionRing = null;
    };
  }, [scene, layerId, verticalScale, onCameraReady, handlePointerDown]);

  return (
    <div
      ref={containerRef}
      style={{ width: "100%", height: "100%", position: "absolute", top: 0, left: 0 }}
    />
  );
});

function clearMeasurementGraphics(state: {
  threeScene: THREE.Scene | null;
  measurementMarkerA: THREE.Mesh | null;
  measurementMarkerB: THREE.Mesh | null;
  measurementLine: THREE.Line | null;
}) {
  if (state.measurementMarkerA && state.threeScene) {
    state.threeScene.remove(state.measurementMarkerA);
    (state.measurementMarkerA.material as THREE.Material).dispose();
    state.measurementMarkerA.geometry.dispose();
    state.measurementMarkerA = null;
  }
  if (state.measurementMarkerB && state.threeScene) {
    state.threeScene.remove(state.measurementMarkerB);
    (state.measurementMarkerB.material as THREE.Material).dispose();
    state.measurementMarkerB.geometry.dispose();
    state.measurementMarkerB = null;
  }
  if (state.measurementLine && state.threeScene) {
    state.threeScene.remove(state.measurementLine);
    (state.measurementLine.material as THREE.Material).dispose();
    state.measurementLine.geometry.dispose();
    state.measurementLine = null;
  }
}

function clearProfileGraphics(state: {
  threeScene: THREE.Scene | null;
  profileMarkerA: THREE.Mesh | null;
  profileMarkerB: THREE.Mesh | null;
  profileLine: THREE.Line | null;
}) {
  if (state.profileMarkerA && state.threeScene) {
    state.threeScene.remove(state.profileMarkerA);
    (state.profileMarkerA.material as THREE.Material).dispose();
    state.profileMarkerA.geometry.dispose();
    state.profileMarkerA = null;
  }
  if (state.profileMarkerB && state.threeScene) {
    state.threeScene.remove(state.profileMarkerB);
    (state.profileMarkerB.material as THREE.Material).dispose();
    state.profileMarkerB.geometry.dispose();
    state.profileMarkerB = null;
  }
  if (state.profileLine && state.threeScene) {
    state.threeScene.remove(state.profileLine);
    (state.profileLine.material as THREE.Material).dispose();
    state.profileLine.geometry.dispose();
    state.profileLine = null;
  }
}

function setPreviewLine(
  state: {
    threeScene: THREE.Scene | null;
    previewGroupRef: THREE.Group | null;
    lastBoundsRef: DisplayBounds | null;
  },
  points: WaypointPosition[] | null,
  currentIndex: number
): void {
  if (state.previewGroupRef && state.threeScene) {
    state.threeScene.remove(state.previewGroupRef);
    disposePreviewGroup(state.previewGroupRef);
    state.previewGroupRef = null;
  }
  if (!points || points.length < 2 || !state.threeScene) return;
  const size = state.lastBoundsRef?.size;
  const reference = Math.max(size?.x ?? 1, size?.y ?? 1, size?.z ?? 1, 1);
  const built = buildPreviewGroup(points, currentIndex, reference * 0.012);
  if (!built) return;
  state.threeScene.add(built.group);
  state.previewGroupRef = built.group;
}

function replaceMeshGroup(
  state: {
    threeScene: THREE.Scene | null;
    currentMeshGroup: MeshGroup | null;
    verticalScaleRef: number;
    renderingModeRef: RenderingMode;
  },
  artifact: SceneArtifact,
  layerId: LayerId
): MeshGroup | null {
  if (!state.threeScene) return state.currentMeshGroup;
  if (state.currentMeshGroup) {
    state.threeScene.remove(state.currentMeshGroup.mesh);
    if (state.currentMeshGroup.wireframe) {
      state.threeScene.remove(state.currentMeshGroup.wireframe);
    }
    disposeLayerMesh(state.currentMeshGroup);
    state.currentMeshGroup = null;
  }
  const group = createLayerMesh(artifact, layerId, state.renderingModeRef);
  if (!group) return null;
  group.mesh.scale.y = state.verticalScaleRef;
  if (group.wireframe) {
    group.wireframe.scale.y = state.verticalScaleRef;
  }
  state.threeScene.add(group.mesh);
  if (group.wireframe) {
    state.threeScene.add(group.wireframe);
  }
  state.currentMeshGroup = group;
  return group;
}

export function updateMeasurementGraphics(
  state: {
    threeScene: THREE.Scene | null;
    measurementMarkerA: THREE.Mesh | null;
    measurementMarkerB: THREE.Mesh | null;
    measurementLine: THREE.Line | null;
    verticalScaleRef: number;
  },
  pointA: MeasurementPoint | null,
  pointB: MeasurementPoint | null
) {
  clearMeasurementGraphics(state);

  if (!state.threeScene) return;

  if (pointA) {
    const markerGeometry = new THREE.SphereGeometry(0.06, 16, 16);
    const markerMaterial = new THREE.MeshBasicMaterial({ color: 0x44aaff });
    state.measurementMarkerA = new THREE.Mesh(markerGeometry, markerMaterial);
    state.measurementMarkerA.position.set(
      pointA.displayPosition.x,
      pointA.displayPosition.y * state.verticalScaleRef,
      pointA.displayPosition.z
    );
    state.threeScene.add(state.measurementMarkerA);
  }

  if (pointA && pointB) {
    const markerGeometryB = new THREE.SphereGeometry(0.06, 16, 16);
    const markerMaterialB = new THREE.MeshBasicMaterial({ color: 0x44ff88 });
    state.measurementMarkerB = new THREE.Mesh(markerGeometryB, markerMaterialB);
    state.measurementMarkerB.position.set(
      pointB.displayPosition.x,
      pointB.displayPosition.y * state.verticalScaleRef,
      pointB.displayPosition.z
    );
    state.threeScene.add(state.measurementMarkerB);

    const points = [
      new THREE.Vector3(
        pointA.displayPosition.x,
        pointA.displayPosition.y * state.verticalScaleRef,
        pointA.displayPosition.z
      ),
      new THREE.Vector3(
        pointB.displayPosition.x,
        pointB.displayPosition.y * state.verticalScaleRef,
        pointB.displayPosition.z
      ),
    ];
    const lineGeometry = new THREE.BufferGeometry().setFromPoints(points);
    const lineMaterial = new THREE.LineBasicMaterial({ color: 0xffaa44, linewidth: 2 });
    state.measurementLine = new THREE.Line(lineGeometry, lineMaterial);
    state.threeScene.add(state.measurementLine);
  }
}

export function updateProfileGraphics(
  state: {
    threeScene: THREE.Scene | null;
    profileMarkerA: THREE.Mesh | null;
    profileMarkerB: THREE.Mesh | null;
    profileLine: THREE.Line | null;
    verticalScaleRef: number;
  },
  pointA: MeasurementPoint | null,
  pointB: MeasurementPoint | null
) {
  clearProfileGraphics(state);

  if (!state.threeScene) return;

  if (pointA) {
    const markerGeometry = new THREE.SphereGeometry(0.06, 16, 16);
    const markerMaterial = new THREE.MeshBasicMaterial({ color: 0xaa44ff });
    state.profileMarkerA = new THREE.Mesh(markerGeometry, markerMaterial);
    state.profileMarkerA.position.set(
      pointA.displayPosition.x,
      pointA.displayPosition.y * state.verticalScaleRef,
      pointA.displayPosition.z
    );
    state.threeScene.add(state.profileMarkerA);
  }

  if (pointA && pointB) {
    const markerGeometryB = new THREE.SphereGeometry(0.06, 16, 16);
    const markerMaterialB = new THREE.MeshBasicMaterial({ color: 0xff44aa });
    state.profileMarkerB = new THREE.Mesh(markerGeometryB, markerMaterialB);
    state.profileMarkerB.position.set(
      pointB.displayPosition.x,
      pointB.displayPosition.y * state.verticalScaleRef,
      pointB.displayPosition.z
    );
    state.threeScene.add(state.profileMarkerB);

    const points = [
      new THREE.Vector3(
        pointA.displayPosition.x,
        pointA.displayPosition.y * state.verticalScaleRef,
        pointA.displayPosition.z
      ),
      new THREE.Vector3(
        pointB.displayPosition.x,
        pointB.displayPosition.y * state.verticalScaleRef,
        pointB.displayPosition.z
      ),
    ];
    const lineGeometry = new THREE.BufferGeometry().setFromPoints(points);
    const lineMaterial = new THREE.LineBasicMaterial({ color: 0xdd44dd, linewidth: 2 });
    state.profileLine = new THREE.Line(lineGeometry, lineMaterial);
    state.threeScene.add(state.profileLine);
  }
}

function computeScaledBounds(mesh: THREE.Mesh, verticalScale: number) {
  mesh.geometry.computeBoundingBox();
  const bbox = mesh.geometry.boundingBox;
  if (!bbox) return computeDisplayBounds([mesh]);

  const scaledBox = new THREE.Box3(
    new THREE.Vector3(bbox.min.x, bbox.min.y * verticalScale, bbox.min.z),
    new THREE.Vector3(bbox.max.x, bbox.max.y * verticalScale, bbox.max.z)
  );

  const center = new THREE.Vector3();
  scaledBox.getCenter(center);

  const size = new THREE.Vector3();
  scaledBox.getSize(size);

  const sphere = new THREE.Sphere();
  scaledBox.getBoundingSphere(sphere);

  return { center, size, sphere, box: scaledBox };
}

