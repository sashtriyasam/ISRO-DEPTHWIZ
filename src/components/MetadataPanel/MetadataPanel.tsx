import { useState } from "react";
import type { SceneArtifact } from "../../types/scene";
import type { LayerId } from "../../layers/types";
import { describeArtifact } from "../../metadata/metadata";

interface MetadataPanelProps {
  artifact: SceneArtifact | null;
  activeLayerId: LayerId;
}

function ExportDsmButton({ exportPath }: { exportPath: string }) {
  const [status, setStatus] = useState<string | null>(null);
  const host = typeof window !== "undefined" ? window.depthwizard : undefined;
  if (!host?.saveStagedFile) return null;
  const onExport = async () => {
    setStatus("Choosing destination…");
    const result = await host.saveStagedFile!({ path: exportPath, defaultName: "dsm.tif" });
    if ("error" in result) setStatus(result.error);
    else setStatus(result.saved ? `Saved to ${result.path}` : null);
  };
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--spacing-xs)" }}>
      <button onClick={() => void onExport()} style={exportButtonStyle}>
        Export DSM (GeoTIFF)
      </button>
      {status && <div style={{ fontSize: "var(--font-size-xs)", color: "var(--color-text-muted)" }}>{status}</div>}
    </div>
  );
}

export function MetadataPanel({ artifact, activeLayerId }: MetadataPanelProps) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--spacing-md)" }}>
      {artifact?.metadata.exportPath && <ExportDsmButton exportPath={artifact.metadata.exportPath} />}
      <div style={sectionLabelStyle}>Metadata</div>
      {!artifact && (
        <div style={mutedStyle}>No artifact loaded. Metadata appears after terrain generation.</div>
      )}
      {artifact?.metadata.warnings?.map((warning) => (
        <div key={warning} role="alert" style={warningStyle}>
          {warning}
        </div>
      ))}
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

const warningStyle: React.CSSProperties = {
  fontSize: "var(--font-size-xs)",
  color: "var(--color-status-warning, var(--color-status-error))",
  border: "1px solid var(--color-border-subtle)",
  borderRadius: "var(--radius-sm)",
  padding: "var(--spacing-xs) var(--spacing-sm)",
};

const exportButtonStyle: React.CSSProperties = {
  padding: "var(--spacing-xs) var(--spacing-sm)",
  fontSize: "var(--font-size-xs)",
  borderRadius: "var(--radius-sm)",
  background: "var(--color-bg-secondary)",
  color: "var(--color-text-primary)",
  border: "1px solid var(--color-border-subtle)",
  cursor: "pointer",
};
