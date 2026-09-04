import type { MeasurementPoint } from "../measurement/types";

export interface ProfilePoint {
  pathPosition: { x: number; z: number };
  cumulativeDistance: number;
  elevation: number;
  agl?: number;
}

export interface ElevationProfile {
  pointA: MeasurementPoint;
  pointB: MeasurementPoint;
  points: ProfilePoint[];
  totalDistance: number;
  minElevation: number;
  maxElevation: number;
  sampleCount: number;
  units: "meters" | "relative" | string;
  source: "fixture-coordinate-system" | "backend";
  elevationSemantics?: string;
}

export type ProfileState =
  | { status: "empty" }
  | { status: "selecting-first" }
  | { status: "selecting-second"; pointA: MeasurementPoint }
  | { status: "completed"; profile: ElevationProfile };
