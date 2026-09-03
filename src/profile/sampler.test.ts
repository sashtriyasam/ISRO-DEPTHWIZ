import { describe, it, expect } from "vitest";
import { generateProfile } from "./sampler";
import type { MeasurementPoint } from "../measurement/types";
import type { ElevationData } from "../types/scene";

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

function createTestElevation(): ElevationData {
  const grid = new Float32Array([
    0, 1, 2, 3,
    1, 2, 3, 4,
    2, 3, 4, 5,
    3, 4, 5, 6,
  ]);
  return {
    grid,
    width: 4,
    height: 4,
    cellSize: 1,
    unit: "meters",
  };
}

describe("generateProfile", () => {
  const elevation = createTestElevation();

  it("generates profile with default sample count", () => {
    const a = createPoint({ displayPosition: { x: 0, y: 0, z: 0 } });
    const b = createPoint({ displayPosition: { x: 3, y: 0, z: 0 } });
    const profile = generateProfile(a, b, elevation, undefined, undefined);
    expect(profile.points.length).toBe(64);
    expect(profile.sampleCount).toBe(64);
  });

  it("generates profile with custom sample count", () => {
    const a = createPoint({ displayPosition: { x: 0, y: 0, z: 0 } });
    const b = createPoint({ displayPosition: { x: 3, y: 0, z: 0 } });
    const profile = generateProfile(a, b, elevation, undefined, undefined, { sampleCount: 5 });
    expect(profile.points.length).toBe(5);
    expect(profile.sampleCount).toBe(5);
  });

  it("calculates cumulative distance correctly", () => {
    const a = createPoint({ displayPosition: { x: 0, y: 0, z: 0 } });
    const b = createPoint({ displayPosition: { x: 3, y: 0, z: 4 } });
    const profile = generateProfile(a, b, elevation, undefined, undefined, { sampleCount: 6 });
    expect(profile.totalDistance).toBeCloseTo(5);
    expect(profile.points[0].cumulativeDistance).toBeCloseTo(0);
    expect(profile.points[5].cumulativeDistance).toBeCloseTo(5);
  });

  it("samples elevation along the path", () => {
    const a = createPoint({ displayPosition: { x: 0, y: 0, z: 0 } });
    const b = createPoint({ displayPosition: { x: 3, y: 0, z: 0 } });
    const profile = generateProfile(a, b, elevation, undefined, undefined, { sampleCount: 4 });
    expect(profile.points.length).toBe(4);
    expect(profile.points[0].elevation).toBeDefined();
    expect(profile.points[3].elevation).toBeDefined();
  });

  it("first point has zero cumulative distance", () => {
    const a = createPoint({ displayPosition: { x: 1, y: 0, z: 2 } });
    const b = createPoint({ displayPosition: { x: 5, y: 0, z: 6 } });
    const profile = generateProfile(a, b, elevation, undefined, undefined, { sampleCount: 10 });
    expect(profile.points[0].cumulativeDistance).toBeCloseTo(0);
  });

  it("last point has total distance", () => {
    const a = createPoint({ displayPosition: { x: 0, y: 0, z: 0 } });
    const b = createPoint({ displayPosition: { x: 3, y: 0, z: 4 } });
    const profile = generateProfile(a, b, elevation, undefined, undefined, { sampleCount: 10 });
    expect(profile.points[9].cumulativeDistance).toBeCloseTo(5);
  });

  it("records min and max elevation", () => {
    const a = createPoint({ displayPosition: { x: 0, y: 0, z: 0 } });
    const b = createPoint({ displayPosition: { x: 3, y: 0, z: 0 } });
    const profile = generateProfile(a, b, elevation, undefined, undefined, { sampleCount: 4 });
    expect(profile.minElevation).toBeLessThanOrEqual(profile.maxElevation);
    for (const p of profile.points) {
      expect(p.elevation).toBeGreaterThanOrEqual(profile.minElevation);
      expect(p.elevation).toBeLessThanOrEqual(profile.maxElevation);
    }
  });

  it("sets units to meters", () => {
    const a = createPoint({ displayPosition: { x: 0, y: 0, z: 0 } });
    const b = createPoint({ displayPosition: { x: 1, y: 0, z: 0 } });
    const profile = generateProfile(a, b, elevation, undefined, undefined, { sampleCount: 2 });
    expect(profile.units).toBe("meters");
  });

  it("sets source to fixture-coordinate-system", () => {
    const a = createPoint({ displayPosition: { x: 0, y: 0, z: 0 } });
    const b = createPoint({ displayPosition: { x: 1, y: 0, z: 0 } });
    const profile = generateProfile(a, b, elevation, undefined, undefined, { sampleCount: 2 });
    expect(profile.source).toBe("fixture-coordinate-system");
  });

  it("preserves pointA and pointB", () => {
    const a = createPoint({ displayPosition: { x: 0, y: 0, z: 0 }, artifactId: "art-1" });
    const b = createPoint({ displayPosition: { x: 1, y: 0, z: 0 }, artifactId: "art-1" });
    const profile = generateProfile(a, b, elevation, undefined, undefined, { sampleCount: 2 });
    expect(profile.pointA).toBe(a);
    expect(profile.pointB).toBe(b);
  });

  it("handles identical A/B points", () => {
    const a = createPoint({ displayPosition: { x: 5, y: 0, z: 5 } });
    const profile = generateProfile(a, a, elevation, undefined, undefined, { sampleCount: 5 });
    expect(profile.totalDistance).toBeCloseTo(0);
    expect(profile.points.length).toBe(5);
    for (const p of profile.points) {
      expect(p.cumulativeDistance).toBeCloseTo(0);
    }
  });

  it("handles reverse direction (B to A)", () => {
    const a = createPoint({ displayPosition: { x: 3, y: 0, z: 0 } });
    const b = createPoint({ displayPosition: { x: 0, y: 0, z: 0 } });
    const profile = generateProfile(a, b, elevation, undefined, undefined, { sampleCount: 4 });
    expect(profile.totalDistance).toBeCloseTo(3);
    expect(profile.points[0].cumulativeDistance).toBeCloseTo(0);
    expect(profile.points[3].cumulativeDistance).toBeCloseTo(3);
  });

  it("handles very short path", () => {
    const a = createPoint({ displayPosition: { x: 0, y: 0, z: 0 } });
    const b = createPoint({ displayPosition: { x: 0.001, y: 0, z: 0 } });
    const profile = generateProfile(a, b, elevation, undefined, undefined, { sampleCount: 3 });
    expect(profile.totalDistance).toBeCloseTo(0.001);
    expect(profile.points.length).toBe(3);
  });

  it("handles single sample", () => {
    const a = createPoint({ displayPosition: { x: 0, y: 0, z: 0 } });
    const b = createPoint({ displayPosition: { x: 3, y: 0, z: 0 } });
    const profile = generateProfile(a, b, elevation, undefined, undefined, { sampleCount: 1 });
    expect(profile.points.length).toBe(1);
    expect(profile.points[0].cumulativeDistance).toBeCloseTo(0);
  });

  it("does not mutate artifact elevation data", () => {
    const originalGrid = new Float32Array(elevation.grid);
    const a = createPoint({ displayPosition: { x: 0, y: 0, z: 0 } });
    const b = createPoint({ displayPosition: { x: 3, y: 0, z: 0 } });
    generateProfile(a, b, elevation, undefined, undefined, { sampleCount: 10 });
    for (let i = 0; i < elevation.grid.length; i++) {
      expect(elevation.grid[i]).toBeCloseTo(originalGrid[i]);
    }
  });

  it("profile invariance across exaggeration levels", () => {
    const a = createPoint({ displayPosition: { x: 0, y: 0, z: 0 } });
    const b = createPoint({ displayPosition: { x: 3, y: 0, z: 0 } });

    const profile1 = generateProfile(a, b, elevation, undefined, undefined, { sampleCount: 10 });
    const profile2 = generateProfile(a, b, elevation, undefined, undefined, { sampleCount: 10 });
    const profile5 = generateProfile(a, b, elevation, undefined, undefined, { sampleCount: 10 });
    const profile10 = generateProfile(a, b, elevation, undefined, undefined, { sampleCount: 10 });

    for (let i = 0; i < 10; i++) {
      expect(profile1.points[i].elevation).toBeCloseTo(profile2.points[i].elevation);
      expect(profile2.points[i].elevation).toBeCloseTo(profile5.points[i].elevation);
      expect(profile5.points[i].elevation).toBeCloseTo(profile10.points[i].elevation);
    }
    expect(profile1.totalDistance).toBeCloseTo(profile10.totalDistance);
    expect(profile1.minElevation).toBeCloseTo(profile10.minElevation);
    expect(profile1.maxElevation).toBeCloseTo(profile10.maxElevation);
  });

  it("path length consistency with horizontal distance", () => {
    const a = createPoint({ displayPosition: { x: 0, y: 0, z: 0 } });
    const b = createPoint({ displayPosition: { x: 3, y: 0, z: 4 } });
    const profile = generateProfile(a, b, elevation, undefined, undefined, { sampleCount: 2 });
    expect(profile.totalDistance).toBeCloseTo(5);
  });

  it("handles negative coordinates", () => {
    const a = createPoint({ displayPosition: { x: -5, y: 0, z: -3 } });
    const b = createPoint({ displayPosition: { x: 5, y: 0, z: 3 } });
    const profile = generateProfile(a, b, elevation, undefined, undefined, { sampleCount: 3 });
    expect(profile.totalDistance).toBeCloseTo(Math.sqrt(100 + 36));
    expect(profile.points.length).toBe(3);
  });

  it("handles path outside grid bounds gracefully", () => {
    const a = createPoint({ displayPosition: { x: -10, y: 0, z: -10 } });
    const b = createPoint({ displayPosition: { x: 10, y: 0, z: 10 } });
    const profile = generateProfile(a, b, elevation, undefined, undefined, { sampleCount: 3 });
    expect(profile.points.length).toBe(3);
    for (const p of profile.points) {
      expect(typeof p.elevation).toBe("number");
      expect(Number.isFinite(p.elevation)).toBe(true);
    }
  });

  it("handles no elevation data", () => {
    const a = createPoint({ displayPosition: { x: 0, y: 0, z: 0 } });
    const b = createPoint({ displayPosition: { x: 3, y: 0, z: 0 } });
    const profile = generateProfile(a, b, undefined, undefined, undefined, { sampleCount: 4 });
    expect(profile.points.length).toBe(4);
    for (const p of profile.points) {
      expect(p.elevation).toBe(0);
    }
  });

  it("samples AGL when available", () => {
    const agl: ElevationData = {
      grid: new Float32Array([0.1, 0.2, 0.3, 0.4]),
      width: 2,
      height: 2,
      cellSize: 1,
      unit: "meters",
    };
    const a = createPoint({ displayPosition: { x: 0, y: 0, z: 0 } });
    const b = createPoint({ displayPosition: { x: 1, y: 0, z: 0 } });
    const profile = generateProfile(a, b, elevation, agl, undefined, { sampleCount: 3 });
    expect(profile.points.length).toBe(3);
    for (const p of profile.points) {
      expect(p.agl).toBeDefined();
      expect(typeof p.agl).toBe("number");
    }
  });

  it("omits AGL when not available", () => {
    const a = createPoint({ displayPosition: { x: 0, y: 0, z: 0 } });
    const b = createPoint({ displayPosition: { x: 1, y: 0, z: 0 } });
    const profile = generateProfile(a, b, elevation, undefined, undefined, { sampleCount: 3 });
    for (const p of profile.points) {
      expect(p.agl).toBeUndefined();
    }
  });
});
