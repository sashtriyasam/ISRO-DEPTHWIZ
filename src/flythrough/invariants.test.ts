import { describe, it, expect } from "vitest";
import { createDeterministicFixture } from "../fixtures/deterministicFixture";
import { calculateMeasurement } from "../measurement/calculator";
import type { MeasurementPoint } from "../measurement/types";
import { evaluateTrajectory } from "./trajectory";
import { DEFAULT_SEGMENT_DURATION_MS, type FlythroughTrajectory } from "./types";

function trajectory(): FlythroughTrajectory {
  return {
    id: "traj-1",
    waypoints: [
      { id: "wp-1", position: { x: 0, y: 4, z: 7 }, target: { x: 0, y: 0, z: 0 } },
      { id: "wp-2", position: { x: 4, y: 4, z: 7 }, target: { x: 0, y: 0, z: 0 } },
    ],
    segmentDurationMs: DEFAULT_SEGMENT_DURATION_MS,
  };
}

function measurementPoint(): MeasurementPoint {
  return {
    displayPosition: { x: 0, y: 0.5, z: 0 },
    scientific: { elevation: 0.5 },
    uv: { u: 0.5, v: 0.5 },
    gridIndex: { col: 4, row: 4 },
    layerId: "dsm",
    artifactId: "dev-fixture-001",
  };
}

describe("display-space invariants", () => {
  it("stores no scientific claims on waypoints", () => {
    const traj = trajectory();
    for (const waypoint of traj.waypoints) {
      const keys = new Set([...Object.keys(waypoint), ...Object.keys(waypoint.position)]);
      for (const forbidden of ["elevation", "altitude", "latitude", "longitude", "crs", "agl", "dsm"]) {
        expect(keys.has(forbidden)).toBe(false);
      }
    }
  });

  it("never modifies artifact grids or meshes during evaluation", () => {
    const artifact = createDeterministicFixture();
    const gridBefore = Array.from(artifact.elevation!.grid);
    const verticesBefore = Array.from(artifact.mesh.vertices);
    const traj = trajectory();
    for (let t = 0; t <= DEFAULT_SEGMENT_DURATION_MS; t += 100) {
      evaluateTrajectory(traj, t);
    }
    expect(Array.from(artifact.elevation!.grid)).toEqual(gridBefore);
    expect(Array.from(artifact.mesh.vertices)).toEqual(verticesBefore);
  });

  it("never modifies measurement inputs or results", () => {
    const a = measurementPoint();
    const b: MeasurementPoint = { ...measurementPoint(), displayPosition: { x: 1, y: 0.6, z: 0 } };
    const before = calculateMeasurement("distance", a, b);
    const traj = trajectory();
    for (let t = 0; t <= DEFAULT_SEGMENT_DURATION_MS; t += 500) {
      evaluateTrajectory(traj, t);
    }
    const after = calculateMeasurement("distance", a, b);
    expect(after).toEqual(before);
    expect(a.scientific.elevation).toBe(0.5);
  });

  it("handles degenerate zero-length segments without NaN", () => {
    const degenerate: FlythroughTrajectory = {
      id: "traj-degenerate",
      waypoints: [
        { id: "wp-1", position: { x: 1, y: 2, z: 3 }, target: { x: 1, y: 2, z: 3 } },
        { id: "wp-2", position: { x: 1, y: 2, z: 3 }, target: { x: 1, y: 2, z: 3 } },
      ],
      segmentDurationMs: DEFAULT_SEGMENT_DURATION_MS,
    };
    const mid = evaluateTrajectory(degenerate, DEFAULT_SEGMENT_DURATION_MS / 2)!;
    expect(Number.isFinite(mid.position.x)).toBe(true);
    expect(Number.isFinite(mid.quaternion.x)).toBe(true);
    expect(mid.quaternion.length()).toBeCloseTo(1);
  });

  it("handles duplicate consecutive waypoint positions", () => {
    const duplicates: FlythroughTrajectory = {
      id: "traj-duplicates",
      waypoints: [
        { id: "wp-1", position: { x: 0, y: 4, z: 7 }, target: { x: 0, y: 0, z: 0 } },
        { id: "wp-2", position: { x: 0, y: 4, z: 7 }, target: { x: 0, y: 0, z: 0 } },
        { id: "wp-3", position: { x: 4, y: 4, z: 7 }, target: { x: 0, y: 0, z: 0 } },
      ],
      segmentDurationMs: DEFAULT_SEGMENT_DURATION_MS,
    };
    const first = evaluateTrajectory(duplicates, DEFAULT_SEGMENT_DURATION_MS / 2)!;
    expect(first.position.x).toBeCloseTo(0);
    const end = evaluateTrajectory(duplicates, DEFAULT_SEGMENT_DURATION_MS * 2)!;
    expect(end.position.x).toBeCloseTo(4);
  });
});
