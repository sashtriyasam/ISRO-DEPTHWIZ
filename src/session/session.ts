import type { MeasurementState } from "../measurement/types";
import type { ProfileState } from "../profile/types";
import type { InspectionState } from "../inspection/types";
import type { ProcessingState } from "../processing/types";
import type { FlythroughWaypoint, PlaybackStatus } from "../flythrough/types";

export type SessionPhase = "empty" | "processing" | "ready" | "error";

export type SessionModified = "clean" | "modified";

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
  if (hasArtifact) {
    return "ready";
  }
  if (processing.status === "error") {
    return "error";
  }
  if (processing.status === "cancelled") {
    return hasArtifact ? "ready" : "empty";
  }
  return "empty";
}

export function deriveSessionModified(snapshot: Pick<SessionSnapshot, "waypoints" | "measurement" | "profile">): SessionModified {
  if (snapshot.waypoints.length > 0) {
    return "modified";
  }
  if (snapshot.measurement.status === "completed") {
    return "modified";
  }
  if (snapshot.profile.status === "completed") {
    return "modified";
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
