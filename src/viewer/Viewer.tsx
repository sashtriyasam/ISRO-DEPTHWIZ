import { useEffect, useRef, useImperativeHandle, forwardRef, useCallback } from "react";
import * as THREE from "three";
import type { SceneArtifact } from "../types/scene";
import type { LayerId } from "../layers/types";
import type { ExaggerationLevel } from "../display/types";
import type { InspectionResult } from "../inspection/types";
import { createLayerMesh, disposeLayerMesh } from "../layers/layerRenderer";
import { CameraManager } from "../camera/CameraManager";
import { computeDisplayBounds } from "../camera/sceneBounds";
import { resolveInspection } from "../inspection/resolver";

interface ViewerProps {
  scene: SceneArtifact;
  layerId: LayerId;
  verticalScale: ExaggerationLevel;
  onCameraReady?: (manager: CameraManager) => void;
  onPointSelected?: (result: InspectionResult | null) => void;
}

export interface ViewerHandle {
  getCameraManager: () => CameraManager | null;
  loadArtifact: (artifact: SceneArtifact) => void;
  clearSelection: () => void;
}

interface MeshGroup {
  mesh: THREE.Mesh;
  wireframe?: THREE.LineSegments;
  geometry: THREE.BufferGeometry;
  material: THREE.Material;
}

export const Viewer = forwardRef<ViewerHandle, ViewerProps>(function Viewer({ scene, layerId, verticalScale, onCameraReady, onPointSelected }, ref) {
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
    currentArtifact: SceneArtifact | null;
    animationId: number;
    disposed: boolean;
    onPointSelectedRef: ((result: InspectionResult | null) => void) | null;
  }>({
    renderer: null,
    camera: null,
    threeScene: null,
    cameraManager: null,
    currentLayerId: null,
    currentMeshGroup: null,
    selectionMarker: null,
    selectionRing: null,
    currentArtifact: null,
    animationId: 0,
    disposed: false,
    onPointSelectedRef: null,
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
      if (state.selectionMarker && state.threeScene) {
        state.threeScene.remove(state.selectionMarker);
        state.selectionMarker = null;
      }
      if (state.selectionRing && state.threeScene) {
        state.threeScene.remove(state.selectionRing);
        state.selectionRing = null;
      }
      state.onPointSelectedRef?.(null);
      return;
    }

    const hit = intersects[0];
    const uv = (hit as THREE.Intersection & { uv?: THREE.Vector2 }).uv;
    const point = hit.point;

    const result = resolveInspection(
      uv ? { u: uv.x, v: uv.y } : null,
      { x: point.x, y: point.y / verticalScale, z: point.z },
      state.currentArtifact,
      state.currentLayerId ?? "dsm"
    );

    if (!result) return;

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
      result.position.x,
      result.position.y * verticalScale,
      result.position.z
    );
    state.selectionRing.position.set(
      result.position.x,
      result.position.y * verticalScale + 0.01,
      result.position.z
    );

    state.onPointSelectedRef?.(result);
  }, [verticalScale]);

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

      state.currentArtifact = artifact;

      const group = createLayerMesh(artifact, state.currentLayerId ?? "dsm");
      if (group) {
        group.mesh.scale.y = verticalScale;
        if (group.wireframe) {
          group.wireframe.scale.y = verticalScale;
        }
        state.threeScene.add(group.mesh);
        if (group.wireframe) {
          state.threeScene.add(group.wireframe);
        }
        state.currentMeshGroup = group;

        const bounds = computeScaledBounds(group.mesh, verticalScale);
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
  }));

  useEffect(() => {
    stateRef.current.onPointSelectedRef = onPointSelected ?? null;
  }, [onPointSelected]);

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
