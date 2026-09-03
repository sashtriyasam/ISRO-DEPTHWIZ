import type { MeasurementMode, MeasurementPoint, MeasurementResult } from "./types";

export function calculateMeasurement(
  mode: MeasurementMode,
  pointA: MeasurementPoint,
  pointB: MeasurementPoint,
  options?: { units?: "meters" | "relative" | string; source?: "fixture-coordinate-system" | "backend" }
): MeasurementResult {
  const dx = pointA.displayPosition.x - pointB.displayPosition.x;
  const dz = pointA.displayPosition.z - pointB.displayPosition.z;
  const horizontalDistance = Math.sqrt(dx * dx + dz * dz);

  const verticalDifference = pointA.scientific.elevation - pointB.scientific.elevation;

  const dy = pointA.scientific.elevation - pointB.scientific.elevation;
  const distance3D = Math.sqrt(dx * dx + dy * dy + dz * dz);

  return {
    mode,
    pointA,
    pointB,
    horizontalDistance,
    verticalDifference,
    distance3D,
    units: options?.units ?? "meters",
    source: options?.source ?? "fixture-coordinate-system",
  };
}

export function formatMeasurementValue(mode: MeasurementMode, result: MeasurementResult): string {
  let value: number;
  switch (mode) {
    case "distance":
      value = result.horizontalDistance;
      break;
    case "vertical":
      value = result.verticalDifference;
      break;
    case "distance-3d":
      value = result.distance3D;
      break;
  }
  const unitLabel = result.units === "meters" ? " m" : result.units === "relative" ? "" : ` ${result.units}`;
  return `${Math.abs(value).toFixed(3)}${unitLabel}`;
}
