export type BackendStage =
  | "preprocessing"
  | "inference_running"
  | "calibrating"
  | "dsm_generation"
  | "mesh_generation";

export type ProcessingStage = "loading" | BackendStage;

export const ALL_STAGES: readonly ProcessingStage[] = [
  "loading",
  "preprocessing",
  "inference_running",
  "calibrating",
  "dsm_generation",
  "mesh_generation",
];

export const BACKEND_STAGES: readonly BackendStage[] = [
  "preprocessing",
  "inference_running",
  "calibrating",
  "dsm_generation",
  "mesh_generation",
];

export function isProcessingStage(value: string): value is ProcessingStage {
  return (ALL_STAGES as readonly string[]).includes(value);
}

export const STAGE_LABELS: Record<ProcessingStage, string> = {
  loading: "Loading input",
  preprocessing: "Preparing data",
  inference_running: "Running depth estimation",
  calibrating: "Calibrating height",
  dsm_generation: "Generating DSM",
  mesh_generation: "Generating terrain mesh",
};

export const STAGE_DESCRIPTIONS: Record<ProcessingStage, string> = {
  loading: "Reading input and starting the backend operation.",
  preprocessing: "Backend is validating and preparing the input.",
  inference_running: "Backend is running depth estimation.",
  calibrating: "Backend is calibrating relative depth to metric height.",
  dsm_generation: "Backend is rasterizing the metric DSM.",
  mesh_generation: "Backend is building the terrain mesh.",
};

export type ProcessingStatus = "idle" | "running" | "ready" | "error" | "cancelled";

export interface ProcessingFailure {
  code: string;
  message: string;
  stage: ProcessingStage | null;
  phase: "process" | "transport" | "validation" | "adapter";
  previousAvailable: boolean;
}

export type ProcessingState =
  | { status: "idle" }
  | {
      status: "running";
      operationId: string;
      sourceId: string;
      sourceLabel: string;
      stage: ProcessingStage;
      completedStages: readonly ProcessingStage[];
      cancellable: boolean;
    }
  | {
      status: "ready";
      operationId: string;
      sourceId: string;
      sourceLabel: string;
      artifactId: string;
      completedStages: readonly ProcessingStage[];
      warnings: readonly string[];
    }
  | {
      status: "error";
      operationId: string;
      sourceId: string;
      sourceLabel: string;
      failure: ProcessingFailure;
      completedStages: readonly ProcessingStage[];
    }
  | {
      status: "cancelled";
      operationId: string;
      sourceId: string;
      sourceLabel: string;
      previousAvailable: boolean;
      completedStages: readonly ProcessingStage[];
    };

export type ProcessingEvent =
  | { type: "start"; operationId: string; sourceId: string; sourceLabel: string; cancellable: boolean }
  | { type: "stage"; stage: ProcessingStage }
  | { type: "complete"; artifactId: string; completedStages: readonly ProcessingStage[]; warnings: readonly string[] }
  | { type: "fail"; failure: ProcessingFailure; completedStages: readonly ProcessingStage[] }
  | { type: "cancel"; previousAvailable: boolean; completedStages: readonly ProcessingStage[] }
  | { type: "reset" };

export function canStartOperation(state: ProcessingState): boolean {
  return state.status !== "running";
}

export function isTerminalState(state: ProcessingState): boolean {
  return state.status === "ready" || state.status === "error" || state.status === "cancelled";
}

export function transition(state: ProcessingState, event: ProcessingEvent): ProcessingState {
  switch (event.type) {
    case "start":
      if (state.status === "running") {
        return state;
      }
      return {
        status: "running",
        operationId: event.operationId,
        sourceId: event.sourceId,
        sourceLabel: event.sourceLabel,
        stage: "loading",
        completedStages: [],
        cancellable: event.cancellable,
      };
    case "stage":
      if (state.status !== "running") {
        return state;
      }
      return {
        ...state,
        stage: event.stage,
        completedStages: state.completedStages.includes(event.stage)
          ? state.completedStages
          : [...state.completedStages, event.stage],
      };
    case "complete":
      if (state.status !== "running") {
        return state;
      }
      return {
        status: "ready",
        operationId: state.operationId,
        sourceId: state.sourceId,
        sourceLabel: state.sourceLabel,
        artifactId: event.artifactId,
        completedStages: event.completedStages,
        warnings: event.warnings,
      };
    case "fail":
      if (state.status !== "running") {
        return state;
      }
      return {
        status: "error",
        operationId: state.operationId,
        sourceId: state.sourceId,
        sourceLabel: state.sourceLabel,
        failure: event.failure,
        completedStages: event.completedStages,
      };
    case "cancel":
      if (state.status !== "running") {
        return state;
      }
      return {
        status: "cancelled",
        operationId: state.operationId,
        sourceId: state.sourceId,
        sourceLabel: state.sourceLabel,
        previousAvailable: event.previousAvailable,
        completedStages: event.completedStages,
      };
    case "reset":
      return { status: "idle" };
  }
}
