import type { MeasurementState } from "../measurement/types";
import type { ProfileState } from "../profile/types";
import type { InspectionState } from "../inspection/types";
import type { ProcessingState } from "../processing/types";
import type { FlythroughWaypoint, PlaybackStatus } from "../flythrough/types";

export type SessionPhase = "empty" | "input-ready" | "processing" | "ready" | "error";

export type SessionDirty = "clean" | "dirty" | "not-applicable";

export interface SessionSnapshot {
  hasArtifact: boolean;
  processing: ProcessingState;
  waypoints: readonly FlythroughWaypoint[];
  playbackStatus: PlaybackStatus;
  measurement: MeasurementState;
  profile: ProfileState;
  inspection: InspectionState;
}

export function deriveSessionPhase(snapshot: Pick<SessionSnapshot, "hasArtifact" | "processing">): SessionPhase {
  const { hasArtifact, processing } = snapshot;
  if (processing.status === "running") {
    return "processing";
  }
  if (processing.status === "error" && !hasArtifact) {
    return "error";
  }
  if (hasArtifact) {
    return "ready";
  }
  if (processing.status === "error") {
    return "error";
  }
  return "empty";
}

export function deriveSessionDirty(snapshot: Pick<SessionSnapshot, "waypoints" | "measurement" | "profile">): SessionDirty {
  if (snapshot.waypoints.length > 0) {
    return "dirty";
  }
  if (snapshot.measurement.status === "completed") {
    return "dirty";
  }
  if (snapshot.profile.status === "completed") {
    return "dirty";
  }
  return "clean";
}

export interface SessionResetDeps {
  abortOperation: () => void;
  setProcessingIdle: () => void;
  clearArtifact: () => void;
  clearLayers: () => void;
  clearAnalysis: () => void;
  clearFlythrough: () => void;
  resetCameraToOrbit: () => void;
}

export function resetSession(deps: SessionResetDeps): void {
  deps.abortOperation();
  deps.setProcessingIdle();
  deps.clearArtifact();
  deps.clearLayers();
  deps.clearAnalysis();
  deps.clearFlythrough();
  deps.resetCameraToOrbit();
}

export function pendingSelections(snapshot: Pick<SessionSnapshot, "measurement" | "profile" | "inspection">): boolean {
  const selecting =
    snapshot.measurement.status === "selecting-first" ||
    snapshot.measurement.status === "selecting-second" ||
    snapshot.profile.status === "selecting-first" ||
    snapshot.profile.status === "selecting-second";
  return selecting || snapshot.inspection.status === "selected";
}
