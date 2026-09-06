/**
 * SolarShadowPanel — Solar-shadow geometry height cues.
 *
 * Sends shadow observations to the Python backend and displays independent
 * height constraints. These are NOT calibration replacements and NOT automatic
 * ground truth.
 *
 * Owner: Aryan (UI/UX). Backend endpoint: POST /solar/analyze (Shivam).
 */
import { useState } from "react";

interface SolarConstraint {
  height_m: number;
  quality: string;
  assumptions: string[];
  method: string;
  source_input_id: string;
}

interface SolarAnalysisResult {
  constraints: SolarConstraint[];
  count: number;
  refused_reason: string | null;
}

interface SolarShadowPanelProps {
  inputPath: string | null;
  onAnalysisComplete?: (result: SolarAnalysisResult) => void;
}

export function SolarShadowPanel({ inputPath, onAnalysisComplete }: SolarShadowPanelProps) {
  const [autoAngles, setAutoAngles] = useState(true);
  const [elevation, setElevation] = useState<string>("");
  const [azimuth, setAzimuth] = useState<string>("");
  const [result, setResult] = useState<SolarAnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const canAnalyze = inputPath != null && (!autoAngles ? elevation !== "" && azimuth !== "" : true);

  async function handleAnalyze() {
    if (!inputPath) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const body: Record<string, unknown> = { input_path: inputPath };
      if (!autoAngles) {
        body.sun_elevation_deg = parseFloat(elevation);
        body.sun_azimuth_deg = parseFloat(azimuth);
      }
      const response = await fetch("/solar/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!response.ok) {
        const text = await response.text();
        throw new Error(`Server error ${response.status}: ${text}`);
      }
      const data: SolarAnalysisResult = await response.json();
      setResult(data);
      onAnalysisComplete?.(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={panelStyle}>
      <div style={headerStyle}>☀ Solar-Shadow Height Analysis</div>
      <div style={disclaimerStyle}>
        Independent height cues from shadow geometry — not calibration replacements.
        Sun angles must be provided or embedded in image metadata.
      </div>

      {!inputPath && (
        <div style={mutedStyle}>Load an image to enable shadow analysis.</div>
      )}

      {inputPath && (
        <>
          <label style={labelStyle}>
            <input
              type="checkbox"
              checked={autoAngles}
              onChange={(e) => setAutoAngles(e.target.checked)}
              style={{ marginRight: "var(--spacing-xs)" }}
            />
            Auto-resolve sun angles from image metadata
          </label>

          {!autoAngles && (
            <div style={{ display: "flex", gap: "var(--spacing-sm)", marginTop: "var(--spacing-sm)" }}>
              <div>
                <div style={fieldLabelStyle}>Solar Elevation (°)</div>
                <input
                  type="number"
                  min="0.1"
                  max="89.9"
                  step="0.1"
                  value={elevation}
                  onChange={(e) => setElevation(e.target.value)}
                  placeholder="e.g. 45.0"
                  style={inputStyle}
                />
              </div>
              <div>
                <div style={fieldLabelStyle}>Solar Azimuth (°)</div>
                <input
                  type="number"
                  min="0"
                  max="359.9"
                  step="0.1"
                  value={azimuth}
                  onChange={(e) => setAzimuth(e.target.value)}
                  placeholder="e.g. 180.0"
                  style={inputStyle}
                />
              </div>
            </div>
          )}

          <button
            style={{
              ...buttonStyle,
              opacity: canAnalyze && !loading ? 1 : 0.5,
              cursor: canAnalyze && !loading ? "pointer" : "not-allowed",
              marginTop: "var(--spacing-md)",
            }}
            disabled={!canAnalyze || loading}
            onClick={handleAnalyze}
          >
            {loading ? "Analyzing…" : "Analyze Shadows"}
          </button>
        </>
      )}

      {error && <div style={errorStyle}>{error}</div>}

      {result && (
        <div style={{ marginTop: "var(--spacing-md)" }}>
          {result.refused_reason ? (
            <div style={errorStyle}>Refused: {result.refused_reason}</div>
          ) : result.count === 0 ? (
            <div style={mutedStyle}>No clear shadow regions detected in this image.</div>
          ) : (
            <>
              <div style={sectionLabelStyle}>{result.count} shadow height cue{result.count !== 1 ? "s" : ""} found</div>
              {result.constraints.map((c, i) => (
                <div key={i} style={constraintStyle}>
                  <div style={{ fontWeight: 600 }}>{c.height_m.toFixed(1)} m</div>
                  <div style={mutedStyle}>Quality: {c.quality} · Method: {c.method}</div>
                  <div style={assumptionStyle}>
                    {c.assumptions.slice(0, 2).map((a, j) => (
                      <div key={j}>• {a}</div>
                    ))}
                  </div>
                </div>
              ))}
            </>
          )}
        </div>
      )}
    </div>
  );
}

const panelStyle: React.CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "var(--spacing-sm)",
  padding: "var(--spacing-md)",
};

