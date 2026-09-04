import {
  PIPELINE_STATE_VALUES,
  SERVICE_ARTIFACT_KINDS,
  SERVICE_CONTRACT_VERSION,
  type ArtifactDescriptorWire,
  type RunSummaryWire,
  type ServiceCapabilitiesWire,
  type ServiceFailureWire,
  type ServiceResponseWire,
} from "./wireTypes";

export class ServiceWireError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ServiceWireError";
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function validateFailure(value: unknown): ServiceFailureWire {
  if (!isRecord(value)) {
    throw new ServiceWireError("Service failure must be an object");
  }
  if (typeof value.code !== "string" || value.code.length === 0) {
    throw new ServiceWireError("Service failure code must be a non-empty string");
  }
  if (typeof value.message !== "string") {
    throw new ServiceWireError("Service failure message must be a string");
  }
  if (value.stage !== null && value.stage !== undefined && typeof value.stage !== "string") {
    throw new ServiceWireError("Service failure stage must be a string or null");
  }
  return {
    code: value.code,
    message: value.message,
    stage: typeof value.stage === "string" ? value.stage : null,
  };
}

function validateDescriptor(value: unknown): ArtifactDescriptorWire {
  if (!isRecord(value)) {
    throw new ServiceWireError("Artifact descriptor must be an object");
  }
  if (typeof value.kind !== "string" || !(SERVICE_ARTIFACT_KINDS as readonly string[]).includes(value.kind)) {
    throw new ServiceWireError(`Unknown artifact kind: ${String(value.kind)}`);
  }
  if (typeof value.available !== "boolean") {
    throw new ServiceWireError("Artifact descriptor available must be a boolean");
  }
  if (typeof value.persisted !== "boolean") {
    throw new ServiceWireError("Artifact descriptor persisted must be a boolean");
  }
  const optionalString = (v: unknown, field: string): string | null => {
    if (v === null || v === undefined) {
      return null;
    }
    if (typeof v !== "string") {
      throw new ServiceWireError(`Artifact descriptor ${field} must be a string or null`);
    }
    return v;
  };
  const optionalInt = (v: unknown, field: string): number | null => {
    if (v === null || v === undefined) {
      return null;
    }
    if (typeof v !== "number" || !Number.isInteger(v)) {
      throw new ServiceWireError(`Artifact descriptor ${field} must be an integer or null`);
    }
    return v;
  };
  const optionalBool = (v: unknown, field: string): boolean | null => {
    if (v === null || v === undefined) {
      return null;
    }
    if (typeof v !== "boolean") {
      throw new ServiceWireError(`Artifact descriptor ${field} must be a boolean or null`);
    }
    return v;
  };
  return {
    kind: value.kind,
    available: value.available,
    persisted: value.persisted,
    path: optionalString(value.path, "path"),
    semantics: optionalString(value.semantics, "semantics"),
    units: optionalString(value.units, "units"),
    width: optionalInt(value.width, "width"),
    height: optionalInt(value.height, "height"),
    georeferenced: optionalBool(value.georeferenced, "georeferenced"),
  };
}

function validateSummary(value: unknown): RunSummaryWire {
  if (!isRecord(value)) {
    throw new ServiceWireError("Run summary must be an object");
  }
  if (typeof value.input_path !== "string") {
    throw new ServiceWireError("Run summary input_path must be a string");
  }
  if (typeof value.engine_version !== "string") {
    throw new ServiceWireError("Run summary engine_version must be a string");
  }
  if (typeof value.mesh_requested !== "boolean") {
    throw new ServiceWireError("Run summary mesh_requested must be a boolean");
  }
  const optionalString = (v: unknown): string | null =>
    v === null || v === undefined ? null : String(v);
  if (
    value.input_checksum !== null &&
    value.input_checksum !== undefined &&
    typeof value.input_checksum !== "string"
  ) {
    throw new ServiceWireError("Run summary input_checksum must be a string or null");
  }
  return {
    input_path: value.input_path,
    input_checksum: (value.input_checksum as string | null) ?? null,
    backend_name: optionalString(value.backend_name),
    backend_version: optionalString(value.backend_version),
    calibration_method: optionalString(value.calibration_method),
    calibration_reference: optionalString(value.calibration_reference),
    target_semantics: optionalString(value.target_semantics),
    mesh_requested: value.mesh_requested,
    geotiff_path: optionalString(value.geotiff_path),
    engine_version: value.engine_version,
  };
}

