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
  return withPayloadExtras(
    withWarnings(result.artifact, bundle.response.warnings),
    bundle.response.payload,
  );
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
  return withPayloadExtras(
    withWarnings(result.artifact, bundle.response.warnings),
    bundle.response.payload,
  );
}

function withWarnings(artifact: SceneArtifact, warnings: string[] | undefined): SceneArtifact {
  if (!warnings || warnings.length === 0) return artifact;
  return { ...artifact, metadata: { ...artifact.metadata, warnings: [...warnings] } };
}

/** Staged extras of the service run (texture for relative runs too). */
function withPayloadExtras(artifact: SceneArtifact, payload: unknown): SceneArtifact {
  if (typeof payload !== "object" || payload === null) return artifact;
  const extras = payload as {
    texture_path?: unknown;
    geotiff_path?: unknown;
    product_path?: unknown;
  };
  const metadata = { ...artifact.metadata };
  if (typeof extras.texture_path === "string" && !metadata.texturePath) {
    metadata.texturePath = extras.texture_path;
  }
  if (typeof extras.geotiff_path === "string" && !metadata.exportPath) {
    metadata.exportPath = extras.geotiff_path;
  }
  if (typeof extras.product_path === "string") {
    metadata.productPath = extras.product_path;
  }
  return { ...artifact, metadata };
}
