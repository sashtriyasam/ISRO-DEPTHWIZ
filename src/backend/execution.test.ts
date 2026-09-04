import { describe, it, expect } from "vitest";
import { BackendBridge } from "./bridge";

describe("backend stage reporting and cancellation", () => {
  const bridge = new BackendBridge({
    bridgeScript: "scripts/backend_bridge.py",
  });

  it("reports real backend stages in order for terrain", async () => {
    const stages: string[] = [];
    const result = await bridge.executeTerrain(4, 4, {
      onStage: (stage) => stages.push(stage),
    });
    expect(result.success).toBe(true);
    expect(stages).toEqual([
      "preprocessing",
      "inference_running",
      "calibrating",
      "dsm_generation",
      "mesh_generation",
    ]);
  });

  it("reports real backend stages for depth-only execution", async () => {
    const stages: string[] = [];
    const result = await bridge.executeSynthetic(4, 4, {
      onStage: (stage) => stages.push(stage),
    });
    expect(result.success).toBe(true);
    expect(stages).toEqual(["preprocessing", "inference_running"]);
  });

  it("rejects pre-aborted operations without spawning", async () => {
    const controller = new AbortController();
    controller.abort();
    const result = await bridge.executeTerrain(4, 4, { signal: controller.signal });
    expect(result.success).toBe(false);
    expect(result.errors.some((e) => e.code === "OPERATION_CANCELLED")).toBe(true);
  });
});
