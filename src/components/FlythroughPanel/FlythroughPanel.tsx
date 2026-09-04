import {
  DEFAULT_SEGMENT_DURATION_MS,
  PLAYBACK_SPEEDS,
  type FlythroughWaypoint,
  type PlaybackSpeed,
  type PlaybackStatus,
} from "../../flythrough/types";
import { totalDurationMs } from "../../flythrough/trajectory";

interface FlythroughPanelProps {
  waypoints: readonly FlythroughWaypoint[];
  status: PlaybackStatus;
  speed: PlaybackSpeed;
  currentIndex: number;
  canCapture: boolean;
  navigationLocked: boolean;
  onAddWaypoint: () => void;
  onRemoveWaypoint: (id: string) => void;
  onClear: () => void;
  onPlay: () => void;
  onPause: () => void;
  onResume: () => void;
  onStop: () => void;
  onReset: () => void;
  onSpeedChange: (speed: PlaybackSpeed) => void;
}

const SPEED_LABELS: Record<PlaybackSpeed, string> = {
  0.5: "0.5×",
  1: "1×",
  2: "2×",
};

export function FlythroughPanel({
  waypoints,
  status,
  speed,
  currentIndex,
  canCapture,
  navigationLocked,
  onAddWaypoint,
  onRemoveWaypoint,
  onClear,
  onPlay,
  onPause,
  onResume,
  onStop,
  onReset,
  onSpeedChange,
}: FlythroughPanelProps) {
  const canPlay = waypoints.length >= 2;
  const isActive = status === "playing" || status === "paused";
  const segmentCount = Math.max(0, waypoints.length - 1);
  const currentSegment = Math.min(Math.max(0, currentIndex), Math.max(0, segmentCount - 1)) + 1;
  const durationMs =
    waypoints.length >= 2
      ? totalDurationMs({
          id: "preview",
          waypoints,
          segmentDurationMs: DEFAULT_SEGMENT_DURATION_MS,
        })
      : 0;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--spacing-md)" }}>
      <div style={sectionLabelStyle}>Flythrough</div>
      <div aria-live="polite" style={{ display: "flex", flexDirection: "column", gap: "var(--spacing-sm)" }}>
        {waypoints.length === 0 && (
          <div style={mutedStyle}>Add a waypoint from the current camera position.</div>
        )}
        {waypoints.length === 1 && (
          <div style={mutedStyle}>Add at least one more waypoint to enable playback.</div>
        )}
        {waypoints.length > 0 && (
          <div role="list" aria-label="Flythrough waypoints" style={{ display: "flex", flexDirection: "column", gap: "var(--spacing-xs)" }}>
            {waypoints.map((waypoint, index) => (
              <div
                key={waypoint.id}
                role="listitem"
                style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "var(--spacing-sm)" }}
              >
                <span style={{ fontSize: "var(--font-size-xs)", color: "var(--color-text-primary)" }}>
                  Waypoint {index + 1}
                  {isActive && index === currentIndex ? " (current)" : ""}
                </span>
                <button
                  style={actionButtonStyle}
                  onClick={() => onRemoveWaypoint(waypoint.id)}
                  disabled={isActive}
                  aria-label={`Remove waypoint ${index + 1}`}
                  title={isActive ? "Stop playback to edit waypoints" : `Remove waypoint ${index + 1}`}
                >
                  Remove
                </button>
              </div>
            ))}
          </div>
        )}
        {canPlay && (
          <div style={mutedStyle}>
            Duration ~{(durationMs / 1000).toFixed(0)}s
            {isActive
              ? ` · Segment ${currentSegment} of ${segmentCount} · Waypoint ${Math.min(currentIndex + 1, waypoints.length)} of ${waypoints.length}`
              : ""}
          </div>
        )}
        {status === "playing" && <div style={mutedStyle}>Flythrough playing…</div>}
        {status === "completed" && <div style={mutedStyle}>Flythrough completed at the final waypoint.</div>}
        <div style={{ display: "flex", gap: "var(--spacing-xs)", flexWrap: "wrap" }}>
          <button
            style={actionButtonStyle}
            onClick={onAddWaypoint}
            disabled={!canCapture || isActive}
            aria-label="Add waypoint from current camera"
            title={isActive ? "Stop playback to edit waypoints" : "Capture the current camera position as a waypoint"}
          >
            Add Waypoint
          </button>
          {waypoints.length > 0 && (
            <button
              style={actionButtonStyle}
              onClick={onClear}
              disabled={isActive}
              aria-label="Clear waypoints"
              title={isActive ? "Stop playback to edit waypoints" : "Remove all waypoints"}
            >
              Clear
            </button>
          )}
        </div>
        {canPlay && (
          <div style={{ display: "flex", gap: "var(--spacing-xs)", flexWrap: "wrap" }}>
            {status !== "playing" && status !== "paused" && (
              <button style={actionButtonStyle} onClick={onPlay} aria-label="Play flythrough" title="Play the trajectory from the start">
                Play
              </button>
            )}
            {status === "playing" && (
              <button style={actionButtonStyle} onClick={onPause} aria-label="Pause flythrough" title="Freeze at the current trajectory time">
                Pause
              </button>
            )}
            {status === "paused" && (
              <button style={actionButtonStyle} onClick={onResume} aria-label="Resume flythrough" title="Continue from the paused time">
                Resume
              </button>
            )}
            {(status === "playing" || status === "paused" || status === "completed") && (
              <button style={actionButtonStyle} onClick={onStop} aria-label="Stop flythrough" title="End playback and restore the previous camera mode">
                Stop
              </button>
            )}
            {(status === "paused" || status === "completed") && (
              <button style={actionButtonStyle} onClick={onReset} aria-label="Reset flythrough" title="Return to the starting waypoint">
                Reset
              </button>
            )}
          </div>
        )}
        <div style={{ display: "flex", gap: "var(--spacing-xs)", alignItems: "center" }}>
          <span style={{ fontSize: "var(--font-size-xs)", color: "var(--color-text-muted)" }}>Speed</span>
          {PLAYBACK_SPEEDS.map((option) => (
            <button
              key={option}
              style={{
                ...actionButtonStyle,
                background: speed === option ? "var(--color-accent)" : "var(--color-bg-tertiary)",
                color: speed === option ? "#fff" : "var(--color-text-secondary)",
              }}
              aria-label={`Playback speed ${SPEED_LABELS[option]}`}
              aria-pressed={speed === option}
              onClick={() => onSpeedChange(option)}
            >
              {SPEED_LABELS[option]}
            </button>
          ))}
        </div>
        {navigationLocked && (
          <div style={mutedStyle}>Manual camera controls resume after Stop.</div>
        )}
      </div>
    </div>
  );
}

const sectionLabelStyle: React.CSSProperties = {
  fontSize: "var(--font-size-xs)",
  color: "var(--color-text-muted)",
  textTransform: "uppercase",
  letterSpacing: "0.05em",
};

const mutedStyle: React.CSSProperties = {
  fontSize: "var(--font-size-xs)",
  color: "var(--color-text-muted)",
  fontStyle: "italic",
};

const actionButtonStyle: React.CSSProperties = {
  padding: "var(--spacing-xs) var(--spacing-sm)",
  fontSize: "var(--font-size-xs)",
  borderRadius: "var(--radius-sm)",
  background: "var(--color-bg-tertiary)",
  color: "var(--color-text-secondary)",
  border: "1px solid var(--color-border-subtle)",
  cursor: "pointer",
  lineHeight: 1.4,
};
