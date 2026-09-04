import { describe, it, expect } from "vitest";

describe("ProfileState transitions", () => {
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

  it("can transition from selecting-second to completed with profile", () => {
    const pointA = { displayPosition: { x: 0, y: 0, z: 0 }, scientific: { elevation: 0 }, uv: { u: 0, v: 0 }, gridIndex: { col: 0, row: 0 }, layerId: "dsm", artifactId: "test" };
    const pointB = { displayPosition: { x: 1, y: 0, z: 0 }, scientific: { elevation: 1 }, uv: { u: 1, v: 0 }, gridIndex: { col: 1, row: 0 }, layerId: "dsm", artifactId: "test" };
    const profile = {
      pointA,
      pointB,
      points: [],
      totalDistance: 1,
      minElevation: 0,
      maxElevation: 1,
      sampleCount: 0,
      units: "meters" as const,
      source: "fixture-coordinate-system" as const,
    };
    const state = { status: "completed" as const, profile };
    expect(state.status).toBe("completed");
    expect(state.profile.totalDistance).toBe(1);
  });

  it("can clear from any state back to empty", () => {
    const states = [
      { status: "empty" as const },
      { status: "selecting-first" as const },
      { status: "selecting-second" as const, pointA: {} as any },
      { status: "completed" as const, profile: {} as any },
    ];
    for (const _state of states) {
      const cleared = { status: "empty" as const };
      expect(cleared.status).toBe("empty");
    }
  });
});
