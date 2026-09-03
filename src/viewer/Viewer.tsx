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
}

export const Viewer = forwardRef<ViewerHandle, ViewerProps>(function Viewer({ scene, onCameraReady }, ref) {
  const containerRef = useRef<HTMLDivElement>(null);
  const stateRef = useRef<{
    renderer: THREE.WebGLRenderer | null;
    camera: THREE.PerspectiveCamera | null;
    threeScene: THREE.Scene | null;
    cameraManager: CameraManager | null;
    animationId: number;
    disposed: boolean;
  }>({
    renderer: null,
    camera: null,
    threeScene: null,
    cameraManager: null,
    animationId: 0,
    disposed: false,
  });

  useImperativeHandle(ref, () => ({
    getCameraManager: () => stateRef.current.cameraManager,
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

    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute(
      "position",
      new THREE.Float32BufferAttribute(scene.mesh.vertices, 3)
    );
    geometry.setIndex(new THREE.BufferAttribute(scene.mesh.indices, 1));
    if (scene.mesh.normals) {
      geometry.setAttribute(
        "normal",
        new THREE.Float32BufferAttribute(scene.mesh.normals, 3)
      );
    } else {
      geometry.computeVertexNormals();
    }
    if (scene.mesh.uvs) {
      geometry.setAttribute(
        "uv",
        new THREE.Float32BufferAttribute(scene.mesh.uvs, 2)
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
    threeScene.add(mesh);

    const wireframe = new THREE.LineSegments(
      new THREE.WireframeGeometry(geometry),
      new THREE.LineBasicMaterial({ color: 0x2a4a2a, opacity: 0.15, transparent: true })
    );
    threeScene.add(wireframe);

    const bounds = computeDisplayBounds([mesh]);
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

      geometry.dispose();
      material.dispose();
      wireframe.geometry.dispose();
      wireframe.material.dispose();
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
