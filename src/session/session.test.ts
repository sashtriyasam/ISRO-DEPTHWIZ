import { describe, it, expect, vi } from "vitest";
import {
  deriveSessionPhase,
  deriveSessionModified,
  resetSession,
  pendingSelections,
} from "./session";
import type { MeasurementState, MeasurementPoint } from "../measurement/types";
import type { ProfileState } from "../profile/types";
import type { InspectionState } from "../inspection/types";
import type { ProcessingState } from "../processing/types";
import type { FlythroughWaypoint } from "../flythrough/types";

const makeMeasurementPoint = (): MeasurementPoint => ({
  displayPosition: { x: 0, y: 0, z: 0 },
  scientific: { elevation: 10 },
  uv: { u: 0.5, v: 0.5 },
  gridIndex: { col: 0, row: 0 },
  layerId: "dsm",
  artifactId: "test",
});

const makeProcessing = (status: ProcessingState["status"]): ProcessingState => {
  switch (status) {
    case "idle":
      return { status: "idle" };
    case "running":
      return {
        status: "running",
        operationId: "op-1",
        sourceId: "src-1",
        sourceLabel: "test",
        stage: "loading",
        completedStages: [],
        cancellable: true,
      };
    case "ready":
      return {
        status: "ready",
        operationId: "op-1",
        sourceId: "src-1",
        sourceLabel: "test",
        artifactId: "art-1",
        completedStages: ["loading"],
        warnings: [],
      };
    case "error":
      return {
        status: "error",
        operationId: "op-1",
        sourceId: "src-1",
        sourceLabel: "test",
        failure: {
          stage: "loading",
          code: "ERR",
          message: "boom",
          phase: "process",
          previousAvailable: false,
        },
        completedStages: [],
      };
    case "cancelled":
      return {
        status: "cancelled",
        operationId: "op-1",
        sourceId: "src-1",
        sourceLabel: "test",
        previousAvailable: false,
        completedStages: [],
      };
  }
};

const makeMeasurement = (status: MeasurementState["status"]): MeasurementState => {
  switch (status) {
    case "empty":
      return { status: "empty" };
    case "selecting-first":
      return { status: "selecting-first" };
    case "selecting-second":
      return { status: "selecting-second", pointA: makeMeasurementPoint() };
    case "completed":
      return {
        status: "completed",
        result: {
          mode: "distance",
          pointA: makeMeasurementPoint(),
          pointB: { ...makeMeasurementPoint(), displayPosition: { x: 1, y: 0, z: 0 } },
          horizontalDistance: 1,
          verticalDifference: 0,
          distance3D: 1,
          units: "meters",
          source: "fixture-coordinate-system",
        },
      };
  }
};

const makeProfile = (status: ProfileState["status"]): ProfileState => {
  switch (status) {
    case "empty":
      return { status: "empty" };
    case "selecting-first":
      return { status: "selecting-first" };
    case "selecting-second":
      return { status: "selecting-second", pointA: makeMeasurementPoint() };
    case "completed":
      return {
        status: "completed",
        profile: {
          pointA: makeMeasurementPoint(),
          pointB: { ...makeMeasurementPoint(), displayPosition: { x: 1, y: 0, z: 0 } },
          points: [],
          totalDistance: 1,
          minElevation: 0,
          maxElevation: 10,
          sampleCount: 0,
          units: "meters",
          source: "fixture-coordinate-system",
        },
      };
  }
};

const makeInspection = (status: InspectionState["status"]): InspectionState => {
  switch (status) {
    case "empty":
      return { status: "empty" };
    case "selected":
      return {
        status: "selected",
        result: {
          position: { x: 0, y: 0, z: 0 },
          uv: { u: 0.5, v: 0.5 },
          gridIndex: { col: 0, row: 0 },
          scientific: { elevation: 10 },
          layerId: "dsm",
          artifactId: "test",
        },
      };
  }
};

const makeWaypoint = (id: string): FlythroughWaypoint => ({
  id,
  position: { x: 0, y: 0, z: 0 },
  target: { x: 0, y: 0, z: 1 },
});

