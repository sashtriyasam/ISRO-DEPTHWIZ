import type { InspectionResult } from "./types";
import type { SceneArtifact, ElevationData } from "../types/scene";
import type { LayerId } from "../layers/types";

function sampleElevation(data: ElevationData | undefined, col: number, row: number): number | undefined {
  if (!data) return undefined;
  if (col < 0 || col >= data.width || row < 0 || row >= data.height) return undefined;
  return data.grid[row * data.width + col];
}

function resolveFromIntersection(
  u: number,
  v: number,
  artifact: SceneArtifact,
  layerId: LayerId,
  position: { x: number; y: number; z: number }
): InspectionResult {
  const elevation = artifact.elevation;
  const col = Math.round(u * ((elevation?.width ?? 1) - 1));
  const row = Math.round(v * ((elevation?.height ?? 1) - 1));

  return {
    position,
    uv: { u, v },
    gridIndex: { col, row },
    scientific: {
      elevation: sampleElevation(elevation, col, row) ?? position.y,
      rdsm: sampleElevation(artifact.layers?.rdsm, col, row),
      agl: sampleElevation(artifact.layers?.agl, col, row),
    },
    layerId,
    artifactId: artifact.id,
  };
}

export function resolveInspection(
  uv: { u: number; v: number } | null,
  position: { x: number; y: number; z: number } | null,
  artifact: SceneArtifact,
  layerId: LayerId
): InspectionResult | null {
  if (!uv || !position) return null;
  return resolveFromIntersection(uv.u, uv.v, artifact, layerId, position);
}
