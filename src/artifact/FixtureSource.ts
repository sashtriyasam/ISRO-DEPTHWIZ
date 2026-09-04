import type { ArtifactSource } from "./types";
import type { SceneArtifact } from "../types/scene";
import { createDeterministicFixture } from "../fixtures/deterministicFixture";

export class FixtureSource implements ArtifactSource {
  readonly id = "deterministic-fixture";
  readonly label = "Development Fixture";

  async load(): Promise<SceneArtifact> {
    return createDeterministicFixture();
  }
}
