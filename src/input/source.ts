import type { SceneArtifact } from "../types/scene";
import type { ArtifactSource, ArtifactLoadOptions } from "../artifact/types";
import {
  BackendBridge,
  type BridgeExecutionHooks,
  type BridgeResult,
} from "../backend/bridge";
import { BackendOperationError } from "../backend/source";
import type { InputMetadata } from "./types";

export interface FileInputSourceOptions {
  stagedPath: string;
  metadata: InputMetadata;
  pythonPath?: string;
  bridgeScript?: string;
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
  private stagedPath: string;
  readonly metadata: InputMetadata;

  constructor(options: FileInputSourceOptions) {
    this.stagedPath = options.stagedPath;
    this.metadata = options.metadata;
    this.bridge = new BackendBridge({
      pythonPath: options.pythonPath,
      bridgeScript: options.bridgeScript,
    });
    this.id = stableIdFor(options.metadata);
    this.label = options.metadata.filename;
  }

  async load(loadOptions?: ArtifactLoadOptions): Promise<SceneArtifact> {
    const hooks: BridgeExecutionHooks = {
      signal: loadOptions?.signal,
      onStage: loadOptions?.onStage,
    };
    const result: BridgeResult = await this.bridge.executeTerrainFile(
      this.stagedPath,
      hooks
    );

    if (!result.success || !result.artifact) {
      throw new BackendOperationError(result.errors);
    }

    return result.artifact;
  }
}
