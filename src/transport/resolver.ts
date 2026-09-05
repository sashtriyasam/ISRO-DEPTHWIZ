import type { SceneArtifact } from "../types/scene";
import {
  adaptRelativeProduct,
  adaptTerrainProduct,
} from "../backend/meshAdapter";
import type { RelativeBundle, TerrainBundle } from "./types";
import { ArtifactTransportFailure } from "./types";
import { verifyBundle, verifyRelativeBundle } from "./verify";

export function resolveTerrainArtifact(bundle: TerrainBundle): SceneArtifact {
  verifyBundle(bundle);
  const result = adaptTerrainProduct(bundle.terrain);
  if (!result.success || !result.artifact) {
    throw new ArtifactTransportFailure({
      code: "RESOLUTION_FAILED",
      message: `Terrain payload rejected: ${result.errors.map((e) => e.code).join(", ")}`,
      stage: null,
      detail: result.errors.map((e) => e.message).join("; "),
    });
  }
  return result.artifact;
}

export function resolveRelativeArtifact(bundle: RelativeBundle): SceneArtifact {
  verifyRelativeBundle(bundle);
  const result = adaptRelativeProduct(bundle.relative);
  if (!result.success || !result.artifact) {
    throw new ArtifactTransportFailure({
      code: "RESOLUTION_FAILED",
      message: `Relative payload rejected: ${result.errors.map((e) => e.code).join(", ")}`,
      stage: null,
      detail: result.errors.map((e) => e.message).join("; "),
    });
  }
  return result.artifact;
}
