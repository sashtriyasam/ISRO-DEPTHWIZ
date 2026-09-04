import type { SceneArtifact } from "../../types/scene";
import type { LayerId } from "../../layers/types";
import { describeArtifact } from "../../metadata/metadata";

interface MetadataPanelProps {
  artifact: SceneArtifact | null;
  activeLayerId: LayerId;
}

export function MetadataPanel({ artifact, activeLayerId }: MetadataPanelProps) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--spacing-md)" }}>
      <div style={sectionLabelStyle}>Metadata</div>
      {!artifact && (
        <div style={mutedStyle}>No artifact loaded. Metadata appears after terrain generation.</div>
      )}
      {artifact &&
        describeArtifact(artifact, activeLayerId).map((section, index) => (
          <details key={section.id} open={index === 0} style={detailsStyle}>
            <summary style={summaryStyle}>{section.title}</summary>
            <div style={{ display: "flex", flexDirection: "column", gap: "var(--spacing-sm)", marginTop: "var(--spacing-sm)" }}>
              {section.rows.map((r) => (
                <div
                  key={r.label}
                  style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: "var(--spacing-sm)" }}
                >
                  <span style={{ fontSize: "var(--font-size-xs)", color: "var(--color-text-muted)" }}>
                    {r.label}
                  </span>
                  <span
                    style={{
                      fontSize: "var(--font-size-xs)",
                      color: "var(--color-text-primary)",
                      fontFamily: "var(--font-mono)",
                      textAlign: "right",
                      wordBreak: "break-all",
                    }}
                    title={r.title}
                  >
                    {r.value}
                  </span>
                </div>
              ))}
            </div>
          </details>
        ))}
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

const detailsStyle: React.CSSProperties = {
  border: "1px solid var(--color-border-subtle)",
  borderRadius: "var(--radius-sm)",
  padding: "var(--spacing-xs) var(--spacing-sm)",
};

const summaryStyle: React.CSSProperties = {
  fontSize: "var(--font-size-xs)",
  color: "var(--color-text-secondary)",
  cursor: "pointer",
};
