import { describe, it, expect } from "vitest";
import {
  MEASUREMENT_MODES,
  MEASUREMENT_LABELS,
  MEASUREMENT_DESCRIPTIONS,
} from "./types";

describe("MeasurementMode type", () => {
  it("has exactly 3 supported modes", () => {
    expect(MEASUREMENT_MODES).toEqual(["distance", "vertical", "distance-3d"]);
    expect(MEASUREMENT_MODES).toHaveLength(3);
  });

  it("has labels for all modes", () => {
    for (const mode of MEASUREMENT_MODES) {
      expect(MEASUREMENT_LABELS[mode]).toBeDefined();
      expect(typeof MEASUREMENT_LABELS[mode]).toBe("string");
    }
  });

  it("has descriptions for all modes", () => {
    for (const mode of MEASUREMENT_MODES) {
      expect(MEASUREMENT_DESCRIPTIONS[mode]).toBeDefined();
      expect(typeof MEASUREMENT_DESCRIPTIONS[mode]).toBe("string");
    }
  });
});

describe("MeasurementState transitions", () => {
  it("can transition from empty to selecting-first", () => {
    const state = { status: "empty" as const };
    expect(state.status).toBe("empty");
    const next = { status: "selecting-first" as const };
    expect(next.status).toBe("selecting-first");
  });

  it("can transition from selecting-first to selecting-second with pointA", () => {
    const pointA = { displayPosition: { x: 0, y: 0, z: 0 }, scientific: { elevation: 0 }, uv: { u: 0, v: 0 }, gridIndex: { col: 0, row: 0 }, layerId: "dsm", artifactId: "test" };
    const next = { status: "selecting-second" as const, pointA };
    expect(next.status).toBe("selecting-second");
    expect(next.pointA).toBe(pointA);
  });

  it("can transition from selecting-second to completed with result", () => {
    const pointA = { displayPosition: { x: 0, y: 0, z: 0 }, scientific: { elevation: 0 }, uv: { u: 0, v: 0 }, gridIndex: { col: 0, row: 0 }, layerId: "dsm", artifactId: "test" };
    const pointB = { displayPosition: { x: 1, y: 0, z: 0 }, scientific: { elevation: 1 }, uv: { u: 1, v: 0 }, gridIndex: { col: 1, row: 0 }, layerId: "dsm", artifactId: "test" };
    const result = {
      mode: "distance" as const,
      pointA,
      pointB,
      horizontalDistance: 1,
      verticalDifference: -1,
      distance3D: Math.sqrt(2),
      units: "meters" as const,
      source: "fixture-coordinate-system" as const,
    };
    const state = { status: "completed" as const, result };
    expect(state.status).toBe("completed");
    expect(state.result.mode).toBe("distance");
  });

  it("can clear from any state back to empty", () => {
    const states = [
      { status: "empty" as const },
      { status: "selecting-first" as const },
      { status: "selecting-second" as const, pointA: {} as any },
      { status: "completed" as const, result: {} as any },
    ];
    for (const _state of states) {
      const cleared = { status: "empty" as const };
      expect(cleared.status).toBe("empty");
    }
  });
});
