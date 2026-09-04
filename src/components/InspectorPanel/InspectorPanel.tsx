import type { InspectionState } from "../../inspection/types";
import type { SceneMetadata } from "../../types/scene";

interface InspectorPanelProps {
  state: InspectionState;
  metadata?: SceneMetadata;
  onClear?: () => void;
}

function formatValue(v: number | undefined): string {
  if (v === undefined) return "—";
  return v.toFixed(3);
}

function getSemanticLabel(metadata: SceneMetadata | undefined): string {
  const semantics = metadata?.backend?.elevation_semantics;
  switch (semantics) {
    case "relative_depth":
      return "Relative Depth";
    case "relative_surface_rdsm":
      return "rDSM";
    case "height_agl_ndsm":
      return "AGL";
    case "absolute_elevation_dsm":
      return "Elevation";
    default:
      return "Value";
  }
}

function getUnitLabel(metadata: SceneMetadata | undefined): string {
  if (metadata?.backend?.depth_scale === "metric") return " m";
  return "";
}

export function InspectorPanel({ state, metadata, onClear }: InspectorPanelProps) {
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
  const semanticLabel = getSemanticLabel(metadata);
  const unitLabel = getUnitLabel(metadata);

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
        <DataRow label={semanticLabel} value={`${formatValue(result.scientific.elevation)}${unitLabel}`} />
        {result.scientific.rdsm !== undefined && (
          <DataRow label="rDSM" value={`${formatValue(result.scientific.rdsm)}${unitLabel}`} />
        )}
        {result.scientific.agl !== undefined && (
          <DataRow label="AGL" value={`${formatValue(result.scientific.agl)}${unitLabel}`} />
        )}
        {metadata?.CRS && (
          <DataRow label="CRS" value={metadata.CRS} />
        )}
        <div style={{ height: 1, background: "var(--color-border-subtle)", margin: "var(--spacing-xs) 0" }} />
        <div style={positionLabelStyle}>Display position (scene units)</div>
        <DataRow label="Display X" value={formatValue(result.position.x)} />
        <DataRow label="Display Y" value={formatValue(result.position.y)} />
        <DataRow label="Display Z" value={formatValue(result.position.z)} />
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

const positionLabelStyle: React.CSSProperties = {
  fontSize: "var(--font-size-xs)",
  color: "var(--color-text-muted)",
  fontStyle: "italic",
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
