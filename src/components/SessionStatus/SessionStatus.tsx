import type { SessionDirty, SessionPhase } from "../../session/session";

interface SessionStatusProps {
  phase: SessionPhase;
  dirty: SessionDirty;
  canReset: boolean;
  onReset?: () => void;
}

const PHASE_LABELS: Record<SessionPhase, string> = {
  empty: "Empty",
  "input-ready": "Input Ready",
  processing: "Processing",
  ready: "Ready",
  error: "Error",
};

const PHASE_COLORS: Record<SessionPhase, string> = {
  empty: "var(--color-text-muted)",
  "input-ready": "var(--color-text-secondary)",
  processing: "var(--color-accent)",
  ready: "var(--color-success)",
  error: "var(--color-error)",
};

export function SessionStatus({ phase, dirty, canReset, onReset }: SessionStatusProps) {
  return (
    <div style={rootStyle} role="region" aria-label="Project session status">
      <div style={headerStyle}>
        <span style={phaseLabelStyle}>
          <span style={{ color: PHASE_COLORS[phase] }} aria-hidden="true">&#9679;</span>
          {" "}Session {PHASE_LABELS[phase]}
        </span>
        {dirty === "dirty" && (
          <span style={dirtyBadgeStyle} aria-label="Unsaved analysis state">
            unsaved
          </span>
        )}
      </div>
      {canReset && (
        <button
          onClick={onReset}
          style={resetButtonStyle}
          aria-label="Reset project session"
        >
          Reset Workspace
        </button>
      )}
    </div>
  );
}

const rootStyle: React.CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "var(--spacing-xs)",
  padding: "var(--spacing-xs) 0",
};

const headerStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
};

const phaseLabelStyle: React.CSSProperties = {
  fontSize: "var(--font-size-xs)",
  color: "var(--color-text-muted)",
  textTransform: "uppercase",
  letterSpacing: "0.05em",
};

const dirtyBadgeStyle: React.CSSProperties = {
  fontSize: "10px",
  padding: "1px 6px",
  borderRadius: "var(--radius-sm)",
  background: "var(--color-warning-bg)",
  color: "var(--color-warning)",
  lineHeight: "1.4",
};

const resetButtonStyle: React.CSSProperties = {
  marginTop: "var(--spacing-xs)",
  padding: "var(--spacing-xs) var(--spacing-sm)",
  fontSize: "var(--font-size-xs)",
  borderRadius: "var(--radius-sm)",
  background: "var(--color-bg-tertiary)",
  color: "var(--color-text-secondary)",
  border: "1px solid var(--color-border-subtle)",
  cursor: "pointer",
  lineHeight: 1.4,
  alignSelf: "flex-start",
};
