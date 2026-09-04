import type { ProcessingState } from "../../processing/types";
import { STAGE_LABELS } from "../../processing/types";

export interface ProcessingResultMeta {
  backend: string;
  target: string;
}

interface ProcessingPanelProps {
  state: ProcessingState;
  resultMeta?: ProcessingResultMeta | null;
  onCancel?: () => void;
  onRetry?: () => void;
  onDismiss?: () => void;
}

export function ProcessingPanel({ state, resultMeta, onCancel, onRetry, onDismiss }: ProcessingPanelProps) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--spacing-md)" }}>
      <div style={sectionLabelStyle}>Processing</div>
      <div aria-live="polite" style={{ display: "flex", flexDirection: "column", gap: "var(--spacing-sm)" }}>
        {state.status === "idle" && (
          <div style={mutedStyle}>No processing operation. Select a source to generate terrain.</div>
        )}
        {state.status === "running" && (
          <>
            <DataRow label="Status" value={STAGE_LABELS[state.stage]} />
            <DataRow label="Progress" value="Processing…" />
            <DataRow label="Source" value={state.sourceLabel} />
            {state.cancellable && onCancel && (
              <button onClick={onCancel} style={actionButtonStyle} aria-label="Cancel operation">
                Cancel
              </button>
            )}
          </>
        )}
        {state.status === "ready" && (
          <>
            <DataRow label="Status" value="Ready" />
            <DataRow label="Source" value={state.sourceLabel} />
            {resultMeta && (
              <>
                <DataRow label="Backend" value={resultMeta.backend} />
                <DataRow label="Target" value={resultMeta.target} />
              </>
            )}
            <DataRow label="Stages" value={`${state.completedStages.length} completed`} />
          </>
        )}
        {state.status === "error" && (
          <>
            <DataRow label="Status" value="Failed" />
            <DataRow label="Stage" value={state.failure.stage ? STAGE_LABELS[state.failure.stage] : "Unknown"} />
            <DataRow label="Error" value={`${state.failure.code}: ${state.failure.message}`} />
            <div style={mutedStyle}>
              {state.failure.previousAvailable
                ? "Previous result remains available."
                : "No result available yet."}
            </div>
            <div style={mutedStyle}>Action: review the input and try again.</div>
            {onRetry && (
              <button onClick={onRetry} style={actionButtonStyle} aria-label="Retry operation">
                Retry
              </button>
            )}
          </>
        )}
        {state.status === "cancelled" && (
          <>
            <DataRow label="Status" value="Cancelled" />
            <div style={mutedStyle}>
              {state.previousAvailable
                ? "Previous result remains available."
                : "No result available yet."}
            </div>
            {onDismiss && (
              <button onClick={onDismiss} style={actionButtonStyle} aria-label="Dismiss">
                Dismiss
              </button>
            )}
          </>
        )}
      </div>
    </div>
  );
}

function DataRow({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "var(--spacing-sm)" }}>
      <span style={{ fontSize: "var(--font-size-xs)", color: "var(--color-text-muted)" }}>{label}</span>
      <span style={{ fontSize: "var(--font-size-xs)", color: "var(--color-text-primary)", textAlign: "right" }}>{value}</span>
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
