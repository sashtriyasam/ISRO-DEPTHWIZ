import { describe, it, expect } from "vitest";
import { mergeRelayedStages, type ProcessingState } from "./types";

const running: ProcessingState = {
  status: "running",
  operationId: "op-1",
  sourceId: "file",
  sourceLabel: "scene.tif",
  stage: "inference_running",
  completedStages: ["preprocessing", "inference_running"],
  cancellable: true,
};

const ready = (operationId: string): ProcessingState => ({
  status: "ready",
  operationId,
  sourceId: "file",
  sourceLabel: "scene.tif",
  artifactId: "a1",
  completedStages: [],
  warnings: [],
});

describe("mergeRelayedStages", () => {
  it("keeps stages relayed over IPC when the operation completes", () => {
    const merged = mergeRelayedStages(running, ready("op-1"));
    expect(merged.status).toBe("ready");
    expect(merged.status !== "idle" && merged.completedStages).toEqual([
      "preprocessing",
      "inference_running",
    ]);
  });

  it("does not carry stages over from a different operation", () => {
    expect(mergeRelayedStages(running, ready("op-2"))).toEqual(ready("op-2"));
  });

  it("passes idle through unchanged", () => {
    expect(mergeRelayedStages(running, { status: "idle" })).toEqual({ status: "idle" });
  });
});
