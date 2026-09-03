export type {
  DepthScale,
  ElevationSemantics,
  GeoreferencingLevel,
  BackendDepthResult,
  BackendCalibrationResult,
  BackendSpatialContext,
  BackendSpatialDetails,
  BackendAffineTransform,
  BackendBounds,
  BackendImageResolution,
  BackendProductProvenance,
  BackendDsmTransport,
  BackendTerrainMeshTransport,
  BackendTerrainProduct,
  MeshCoordinateFrame,
} from "./types";
export { adaptBackendResult, adaptCalibratedResult, mapBackendTransform } from "./adapter";
export type { AdapterResult, AdapterError } from "./adapter";
export { adaptTerrainProduct, validateTerrainProduct } from "./meshAdapter";
export type { MeshAdapterResult } from "./meshAdapter";
export { BACKEND_TEST_FIXTURE, BACKEND_CALIBRATION_FIXTURE, BACKEND_METRIC_FIXTURE } from "./fixtures";
export { BackendBridge } from "./bridge";
export type { BridgeResult, BridgeError, BackendBridgeOptions } from "./bridge";
export { BackendArtifactSource } from "./source";
export type { BackendSourceOptions, BackendSourceMode } from "./source";