const headerStyle: React.CSSProperties = {
  fontSize: "var(--font-size-sm)",
  fontWeight: 600,
  color: "var(--color-text-primary)",
};

const disclaimerStyle: React.CSSProperties = {
  fontSize: "var(--font-size-xs)",
  color: "var(--color-accent)",
  padding: "var(--spacing-xs) var(--spacing-sm)",
  background: "var(--color-bg-secondary)",
  borderRadius: "var(--radius-sm)",
  borderLeft: "3px solid var(--color-accent)",
};

const labelStyle: React.CSSProperties = {
  fontSize: "var(--font-size-xs)",
  color: "var(--color-text-secondary)",
  display: "flex",
  alignItems: "center",
  cursor: "pointer",
};

const fieldLabelStyle: React.CSSProperties = {
  fontSize: "var(--font-size-xs)",
  color: "var(--color-text-muted)",
  marginBottom: "var(--spacing-xs)",
};

const inputStyle: React.CSSProperties = {
  width: "120px",
  padding: "var(--spacing-xs)",
  fontSize: "var(--font-size-xs)",
  background: "var(--color-bg-tertiary)",
  color: "var(--color-text-primary)",
  border: "1px solid var(--color-border-subtle)",
  borderRadius: "var(--radius-sm)",
};

const buttonStyle: React.CSSProperties = {
  padding: "var(--spacing-xs) var(--spacing-sm)",
  fontSize: "var(--font-size-xs)",
  background: "var(--color-accent)",
  color: "#fff",
  border: "none",
  borderRadius: "var(--radius-sm)",
  fontWeight: 600,
};

const errorStyle: React.CSSProperties = {
  fontSize: "var(--font-size-xs)",
  color: "#ef4444",
  padding: "var(--spacing-xs)",
  background: "rgba(239,68,68,0.1)",
  borderRadius: "var(--radius-sm)",
};

const mutedStyle: React.CSSProperties = {
  fontSize: "var(--font-size-xs)",
  color: "var(--color-text-muted)",
};

const sectionLabelStyle: React.CSSProperties = {
  fontSize: "var(--font-size-xs)",
  color: "var(--color-text-muted)",
  textTransform: "uppercase",
  letterSpacing: "0.05em",
  marginBottom: "var(--spacing-xs)",
};

const constraintStyle: React.CSSProperties = {
  padding: "var(--spacing-xs) var(--spacing-sm)",
  background: "var(--color-bg-secondary)",
  borderRadius: "var(--radius-sm)",
  marginBottom: "var(--spacing-xs)",
  fontSize: "var(--font-size-xs)",
};

const assumptionStyle: React.CSSProperties = {
  color: "var(--color-text-muted)",
  fontSize: "10px",
  marginTop: "var(--spacing-xs)",
};
