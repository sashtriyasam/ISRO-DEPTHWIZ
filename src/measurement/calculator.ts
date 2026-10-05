import type { MeasurementMode, MeasurementPoint, MeasurementResult } from "./types";

export interface MeasurementUnitsOptions {
  /** Vertical (elevation) units. */
  units?: "meters" | "relative" | string;
  /** Horizontal units of display coordinates (metres or pixel indices). */
  horizontalUnits?: "meters" | "pixels" | string;
  source?: "fixture-coordinate-system" | "backend";
}

export function calculateMeasurement(
  mode: MeasurementMode,
  pointA: MeasurementPoint,
  pointB: MeasurementPoint,
  options?: MeasurementUnitsOptions
): MeasurementResult {
  const units = options?.units ?? "meters";
  const horizontalUnits = options?.horizontalUnits ?? "meters";

  const dx = pointA.displayPosition.x - pointB.displayPosition.x;
  const dz = pointA.displayPosition.z - pointB.displayPosition.z;
  const horizontalDistance = Math.sqrt(dx * dx + dz * dz);

  const verticalDifference = pointA.scientific.elevation - pointB.scientific.elevation;

  // A 3D length only exists when both axes share one unit; pixels beside
  // metres (or relative values) would produce a number with no meaning.
  const distance3D =
    units === horizontalUnits
      ? Math.sqrt(dx * dx + verticalDifference * verticalDifference + dz * dz)
      : Number.NaN;

  return {
    mode,
    pointA,
    pointB,
    horizontalDistance,
    verticalDifference,
    distance3D,
    units,
    horizontalUnits,
    source: options?.source ?? "fixture-coordinate-system",
  };
}

function unitSuffix(units: string): string {
  if (units === "meters") return " m";
  if (units === "pixels") return " px";
  if (units === "relative") return " (relative)";
  return ` ${units}`;
}

export function formatMeasurementValue(mode: MeasurementMode, result: MeasurementResult): string {
  switch (mode) {
    case "distance":
      return `${Math.abs(result.horizontalDistance).toFixed(3)}${unitSuffix(result.horizontalUnits)}`;
    case "vertical":
      return `${Math.abs(result.verticalDifference).toFixed(3)}${unitSuffix(result.units)}`;
    case "distance-3d":
      if (!Number.isFinite(result.distance3D)) {
        return `n/a (horizontal in ${result.horizontalUnits}, vertical in ${result.units})`;
      }
      return `${Math.abs(result.distance3D).toFixed(3)}${unitSuffix(result.units)}`;
  }
}