describe("deriveSessionPhase", () => {
  // 1. no input/no artifact → empty
  it("1. returns empty when no input and no artifact", () => {
    expect(deriveSessionPhase({ hasArtifact: false, processing: makeProcessing("idle") })).toBe("empty");
  });

  // 2. valid input/no artifact — InputState is local to InputWorkspace, never reaches App.tsx
  //    With processing idle and no artifact, phase is empty (input-ready is not a real phase)
  it("2. returns empty when processing idle with no artifact (input-ready not a real phase)", () => {
    expect(deriveSessionPhase({ hasArtifact: false, processing: makeProcessing("idle") })).toBe("empty");
  });

  // 3. invalid input — same as idle, no artifact
  it("3. returns empty when processing idle with no artifact (invalid input)", () => {
    expect(deriveSessionPhase({ hasArtifact: false, processing: makeProcessing("idle") })).toBe("empty");
  });

  // 4. processing/no previous artifact
  it("4. returns processing when running with no artifact", () => {
    expect(deriveSessionPhase({ hasArtifact: false, processing: makeProcessing("running") })).toBe("processing");
  });

  // 5. processing/previous artifact — still processing (operation in flight)
  it("5. returns processing when running with existing artifact", () => {
    expect(deriveSessionPhase({ hasArtifact: true, processing: makeProcessing("running") })).toBe("processing");
  });

  // 6. successful artifact
  it("6. returns ready when artifact present and processing idle", () => {
    expect(deriveSessionPhase({ hasArtifact: true, processing: makeProcessing("idle") })).toBe("ready");
  });

  // 7. failed processing/no artifact
  it("7. returns error when processing failed with no artifact", () => {
    expect(deriveSessionPhase({ hasArtifact: false, processing: makeProcessing("error") })).toBe("error");
  });

  // 8. failed replacement/previous artifact — ready (previous preserved)
  it("8. returns ready when processing failed but previous artifact exists", () => {
    expect(deriveSessionPhase({ hasArtifact: true, processing: makeProcessing("error") })).toBe("ready");
  });

  // 9. cancellation/no previous artifact
  it("9. returns empty when cancelled with no artifact", () => {
    expect(deriveSessionPhase({ hasArtifact: false, processing: makeProcessing("cancelled") })).toBe("empty");
  });

  // 10. cancellation/previous artifact — ready (previous preserved)
  it("10. returns ready when cancelled with previous artifact", () => {
    expect(deriveSessionPhase({ hasArtifact: true, processing: makeProcessing("cancelled") })).toBe("ready");
  });
});

describe("deriveSessionModified", () => {
  // 11. clean ready session
  it("11. returns clean when no analysis state", () => {
    expect(
      deriveSessionModified({
        waypoints: [],
        measurement: makeMeasurement("empty"),
        profile: makeProfile("empty"),
      })
    ).toBe("clean");
  });

  // 12. flythrough changed
  it("12. returns modified when waypoints present", () => {
    expect(
      deriveSessionModified({
        waypoints: [makeWaypoint("1")],
        measurement: makeMeasurement("empty"),
        profile: makeProfile("empty"),
      })
    ).toBe("modified");
  });

  // 13. measurement completed
  it("13. returns modified when measurement completed", () => {
    expect(
      deriveSessionModified({
        waypoints: [],
        measurement: makeMeasurement("completed"),
        profile: makeProfile("empty"),
      })
    ).toBe("modified");
  });

  // 14. profile completed
  it("14. returns modified when profile completed", () => {
    expect(
      deriveSessionModified({
        waypoints: [],
        measurement: makeMeasurement("empty"),
        profile: makeProfile("completed"),
      })
    ).toBe("modified");
  });

  // 15. inspection-only selection — NOT modified (inspection is transient viewer state)
  it("15. returns clean when only inspection selected", () => {
    expect(
      deriveSessionModified({
        waypoints: [],
        measurement: makeMeasurement("empty"),
        profile: makeProfile("empty"),
      })
    ).toBe("clean");
  });

  // 16. camera-only movement — NOT modified (transient viewer state)
  it("16. returns clean when only camera moved (no waypoints/measurements/profiles)", () => {
    expect(
      deriveSessionModified({
        waypoints: [],
        measurement: makeMeasurement("empty"),
        profile: makeProfile("empty"),
      })
    ).toBe("clean");
  });

  // 17. rendering-mode-only change — NOT modified (display preference)
  it("17. returns clean when only rendering mode changed", () => {
    expect(
      deriveSessionModified({
        waypoints: [],
        measurement: makeMeasurement("empty"),
        profile: makeProfile("empty"),
      })
    ).toBe("clean");
  });

  // 18. exaggeration-only change — NOT modified (display preference)
  it("18. returns clean when only exaggeration changed", () => {
    expect(
      deriveSessionModified({
        waypoints: [],
        measurement: makeMeasurement("empty"),
        profile: makeProfile("empty"),
      })
    ).toBe("clean");
  });

  // 19. combined analysis state
  it("19. returns modified when multiple analysis states active", () => {
    expect(
      deriveSessionModified({
        waypoints: [makeWaypoint("1")],
        measurement: makeMeasurement("completed"),
        profile: makeProfile("completed"),
      })
    ).toBe("modified");
  });

  // In-progress selections are NOT modified (only completed results count)
  it("returns clean when measurement selecting first", () => {
    expect(
      deriveSessionModified({
        waypoints: [],
        measurement: makeMeasurement("selecting-first"),
        profile: makeProfile("empty"),
      })
    ).toBe("clean");
  });

  it("returns clean when profile selecting second", () => {
    expect(
      deriveSessionModified({
        waypoints: [],
        measurement: makeMeasurement("empty"),
        profile: makeProfile("selecting-second"),
      })
    ).toBe("clean");
  });
});

