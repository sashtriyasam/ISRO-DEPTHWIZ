import { useMemo } from "react";
import { createDeterministicFixture } from "./deterministicFixture";
import type { SceneArtifact } from "../types/scene";

export function useTestFixture(): SceneArtifact {
  return useMemo(() => createDeterministicFixture(), []);
}
