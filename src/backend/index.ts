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
export { BackendBridge, OperationCancelledError } from "./bridge";
export type {
  BridgeResult,
  BridgeError,
  BackendBridgeOptions,
  BridgeExecutionHooks,
  BackendCapabilities,
  BackendInspection,
  BackendInspectionHandle,
  InspectInputResult,
  StagedInput,
} from "./bridge";
export { BackendArtifactSource, BackendOperationError } from "./source";
export {
  SYNTHETIC_BACKEND_ID,
  kindForBackendName,
  describeBackendSource,
  isBackendRegistered,
  probeBackendAvailability,
} from "./sourceDescriptor";
export type {
  BackendSourceKind,
  BackendAvailability,
  BackendSourceDescriptor,
} from "./sourceDescriptor";
export type { BackendSourceOptions, BackendSourceMode } from "./source";
