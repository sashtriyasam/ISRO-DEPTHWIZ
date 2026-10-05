export type MeasurementMode = "distance" | "vertical" | "distance-3d";

export const MEASUREMENT_MODES: MeasurementMode[] = ["distance", "vertical", "distance-3d"];

export const MEASUREMENT_LABELS: Record<MeasurementMode, string> = {
  distance: "Distance",
  vertical: "Vertical",
  "distance-3d": "3D Distance",
};

export const MEASUREMENT_DESCRIPTIONS: Record<MeasurementMode, string> = {
  distance: "Horizontal point-to-point distance",
  vertical: "Vertical elevation difference",
  "distance-3d": "3D Euclidean distance",
};

export interface MeasurementPoint {
  displayPosition: { x: number; y: number; z: number };
  scientific: {
    elevation: number;
    rdsm?: number;
    agl?: number;
  };
  uv: { u: number; v: number };
  gridIndex: { col: number; row: number };
  layerId: string;
  artifactId: string;
}

export interface MeasurementResult {
  mode: MeasurementMode;
  pointA: MeasurementPoint;
  pointB: MeasurementPoint;
  horizontalDistance: number;
  verticalDifference: number;
  /** NaN when horizontal and vertical units differ (no meaningful 3D length). */
  distance3D: number;
  /** Vertical (elevation) units. */
  units: "meters" | "relative" | string;
  /** Horizontal units of the display frame (metres or pixel indices). */
  horizontalUnits: "meters" | "pixels" | string;
  source: "fixture-coordinate-system" | "backend";
}

export type MeasurementState =
  | { status: "empty" }
  | { status: "selecting-first" }
  | { status: "selecting-second"; pointA: MeasurementPoint }
  | { status: "completed"; result: MeasurementResult };
