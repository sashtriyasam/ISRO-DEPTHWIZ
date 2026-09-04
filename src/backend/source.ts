import type { SceneArtifact } from "../types/scene";
import type { ArtifactSource, ArtifactLoadOptions } from "../artifact/types";
import { BackendBridge, type BridgeError, type BridgeExecutionHooks, type BridgeResult } from "./bridge";

export class BackendOperationError extends Error {
  readonly bridgeErrors: BridgeError[];

  constructor(bridgeErrors: BridgeError[]) {
    super(`Backend execution failed: ${bridgeErrors.map((e) => `[${e.phase}] ${e.message}`).join("; ")}`);
    this.name = "BackendOperationError";
    this.bridgeErrors = bridgeErrors;
  }
}

export type BackendSourceMode = "depth" | "terrain";

export interface BackendSourceOptions {
  width?: number;
  height?: number;
  pythonPath?: string;
  bridgeScript?: string;
  mode?: BackendSourceMode;
}

export class BackendArtifactSource implements ArtifactSource {
  readonly id: string;
  readonly label: string;

  private bridge: BackendBridge;
  private width: number;
  private height: number;
  private mode: BackendSourceMode;

  constructor(options: BackendSourceOptions = {}) {
    this.width = options.width ?? 8;
    this.height = options.height ?? 8;
    this.mode = options.mode ?? "terrain";
    this.bridge = new BackendBridge({
      pythonPath: options.pythonPath,
      bridgeScript: options.bridgeScript,
    });
    this.id = "backend-synthetic";
    this.label = "Synthetic Backend";
  }

  async load(options?: ArtifactLoadOptions): Promise<SceneArtifact> {
    const hooks: BridgeExecutionHooks = {
      signal: options?.signal,
      onStage: options?.onStage,
    };
    const result: BridgeResult =
      this.mode === "terrain"
        ? await this.bridge.executeTerrain(this.width, this.height, hooks)
        : await this.bridge.executeSynthetic(this.width, this.height, hooks);

    if (!result.success || !result.artifact) {
      throw new BackendOperationError(result.errors);
    }

    return result.artifact;
  }

  getWarnings(): string[] {
    return [];
  }
}
