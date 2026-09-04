import type { ArtifactLoader } from "../artifact/ArtifactLoader";
import type { ArtifactSource } from "../artifact/types";
import type { SceneArtifact } from "../types/scene";
import type { BridgeError } from "../backend/bridge";
import { BackendOperationError } from "../backend/source";
import {
  canStartOperation,
  isProcessingStage,
  transition,
  type ProcessingFailure,
  type ProcessingStage,
  type ProcessingState,
} from "./types";

export interface RunOperationOptions {
  source: ArtifactSource;
  loader: ArtifactLoader;
  operationId: string;
  previousAvailable: boolean;
  signal?: AbortSignal;
}

export type OperationOutcome =
  | { kind: "ready"; artifact: SceneArtifact }
  | { kind: "failed" }
  | { kind: "cancelled" }
  | { kind: "duplicate" };

function findBridgeErrors(err: unknown): BridgeError[] | null {
  let current: unknown = err;
  const seen = new Set<unknown>();
  while (current && typeof current === "object" && !seen.has(current)) {
    seen.add(current);
    if (current instanceof BackendOperationError) {
      return current.bridgeErrors;
    }
    const record = current as { bridgeErrors?: unknown; cause?: unknown };
    if (Array.isArray(record.bridgeErrors)) {
      return record.bridgeErrors as BridgeError[];
    }
    current = record.cause;
  }
  return null;
}

function messageOf(err: unknown): string {
  if (err instanceof Error) {
    return err.message;
  }
  if (err && typeof err === "object" && "message" in err && typeof err.message === "string") {
    return err.message;
  }
  return String(err);
}

export async function runProcessingOperation(
  initial: ProcessingState,
  options: RunOperationOptions,
  emit: (state: ProcessingState) => void
): Promise<OperationOutcome> {
  if (!canStartOperation(initial)) {
    return { kind: "duplicate" };
  }

  if (options.signal?.aborted) {
    emit(
      transition(initial, {
        type: "start",
        operationId: options.operationId,
        sourceId: options.source.id,
        sourceLabel: options.source.label,
        cancellable: false,
      })
    );
    const running = transition(
      transition(initial, {
        type: "start",
        operationId: options.operationId,
        sourceId: options.source.id,
        sourceLabel: options.source.label,
        cancellable: false,
      }),
      { type: "cancel", previousAvailable: options.previousAvailable, completedStages: [] }
    );
    emit(running);
    return { kind: "cancelled" };
  }

  let state = transition(initial, {
    type: "start",
    operationId: options.operationId,
    sourceId: options.source.id,
    sourceLabel: options.source.label,
    cancellable: Boolean(options.signal),
  });
  emit(state);

  const completedStages: ProcessingStage[] = [];
  const onStage = (stage: string) => {
    if (!isProcessingStage(stage)) {
      return;
    }
    if (state.status !== "running") {
      return;
    }
    if (!completedStages.includes(stage)) {
      completedStages.push(stage);
    }
    state = transition(state, { type: "stage", stage });
    emit(state);
  };

  try {
    const result = await options.loader.load(options.source, {
      signal: options.signal,
      onStage,
    });
    const stages = [...completedStages];
    state = transition(state, {
      type: "complete",
      artifactId: result.artifact.id,
      completedStages: stages,
      warnings: [],
    });
    emit(state);
    return { kind: "ready", artifact: result.artifact };
  } catch (err) {
    const bridgeErrors = findBridgeErrors(err);
    const cancelled =
      options.signal?.aborted ||
      (bridgeErrors !== null && bridgeErrors.some((e) => e.code === "OPERATION_CANCELLED"));
    const stages = [...completedStages];
    if (cancelled) {
      state = transition(state, {
        type: "cancel",
        previousAvailable: options.previousAvailable,
        completedStages: stages,
      });
      emit(state);
      return { kind: "cancelled" };
    }
    const currentStage = state.status === "running" ? state.stage : null;
    const failure: ProcessingFailure =
      bridgeErrors !== null && bridgeErrors.length > 0
        ? {
            code: bridgeErrors[0].code,
            message: bridgeErrors[0].message,
            stage: currentStage,
            phase: bridgeErrors[0].phase,
            previousAvailable: options.previousAvailable,
          }
        : {
            code: "OPERATION_FAILED",
            message: messageOf(err),
            stage: currentStage,
            phase: "process",
            previousAvailable: options.previousAvailable,
          };
    state = transition(state, { type: "fail", failure, completedStages: stages });
    emit(state);
    return { kind: "failed" };
  }
}
