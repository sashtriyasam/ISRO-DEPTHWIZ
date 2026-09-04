export interface InspectionResult {
  position: {
    x: number;
    y: number;
    z: number;
  };
  uv: {
    u: number;
    v: number;
  };
  gridIndex: {
    col: number;
    row: number;
  };
  scientific: {
    elevation: number;
    rdsm?: number;
    agl?: number;
  };
  layerId: string;
  artifactId: string;
}

export type InspectionState =
  | { status: "empty" }
  | { status: "selected"; result: InspectionResult };
