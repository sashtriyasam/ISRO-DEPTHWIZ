import * as THREE from "three";
import type { SceneArtifact, ElevationData } from "../types/scene";
import type { LayerId, RenderingMode } from "./types";

function elevationToColor(value: number, min: number, max: number): THREE.Color {
  const t = max > min ? (value - min) / (max - min) : 0.5;
  const r = t * 0.8 + 0.1;
  const g = 0.2 + (1 - Math.abs(t - 0.5) * 2) * 0.3;
  const b = (1 - t) * 0.8 + 0.1;
  return new THREE.Color(r, g, b);
}

const NODATA_COLOR = new THREE.Color(0.35, 0.35, 0.35);

/**
 * One colour per mesh *vertex*. Vertices are compacted valid pixels (and a
 * lattice for LOD meshes), so each vertex looks up its own source pixel;
 * indexing the grid by vertex number painted other pixels' values.
 */
function createColorFromElevation(
  elevation: ElevationData,
  vertexCount: number,
  sourceIndices?: Uint32Array,
): Float32Array {
  const { grid } = elevation;
  let min = Infinity;
  let max = -Infinity;
  for (let i = 0; i < grid.length; i++) {
    const v = grid[i];
    if (!Number.isFinite(v)) continue;
    if (v < min) min = v;
    if (v > max) max = v;
  }
  const colors = new Float32Array(vertexCount * 3);
  for (let i = 0; i < vertexCount; i++) {
    const pixel = sourceIndices ? sourceIndices[i] : i;
    const value = grid[pixel];
    const c = Number.isFinite(value) ? elevationToColor(value, min, max) : NODATA_COLOR;
    colors[i * 3] = c.r;
    colors[i * 3 + 1] = c.g;
    colors[i * 3 + 2] = c.b;
  }
  return colors;
}

function layerElevation(artifact: SceneArtifact, layerId: LayerId): ElevationData | undefined {
  switch (layerId) {
    case "dsm":
      return artifact.elevation;
    case "rdsm":
      return artifact.layers?.rdsm;
    case "agl":
      return artifact.layers?.agl;
    case "slope":
      return artifact.layers?.slope;
    default:
      return undefined;
  }
}

function buildTerrainGeometry(
  artifact: SceneArtifact,
  layerId: LayerId
): THREE.BufferGeometry | null {
  switch (layerId) {
    case "dsm":
    case "rdsm":
    case "agl":
    case "rgb":
    case "wireframe":
      break;
    case "slope":
      if (!artifact.layers?.slope) return null; // no slope from the backend
      break;
    default:
      return null;
  }
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
  const elevation = layerElevation(artifact, layerId);
  if (elevation) {
    const colors = createColorFromElevation(
      elevation,
      artifact.mesh.vertexCount,
      artifact.mesh.sourceIndices,
    );
    geometry.setAttribute("color", new THREE.Float32BufferAttribute(colors, 3));
  }
  return geometry;
}

function surfaceMaterial(
  layerId: LayerId,
  elevation: ElevationData | undefined,
  wireframe: boolean
): THREE.MeshStandardMaterial {
  const fallbackColors: Record<string, number> = {
    dsm: 0x4a7a4a,
    rdsm: 0x6a9a6a,
    agl: 0x9a6a4a,
    rgb: 0x4a7a4a,
    slope: 0x4a7a4a,
    wireframe: 0x3a5a3a,
  };
  return new THREE.MeshStandardMaterial({
    vertexColors: elevation != null,
    color: elevation != null ? 0xffffff : (fallbackColors[layerId] ?? 0x4a7a4a),
    roughness: layerId === "wireframe" ? 0.9 : 0.85,
    metalness: layerId === "wireframe" ? 0.0 : 0.05,
    wireframe,
    side: THREE.DoubleSide,
  });
}

function overlayTint(layerId: LayerId): number {
  switch (layerId) {
    case "rdsm":
      return 0x2a6a2a;
    case "agl":
      return 0x6a4a2a;
    default:
      return 0x2a4a2a;
  }
}

export interface LayerMeshGroup {
  mesh: THREE.Mesh;
  wireframe?: THREE.LineSegments;
  geometry: THREE.BufferGeometry;
  material: THREE.Material;
}

export function createLayerMesh(
  artifact: SceneArtifact,
  layerId: LayerId,
  mode: RenderingMode = "shaded-wireframe"
): LayerMeshGroup | null {
  const geometry = buildTerrainGeometry(artifact, layerId);
  if (!geometry) {
    return null;
  }

  if (layerId === "wireframe") {
    const material = surfaceMaterial(layerId, undefined, true);
    const mesh = new THREE.Mesh(geometry, material);
    mesh.userData.pickable = true;
    return { mesh, geometry, material };
  }

  const elevation = layerElevation(artifact, layerId);
  if (mode === "wireframe") {
    const material = surfaceMaterial(layerId, elevation, true);
    const mesh = new THREE.Mesh(geometry, material);
    mesh.userData.pickable = true;
    return { mesh, geometry, material };
  }

  const material = surfaceMaterial(layerId, elevation, false);
  if (layerId === "rgb") {
    const map = createRgbTexture(artifact);
    if (map) {
      material.map = map;
      material.color.set(0xffffff);
      material.needsUpdate = true;
    }
  }
  const mesh = new THREE.Mesh(geometry, material);
  mesh.userData.pickable = true;
  if (mode === "shaded") {
    return { mesh, geometry, material };
  }

  const wireframe = new THREE.LineSegments(
    new THREE.WireframeGeometry(geometry),
    new THREE.LineBasicMaterial({ color: overlayTint(layerId), opacity: 0.12, transparent: true })
  );
  wireframe.userData.pickable = false;
  return { mesh, wireframe, geometry, material };
}

/**
 * RGB texture mapped with pixel-centre UVs: mesh UVs are col/(w-1), row/(h-1)
 * with row 0 at the top, so the texture is not flipped and is shifted by half
 * a texel to land each pixel centre on its own vertex.
 */
export function createRgbTexture(artifact: SceneArtifact): THREE.Texture | null {
  const data = artifact.texture;
  if (!data) return null;
  const texture = new THREE.Texture(data.image as THREE.Texture["image"]);
  texture.flipY = false;
  texture.colorSpace = THREE.SRGBColorSpace;
  const gridW = artifact.elevation?.width ?? data.width;
  const gridH = artifact.elevation?.height ?? data.height;
  if (gridW > 1 && gridH > 1) {
    texture.repeat.set((gridW - 1) / gridW, (gridH - 1) / gridH);
    texture.offset.set(0.5 / gridW, 0.5 / gridH);
  }
  texture.needsUpdate = true;
  return texture;
}

export function disposeLayerMesh(group: {
  mesh: THREE.Mesh;
  wireframe?: THREE.LineSegments;
  geometry: THREE.BufferGeometry;
  material: THREE.Material;
}): void {
  group.geometry.dispose();
  const map = (group.material as THREE.MeshStandardMaterial).map;
  if (map) map.dispose();
  group.material.dispose();
  if (group.wireframe) {
    group.wireframe.geometry.dispose();
    (group.wireframe.material as THREE.Material).dispose();
  }
}
