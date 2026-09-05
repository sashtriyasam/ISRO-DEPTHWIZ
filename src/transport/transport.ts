import {
  BackendBridge,
  OperationCancelledError,
  type BridgeExecutionHooks,
} from "../backend/bridge";
import type { ArtifactLoadOptions } from "../artifact/types";
import { LocalServiceClient } from "../service/client";
import { meshDescriptorOf } from "../service/processing";
import { ServiceWireError } from "../service/validator";
import {
  ArtifactTransportFailure,
  type TerrainBundle,
  type TerrainFetchRequest,
} from "./types";

export interface ArtifactTransport {
  fetchTerrain(
    request: TerrainFetchRequest,
    options?: ArtifactLoadOptions,
  ): Promise<TerrainBundle>;
}

export interface ServiceArtifactTransportOptions {
  serviceClient?: LocalServiceClient;
  bridge?: BackendBridge;
}

export class ServiceArtifactTransport implements ArtifactTransport {
  private serviceClient: LocalServiceClient;
  private bridge: BackendBridge;

  constructor(options: ServiceArtifactTransportOptions = {}) {
    this.serviceClient = options.serviceClient ?? new LocalServiceClient();
    this.bridge = options.bridge ?? new BackendBridge();
  }

  async fetchTerrain(
    request: TerrainFetchRequest,
    options: ArtifactLoadOptions = {},
  ): Promise<TerrainBundle> {
    const hooks: BridgeExecutionHooks = {
      signal: options.signal,
      onStage: options.onStage,
    };

    let response;
    try {
      const execution = await this.serviceClient.executeService(
        {
          inputPath: request.stagedPath,
          targetSemantics: request.targetSemantics,
          buildMesh: request.buildMesh ?? true,
          backend: request.backend,
        },
        hooks,
      );
      response = execution.response;
    } catch (err) {
      throw this.controlFailure(err, options.signal?.aborted === true);
    }

    if (!response.success) {
      throw new ArtifactTransportFailure({
        code: response.failure?.code ?? "SERVICE_REJECTED",
        message: response.failure?.message ?? "Service execution failed",
        stage: null,
        detail: response.failure?.stage
          ? `stage ${response.failure.stage}`
          : undefined,
      });
    }

    const mesh = meshDescriptorOf(response);
    if (!mesh || !mesh.available) {
      throw new ArtifactTransportFailure({
        code: "ARTIFACT_UNAVAILABLE",
        message: "Service completed without an available mesh artifact",
        stage: null,
      });
    }

    try {
      const terrain = await this.bridge.fetchTerrainPayload(
        request.stagedPath,
        hooks,
        request.targetSemantics,
        request.backend,
      );
      return { response, terrain };
    } catch (err) {
      if (err instanceof ArtifactTransportFailure) {
        throw err;
      }
      if (err instanceof OperationCancelledError || options.signal?.aborted) {
        throw new ArtifactTransportFailure({
          code: "OPERATION_CANCELLED",
          message: "Operation cancelled",
          stage: null,
        });
      }
      throw new ArtifactTransportFailure({
        code: "PAYLOAD_FAILED",
        message: "Terrain payload transfer failed",
        stage: null,
        detail: err instanceof Error ? err.message : String(err),
      });
    }
  }

  private controlFailure(
    err: unknown,
    aborted: boolean,
  ): ArtifactTransportFailure {
    if (err instanceof OperationCancelledError || aborted) {
      return new ArtifactTransportFailure({
        code: "OPERATION_CANCELLED",
        message: "Operation cancelled",
        stage: null,
      });
    }
    if (err instanceof ServiceWireError) {
      return new ArtifactTransportFailure({
        code: "SERVICE_UNAVAILABLE",
        message: "Service control plane failed",
        stage: null,
        detail: err.message,
      });
    }
    return new ArtifactTransportFailure({
      code: "SERVICE_UNAVAILABLE",
      message: "Service control plane failed",
      stage: null,
      detail: err instanceof Error ? err.message : String(err),
    });
  }
}
