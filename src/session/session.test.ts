import { describe, it, expect, vi } from "vitest";
import {
  deriveSessionPhase,
  deriveSessionDirty,
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
  it("returns empty when no artifact and processing idle", () => {
    expect(deriveSessionPhase({ hasArtifact: false, processing: makeProcessing("idle") })).toBe("empty");
  });

  it("returns processing when running", () => {
    expect(deriveSessionPhase({ hasArtifact: false, processing: makeProcessing("running") })).toBe("processing");
  });

  it("returns ready when artifact present", () => {
    expect(deriveSessionPhase({ hasArtifact: true, processing: makeProcessing("idle") })).toBe("ready");
  });

  it("returns ready even if processing error but artifact exists", () => {
    expect(deriveSessionPhase({ hasArtifact: true, processing: makeProcessing("error") })).toBe("ready");
  });

  it("returns error when processing failed and no artifact", () => {
    expect(deriveSessionPhase({ hasArtifact: false, processing: makeProcessing("error") })).toBe("error");
  });

  it("returns ready when processing is ready and artifact present", () => {
    expect(deriveSessionPhase({ hasArtifact: true, processing: makeProcessing("ready") })).toBe("ready");
  });
});

describe("deriveSessionDirty", () => {
  it("returns clean when no analysis artifacts", () => {
    expect(
      deriveSessionDirty({
        waypoints: [],
        measurement: makeMeasurement("empty"),
        profile: makeProfile("empty"),
      })
    ).toBe("clean");
  });

  it("returns dirty when waypoints present", () => {
    expect(
      deriveSessionDirty({
        waypoints: [makeWaypoint("1")],
        measurement: makeMeasurement("empty"),
        profile: makeProfile("empty"),
      })
    ).toBe("dirty");
  });

  it("returns dirty when measurement completed", () => {
    expect(
      deriveSessionDirty({
        waypoints: [],
        measurement: makeMeasurement("completed"),
        profile: makeProfile("empty"),
      })
    ).toBe("dirty");
  });

  it("returns dirty when profile completed", () => {
    expect(
      deriveSessionDirty({
        waypoints: [],
        measurement: makeMeasurement("empty"),
        profile: makeProfile("completed"),
      })
    ).toBe("dirty");
  });

  it("returns clean when measurement selecting (in-progress, not completed)", () => {
    expect(
      deriveSessionDirty({
        waypoints: [],
        measurement: makeMeasurement("selecting-first"),
        profile: makeProfile("empty"),
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
  it("calls all reset deps in order", () => {
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
});
