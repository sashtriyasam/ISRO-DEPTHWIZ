import type { SceneArtifact } from "../types/scene";

/** Target relief of a relative scene as a fraction of its horizontal span. */
export const RELATIVE_RELIEF_FRACTION = 0.15;

/**
 * Display-only vertical factor for relative (Path A) scenes.
 *
 * Relative meshes place vertices on pixel indices (X/Z) with unitless
 * heights (Y): DA-V2 disparity spans tens of units over thousands of
 * pixels, so the surface renders flat. This factor gives the relief a
 * readable share of the footprint. It only scales the rendered geometry;
 * inspected and measured values come from the elevation grid and are
 * unchanged. Metric scenes always return 1 (true proportions).
 */
export function relativeDisplayFit(scene: SceneArtifact | null | undefined): number {
  if (!scene) return 1;
  const { units, bounds } = scene.metadata;
  if (units.elevation !== "relative" || units.spatial !== "pixels" || !bounds) return 1;
  const relief = bounds.maxY - bounds.minY;
  const span = Math.max(bounds.maxX - bounds.minX, bounds.maxZ - bounds.minZ);
  if (!(relief > 0) || !(span > 0)) return 1;
  return Math.min(1000, Math.max(0.01, (RELATIVE_RELIEF_FRACTION * span) / relief));
}