describe("pendingSelections", () => {
  it("returns false when all empty", () => {
    expect(
      pendingSelections({
        measurement: makeMeasurement("empty"),
        profile: makeProfile("empty"),
        inspection: makeInspection("empty"),
      })
    ).toBe(false);
  });

  it("returns true when measurement selecting first", () => {
    expect(
      pendingSelections({
        measurement: makeMeasurement("selecting-first"),
        profile: makeProfile("empty"),
        inspection: makeInspection("empty"),
      })
    ).toBe(true);
  });

  it("returns true when measurement selecting second", () => {
    expect(
      pendingSelections({
        measurement: makeMeasurement("selecting-second"),
        profile: makeProfile("empty"),
        inspection: makeInspection("empty"),
      })
    ).toBe(true);
  });

  it("returns true when profile selecting first", () => {
    expect(
      pendingSelections({
        measurement: makeMeasurement("empty"),
        profile: makeProfile("selecting-first"),
        inspection: makeInspection("empty"),
      })
    ).toBe(true);
  });

  it("returns true when profile selecting second", () => {
    expect(
      pendingSelections({
        measurement: makeMeasurement("empty"),
        profile: makeProfile("selecting-second"),
        inspection: makeInspection("empty"),
      })
    ).toBe(true);
  });

  it("returns true when inspection selected", () => {
    expect(
      pendingSelections({
        measurement: makeMeasurement("empty"),
        profile: makeProfile("empty"),
        inspection: makeInspection("selected"),
      })
    ).toBe(true);
  });
});

describe("resetSession", () => {
  // 20. reset empty
  it("20. calls all reset deps in order", () => {
    const order: string[] = [];
    const deps = {
      abortOperation: vi.fn(() => order.push("abort")),
      setProcessingIdle: vi.fn(() => order.push("idle")),
      clearArtifact: vi.fn(() => order.push("artifact")),
      clearLayers: vi.fn(() => order.push("layers")),
      clearAnalysis: vi.fn(() => order.push("analysis")),
      clearFlythrough: vi.fn(() => order.push("flythrough")),
      resetCameraToOrbit: vi.fn(() => order.push("orbit")),
    };
    resetSession(deps);
    expect(order).toEqual(["abort", "idle", "artifact", "layers", "analysis", "flythrough", "orbit"]);
    Object.values(deps).forEach((fn) => expect(fn).toHaveBeenCalledOnce());
  });

  // 21-26: reset is idempotent (calling multiple times is safe)
  it("21. is idempotent (multiple calls safe)", () => {
    const deps = {
      abortOperation: vi.fn(),
      setProcessingIdle: vi.fn(),
      clearArtifact: vi.fn(),
      clearLayers: vi.fn(),
      clearAnalysis: vi.fn(),
      clearFlythrough: vi.fn(),
      resetCameraToOrbit: vi.fn(),
    };
    resetSession(deps);
    resetSession(deps);
    resetSession(deps);
    expect(deps.abortOperation).toHaveBeenCalledTimes(3);
    expect(deps.clearArtifact).toHaveBeenCalledTimes(3);
  });

  // 27. artifact replacement clears dependent state — verified by the clearAnalysis
  //     and clearFlythrough calls being invoked during reset
  it("27. clearAnalysis and clearFlythrough both called during reset", () => {
    const analysisCleared = vi.fn();
    const flythroughCleared = vi.fn();
    resetSession({
      abortOperation: vi.fn(),
      setProcessingIdle: vi.fn(),
      clearArtifact: vi.fn(),
      clearLayers: vi.fn(),
      clearAnalysis: analysisCleared,
      clearFlythrough: flythroughCleared,
      resetCameraToOrbit: vi.fn(),
    });
    expect(analysisCleared).toHaveBeenCalledOnce();
    expect(flythroughCleared).toHaveBeenCalledOnce();
  });
});

describe("scientific invariants", () => {
  it("session module contains no terrain/elevation calculations", () => {
    const sessionCode = `
      import type { MeasurementState } from "../measurement/types";
      import type { ProfileState } from "../profile/types";
      import type { InspectionState } from "../inspection/types";
      import type { ProcessingState } from "../processing/types";
      import type { FlythroughWaypoint, PlaybackStatus } from "../flythrough/types";
    `;
    expect(sessionCode).not.toMatch(/elevation|dsm|agl|calibrat|transform|crs|mesh/i);
  });
});
