import { MANUAL_CAMERA_MODES, type ManualCameraMode } from "../../camera/types";

interface CameraControlsProps {
  currentMode: ManualCameraMode | "trajectory" | null;
  onModeChange: (mode: ManualCameraMode) => void;
  onFrameScene: () => void;
  onReset: () => void;
  navigationLocked?: boolean;
}

const MODE_LABELS: Record<ManualCameraMode, string> = {
  orbit: "Orbit",
  "first-person": "First Person",
  aerial: "Aerial",
};

export function CameraControls({ currentMode, onModeChange, onFrameScene, onReset, navigationLocked = false }: CameraControlsProps) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--spacing-md)" }}>
      <div>
        <div style={sectionLabelStyle}>Camera</div>
        <div style={{ display: "flex", gap: "var(--spacing-xs)", flexWrap: "wrap" }}>
          {MANUAL_CAMERA_MODES.map((mode) => {
            const active = currentMode === mode;
            return (
              <button
                key={mode}
                style={{
                  ...buttonStyle,
                  background: active ? "var(--color-accent)" : "var(--color-bg-tertiary)",
                  color: active ? "#fff" : "var(--color-text-secondary)",
                }}
                aria-label={`${MODE_LABELS[mode]} camera mode`}
                aria-pressed={active}
                title={`${MODE_LABELS[mode]} mode${active ? " (active)" : ""}`}
                onClick={() => onModeChange(mode)}
                disabled={navigationLocked}
              >
                {MODE_LABELS[mode]}
              </button>
            );
          })}
        </div>
        {currentMode === "first-person" && (
          <div style={{ marginTop: "var(--spacing-xs)", fontSize: "var(--font-size-xs)", color: "var(--color-text-muted)", lineHeight: 1.6 }}>
            <div>W A S D — Move · Q / E — Down / Up · Shift — Boost</div>
            <div>Drag — Look · Esc — Exit to Orbit</div>
            <div>Terrain picking is paused in First Person.</div>
          </div>
        )}
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
