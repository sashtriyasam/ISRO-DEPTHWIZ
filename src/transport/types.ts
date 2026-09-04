import type { BridgeError } from "../backend/bridge";
import type { BackendTerrainProduct } from "../backend/types";
import type { MetricTargetSemantics, ServiceResponseWire } from "../service/wireTypes";
import type { ProcessingStage } from "../processing/types";

export interface TerrainFetchRequest {
  stagedPath: string;
  targetSemantics?: MetricTargetSemantics;
  buildMesh?: boolean;
}

export interface TerrainBundle {
  response: ServiceResponseWire;
  terrain: BackendTerrainProduct;
}

export const TRANSPORT_ERROR_CODES = [
  "SERVICE_UNAVAILABLE",
  "SERVICE_REJECTED",
  "ARTIFACT_UNAVAILABLE",
  "PAYLOAD_FAILED",
  "CHECKSUM_MISMATCH",
  "DESCRIPTOR_MISMATCH",
  "RESOLUTION_FAILED",
  "OPERATION_CANCELLED",
] as const;

export type TransportErrorCode = (typeof TRANSPORT_ERROR_CODES)[number];

export type ArtifactTransportErrorCode = TransportErrorCode | (string & {});

export interface ArtifactTransportError {
  code: ArtifactTransportErrorCode;
  message: string;
  stage: ProcessingStage | null;
  detail?: string;
}

const ADAPTER_PHASE_CODES: readonly string[] = [
  "ARTIFACT_UNAVAILABLE",
  "PAYLOAD_FAILED",
  "CHECKSUM_MISMATCH",
  "DESCRIPTOR_MISMATCH",
  "RESOLUTION_FAILED",
];

export function toBridgeErrors(error: ArtifactTransportError): BridgeError[] {
  return [
    {
      code: error.code,
      message: error.detail ? `${error.message} (${error.detail})` : error.message,
      phase: ADAPTER_PHASE_CODES.includes(error.code) ? "adapter" : "process",
    },
  ];
}

export class ArtifactTransportFailure extends Error {
  readonly transportError: ArtifactTransportError;

  constructor(transportError: ArtifactTransportError) {
    super(transportError.message);
    this.name = "ArtifactTransportFailure";
    this.transportError = transportError;
  }

  toBridgeErrors(): BridgeError[] {
    return toBridgeErrors(this.transportError);
  }
}
