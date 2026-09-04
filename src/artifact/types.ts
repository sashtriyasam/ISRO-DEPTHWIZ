import type { SceneArtifact } from "../types/scene";

export type ArtifactState = "idle" | "loading" | "ready" | "error";

export interface ArtifactLoadOptions {
  signal?: AbortSignal;
  onStage?: (stage: string) => void;
}

export interface ArtifactSource {
  readonly id: string;
  readonly label: string;
  load(options?: ArtifactLoadOptions): Promise<SceneArtifact>;
}

export interface ArtifactLoadResult {
  artifact: SceneArtifact;
  source: ArtifactSource;
}

export interface ArtifactError {
  source: ArtifactSource;
  message: string;
  cause?: unknown;
}
