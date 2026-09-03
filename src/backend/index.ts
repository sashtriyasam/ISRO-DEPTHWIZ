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
} from "./types";
export { adaptBackendResult, adaptCalibratedResult } from "./adapter";
export type { AdapterResult, AdapterError } from "./adapter";
export { BACKEND_TEST_FIXTURE, BACKEND_CALIBRATION_FIXTURE, BACKEND_METRIC_FIXTURE } from "./fixtures";
export { BackendBridge } from "./bridge";
export type { BridgeResult, BridgeError, BackendBridgeOptions } from "./bridge";
export { BackendArtifactSource } from "./source";
export type { BackendSourceOptions } from "./source";
