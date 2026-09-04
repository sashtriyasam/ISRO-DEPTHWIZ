import type { ArtifactSource, ArtifactLoadResult, ArtifactError, ArtifactLoadOptions } from "./types";

export class ArtifactLoader {
  private currentSource: ArtifactSource | null = null;

  async load(source: ArtifactSource, options?: ArtifactLoadOptions): Promise<ArtifactLoadResult> {
    this.currentSource = source;
    try {
      const artifact = await source.load(options);
      return { artifact, source };
    } catch (err) {
      const error: ArtifactError = {
        source,
        message: err instanceof Error ? err.message : "Unknown error during artifact load",
        cause: err,
      };
      throw error;
    }
  }

  getCurrentSource(): ArtifactSource | null {
    return this.currentSource;
  }

  cancel(): void {
    this.currentSource = null;
  }
}
