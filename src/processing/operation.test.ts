import { describe, it, expect, vi } from "vitest";
import { ArtifactLoader } from "../artifact/ArtifactLoader";
import { FixtureSource } from "../artifact/FixtureSource";
import type { ArtifactSource } from "../artifact/types";
import { BackendOperationError } from "../backend/source";
import type { BridgeError } from "../backend/bridge";
import { runProcessingOperation } from "./operation";
import type { ProcessingState } from "./types";

function collect() {
  const states: ProcessingState[] = [];
  return { states, emit: (s: ProcessingState) => states.push(s) };
}

function stageReportingSource(stages: string[]): ArtifactSource {
  return {
    id: "stage-source",
    label: "Stage Source",
    load: async (options) => {
      for (const stage of stages) {
        options?.onStage?.(stage);
      }
      return new FixtureSource().load();
    },
  };
}

describe("runProcessingOperation", () => {
  it("runs loading → stages → ready and returns the artifact", async () => {
    const { states, emit } = collect();
    const outcome = await runProcessingOperation(
      { status: "idle" },
      {
        source: stageReportingSource(["preprocessing", "inference_running"]),
        loader: new ArtifactLoader(),
        operationId: "op-1",
        previousAvailable: false,
      },
      emit
    );
    expect(outcome.kind).toBe("ready");
    if (outcome.kind === "ready") {
      expect(outcome.artifact.id).toBe("dev-fixture-001");
    }
    expect(states[0]).toMatchObject({ status: "running", stage: "loading" });
    expect(states[states.length - 1]).toMatchObject({ status: "ready" });
    const last = states[states.length - 1];
    if (last.status === "ready") {
      expect(last.completedStages).toEqual(["preprocessing", "inference_running"]);
    }
  });

  it("maps structured bridge errors to a processing failure", async () => {
    const bridgeErrors: BridgeError[] = [
      { code: "BACKEND_ERROR", message: "python exploded", phase: "process" },
    ];
    const failing: ArtifactSource = {
      id: "failing",
      label: "Failing",
      load: async () => {
        throw new BackendOperationError(bridgeErrors);
      },
    };
    const { states, emit } = collect();
    const outcome = await runProcessingOperation(
      { status: "idle" },
      { source: failing, loader: new ArtifactLoader(), operationId: "op-2", previousAvailable: true },
      emit
    );
    expect(outcome.kind).toBe("failed");
    const last = states[states.length - 1];
    expect(last.status).toBe("error");
    if (last.status === "error") {
      expect(last.failure.code).toBe("BACKEND_ERROR");
      expect(last.failure.message).toBe("python exploded");
      expect(last.failure.phase).toBe("process");
      expect(last.failure.previousAvailable).toBe(true);
    }
  });

  it("maps unstructured errors without inventing structure", async () => {
    const failing: ArtifactSource = {
      id: "failing",
      label: "Failing",
      load: async () => {
        throw new Error("weird failure");
      },
    };
    const { states, emit } = collect();
    const outcome = await runProcessingOperation(
      { status: "idle" },
      { source: failing, loader: new ArtifactLoader(), operationId: "op-3", previousAvailable: false },
      emit
    );
    expect(outcome.kind).toBe("failed");
    const last = states[states.length - 1];
    if (last.status === "error") {
      expect(last.failure.code).toBe("OPERATION_FAILED");
      expect(last.failure.message).toBe("weird failure");
    }
  });

  it("treats a pre-aborted signal as cancelled without calling the loader", async () => {
    const controller = new AbortController();
    controller.abort();
    const load = vi.fn(async () => new FixtureSource().load());
    const source: ArtifactSource = { id: "s", label: "s", load };
    const { states, emit } = collect();
    const outcome = await runProcessingOperation(
      { status: "idle" },
      { source, loader: new ArtifactLoader(), operationId: "op-4", previousAvailable: true, signal: controller.signal },
      emit
    );
    expect(outcome.kind).toBe("cancelled");
    expect(load).not.toHaveBeenCalled();
    const last = states[states.length - 1];
    expect(last.status).toBe("cancelled");
    if (last.status === "cancelled") {
      expect(last.previousAvailable).toBe(true);
    }
  });

  it("maps OPERATION_CANCELLED bridge errors to cancelled, not failed", async () => {
    const failing: ArtifactSource = {
      id: "failing",
      label: "Failing",
      load: async () => {
        throw new BackendOperationError([
          { code: "OPERATION_CANCELLED", message: "Operation cancelled", phase: "process" },
        ]);
      },
    };
    const { states, emit } = collect();
    const outcome = await runProcessingOperation(
      { status: "idle" },
      { source: failing, loader: new ArtifactLoader(), operationId: "op-5", previousAvailable: true },
      emit
    );
    expect(outcome.kind).toBe("cancelled");
    expect(states[states.length - 1].status).toBe("cancelled");
  });

  it("retains the previous artifact when resolution fails", async () => {
    const failing: ArtifactSource = {
      id: "failing",
      label: "Failing",
      load: async () => {
        throw new BackendOperationError([
          { code: "RESOLUTION_FAILED", message: "payload rejected", phase: "adapter" },
        ]);
      },
    };
    const { states, emit } = collect();
    const outcome = await runProcessingOperation(
      { status: "idle" },
      { source: failing, loader: new ArtifactLoader(), operationId: "op-7", previousAvailable: true },
      emit
    );
    expect(outcome.kind).toBe("failed");
    const last = states[states.length - 1];
    expect(last.status).toBe("error");
    if (last.status === "error") {
      expect(last.failure.code).toBe("RESOLUTION_FAILED");
      expect(last.failure.previousAvailable).toBe(true);
    }
  });

  it("refuses duplicate operations while one is running", async () => {
    const running: ProcessingState = {
      status: "running",
      operationId: "op-1",
      sourceId: "s",
      sourceLabel: "s",
      stage: "loading",
      completedStages: [],
      cancellable: true,
    };
    const { states, emit } = collect();
    const outcome = await runProcessingOperation(
      running,
      { source: new FixtureSource(), loader: new ArtifactLoader(), operationId: "op-2", previousAvailable: false },
      emit
    );
    expect(outcome.kind).toBe("duplicate");
    expect(states).toEqual([]);
  });

  it("ignores unknown stage reports without crashing", async () => {
    const { states, emit } = collect();
    const outcome = await runProcessingOperation(
      { status: "idle" },
      {
        source: stageReportingSource(["73%", "warp_drive"]),
        loader: new ArtifactLoader(),
        operationId: "op-6",
        previousAvailable: false,
      },
      emit
    );
    expect(outcome.kind).toBe("ready");
    const last = states[states.length - 1];
    if (last.status === "ready") {
      expect(last.completedStages).toEqual([]);
    }
  });
});
