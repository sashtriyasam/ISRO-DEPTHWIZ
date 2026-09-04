import { RENDERING_MODES, RENDERING_MODE_LABELS, type RenderingMode } from "../../layers/types";

interface RenderingControlsProps {
  currentMode: RenderingMode;
  onModeChange: (mode: RenderingMode) => void;
}

export function RenderingControls({ currentMode, onModeChange }: RenderingControlsProps) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--spacing-md)" }}>
      <div>
        <div style={sectionLabelStyle}>View</div>
        <div style={{ display: "flex", gap: "var(--spacing-xs)", flexWrap: "wrap" }}>
          {RENDERING_MODES.map((mode) => {
            const active = currentMode === mode;
            return (
              <button
                key={mode}
                style={{
                  ...buttonStyle,
                  background: active ? "var(--color-accent)" : "var(--color-bg-tertiary)",
                  color: active ? "#fff" : "var(--color-text-secondary)",
                }}
                aria-label={`${RENDERING_MODE_LABELS[mode]} rendering mode`}
                aria-pressed={active}
                title={`${RENDERING_MODE_LABELS[mode]} mode${active ? " (active)" : ""}`}
                onClick={() => onModeChange(mode)}
              >
                {RENDERING_MODE_LABELS[mode]}
              </button>
            );
          })}
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

const buttonStyle: React.CSSProperties = {
  padding: "var(--spacing-xs) var(--spacing-sm)",
  fontSize: "var(--font-size-xs)",
  borderRadius: "var(--radius-sm)",
  background: "var(--color-bg-tertiary)",
  color: "var(--color-text-secondary)",
  border: "1px solid var(--color-border-subtle)",
  cursor: "pointer",
  lineHeight: 1.4,
};
