import type { SceneArtifact } from "../../types/scene";
import type { ArtifactState } from "../../artifact/types";

interface SceneInfoProps {
  artifact: SceneArtifact | null;
  state: ArtifactState;
  sourceLabel: string;
}

export function SceneInfo({ artifact, state, sourceLabel }: SceneInfoProps) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--spacing-md)" }}>
      <div>
        <div style={sectionLabelStyle}>Source</div>
        <div style={{ fontSize: "var(--font-size-sm)", color: "var(--color-text-secondary)" }}>
          {sourceLabel}
        </div>
      </div>
      <div>
        <div style={sectionLabelStyle}>Artifact</div>
        <div style={{ display: "flex", alignItems: "center", gap: "var(--spacing-sm)" }}>
          <div style={{
            width: 6,
            height: 6,
            borderRadius: "50%",
            background: state === "ready" ? "var(--color-status-ok)"
              : state === "loading" ? "var(--color-status-warn)"
              : state === "error" ? "var(--color-status-error)"
              : "var(--color-text-muted)",
          }} />
          <span style={{ fontSize: "var(--font-size-sm)", color: "var(--color-text-secondary)", textTransform: "capitalize" }}>
            {state}
          </span>
        </div>
      </div>
      {artifact && (
        <>
          <div>
            <div style={sectionLabelStyle}>Label</div>
            <div style={{ fontSize: "var(--font-size-sm)", color: "var(--color-text-secondary)" }}>
              {artifact.label}
            </div>
          </div>
          {artifact.metadata.backend && (
            <div>
              <div style={sectionLabelStyle}>Product</div>
              <div style={{ fontSize: "var(--font-size-sm)", color: "var(--color-text-secondary)" }}>
                {productLabel(artifact.metadata.backend.elevation_semantics)}
                {" · "}
                {artifact.metadata.backend.depth_scale === "metric" ? "meters" : "relative units"}
              </div>
              <div style={{ fontSize: "var(--font-size-xs)", color: "var(--color-text-muted)" }}>
                {artifact.metadata.backend.model_name}
                {artifact.metadata.backend.calibration_reference
                  ? ` · ref ${artifact.metadata.backend.calibration_reference}`
                  : ""}
              </div>
            </div>
          )}
          <div>
            <div style={sectionLabelStyle}>Geometry</div>
            <div style={{ fontSize: "var(--font-size-sm)", color: "var(--color-text-secondary)" }}>
              {artifact.mesh.vertexCount} vertices, {artifact.mesh.indexCount / 3} triangles
            </div>
          </div>
          {artifact.elevation && (
            <div>
              <div style={sectionLabelStyle}>Elevation Grid</div>
              <div style={{ fontSize: "var(--font-size-sm)", color: "var(--color-text-secondary)" }}>
                {artifact.elevation.width}x{artifact.elevation.height} ({artifact.elevation.cellSize}m cells)
              </div>
            </div>
          )}
          {artifact.metadata.bounds && (
            <div>
              <div style={sectionLabelStyle}>Display Bounds</div>
              <div style={{ fontSize: "var(--font-size-sm)", color: "var(--color-text-secondary)", fontFamily: "var(--font-mono)", lineHeight: 1.6 }}>
                X: [{artifact.metadata.bounds.minX.toFixed(1)}, {artifact.metadata.bounds.maxX.toFixed(1)}]<br />
                Y: [{artifact.metadata.bounds.minY.toFixed(1)}, {artifact.metadata.bounds.maxY.toFixed(1)}]<br />
                Z: [{artifact.metadata.bounds.minZ.toFixed(1)}, {artifact.metadata.bounds.maxZ.toFixed(1)}]
              </div>
            </div>
          )}
          <div>
            <div style={sectionLabelStyle}>Note</div>
            <div style={{ fontSize: "var(--font-size-xs)", color: "var(--color-text-muted)", fontStyle: "italic" }}>
              Synthetic development data — not scientific output
            </div>
          </div>
        </>
      )}
    </div>
  );
}

function productLabel(semantics: string): string {
  switch (semantics) {
    case "absolute_elevation_dsm":
      return "DSM";
    case "height_agl_ndsm":
      return "AGL";
    case "relative_surface_rdsm":
      return "Relative surface";
    case "relative_depth":
      return "Relative depth";
    default:
      return semantics;
  }
}

const sectionLabelStyle: React.CSSProperties = {
  fontSize: "var(--font-size-xs)",
  color: "var(--color-text-muted)",
  textTransform: "uppercase",
  letterSpacing: "0.05em",
  marginBottom: "var(--spacing-sm)",
};
