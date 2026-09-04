import type { MeasurementMode, MeasurementState } from "../../measurement/types";
import { MEASUREMENT_MODES, MEASUREMENT_LABELS } from "../../measurement/types";
import { formatMeasurementValue } from "../../measurement/calculator";

interface MeasurementPanelProps {
  state: MeasurementState;
  mode: MeasurementMode;
  onModeChange: (mode: MeasurementMode) => void;
  onStartMeasurement: () => void;
  onClear: () => void;
  startDisabled?: boolean;
}

export function MeasurementPanel({ state, mode, onModeChange, onStartMeasurement, onClear, startDisabled = false }: MeasurementPanelProps) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--spacing-md)" }}>
      <div style={sectionLabelStyle}>Measurement</div>
      <div style={{ display: "flex", gap: "var(--spacing-xs)" }}>
        {MEASUREMENT_MODES.map((m) => (
          <button
            key={m}
            style={{
              ...buttonStyle,
              background: mode === m ? "var(--color-accent)" : "var(--color-bg-tertiary)",
              color: mode === m ? "#fff" : "var(--color-text-secondary)",
            }}
            onClick={() => onModeChange(m)}
            aria-label={`${MEASUREMENT_LABELS[m]} measurement`}
            title={`Select ${MEASUREMENT_LABELS[m]} measurement`}
          >
            {MEASUREMENT_LABELS[m]}
          </button>
        ))}
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: "var(--spacing-sm)" }}>
        {state.status === "empty" && (
          <>
            <StatusRow label="Mode" value={MEASUREMENT_LABELS[mode]} />
            <StatusRow label="Point A" value="Select point" muted />
            <StatusRow label="Point B" value="Select point" muted />
            <button
              style={startButtonStyle}
              onClick={onStartMeasurement}
              aria-label="Start measurement"
              title={startDisabled ? "Unavailable during flythrough playback" : "Start measurement"}
              disabled={startDisabled}
            >
              Start
            </button>
          </>
        )}
        {state.status === "selecting-first" && (
          <>
            <StatusRow label="Mode" value={MEASUREMENT_LABELS[mode]} />
            <StatusRow label="Point A" value="Click terrain..." accent />
            <StatusRow label="Point B" value="Select point" muted />
            <button style={cancelButtonStyle} onClick={onClear} aria-label="Cancel measurement">
              Cancel
            </button>
          </>
        )}
        {state.status === "selecting-second" && (
          <>
            <StatusRow label="Mode" value={MEASUREMENT_LABELS[mode]} />
            <StatusRow label="Point A" value="Selected" ok />
            <StatusRow label="Point B" value="Click terrain..." accent />
            <button style={cancelButtonStyle} onClick={onClear} aria-label="Cancel measurement">
              Cancel
            </button>
          </>
        )}
        {state.status === "completed" && (
          <>
            <StatusRow label="Mode" value={MEASUREMENT_LABELS[state.result.mode]} />
            <div style={{ height: 1, background: "var(--color-border-subtle)", margin: "var(--spacing-xs) 0" }} />
            <DataRow label="Value" value={formatMeasurementValue(mode, state.result)} />
            <DataRow label="Source" value="Fixture coordinate system" />
            <div style={{ height: 1, background: "var(--color-border-subtle)", margin: "var(--spacing-xs) 0" }} />
            <DataRow label="Horizontal" value={`${state.result.horizontalDistance.toFixed(3)} m`} />
            <DataRow label="Vertical" value={`${state.result.verticalDifference.toFixed(3)} m`} />
            <DataRow label="3D" value={`${state.result.distance3D.toFixed(3)} m`} />
            <button style={clearButtonStyle} onClick={onClear} aria-label="Clear measurement">
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

const buttonStyle: React.CSSProperties = {
  padding: "var(--spacing-xs) var(--spacing-sm)",
  fontSize: "var(--font-size-xs)",
  borderRadius: "var(--radius-sm)",
  background: "var(--color-bg-tertiary)",
  color: "var(--color-text-secondary)",
  border: "1px solid var(--color-border-subtle)",
  cursor: "pointer",
  lineHeight: 1.4,
  minWidth: 36,
};

const startButtonStyle: React.CSSProperties = {
  ...buttonStyle,
  background: "var(--color-accent)",
  color: "#fff",
  width: "100%",
};

const cancelButtonStyle: React.CSSProperties = {
  ...buttonStyle,
  background: "var(--color-bg-tertiary)",
  color: "var(--color-status-warn)",
  width: "100%",
};

const clearButtonStyle: React.CSSProperties = {
  ...buttonStyle,
  background: "var(--color-bg-tertiary)",
  color: "var(--color-text-secondary)",
  width: "100%",
};
