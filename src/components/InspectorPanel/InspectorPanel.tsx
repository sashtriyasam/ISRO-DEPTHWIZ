import type { InspectionState } from "../../inspection/types";

interface InspectorPanelProps {
  state: InspectionState;
  onClear?: () => void;
}

function formatValue(v: number | undefined): string {
  if (v === undefined) return "—";
  return v.toFixed(3);
}

export function InspectorPanel({ state, onClear }: InspectorPanelProps) {
  if (state.status === "empty") {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: "var(--spacing-md)" }}>
        <div style={sectionLabelStyle}>Point Inspector</div>
        <div style={{ fontSize: "var(--font-size-xs)", color: "var(--color-text-muted)", fontStyle: "italic" }}>
          Click on the terrain to inspect scientific data at a point
        </div>
      </div>
    );
  }

  const { result } = state;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--spacing-md)" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div style={sectionLabelStyle}>Point Inspector</div>
        {onClear && (
          <button
            onClick={onClear}
            style={clearButtonStyle}
            title="Clear selection"
            aria-label="Clear selection"
          >
            Clear
          </button>
        )}
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: "var(--spacing-sm)" }}>
        <DataRow label="Elevation" value={`${formatValue(result.scientific.elevation)} m`} />
        {result.scientific.rdsm !== undefined && (
          <DataRow label="rDSM" value={`${formatValue(result.scientific.rdsm)} m`} />
        )}
        {result.scientific.agl !== undefined && (
          <DataRow label="AGL" value={`${formatValue(result.scientific.agl)} m`} />
        )}
        <div style={{ height: 1, background: "var(--color-border-subtle)", margin: "var(--spacing-xs) 0" }} />
        <DataRow label="Position X" value={`${formatValue(result.position.x)} m`} />
        <DataRow label="Position Y" value={`${formatValue(result.position.y)} m`} />
        <DataRow label="Position Z" value={`${formatValue(result.position.z)} m`} />
        <div style={{ height: 1, background: "var(--color-border-subtle)", margin: "var(--spacing-xs) 0" }} />
        <DataRow label="U" value={formatValue(result.uv.u)} />
        <DataRow label="V" value={formatValue(result.uv.v)} />
        <DataRow label="Grid Col" value={`${result.gridIndex.col}`} />
        <DataRow label="Grid Row" value={`${result.gridIndex.row}`} />
      </div>
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

const clearButtonStyle: React.CSSProperties = {
  padding: "var(--spacing-xs) var(--spacing-sm)",
  fontSize: "var(--font-size-xs)",
  borderRadius: "var(--radius-sm)",
  background: "var(--color-bg-tertiary)",
  color: "var(--color-text-secondary)",
  border: "1px solid var(--color-border-subtle)",
  cursor: "pointer",
  lineHeight: 1.4,
};
