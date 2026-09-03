import type { ElevationData } from "../types/scene";
import type { MeasurementPoint } from "../measurement/types";
import type { ProfilePoint, ElevationProfile } from "./types";

const DEFAULT_SAMPLE_COUNT = 64;

export interface ProfileSamplerOptions {
  sampleCount?: number;
}

function bilinearSample(grid: Float32Array, width: number, height: number, u: number, v: number): number {
  const gx = u * (width - 1);
  const gy = v * (height - 1);

  const x0 = Math.floor(gx);
  const y0 = Math.floor(gy);
  const x1 = Math.min(x0 + 1, width - 1);
  const y1 = Math.min(y0 + 1, height - 1);

  const fx = gx - x0;
  const fy = gy - y0;

  const v00 = grid[y0 * width + x0];
  const v10 = grid[y0 * width + x1];
  const v01 = grid[y1 * width + x0];
  const v11 = grid[y1 * width + x1];

  const top = v00 * (1 - fx) + v10 * fx;
  const bottom = v01 * (1 - fx) + v11 * fx;
  return top * (1 - fy) + bottom * fy;
}

function sampleElevationAt(
  elevationData: ElevationData,
  pathX: number,
  pathZ: number,
  originX: number,
  originZ: number,
  cellSize: number
): number {
  const u = (pathX - originX) / (cellSize * (elevationData.width - 1));
  const v = (pathZ - originZ) / (cellSize * (elevationData.height - 1));

  const clampedU = Math.max(0, Math.min(1, u));
  const clampedV = Math.max(0, Math.min(1, v));

  return bilinearSample(elevationData.grid, elevationData.width, elevationData.height, clampedU, clampedV);
}

export function generateProfile(
  pointA: MeasurementPoint,
  pointB: MeasurementPoint,
  elevationData: ElevationData | undefined,
  aglData: ElevationData | undefined,
  transform: { originX: number; originY: number; pixelWidth: number; pixelHeight: number } | undefined,
  options?: ProfileSamplerOptions
): ElevationProfile {
  const sampleCount = options?.sampleCount ?? DEFAULT_SAMPLE_COUNT;
  const originX = transform?.originX ?? 0;
  const originZ = transform?.originY ?? 0;
  const cellSize = transform?.pixelWidth ?? elevationData?.cellSize ?? 1;

  const ax = pointA.displayPosition.x;
  const az = pointA.displayPosition.z;
  const bx = pointB.displayPosition.x;
  const bz = pointB.displayPosition.z;

  const dx = bx - ax;
  const dz = bz - az;
  const totalDistance = Math.sqrt(dx * dx + dz * dz);

  const points: ProfilePoint[] = [];
  let minElevation = Infinity;
  let maxElevation = -Infinity;

  for (let i = 0; i < sampleCount; i++) {
    const t = sampleCount === 1 ? 0 : i / (sampleCount - 1);
    const pathX = ax + dx * t;
    const pathZ = az + dz * t;
    const cumulativeDistance = totalDistance * t;

    let elevation: number;
    if (elevationData && transform) {
      elevation = sampleElevationAt(elevationData, pathX, pathZ, originX, originZ, cellSize);
    } else if (elevationData) {
      elevation = sampleElevationAt(elevationData, pathX, pathZ, 0, 0, elevationData.cellSize);
    } else {
      elevation = 0;
    }

    let agl: number | undefined;
    if (aglData && transform) {
      agl = sampleElevationAt(aglData, pathX, pathZ, originX, originZ, cellSize);
    } else if (aglData) {
      agl = sampleElevationAt(aglData, pathX, pathZ, 0, 0, aglData.cellSize);
    }

    if (elevation < minElevation) minElevation = elevation;
    if (elevation > maxElevation) maxElevation = elevation;

    points.push({
      pathPosition: { x: pathX, z: pathZ },
      cumulativeDistance,
      elevation,
      agl,
    });
  }

  return {
    pointA,
    pointB,
    points,
    totalDistance,
    minElevation,
    maxElevation,
    sampleCount,
    units: "meters",
    source: "fixture-coordinate-system",
  };
}
