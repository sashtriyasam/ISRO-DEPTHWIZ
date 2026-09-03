import type { SceneArtifact } from "../types/scene";
import type { ArtifactSource } from "../artifact/types";
import { BackendBridge, type BridgeResult } from "./bridge";

export interface BackendSourceOptions {
  width?: number;
  height?: number;
  pythonPath?: string;
  bridgeScript?: string;
}

export class BackendArtifactSource implements ArtifactSource {
  readonly id: string;
  readonly label: string;

  private bridge: BackendBridge;
  private width: number;
  private height: number;

  constructor(options: BackendSourceOptions = {}) {
    this.width = options.width ?? 8;
    this.height = options.height ?? 8;
    this.bridge = new BackendBridge({
      pythonPath: options.pythonPath,
      bridgeScript: options.bridgeScript,
    });
    this.id = "backend-synthetic";
    this.label = "Synthetic Backend";
  }

  async load(): Promise<SceneArtifact> {
    const result: BridgeResult = await this.bridge.executeSynthetic(
      this.width,
      this.height
    );

    if (!result.success || !result.artifact) {
      const errorMessages = result.errors.map((e) => `[${e.phase}] ${e.message}`).join("; ");
      throw new Error(`Backend execution failed: ${errorMessages}`);
    }

    return result.artifact;
  }

  getWarnings(): string[] {
    return [];
  }
}
