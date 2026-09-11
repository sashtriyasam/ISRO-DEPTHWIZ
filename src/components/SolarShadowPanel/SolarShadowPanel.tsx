import { useState, useCallback, useEffect, useRef } from "react";
import { BackendBridge, type SolarAnalysisResult } from "../../backend/bridge";
import "./SolarShadowPanel.css";
export interface SolarConfig {
  sun_elevation_deg?: number;
  sun_azimuth_deg?: number;
  min_shadow_area_px?: number;
  gsd_override?: number;
}

export interface SolarConstraint {
  height_m: number;
  quality: string;
  assumptions: string[];
  method: string;
  source_input_id: string;
}


export interface SolarShadowPanelProps {
  inputPath?: string;
}

export function SolarShadowPanel({ inputPath = "" }: SolarShadowPanelProps) {
  const [sunElevation, setSunElevation] = useState("45");
  const [sunAzimuth, setSunAzimuth] = useState("180");
  const [gsdOverride, setGsdOverride] = useState("");
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<SolarAnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const bridgeRef = useRef<BackendBridge | null>(null);

  useEffect(() => {
    bridgeRef.current = new BackendBridge();
  }, []);

  const handleRun = useCallback(async () => {
    if (!inputPath) {
      setError("No input file selected");
      return;
    }
    const bridge = bridgeRef.current;
    if (!bridge || !bridge.hostCapabilities.processSpawning) {
      setError("Solar analysis requires a desktop host with process spawning");
      return;
    }
    setLoading(true);
    setError(null);
    setResults(null);
    try {
      const result: SolarAnalysisResult = await bridge.executeSolar(inputPath, {
        sunElevationDeg: parseFloat(sunElevation) || undefined,
        sunAzimuthDeg: parseFloat(sunAzimuth) || undefined,
        minShadowAreaPx: 20,
        gsdOverride: gsdOverride ? parseFloat(gsdOverride) : undefined,
      });
      setResults(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }, [inputPath, sunElevation, sunAzimuth, gsdOverride]);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--spacing-md)" }}>
      <div style={sectionLabelStyle}>Solar Shadow Analysis</div>

      <div style={mutedStyle}>
        Input: {inputPath || "No input selected"}
      </div>

      <div className="solar-field">
        <span className="solar-field-label">Sun elevation (°)</span>
        <input
          type="number"
          className="solar-input"
          value={sunElevation}
          onChange={(e) => setSunElevation(e.target.value)}
          disabled={loading}
          min="0"
          max="90"
          step="1"
        />
      </div>

      <div className="solar-field">
        <span className="solar-field-label">Sun azimuth (°)</span>
        <input
          type="number"
          className="solar-input"
          value={sunAzimuth}
          onChange={(e) => setSunAzimuth(e.target.value)}
          disabled={loading}
          min="0"
          max="360"
          step="1"
        />
      </div>

      <div className="solar-field">
        <span className="solar-field-label">GSD override (m/px, optional)</span>
        <input
          type="number"
          className="solar-input"
          value={gsdOverride}
          onChange={(e) => setGsdOverride(e.target.value)}
          disabled={loading}
          min="0"
          step="0.01"
          placeholder="Auto-detect"
        />
      </div>

      <button
        className="solar-button"
        onClick={handleRun}
        disabled={loading || !inputPath}
      >
        {loading ? "Analyzing…" : "Run Solar Analysis"}
      </button>

      {error && <div className="solar-error" role="alert">{error}</div>}

      {results && (
        <div className="solar-results">
          <div className="solar-result-title">Results</div>
          <div className="solar-result-row">
            <span className="solar-result-label">Shadows detected</span>
            <span className="solar-result-value">{results.count}</span>
          </div>
          {results.refused_reason && (
            <div className="solar-result-item">
              <span className="solar-result-label">Refused reason</span>
              <span className="solar-result-value">{results.refused_reason}</span>
            </div>
          )}
          {results.constraints.map((c, idx) => (
            <div key={idx} className="solar-result-item">
              <div className="solar-result-row">
                <span className="solar-result-label">Height constraint {idx + 1}</span>
                <span className="solar-result-value">{c.height_m.toFixed(2)} m</span>
              </div>
              <div className="solar-result-row">
                <span className="solar-result-label">Quality</span>
                <span className="solar-result-value">{c.quality}</span>
              </div>
              <div className="solar-result-row">
                <span className="solar-result-label">Method</span>
                <span className="solar-result-value">{c.method}</span>
              </div>
              <div className="solar-result-row">
                <span className="solar-result-label">Assumptions</span>
                <span className="solar-result-value">{c.assumptions.join(", ")}</span>
              </div>
            </div>
          ))}
        </div>
      )}
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

const mutedStyle: React.CSSProperties = {
  fontSize: "var(--font-size-xs)",
  color: "var(--color-text-muted)",
  fontStyle: "italic",
};





