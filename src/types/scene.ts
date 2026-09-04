export interface SceneArtifact {
  id: string;
  label: string;
  mesh: MeshData;
  texture?: TextureData;
  elevation?: ElevationData;
  layers?: LayerPayloads;
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

export type ElevationUnit = "meters" | "relative" | string;

export interface ElevationData {
  grid: Float32Array;
  width: number;
  height: number;
  cellSize: number;
  noDataValue?: number;
  unit: ElevationUnit;
}

export interface LayerPayloads {
  rdsm?: ElevationData;
  agl?: ElevationData;
}

export interface BackendOrigin {
  model_name: string;
  model_version?: string;
  depth_scale: "relative" | "metric";
  elevation_semantics: string;
  georeferencing: string;
  calibration_method?: string;
  calibration_reference?: string;
  calibration_scale?: number;
  calibration_offset?: number;
  input_id?: string;
  input_checksum?: string;
  software_version?: string;
  semantic_meaning?: string;
}

export interface SpatialDetails {
  gsd?: number;
  nodata?: number | null;
  rasterWidth?: number;
  rasterHeight?: number;
  spatialUnits?: string;
  source?: string;
  affine?: [number, number, number, number, number, number];
  spatialBounds?: { minX: number; minY: number; maxX: number; maxY: number };
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
  backend?: BackendOrigin;
  spatialDetails?: SpatialDetails;
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
