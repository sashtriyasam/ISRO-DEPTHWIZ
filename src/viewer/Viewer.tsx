import { useEffect, useRef, useImperativeHandle, forwardRef, useCallback } from "react";
import * as THREE from "three";
import type { SceneArtifact } from "../types/scene";
import type { LayerId } from "../layers/types";
import type { ExaggerationLevel } from "../display/types";
import type { InspectionResult } from "../inspection/types";
import type { MeasurementPoint } from "../measurement/types";
import { createLayerMesh, disposeLayerMesh } from "../layers/layerRenderer";
import { CameraManager } from "../camera/CameraManager";
import { computeDisplayBounds } from "../camera/sceneBounds";
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
  });

  const handlePointerDown = useCallback((event: PointerEvent) => {
    const state = stateRef.current;
    if (state.disposed || !state.camera || !state.threeScene || !state.currentMeshGroup || !state.currentArtifact) return;

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
        state.currentLayerId = null;
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

      const group = createLayerMesh(artifact, state.currentLayerId ?? "dsm");
      if (group) {
        group.mesh.scale.y = state.verticalScaleRef;
        if (group.wireframe) {
          group.wireframe.scale.y = state.verticalScaleRef;
        }
        state.threeScene.add(group.mesh);
        if (group.wireframe) {
          state.threeScene.add(group.wireframe);
        }
        state.currentMeshGroup = group;

        const bounds = computeScaledBounds(group.mesh, state.verticalScaleRef);
        state.cameraManager.frameBounds(bounds);
      }
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

    const ambientLight = new THREE.AmbientLight(0xffffff, 0.4);
    threeScene.add(ambientLight);

    const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
    directionalLight.position.set(5, 8, 5);
    directionalLight.lookAt(0, 0, 0);
    threeScene.add(directionalLight);

    const hemisphereLight = new THREE.HemisphereLight(0x87ceeb, 0x362a28, 0.3);
    threeScene.add(hemisphereLight);

    state.currentArtifact = scene;

    const group = createLayerMesh(scene, layerId);
    if (group) {
      group.mesh.scale.y = verticalScale;
      if (group.wireframe) {
        group.wireframe.scale.y = verticalScale;
      }
      threeScene.add(group.mesh);
      if (group.wireframe) {
        threeScene.add(group.wireframe);
      }
      state.currentMeshGroup = group;
      state.currentLayerId = layerId;
    }

    const bounds = group ? computeScaledBounds(group.mesh, verticalScale) : computeDisplayBounds([]);
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
