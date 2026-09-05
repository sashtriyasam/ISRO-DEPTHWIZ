import type { SceneArtifact } from "../types/scene";
import type { ArtifactSource, ArtifactLoadOptions } from "../artifact/types";
import { BackendOperationError } from "../backend/source";
import {
  ArtifactTransportFailure,
  ServiceArtifactTransport,
  resolveRelativeArtifact,
  resolveTerrainArtifact,
  type ArtifactTransport,
} from "../transport";
import type { MetricTargetSemantics } from "../service/wireTypes";
import type { InputMetadata } from "./types";

export interface FileInputSourceOptions {
  stagedPath: string;
  metadata: InputMetadata;
  transport?: ArtifactTransport;
  targetSemantics?: MetricTargetSemantics;
  backend?: string;
  mode?: "metric" | "relative";
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

  private transport: ArtifactTransport;
  private stagedPath: string;
  readonly metadata: InputMetadata;
  readonly targetSemantics: MetricTargetSemantics;
  private backend?: string;
  private mode: "metric" | "relative";

  constructor(options: FileInputSourceOptions) {
    this.stagedPath = options.stagedPath;
    this.metadata = options.metadata;
    this.transport = options.transport ?? new ServiceArtifactTransport();
    this.targetSemantics = options.targetSemantics ?? "absolute_elevation_dsm";
    this.backend = options.backend;
    this.mode = options.mode ?? "metric";
    this.id = stableIdFor(options.metadata);
    this.label = options.metadata.filename;
  }

  async load(loadOptions?: ArtifactLoadOptions): Promise<SceneArtifact> {
    try {
      if (this.mode === "relative") {
        if (!this.transport.fetchRelative) {
          throw new ArtifactTransportFailure({
            code: "ARTIFACT_UNAVAILABLE",
            message: "Transport does not support relative products",
            stage: null,
          });
        }
        const bundle = await this.transport.fetchRelative(
          {
            stagedPath: this.stagedPath,
            targetSemantics: this.targetSemantics,
            backend: this.backend,
            mode: "relative",
          },
          loadOptions,
        );
        return resolveRelativeArtifact(bundle);
      }
      const bundle = await this.transport.fetchTerrain(
        {
          stagedPath: this.stagedPath,
          targetSemantics: this.targetSemantics,
          backend: this.backend,
        },
        loadOptions,
      );
      return resolveTerrainArtifact(bundle);
    } catch (err) {
      if (err instanceof ArtifactTransportFailure) {
        throw new BackendOperationError(err.toBridgeErrors());
      }
      throw new BackendOperationError([
        {
          code: "ARTIFACT_UNAVAILABLE",
          message: err instanceof Error ? err.message : String(err),
          phase: "process",
        },
      ]);
    }
  }
}
