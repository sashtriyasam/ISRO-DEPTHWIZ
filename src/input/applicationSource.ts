import type { SceneArtifact } from "../types/scene";
import type { ArtifactSource, ArtifactLoadOptions } from "../artifact/types";
import { BackendBridge, type BridgeResult } from "../backend/bridge";
import { BackendOperationError } from "../backend/source";
import type { MetricTargetSemantics } from "../service/wireTypes";
import type { ArtifactTransport } from "../transport/transport";
import { FileInputSource } from "./source";
import type { InputMetadata } from "./types";

export type ApplicationBackendKind = "file" | "synthetic";

export const APPLICATION_BACKEND_LABEL = "Synthetic Development Backend";

export const DEFAULT_TARGET_SEMANTICS: MetricTargetSemantics =
  "absolute_elevation_dsm";

export interface ApplicationBackendOptions {
  stagedPath?: string;
  metadata?: InputMetadata;
  syntheticSize?: { width: number; height: number };
  targetSemantics?: MetricTargetSemantics;
  transport?: ArtifactTransport;
  bridge?: BackendBridge;
  backend?: string;
}

export class ApplicationBackendSource implements ArtifactSource {
  readonly id: string;
  readonly label: string;
  readonly kind: ApplicationBackendKind;
  readonly targetSemantics: MetricTargetSemantics;
  readonly backendLabel: string;

  private fileSource: FileInputSource | null;
  private bridge: BackendBridge;
  private syntheticWidth = 8;
  private syntheticHeight = 8;

  constructor(options: ApplicationBackendOptions = {}) {
    this.targetSemantics = options.targetSemantics ?? DEFAULT_TARGET_SEMANTICS;
    this.backendLabel =
      options.backend && options.backend !== "synthetic-depth"
        ? `Backend model (${options.backend})`
        : APPLICATION_BACKEND_LABEL;
    this.bridge =
      options.bridge ?? new BackendBridge({ backend: options.backend });
    if (options.stagedPath && options.metadata) {
      this.kind = "file";
      this.fileSource = new FileInputSource({
        stagedPath: options.stagedPath,
        metadata: options.metadata,
        transport: options.transport,
        targetSemantics: this.targetSemantics,
        backend: options.backend,
      });
      this.id = this.fileSource.id;
      this.label = this.fileSource.label;
    } else {
      this.kind = "synthetic";
      this.fileSource = null;
      this.syntheticWidth = options.syntheticSize?.width ?? 8;
      this.syntheticHeight = options.syntheticSize?.height ?? 8;
      this.id = "backend-synthetic";
      this.label = APPLICATION_BACKEND_LABEL;
    }
  }

  async load(loadOptions?: ArtifactLoadOptions): Promise<SceneArtifact> {
    if (this.fileSource) {
      return this.fileSource.load(loadOptions);
    }
    const result: BridgeResult = await this.bridge.executeTerrain(
      this.syntheticWidth,
      this.syntheticHeight,
      { signal: loadOptions?.signal, onStage: loadOptions?.onStage },
    );
    if (!result.success || !result.artifact) {
      throw new BackendOperationError(result.errors);
    }
    return result.artifact;
  }
}
