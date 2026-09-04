import type { ProfileState } from "../../profile/types";
import { ProfileChart } from "../ProfileChart/ProfileChart";

interface ProfilePanelProps {
  state: ProfileState;
  onStartProfile: () => void;
  onClear: () => void;
  startDisabled?: boolean;
}

export function ProfilePanel({ state, onStartProfile, onClear, startDisabled = false }: ProfilePanelProps) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--spacing-md)" }}>
      <div style={sectionLabelStyle}>Elevation Profile</div>
      <div style={{ display: "flex", flexDirection: "column", gap: "var(--spacing-sm)" }}>
        {state.status === "empty" && (
          <>
            <StatusRow label="Point A" value="Select point" muted />
            <StatusRow label="Point B" value="Select point" muted />
            <button
              style={startButtonStyle}
              onClick={onStartProfile}
              aria-label="Start elevation profile"
              title={startDisabled ? "Unavailable during flythrough playback" : "Start elevation profile"}
              disabled={startDisabled}
            >
              Start
            </button>
          </>
        )}
        {state.status === "selecting-first" && (
          <>
            <StatusRow label="Point A" value="Click terrain..." accent />
            <StatusRow label="Point B" value="Select point" muted />
            <button style={cancelButtonStyle} onClick={onClear} aria-label="Cancel profile">
              Cancel
            </button>
          </>
        )}
        {state.status === "selecting-second" && (
          <>
            <StatusRow label="Point A" value="Selected" ok />
            <StatusRow label="Point B" value="Click terrain..." accent />
            <button style={cancelButtonStyle} onClick={onClear} aria-label="Cancel profile">
              Cancel
            </button>
          </>
        )}
        {state.status === "completed" && (
          <>
            <div style={{ height: 1, background: "var(--color-border-subtle)", margin: "var(--spacing-xs) 0" }} />
            <DataRow label="Path length" value={`${state.profile.totalDistance.toFixed(3)} m`} />
            <DataRow label="Min elevation" value={`${state.profile.minElevation.toFixed(3)} m`} />
            <DataRow label="Max elevation" value={`${state.profile.maxElevation.toFixed(3)} m`} />
            <DataRow label="Samples" value={`${state.profile.sampleCount}`} />
            <DataRow label="Source" value="Fixture coordinate system" />
            <div style={{ height: 1, background: "var(--color-border-subtle)", margin: "var(--spacing-xs) 0" }} />
            <ProfileChart profile={state.profile} />
            <div style={{ fontSize: "var(--font-size-xs)", color: "var(--color-text-muted)", fontStyle: "italic" }}>
              Synthetic development data — not scientific output
            </div>
            <button style={clearButtonStyle} onClick={onClear} aria-label="Clear profile">
              Clear
            </button>
          </>
        )}
      </div>
    </div>
  );
}

function StatusRow({ label, value, muted, accent, ok }: { label: string; value: string; muted?: boolean; accent?: boolean; ok?: boolean }) {
  const color = ok ? "var(--color-status-ok)" : accent ? "var(--color-accent)" : muted ? "var(--color-text-muted)" : "var(--color-text-primary)";
  return (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
      <span style={{ fontSize: "var(--font-size-xs)", color: "var(--color-text-muted)" }}>{label}</span>
      <span style={{ fontSize: "var(--font-size-xs)", color }}>{value}</span>
    </div>
  );
}

function DataRow({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
      <span style={{ fontSize: "var(--font-size-xs)", color: "var(--color-text-muted)" }}>{label}</span>
      <span style={{ fontSize: "var(--font-size-xs)", color: "var(--color-text-primary)", fontFamily: "var(--font-mono)" }}>{value}</span>
    </div>
  );
}

const sectionLabelStyle: React.CSSProperties = {
  fontSize: "var(--font-size-xs)",
  color: "var(--color-text-muted)",
  textTransform: "uppercase",
  letterSpacing: "0.05em",
};

const startButtonStyle: React.CSSProperties = {
  padding: "var(--spacing-xs) var(--spacing-sm)",
  fontSize: "var(--font-size-xs)",
  borderRadius: "var(--radius-sm)",
  background: "var(--color-accent)",
  color: "#fff",
  border: "1px solid var(--color-border-subtle)",
  cursor: "pointer",
  lineHeight: 1.4,
  width: "100%",
};

const cancelButtonStyle: React.CSSProperties = {
  padding: "var(--spacing-xs) var(--spacing-sm)",
  fontSize: "var(--font-size-xs)",
  borderRadius: "var(--radius-sm)",
  background: "var(--color-bg-tertiary)",
  color: "var(--color-status-warn)",
  border: "1px solid var(--color-border-subtle)",
  cursor: "pointer",
  lineHeight: 1.4,
  width: "100%",
};

const clearButtonStyle: React.CSSProperties = {
  padding: "var(--spacing-xs) var(--spacing-sm)",
  fontSize: "var(--font-size-xs)",
  borderRadius: "var(--radius-sm)",
  background: "var(--color-bg-tertiary)",
  color: "var(--color-text-secondary)",
  border: "1px solid var(--color-border-subtle)",
  cursor: "pointer",
  lineHeight: 1.4,
  width: "100%",
};
