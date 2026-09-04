import { describe, it, expect } from "vitest";
import {
  canStartOperation,
  isTerminalState,
  isProcessingStage,
  STAGE_LABELS,
  ALL_STAGES,
  transition,
  type ProcessingState,
} from "./types";

const IDLE: ProcessingState = { status: "idle" };

function started(): ProcessingState {
  return transition(IDLE, {
    type: "start",
    operationId: "op-1",
    sourceId: "backend-synthetic",
    sourceLabel: "Synthetic Development Backend",
    cancellable: true,
  });
}

describe("processing state machine", () => {
  it("starts idle", () => {
    expect(IDLE.status).toBe("idle");
    expect(canStartOperation(IDLE)).toBe(true);
    expect(isTerminalState(IDLE)).toBe(false);
  });

  it("transitions idle → running on start", () => {
    const next = started();
    expect(next.status).toBe("running");
    if (next.status === "running") {
      expect(next.stage).toBe("loading");
      expect(next.completedStages).toEqual([]);
      expect(next.operationId).toBe("op-1");
    }
    expect(canStartOperation(next)).toBe(false);
  });

  it("records stage progress while running", () => {
    let state = started();
    state = transition(state, { type: "stage", stage: "preprocessing" });
    state = transition(state, { type: "stage", stage: "inference_running" });
    expect(state.status).toBe("running");
    if (state.status === "running") {
      expect(state.stage).toBe("inference_running");
      expect(state.completedStages).toEqual(["preprocessing", "inference_running"]);
    }
  });

  it("does not duplicate repeated stage reports", () => {
    let state = started();
    state = transition(state, { type: "stage", stage: "preprocessing" });
    state = transition(state, { type: "stage", stage: "preprocessing" });
    if (state.status === "running") {
      expect(state.completedStages).toEqual(["preprocessing"]);
    }
  });

  it("transitions running → ready on complete", () => {
    let state = started();
    state = transition(state, { type: "stage", stage: "mesh_generation" });
    state = transition(state, {
      type: "complete",
      artifactId: "backend-x-terrain",
      completedStages: ["mesh_generation"],
      warnings: [],
    });
    expect(state.status).toBe("ready");
    if (state.status === "ready") {
      expect(state.artifactId).toBe("backend-x-terrain");
    }
    expect(isTerminalState(state)).toBe(true);
    expect(canStartOperation(state)).toBe(true);
  });

  it("transitions running → error on fail", () => {
    let state = started();
    state = transition(state, {
      type: "fail",
      failure: {
        code: "BACKEND_ERROR",
        message: "boom",
        stage: "inference_running",
        phase: "process",
        previousAvailable: true,
      },
      completedStages: [],
    });
    expect(state.status).toBe("error");
    if (state.status === "error") {
      expect(state.failure.code).toBe("BACKEND_ERROR");
      expect(state.failure.stage).toBe("inference_running");
      expect(state.failure.previousAvailable).toBe(true);
    }
    expect(isTerminalState(state)).toBe(true);
  });

  it("transitions running → cancelled on cancel without calling it failure", () => {
    let state = started();
    state = transition(state, {
      type: "cancel",
      previousAvailable: true,
      completedStages: [],
    });
    expect(state.status).toBe("cancelled");
    expect(isTerminalState(state)).toBe(true);
  });

  it("rejects start while running (duplicate prevention)", () => {
    const running = started();
    const next = transition(running, {
      type: "start",
      operationId: "op-2",
      sourceId: "x",
      sourceLabel: "x",
      cancellable: true,
    });
    expect(next).toBe(running);
  });

  it("rejects stage updates when not running", () => {
    expect(transition(IDLE, { type: "stage", stage: "preprocessing" })).toBe(IDLE);
    const ready: ProcessingState = {
      status: "ready",
      operationId: "op-1",
      sourceId: "s",
      sourceLabel: "s",
      artifactId: "a",
      completedStages: [],
      warnings: [],
    };
    expect(transition(ready, { type: "stage", stage: "preprocessing" })).toBe(ready);
  });

  it("rejects complete/fail/cancel when not running", () => {
    expect(
      transition(IDLE, { type: "complete", artifactId: "a", completedStages: [], warnings: [] })
    ).toBe(IDLE);
    expect(
      transition(IDLE, {
        type: "fail",
        failure: { code: "x", message: "x", stage: null, phase: "process", previousAvailable: false },
        completedStages: [],
      })
    ).toBe(IDLE);
    expect(
      transition(IDLE, { type: "cancel", previousAvailable: false, completedStages: [] })
    ).toBe(IDLE);
  });

  it("resets any state to idle", () => {
    expect(transition(started(), { type: "reset" })).toEqual(IDLE);
    expect(transition({ status: "cancelled", operationId: "o", sourceId: "s", sourceLabel: "s", previousAvailable: false, completedStages: [] }, { type: "reset" })).toEqual(IDLE);
  });

  it("running state carries no numeric progress", () => {
    const state = started();
    expect("progress" in state).toBe(false);
    expect("percent" in state).toBe(false);
  });

  it("labels every stage with backend-consistent terminology", () => {
    for (const stage of ALL_STAGES) {
      expect(STAGE_LABELS[stage]).toBeTruthy();
      expect(typeof STAGE_LABELS[stage]).toBe("string");
    }
    expect(STAGE_LABELS["inference_running"]).toContain("depth");
    expect(STAGE_LABELS["dsm_generation"]).toContain("DSM");
    expect(STAGE_LABELS["mesh_generation"]).toContain("mesh");
  });

  it("validates stage names", () => {
    expect(isProcessingStage("preprocessing")).toBe(true);
    expect(isProcessingStage("mesh_generation")).toBe(true);
    expect(isProcessingStage("loading")).toBe(true);
    expect(isProcessingStage("73%")).toBe(false);
    expect(isProcessingStage("exporting")).toBe(false);
  });
});
