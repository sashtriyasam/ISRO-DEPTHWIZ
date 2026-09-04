import type { SceneArtifact } from "../types/scene";
import type { ArtifactSource, ArtifactLoadOptions } from "../artifact/types";
import {
  BackendBridge,
  type BridgeExecutionHooks,
  type BridgeResult,
} from "../backend/bridge";
import { BackendOperationError } from "../backend/source";
import { LocalServiceClient } from "../service/client";
import { meshDescriptorOf } from "../service/processing";
import type { InputMetadata } from "./types";

export interface FileInputSourceOptions {
  stagedPath: string;
  metadata: InputMetadata;
  pythonPath?: string;
  bridgeScript?: string;
  serviceClient?: LocalServiceClient;
}

function stableIdFor(metadata: InputMetadata): string {
  if (metadata.checksum) {
    return `file-${metadata.checksum.slice(0, 16)}`;
  }
  const slug = metadata.filename
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 32);
  return `file-${slug || "input"}`;
}

export class FileInputSource implements ArtifactSource {
  readonly id: string;
  readonly label: string;

  private bridge: BackendBridge;
  private serviceClient: LocalServiceClient;
  private stagedPath: string;
  readonly metadata: InputMetadata;

  constructor(options: FileInputSourceOptions) {
    this.stagedPath = options.stagedPath;
    this.metadata = options.metadata;
    this.bridge = new BackendBridge({
      pythonPath: options.pythonPath,
      bridgeScript: options.bridgeScript,
    });
    this.serviceClient = options.serviceClient ?? new LocalServiceClient();
    this.id = stableIdFor(options.metadata);
    this.label = options.metadata.filename;
  }

  async load(loadOptions?: ArtifactLoadOptions): Promise<SceneArtifact> {
    const hooks: BridgeExecutionHooks = {
      signal: loadOptions?.signal,
      onStage: loadOptions?.onStage,
    };

    let meshAvailable = false;
    let meshSemantics: string | null = null;
    let meshUnits: string | null = null;
    try {
      const { response } = await this.serviceClient.executeService(
        { inputPath: this.stagedPath, buildMesh: true },
        hooks
      );
      if (!response.success) {
        throw new BackendOperationError([
          {
            code: response.failure?.code ?? "SERVICE_FAILURE",
            message: response.failure?.message ?? "Service execution failed",
            phase: "process",
          },
        ]);
      }
      const mesh = meshDescriptorOf(response);
      meshAvailable = mesh?.available === true;
      meshSemantics = mesh?.semantics ?? null;
      meshUnits = mesh?.units ?? null;
    } catch (err) {
      if (err instanceof BackendOperationError) {
        throw err;
      }
      throw new BackendOperationError([
        {
          code: "SERVICE_UNAVAILABLE",
          message: err instanceof Error ? err.message : String(err),
          phase: "process",
        },
      ]);
    }

    if (!meshAvailable) {
      throw new BackendOperationError([
        {
          code: "MESH_UNAVAILABLE",
          message: "Service completed without an available mesh artifact",
          phase: "adapter",
        },
      ]);
    }

    const result: BridgeResult = await this.bridge.executeTerrainFile(
      this.stagedPath,
      hooks
    );

    if (!result.success || !result.artifact) {
      throw new BackendOperationError(result.errors);
    }

    const backend = result.artifact.metadata.backend;
    if (
      (meshSemantics !== null && backend?.elevation_semantics !== meshSemantics) ||
      (meshUnits !== null && backend?.depth_scale === "metric" && meshUnits !== "meters")
    ) {
      throw new BackendOperationError([
        {
          code: "DESCRIPTOR_MISMATCH",
          message: "Terrain payload disagrees with the service artifact descriptor",
          phase: "adapter",
        },
      ]);
    }

    return result.artifact;
  }
}
