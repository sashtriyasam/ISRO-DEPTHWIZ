import { useEffect, useState } from "react";
import "./IsroLoader.css";

export interface IsroLoaderProps {
  stageText?: string;
  sourceLabel?: string;
}

export function IsroLoader({ stageText = "GENERATING 3D TERRAIN MESH...", sourceLabel }: IsroLoaderProps) {
  const [telemetryAlt, setTelemetryAlt] = useState(540);
  const [telemetryLat, setTelemetryLat] = useState("13.0827° N");
  const [telemetryLon, setTelemetryLon] = useState("80.2707° E");

  useEffect(() => {
    const interval = setInterval(() => {
      setTelemetryAlt(540 + Math.floor(Math.random() * 5) - 2);
      const latVal = (13.0827 + (Math.random() - 0.5) * 0.002).toFixed(4);
      const lonVal = (80.2707 + (Math.random() - 0.5) * 0.002).toFixed(4);
      setTelemetryLat(`${latVal}° N`);
      setTelemetryLon(`${lonVal}° E`);
    }, 800);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="isro-loader-container" role="status" aria-label="ISRO Telemetry Processing">
      <div className="isro-radar-grid" />
      <div className="isro-radar-scanline" />

      <div className="isro-orbit-wrapper">
        <div className="isro-outer-ring" />
        <div className="isro-middle-ring" />
        <div className="isro-inner-ring" />
        <div className="isro-core-beacon">
          <svg
            className="isro-satellite-icon"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M13 2 3 14h9l-1 8 10-12h-9l1-8z" />
          </svg>
        </div>
      </div>

      <div className="isro-hud-card">
        <div className="isro-badge">
          <span className="isro-badge-dot" />
          ISRO SIH 26175 TELEMETRY
        </div>

        <div className="isro-stage-title">{stageText}</div>

        {sourceLabel && (
          <div style={{ fontSize: "var(--font-size-xs)", color: "var(--color-text-muted)" }}>
            Source: {sourceLabel}
          </div>
        )}

        <div className="isro-telemetry-text">
          LAT: {telemetryLat} | LON: {telemetryLon} | ALT: {telemetryAlt} KM
        </div>

        <div className="isro-progress-track">
          <div className="isro-progress-fill" style={{ width: "75%" }}>
            <div className="isro-progress-shimmer" />
          </div>
        </div>
      </div>
    </div>
  );
}
