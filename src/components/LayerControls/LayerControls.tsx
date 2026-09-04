import type { LayerId, LayerState } from "../../layers/types";

interface LayerControlsProps {
  layerState: LayerState;
  onLayerSelect: (layerId: LayerId) => void;
}

export function LayerControls({ layerState, onLayerSelect }: LayerControlsProps) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--spacing-md)" }}>
      <div>
        <div style={sectionLabelStyle}>Layers</div>
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--spacing-xs)" }}>
          {layerState.layers.map((layer) => (
            <button
              key={layer.id}
              style={{
                ...layerButtonStyle,
                background: layer.enabled ? "var(--color-accent)" : "var(--color-bg-tertiary)",
                color: layer.enabled ? "#fff" : layer.available ? "var(--color-text-secondary)" : "var(--color-text-muted)",
                opacity: layer.available ? 1 : 0.5,
                cursor: layer.available ? "pointer" : "not-allowed",
              }}
              onClick={() => layer.available && onLayerSelect(layer.id)}
              disabled={!layer.available}
              aria-label={`${layer.label} layer${layer.available ? "" : " (not available)"}`}
              title={layer.available ? layer.description : `${layer.label} — not available in current fixture`}
            >
              <span style={{ display: "flex", alignItems: "center", gap: "var(--spacing-sm)" }}>
                <span style={{
                  width: 8,
                  height: 8,
                  borderRadius: "50%",
                  background: layer.enabled ? "#fff" : layer.available ? "var(--color-text-muted)" : "var(--color-border)",
                  flexShrink: 0,
                }} />
                {layer.label}
              </span>
              {!layer.available && (
                <span style={{ fontSize: "var(--font-size-xs)", opacity: 0.7 }}>N/A</span>
              )}
            </button>
          ))}
        </div>
      </div>
      <div>
        <div style={sectionLabelStyle}>Active Layer</div>
        <div style={{ fontSize: "var(--font-size-sm)", color: "var(--color-text-secondary)" }}>
          {layerState.layers.find((l) => l.id === layerState.activeLayerId)?.label ?? "None"}
        </div>
      </div>
    </div>
  );
}

const sectionLabelStyle: React.CSSProperties = {
  fontSize: "var(--font-size-xs)",
  color: "var(--color-text-muted)",
  textTransform: "uppercase",
  letterSpacing: "0.05em",
  marginBottom: "var(--spacing-sm)",
};

const layerButtonStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  justifyContent: "space-between",
  padding: "var(--spacing-xs) var(--spacing-sm)",
  fontSize: "var(--font-size-xs)",
  borderRadius: "var(--radius-sm)",
  border: "1px solid var(--color-border-subtle)",
  textAlign: "left",
  lineHeight: 1.4,
};
