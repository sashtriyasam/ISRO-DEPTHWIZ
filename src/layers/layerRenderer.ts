import * as THREE from "three";
import type { SceneArtifact, ElevationData } from "../types/scene";
import type { LayerId } from "./types";

function elevationToColor(value: number, min: number, max: number): THREE.Color {
  const t = max > min ? (value - min) / (max - min) : 0.5;
  const r = t * 0.8 + 0.1;
  const g = 0.2 + (1 - Math.abs(t - 0.5) * 2) * 0.3;
  const b = (1 - t) * 0.8 + 0.1;
  return new THREE.Color(r, g, b);
}

function createColorFromElevation(elevation: ElevationData): Float32Array {
  const { grid, width, height } = elevation;
  let min = Infinity;
  let max = -Infinity;
  for (let i = 0; i < grid.length; i++) {
    if (grid[i] < min) min = grid[i];
    if (grid[i] > max) max = grid[i];
  }
  const colors = new Float32Array(width * height * 3);
  for (let i = 0; i < grid.length; i++) {
    const c = elevationToColor(grid[i], min, max);
    colors[i * 3] = c.r;
    colors[i * 3 + 1] = c.g;
    colors[i * 3 + 2] = c.b;
  }
  return colors;
}

export function createLayerMesh(
  artifact: SceneArtifact,
  layerId: LayerId
): { mesh: THREE.Mesh; wireframe?: THREE.LineSegments; geometry: THREE.BufferGeometry; material: THREE.Material } | null {
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

  switch (layerId) {
    case "dsm": {
      if (artifact.elevation) {
        const colors = createColorFromElevation(artifact.elevation);
        geometry.setAttribute("color", new THREE.Float32BufferAttribute(colors, 3));
      }
      const material = new THREE.MeshStandardMaterial({
        vertexColors: artifact.elevation != null,
        color: artifact.elevation != null ? 0xffffff : 0x4a7a4a,
        roughness: 0.85,
        metalness: 0.05,
        side: THREE.DoubleSide,
      });
      const mesh = new THREE.Mesh(geometry, material);
      const wireframe = new THREE.LineSegments(
        new THREE.WireframeGeometry(geometry),
        new THREE.LineBasicMaterial({ color: 0x2a4a2a, opacity: 0.12, transparent: true })
      );
      return { mesh, wireframe, geometry, material };
    }

    case "rdsm": {
      const rdsmData = artifact.layers?.rdsm;
      if (rdsmData) {
        const colors = createColorFromElevation(rdsmData);
        geometry.setAttribute("color", new THREE.Float32BufferAttribute(colors, 3));
      }
      const material = new THREE.MeshStandardMaterial({
        vertexColors: rdsmData != null,
        color: rdsmData != null ? 0xffffff : 0x6a9a6a,
        roughness: 0.85,
        metalness: 0.05,
        side: THREE.DoubleSide,
      });
      const mesh = new THREE.Mesh(geometry, material);
      const wireframe = new THREE.LineSegments(
        new THREE.WireframeGeometry(geometry),
        new THREE.LineBasicMaterial({ color: 0x2a6a2a, opacity: 0.12, transparent: true })
      );
      return { mesh, wireframe, geometry, material };
    }

    case "agl": {
      const aglData = artifact.layers?.agl;
      if (aglData) {
        const colors = createColorFromElevation(aglData);
        geometry.setAttribute("color", new THREE.Float32BufferAttribute(colors, 3));
      }
      const material = new THREE.MeshStandardMaterial({
        vertexColors: aglData != null,
        color: aglData != null ? 0xffffff : 0x9a6a4a,
        roughness: 0.85,
        metalness: 0.05,
        side: THREE.DoubleSide,
      });
      const mesh = new THREE.Mesh(geometry, material);
      const wireframe = new THREE.LineSegments(
        new THREE.WireframeGeometry(geometry),
        new THREE.LineBasicMaterial({ color: 0x6a4a2a, opacity: 0.12, transparent: true })
      );
      return { mesh, wireframe, geometry, material };
    }

    case "rgb": {
      const material = new THREE.MeshStandardMaterial({
        color: 0x4a7a4a,
        roughness: 0.85,
        metalness: 0.05,
        side: THREE.DoubleSide,
      });
      const mesh = new THREE.Mesh(geometry, material);
      const wireframe = new THREE.LineSegments(
        new THREE.WireframeGeometry(geometry),
        new THREE.LineBasicMaterial({ color: 0x2a4a2a, opacity: 0.12, transparent: true })
      );
      return { mesh, wireframe, geometry, material };
    }

    case "wireframe": {
      const material = new THREE.MeshStandardMaterial({
        color: 0x3a5a3a,
        roughness: 0.9,
        metalness: 0.0,
        wireframe: true,
        side: THREE.DoubleSide,
      });
      const mesh = new THREE.Mesh(geometry, material);
      return { mesh, geometry, material };
    }

    default:
      geometry.dispose();
      return null;
  }
}

export function disposeLayerMesh(group: {
  mesh: THREE.Mesh;
  wireframe?: THREE.LineSegments;
  geometry: THREE.BufferGeometry;
  material: THREE.Material;
}): void {
  group.geometry.dispose();
  group.material.dispose();
  if (group.wireframe) {
    group.wireframe.geometry.dispose();
    (group.wireframe.material as THREE.Material).dispose();
  }
}
