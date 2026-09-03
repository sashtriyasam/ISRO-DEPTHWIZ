import { useEffect, useRef } from "react";
import * as THREE from "three";
import type { SceneArtifact } from "../types/scene";

interface ViewerProps {
  scene: SceneArtifact;
}

export function Viewer({ scene }: ViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const stateRef = useRef<{
    renderer: THREE.WebGLRenderer | null;
    camera: THREE.PerspectiveCamera | null;
    threeScene: THREE.Scene | null;
    mesh: THREE.Mesh | null;
    animationId: number;
    disposed: boolean;
  }>({
    renderer: null,
    camera: null,
    threeScene: null,
    mesh: null,
    animationId: 0,
    disposed: false,
  });

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
    state.mesh = mesh;

    const wireframe = new THREE.LineSegments(
      new THREE.WireframeGeometry(geometry),
      new THREE.LineBasicMaterial({ color: 0x2a4a2a, opacity: 0.15, transparent: true })
    );
    threeScene.add(wireframe);

    function onResize() {
      if (state.disposed || !container) return;
      const w = container.clientWidth;
      const h = container.clientHeight;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    }

    window.addEventListener("resize", onResize);

    let time = 0;
    function animate() {
      if (state.disposed) return;
      state.animationId = requestAnimationFrame(animate);
      time += 0.002;
      camera.position.x = 6 * Math.cos(time);
      camera.position.z = 6 * Math.sin(time);
      camera.position.y = 5;
      camera.lookAt(0, 0, 0);
      renderer.render(threeScene, camera);
    }
    state.animationId = requestAnimationFrame(animate);

    return () => {
      state.disposed = true;
      cancelAnimationFrame(state.animationId);
      window.removeEventListener("resize", onResize);

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
      state.mesh = null;
    };
  }, [scene]);

  return (
    <div
      ref={containerRef}
      style={{ width: "100%", height: "100%", position: "absolute", top: 0, left: 0 }}
    />
  );
}
