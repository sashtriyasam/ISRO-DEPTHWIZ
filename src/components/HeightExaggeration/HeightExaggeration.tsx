import type { ExaggerationLevel } from "../../display/types";
import { EXAGGERATION_LEVELS, EXAGGERATION_LABELS } from "../../display/types";

interface HeightExaggerationProps {
  current: ExaggerationLevel;
  onChange: (level: ExaggerationLevel) => void;
}

export function HeightExaggeration({ current, onChange }: HeightExaggerationProps) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--spacing-md)" }}>
      <div>
        <div style={sectionLabelStyle}>Height Exaggeration</div>
        <div style={{ display: "flex", gap: "var(--spacing-xs)" }}>
          {EXAGGERATION_LEVELS.map((level) => (
            <button
              key={level}
              style={{
                ...buttonStyle,
                background: current === level ? "var(--color-accent)" : "var(--color-bg-tertiary)",
                color: current === level ? "#fff" : "var(--color-text-secondary)",
              }}
              onClick={() => onChange(level)}
              aria-label={`${EXAGGERATION_LABELS[level]} height exaggeration`}
              title={`Set height exaggeration to ${EXAGGERATION_LABELS[level]}`}
            >
              {EXAGGERATION_LABELS[level]}
            </button>
          ))}
        </div>
      </div>
      <div>
        <div style={sectionLabelStyle}>Mode</div>
        <div style={{ fontSize: "var(--font-size-xs)", color: "var(--color-text-muted)", fontStyle: "italic" }}>
          Display only — does not modify scientific data
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
  minWidth: 36,
};
