export const SERVICE_CONTRACT_VERSION = "1";

export type ServiceArtifactKind =
  | "depth"
  | "calibration"
  | "height"
  | "dsm"
  | "mesh"
  | "geotiff";

export const SERVICE_ARTIFACT_KINDS: readonly ServiceArtifactKind[] = [
  "depth",
  "calibration",
  "height",
  "dsm",
  "mesh",
  "geotiff",
];

export type PipelineStateValue =
  | "input_validated"
  | "preprocessing"
  | "inference_running"
  | "calibrating"
  | "dsm_generation"
  | "mesh_generation"
  | "exporting"
  | "completed"
  | "failed"
  | "cancelled";

export const PIPELINE_STATE_VALUES: readonly PipelineStateValue[] = [
  "input_validated",
  "preprocessing",
  "inference_running",
  "calibrating",
  "dsm_generation",
  "mesh_generation",
  "exporting",
  "completed",
  "failed",
  "cancelled",
];

export type MetricTargetSemantics = "height_agl_ndsm" | "absolute_elevation_dsm";

export interface ServiceRequestArgs {
  inputPath: string;
  targetSemantics?: MetricTargetSemantics;
  buildMesh?: boolean;
}

export interface ServiceRequestWire {
  contract_version: string;
  input_path: string;
  target_semantics: string;
  backend: string;
  preprocessor: string;
  build_mesh: boolean;
  geotiff_path: string | null;
  export_compression: string;
  export_overwrite: boolean;
}

export interface ServiceFailureWire {
  code: string;
  message: string;
  stage: string | null;
}

export interface ArtifactDescriptorWire {
  kind: string;
  available: boolean;
  persisted: boolean;
  path: string | null;
  semantics: string | null;
  units: string | null;
  width: number | null;
  height: number | null;
  georeferenced: boolean | null;
}

export interface RunSummaryWire {
  input_path: string;
  input_checksum: string | null;
  backend_name: string | null;
  backend_version: string | null;
  calibration_method: string | null;
  calibration_reference: string | null;
  target_semantics: string | null;
  mesh_requested: boolean;
  geotiff_path: string | null;
  engine_version: string;
}

export interface ServiceResponseWire {
  contract_version: string;
  success: boolean;
  final_state: string;
  states: string[];
  failure: ServiceFailureWire | null;
  artifacts: ArtifactDescriptorWire[];
  summary: RunSummaryWire;
}

export interface ServiceCapabilitiesWire {
  contract_version: string;
  supported_input_formats: string[];
  supported_target_semantics: string[];
  available_backends: string[];
  mesh_supported: boolean;
  geotiff_supported: boolean;
}
