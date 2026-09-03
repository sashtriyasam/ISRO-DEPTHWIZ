export interface SceneArtifact {
  id: string;
  label: string;
  mesh: MeshData;
  texture?: TextureData;
  elevation?: ElevationData;
  metadata: SceneMetadata;
}

export interface MeshData {
  vertices: Float32Array;
  indices: Uint32Array;
  normals?: Float32Array;
  uvs?: Float32Array;
  vertexCount: number;
  indexCount: number;
}

export interface TextureData {
  image: ImageData | HTMLImageElement;
  width: number;
  height: number;
}

export interface ElevationData {
  grid: Float32Array;
  width: number;
  height: number;
  cellSize: number;
  noDataValue?: number;
  unit: "meters";
}

export interface SceneMetadata {
  CRS?: string;
  transform?: GeoTransform;
  bounds?: BoundingBox3D;
  units: {
    spatial: "meters";
    elevation: "meters";
  };
  source: "deterministic-fixture" | "backend";
  description?: string;
}

export interface GeoTransform {
  originX: number;
  originY: number;
  pixelWidth: number;
  pixelHeight: number;
  rotation?: number;
}

export interface BoundingBox3D {
  minX: number;
  minY: number;
  minZ: number;
  maxX: number;
  maxY: number;
  maxZ: number;
}

export interface DisplayTransform {
  heightExaggeration: number;
}

export const DEFAULT_DISPLAY_TRANSFORM: DisplayTransform = {
  heightExaggeration: 1.0,
};
