import type { CameraMode } from "../../camera/types";

interface CameraControlsProps {
  currentMode: CameraMode | null;
  onFrameScene: () => void;
  onReset: () => void;
}

export function CameraControls({ currentMode, onFrameScene, onReset }: CameraControlsProps) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--spacing-md)" }}>
      <div>
        <div style={sectionLabelStyle}>Camera</div>
        <div style={{ display: "flex", gap: "var(--spacing-xs)" }}>
          <button
            style={{
              ...buttonStyle,
              background: currentMode === "orbit" ? "var(--color-accent)" : "var(--color-bg-tertiary)",
              color: currentMode === "orbit" ? "#fff" : "var(--color-text-secondary)",
            }}
            aria-label="Orbit camera mode"
            title="Orbit mode (active)"
          >
            Orbit
          </button>
        </div>
      </div>
      <div style={{ display: "flex", gap: "var(--spacing-xs)" }}>
        <button
          style={buttonStyle}
          onClick={onFrameScene}
          aria-label="Frame scene"
          title="Frame the entire scene in view"
        >
          Frame Scene
        </button>
        <button
          style={buttonStyle}
          onClick={onReset}
          aria-label="Reset camera"
          title="Reset camera to initial position"
        >
          Reset
        </button>
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
