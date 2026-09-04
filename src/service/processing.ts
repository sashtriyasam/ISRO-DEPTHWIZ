import type { ProcessingFailure, ProcessingStage } from "../processing/types";
import { isProcessingStage } from "../processing/types";
import type { ServiceResponseWire } from "./wireTypes";

const TERMINAL_STATES = new Set(["completed", "failed", "cancelled"]);

export function serviceStatesToStages(states: readonly string[]): ProcessingStage[] {
  const stages: ProcessingStage[] = [];
  for (const state of states) {
    if (TERMINAL_STATES.has(state)) {
      continue;
    }
    if (state === "input_validated") {
      if (!stages.includes("loading")) {
        stages.push("loading");
      }
      continue;
    }
    if (isProcessingStage(state) && !stages.includes(state)) {
      stages.push(state);
    }
  }
  return stages;
}

export function serviceFailureToProcessingFailure(
  response: ServiceResponseWire,
  previousAvailable: boolean
): ProcessingFailure {
  const failure = response.failure;
  return {
    code: failure?.code ?? "SERVICE_FAILURE",
    message: failure?.message ?? "Service execution failed",
    stage:
      failure?.stage && isProcessingStage(failure.stage)
        ? failure.stage
        : completedStageOf(response),
    phase: "process",
    previousAvailable,
  };
}

function completedStageOf(response: ServiceResponseWire): ProcessingStage | null {
  const stages = serviceStatesToStages(response.states);
  return stages.length > 0 ? stages[stages.length - 1] : null;
}

export function meshDescriptorOf(response: ServiceResponseWire) {
  return response.artifacts.find((a) => a.kind === "mesh");
}
