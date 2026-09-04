import type { SceneArtifact } from "../types/scene";
import type { ArtifactSource, ArtifactLoadOptions } from "../artifact/types";
import { BackendOperationError } from "../backend/source";
import {
  ArtifactTransportFailure,
  ServiceArtifactTransport,
  resolveTerrainArtifact,
  type ArtifactTransport,
} from "../transport";
import type { InputMetadata } from "./types";

export interface FileInputSourceOptions {
  stagedPath: string;
  metadata: InputMetadata;
  transport?: ArtifactTransport;
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

  constructor(options: FileInputSourceOptions) {
    this.stagedPath = options.stagedPath;
    this.metadata = options.metadata;
    this.transport = options.transport ?? new ServiceArtifactTransport();
    this.id = stableIdFor(options.metadata);
    this.label = options.metadata.filename;
  }

  async load(loadOptions?: ArtifactLoadOptions): Promise<SceneArtifact> {
    try {
      const bundle = await this.transport.fetchTerrain(
        { stagedPath: this.stagedPath },
        loadOptions
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