export function validateServiceResponse(data: unknown): ServiceResponseWire {
  if (!isRecord(data)) {
    throw new ServiceWireError("Service response must be an object");
  }
  if (data.contract_version !== SERVICE_CONTRACT_VERSION) {
    throw new ServiceWireError(
      `Unsupported service contract version: ${String(data.contract_version)}`
    );
  }
  if (typeof data.success !== "boolean") {
    throw new ServiceWireError("Service response success must be a boolean");
  }
  if (typeof data.final_state !== "string" || !(PIPELINE_STATE_VALUES as readonly string[]).includes(data.final_state)) {
    throw new ServiceWireError(`Unknown service final_state: ${String(data.final_state)}`);
  }
  if (!Array.isArray(data.states) || !data.states.every((s) => typeof s === "string" && (PIPELINE_STATE_VALUES as readonly string[]).includes(s))) {
    throw new ServiceWireError("Service response states must be known pipeline states");
  }
  if (data.success && data.final_state !== "completed") {
    throw new ServiceWireError(
      `Inconsistent service response: success with final_state '${data.final_state}'`
    );
  }
  if (!data.success && data.final_state !== "failed" && data.final_state !== "cancelled") {
    throw new ServiceWireError(
      `Inconsistent service response: failure with final_state '${data.final_state}'`
    );
  }
  if (data.failure !== null && data.failure !== undefined) {
    validateFailure(data.failure);
  }
  if (!data.success && (data.failure === null || data.failure === undefined)) {
    throw new ServiceWireError("Failed service response must carry a failure record");
  }
  if (!Array.isArray(data.artifacts)) {
    throw new ServiceWireError("Service response artifacts must be an array");
  }
  const artifacts = data.artifacts.map(validateDescriptor);
  const summary = validateSummary(data.summary);
  return {
    contract_version: data.contract_version,
    success: data.success,
    final_state: data.final_state,
    states: data.states as string[],
    failure: (data.failure as ServiceFailureWire | null) ?? null,
    artifacts,
    summary,
  };
}

export function validateServiceCapabilities(data: unknown): ServiceCapabilitiesWire {
  if (!isRecord(data)) {
    throw new ServiceWireError("Service capabilities must be an object");
  }
  if (data.contract_version !== SERVICE_CONTRACT_VERSION) {
    throw new ServiceWireError(
      `Unsupported service contract version: ${String(data.contract_version)}`
    );
  }
  if (
    !Array.isArray(data.supported_input_formats) ||
    !data.supported_input_formats.every((s): s is string => typeof s === "string")
  ) {
    throw new ServiceWireError("Capabilities supported_input_formats must be strings");
  }
  if (
    !Array.isArray(data.supported_target_semantics) ||
    !data.supported_target_semantics.every((s): s is string => typeof s === "string")
  ) {
    throw new ServiceWireError("Capabilities supported_target_semantics must be strings");
  }
  if (
    !Array.isArray(data.available_backends) ||
    !data.available_backends.every((s): s is string => typeof s === "string")
  ) {
    throw new ServiceWireError("Capabilities available_backends must be strings");
  }
  if (typeof data.mesh_supported !== "boolean" || typeof data.geotiff_supported !== "boolean") {
    throw new ServiceWireError("Capabilities mesh/geotiff flags must be booleans");
  }
  return {
    contract_version: data.contract_version,
    supported_input_formats: data.supported_input_formats,
    supported_target_semantics: data.supported_target_semantics,
    available_backends: data.available_backends,
    mesh_supported: data.mesh_supported,
    geotiff_supported: data.geotiff_supported,
  };
}
