import { useEffect, useRef, useImperativeHandle, forwardRef } from "react";
import * as THREE from "three";
import type { SceneArtifact } from "../types/scene";
import { CameraManager } from "../camera/CameraManager";
import { computeDisplayBounds } from "../camera/sceneBounds";

interface ViewerProps {
  scene: SceneArtifact;
  onCameraReady?: (manager: CameraManager) => void;
}

export interface ViewerHandle {
  getCameraManager: () => CameraManager | null;
  loadArtifact: (artifact: SceneArtifact) => void;
}

function createMeshFromArtifact(artifact: SceneArtifact): {
  mesh: THREE.Mesh;
  wireframe: THREE.LineSegments;
  geometry: THREE.BufferGeometry;
  material: THREE.Material;
} {
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute(
    "position",
    new THREE.Float32BufferAttribute(artifact.mesh.vertices, 3)
  );
  geometry.setIndex(new THREE.BufferAttribute(artifact.mesh.indices, 1));
  if (artifact.mesh.normals) {
    geometry.setAttribute(
      "normal",
      new THREE.Float32BufferAttribute(artifact.mesh.normals, 3)
    );
  } else {
    geometry.computeVertexNormals();
  }
  if (artifact.mesh.uvs) {
    geometry.setAttribute(
      "uv",
      new THREE.Float32BufferAttribute(artifact.mesh.uvs, 2)
    );
  }

  const material = new THREE.MeshStandardMaterial({
    color: 0x4a7a4a,
    roughness: 0.85,
    metalness: 0.05,
    flatShading: false,
    side: THREE.DoubleSide,
  });

  const mesh = new THREE.Mesh(geometry, material);

  const wireframe = new THREE.LineSegments(
    new THREE.WireframeGeometry(geometry),
    new THREE.LineBasicMaterial({ color: 0x2a4a2a, opacity: 0.15, transparent: true })
  );

  return { mesh, wireframe, geometry, material };
}

function disposeMeshGroup(group: {
  mesh: THREE.Mesh;
  wireframe: THREE.LineSegments;
  geometry: THREE.BufferGeometry;
  material: THREE.Material;
}) {
  group.geometry.dispose();
  group.material.dispose();
  group.wireframe.geometry.dispose();
  (group.wireframe.material as THREE.Material).dispose();
}

export const Viewer = forwardRef<ViewerHandle, ViewerProps>(function Viewer({ scene, onCameraReady }, ref) {
  const containerRef = useRef<HTMLDivElement>(null);
  const stateRef = useRef<{
    renderer: THREE.WebGLRenderer | null;
    camera: THREE.PerspectiveCamera | null;
    threeScene: THREE.Scene | null;
    cameraManager: CameraManager | null;
    currentMeshGroup: {
      mesh: THREE.Mesh;
      wireframe: THREE.LineSegments;
      geometry: THREE.BufferGeometry;
      material: THREE.Material;
    } | null;
    animationId: number;
    disposed: boolean;
  }>({
    renderer: null,
    camera: null,
    threeScene: null,
    cameraManager: null,
    currentMeshGroup: null,
    animationId: 0,
    disposed: false,
  });

  useImperativeHandle(ref, () => ({
    getCameraManager: () => stateRef.current.cameraManager,
    loadArtifact: (artifact: SceneArtifact) => {
      const state = stateRef.current;
      if (state.disposed || !state.threeScene || !state.cameraManager) return;

      if (state.currentMeshGroup) {
        state.threeScene.remove(state.currentMeshGroup.mesh);
        state.threeScene.remove(state.currentMeshGroup.wireframe);
        disposeMeshGroup(state.currentMeshGroup);
        state.currentMeshGroup = null;
      }

      const group = createMeshFromArtifact(artifact);
      state.threeScene.add(group.mesh);
      state.threeScene.add(group.wireframe);
      state.currentMeshGroup = group;

      const bounds = computeDisplayBounds([group.mesh]);
      state.cameraManager.frameBounds(bounds);
    },
  }));

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

    const group = createMeshFromArtifact(scene);
    threeScene.add(group.mesh);
    threeScene.add(group.wireframe);
    state.currentMeshGroup = group;

    const bounds = computeDisplayBounds([group.mesh]);
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

      cameraManager.dispose();

      if (state.currentMeshGroup) {
        disposeMeshGroup(state.currentMeshGroup);
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
    };
  }, [scene, onCameraReady]);

  return (
    <div
      ref={containerRef}
      style={{ width: "100%", height: "100%", position: "absolute", top: 0, left: 0 }}
    />
  );
});
