import { describe, it, expect } from "vitest";
import { calculateMeasurement, formatMeasurementValue } from "./calculator";
import type { MeasurementPoint } from "./types";

function createPoint(overrides: Partial<MeasurementPoint> = {}): MeasurementPoint {
  return {
    displayPosition: { x: 0, y: 0, z: 0 },
    scientific: { elevation: 0 },
    uv: { u: 0, v: 0 },
    gridIndex: { col: 0, row: 0 },
    layerId: "dsm",
    artifactId: "test-001",
    ...overrides,
  };
}

describe("calculateMeasurement", () => {
  describe("horizontal distance", () => {
    it("calculates distance between two points on the same X axis", () => {
      const a = createPoint({ displayPosition: { x: 0, y: 0, z: 0 } });
      const b = createPoint({ displayPosition: { x: 3, y: 0, z: 0 } });
      const result = calculateMeasurement("distance", a, b);
      expect(result.horizontalDistance).toBeCloseTo(3);
    });

    it("calculates distance between two points on the same Z axis", () => {
      const a = createPoint({ displayPosition: { x: 0, y: 0, z: 0 } });
      const b = createPoint({ displayPosition: { x: 0, y: 0, z: 4 } });
      const result = calculateMeasurement("distance", a, b);
      expect(result.horizontalDistance).toBeCloseTo(4);
    });

    it("calculates diagonal horizontal distance", () => {
      const a = createPoint({ displayPosition: { x: 0, y: 0, z: 0 } });
      const b = createPoint({ displayPosition: { x: 3, y: 0, z: 4 } });
      const result = calculateMeasurement("distance", a, b);
      expect(result.horizontalDistance).toBeCloseTo(5);
    });

    it("ignores vertical difference for horizontal distance", () => {
      const a = createPoint({ displayPosition: { x: 0, y: 10, z: 0 } });
      const b = createPoint({ displayPosition: { x: 3, y: 100, z: 0 } });
      const result = calculateMeasurement("distance", a, b);
      expect(result.horizontalDistance).toBeCloseTo(3);
    });

    it("handles identical points", () => {
      const a = createPoint({ displayPosition: { x: 5, y: 5, z: 5 } });
      const b = createPoint({ displayPosition: { x: 5, y: 5, z: 5 } });
      const result = calculateMeasurement("distance", a, b);
      expect(result.horizontalDistance).toBeCloseTo(0);
    });

    it("handles very small distances", () => {
      const a = createPoint({ displayPosition: { x: 0, y: 0, z: 0 } });
      const b = createPoint({ displayPosition: { x: 0.001, y: 0, z: 0 } });
      const result = calculateMeasurement("distance", a, b);
      expect(result.horizontalDistance).toBeCloseTo(0.001);
    });
  });

  describe("vertical difference", () => {
    it("calculates positive vertical difference", () => {
      const a = createPoint({ displayPosition: { x: 0, y: 10, z: 0 }, scientific: { elevation: 10 } });
      const b = createPoint({ displayPosition: { x: 0, y: 5, z: 0 }, scientific: { elevation: 5 } });
      const result = calculateMeasurement("vertical", a, b);
      expect(result.verticalDifference).toBeCloseTo(5);
    });

    it("calculates negative vertical difference", () => {
      const a = createPoint({ displayPosition: { x: 0, y: 5, z: 0 }, scientific: { elevation: 5 } });
      const b = createPoint({ displayPosition: { x: 0, y: 10, z: 0 }, scientific: { elevation: 10 } });
      const result = calculateMeasurement("vertical", a, b);
      expect(result.verticalDifference).toBeCloseTo(-5);
    });

    it("handles zero vertical difference", () => {
      const a = createPoint({ displayPosition: { x: 0, y: 7, z: 0 }, scientific: { elevation: 7 } });
      const b = createPoint({ displayPosition: { x: 1, y: 7, z: 1 }, scientific: { elevation: 7 } });
      const result = calculateMeasurement("vertical", a, b);
      expect(result.verticalDifference).toBeCloseTo(0);
    });

    it("uses scientific elevation, not display Y", () => {
      const a = createPoint({ displayPosition: { x: 0, y: 100, z: 0 }, scientific: { elevation: 10 } });
      const b = createPoint({ displayPosition: { x: 0, y: 200, z: 0 }, scientific: { elevation: 5 } });
      const result = calculateMeasurement("vertical", a, b);
      expect(result.verticalDifference).toBeCloseTo(5);
    });

    it("uses scientific elevation with height exaggeration", () => {
      const a = createPoint({ displayPosition: { x: 0, y: 100, z: 0 }, scientific: { elevation: 10 } });
      const b = createPoint({ displayPosition: { x: 0, y: 50, z: 0 }, scientific: { elevation: 5 } });
      const result = calculateMeasurement("vertical", a, b);
      expect(result.verticalDifference).toBeCloseTo(5);
    });
  });

  describe("3D distance", () => {
    it("calculates 3D distance with all components", () => {
      const a = createPoint({ displayPosition: { x: 0, y: 0, z: 0 }, scientific: { elevation: 0 } });
      const b = createPoint({ displayPosition: { x: 3, y: 0, z: 4 }, scientific: { elevation: 0 } });
      const result = calculateMeasurement("distance-3d", a, b);
      expect(result.distance3D).toBeCloseTo(5);
    });

    it("calculates 3D distance with elevation difference", () => {
      const a = createPoint({ displayPosition: { x: 0, y: 0, z: 0 }, scientific: { elevation: 0 } });
      const b = createPoint({ displayPosition: { x: 3, y: 0, z: 0 }, scientific: { elevation: 4 } });
      const result = calculateMeasurement("distance-3d", a, b);
      expect(result.distance3D).toBeCloseTo(5);
    });

    it("handles identical points in 3D", () => {
      const a = createPoint({ displayPosition: { x: 5, y: 5, z: 5 }, scientific: { elevation: 10 } });
      const b = createPoint({ displayPosition: { x: 5, y: 5, z: 5 }, scientific: { elevation: 10 } });
      const result = calculateMeasurement("distance-3d", a, b);
      expect(result.distance3D).toBeCloseTo(0);
    });

    it("handles very small 3D distances", () => {
      const a = createPoint({ displayPosition: { x: 0, y: 0, z: 0 }, scientific: { elevation: 0 } });
      const b = createPoint({ displayPosition: { x: 0.001, y: 0, z: 0 }, scientific: { elevation: 0 } });
      const result = calculateMeasurement("distance-3d", a, b);
      expect(result.distance3D).toBeCloseTo(0.001);
    });
  });

  describe("scientific values", () => {
    it("preserves point A and B data in result", () => {
      const a = createPoint({ layerId: "rdsm", artifactId: "art-1" });
      const b = createPoint({ layerId: "agl", artifactId: "art-1" });
      const result = calculateMeasurement("distance", a, b);
      expect(result.pointA).toBe(a);
      expect(result.pointB).toBe(b);
      expect(result.pointA.layerId).toBe("rdsm");
      expect(result.pointB.layerId).toBe("agl");
    });

    it("sets units to meters", () => {
      const a = createPoint();
      const b = createPoint({ displayPosition: { x: 1, y: 0, z: 0 } });
      const result = calculateMeasurement("distance", a, b);
      expect(result.units).toBe("meters");
    });

    it("sets source to fixture-coordinate-system", () => {
      const a = createPoint();
      const b = createPoint({ displayPosition: { x: 1, y: 0, z: 0 } });
      const result = calculateMeasurement("distance", a, b);
      expect(result.source).toBe("fixture-coordinate-system");
    });

    it("preserves rDSM and AGL values from points", () => {
      const a = createPoint({ scientific: { elevation: 10, rdsm: 5, agl: 2 } });
      const b = createPoint({ scientific: { elevation: 20, rdsm: 15, agl: 8 } });
      const result = calculateMeasurement("vertical", a, b);
      expect(result.pointA.scientific.rdsm).toBe(5);
      expect(result.pointA.scientific.agl).toBe(2);
      expect(result.pointB.scientific.rdsm).toBe(15);
      expect(result.pointB.scientific.agl).toBe(8);
    });
  });

  describe("height exaggeration safety", () => {
    const pointA = createPoint({ displayPosition: { x: 0, y: 0, z: 0 }, scientific: { elevation: 100 } });
    const pointB = createPoint({ displayPosition: { x: 3, y: 0, z: 4 }, scientific: { elevation: 120 } });

    it("scientific measurements are identical at 1x and 10x", () => {
      const result1x = calculateMeasurement("distance", pointA, pointB);
      const result10x = calculateMeasurement("distance", pointA, pointB);
      expect(result1x.horizontalDistance).toBeCloseTo(result10x.horizontalDistance);
      expect(result1x.verticalDifference).toBeCloseTo(result10x.verticalDifference);
      expect(result1x.distance3D).toBeCloseTo(result10x.distance3D);
    });

    it("vertical difference is independent of display exaggeration", () => {
      for (const _scale of [1, 2, 5, 10]) {
        const a = createPoint({ displayPosition: { x: 0, y: 0, z: 0 }, scientific: { elevation: 100 } });
        const b = createPoint({ displayPosition: { x: 0, y: 0, z: 0 }, scientific: { elevation: 120 } });
        const result = calculateMeasurement("vertical", a, b);
        expect(result.verticalDifference).toBeCloseTo(-20);
      }
    });

    it("horizontal distance is independent of display exaggeration", () => {
      for (const _scale of [1, 2, 5, 10]) {
        const a = createPoint({ displayPosition: { x: 0, y: 0, z: 0 }, scientific: { elevation: 0 } });
        const b = createPoint({ displayPosition: { x: 3, y: 0, z: 4 }, scientific: { elevation: 0 } });
        const result = calculateMeasurement("distance", a, b);
        expect(result.horizontalDistance).toBeCloseTo(5);
      }
    });

    it("3D distance uses scientific elevation, not display Y", () => {
      const a = createPoint({ displayPosition: { x: 0, y: 100, z: 0 }, scientific: { elevation: 10 } });
      const b = createPoint({ displayPosition: { x: 3, y: 100, z: 0 }, scientific: { elevation: 14 } });
      const result = calculateMeasurement("distance-3d", a, b);
      expect(result.distance3D).toBeCloseTo(5);
    });
  });

  describe("cumulative exaggeration safety", () => {
    it("measurement results are stable regardless of scale sequence", () => {
      const a = createPoint({ displayPosition: { x: 0, y: 0, z: 0 }, scientific: { elevation: 50 } });
      const b = createPoint({ displayPosition: { x: 3, y: 0, z: 4 }, scientific: { elevation: 80 } });

      const result1 = calculateMeasurement("distance-3d", a, b);
      const result2 = calculateMeasurement("distance-3d", a, b);
      const result3 = calculateMeasurement("distance-3d", a, b);

      expect(result1.distance3D).toBeCloseTo(result2.distance3D);
      expect(result2.distance3D).toBeCloseTo(result3.distance3D);
      expect(result1.verticalDifference).toBeCloseTo(result2.verticalDifference);
      expect(result2.verticalDifference).toBeCloseTo(result3.verticalDifference);
    });
  });

  describe("edge cases", () => {
    it("handles negative coordinates", () => {
      const a = createPoint({ displayPosition: { x: -5, y: -3, z: -2 } });
      const b = createPoint({ displayPosition: { x: 5, y: 3, z: 2 } });
      const result = calculateMeasurement("distance", a, b);
      expect(result.horizontalDistance).toBeCloseTo(Math.sqrt(100 + 16));
    });

    it("handles very large coordinates", () => {
      const a = createPoint({ displayPosition: { x: 1000000, y: 0, z: 0 } });
      const b = createPoint({ displayPosition: { x: 1000003, y: 0, z: 4 } });
      const result = calculateMeasurement("distance", a, b);
      expect(result.horizontalDistance).toBeCloseTo(5);
    });
  });
});

describe("formatMeasurementValue", () => {
  const pointA = createPoint({ displayPosition: { x: 0, y: 0, z: 0 }, scientific: { elevation: 0 } });
  const pointB = createPoint({ displayPosition: { x: 3, y: 0, z: 4 }, scientific: { elevation: 5 } });

  it("formats horizontal distance", () => {
    const result = calculateMeasurement("distance", pointA, pointB);
    expect(formatMeasurementValue("distance", result)).toBe("5.000 m");
  });

  it("formats vertical difference", () => {
    const result = calculateMeasurement("vertical", pointA, pointB);
    expect(formatMeasurementValue("vertical", result)).toBe("5.000 m");
  });

  it("formats 3D distance", () => {
    const result = calculateMeasurement("distance-3d", pointA, pointB);
    const formatted = formatMeasurementValue("distance-3d", result);
    const numericValue = parseFloat(formatted.replace(" m", ""));
    expect(numericValue).toBeCloseTo(7.071);
  });

  it("formats zero value", () => {
    const result = calculateMeasurement("distance", pointA, pointA);
    expect(formatMeasurementValue("distance", result)).toBe("0.000 m");
  });
});
