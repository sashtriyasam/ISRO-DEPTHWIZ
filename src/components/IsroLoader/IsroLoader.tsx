import { useEffect, useState } from "react";
import { ALL_STAGES, type ProcessingStage } from "../../processing/types";
import "./IsroLoader.css";

export interface IsroLoaderProps {
  stageText?: string;
  sourceLabel?: string;
  stage?: ProcessingStage;
  completedStages?: readonly ProcessingStage[];
}

/** Number of processing stages — used to derive real progress %. */
const TOTAL_STAGES = ALL_STAGES.length;

export function IsroLoader({
  stageText = "GENERATING 3D TERRAIN MESH...",
  sourceLabel,
  stage,
  completedStages = [],
}: IsroLoaderProps) {
  // ── Simulated telemetry (decorative only — hidden from assistive tech) ──────
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

  // ── Real progress % derived from completed stages ─────────────────────────
  const stageIndex = stage ? ALL_STAGES.indexOf(stage) : -1;
  // Count the current stage as in-progress (add 0.5) so the bar visibly moves.
  const done = completedStages.length;
  const inProgress = stageIndex >= 0 && !completedStages.includes(stage!) ? 0.5 : 0;
  const rawPct = ((done + inProgress) / TOTAL_STAGES) * 100;
  // Clamp between 5 % (always some fill) and 95 % (never fake "done").
  const progressPct = Math.min(95, Math.max(5, rawPct));

  // Track stage text changes via useEffect for screen reader live region announcements
  // avoiding inline ref mutation during render.
  const [announcedStage, setAnnouncedStage] = useState(stageText);

  useEffect(() => {
    setAnnouncedStage(stageText);
  }, [stageText]);

  return (
    <div
      className="isro-loader-container"
      role="status"
      aria-label="Processing — please wait"
    >
      {/* Only announce stage changes to screen readers, not telemetry updates */}
      <div className="isro-sr-live" aria-live="polite" aria-atomic="true">
        {announcedStage}
      </div>

      <div className="isro-radar-grid" aria-hidden="true" />
      <div className="isro-radar-scanline" aria-hidden="true" />

      <div className="isro-orbit-wrapper" aria-hidden="true">
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
          <span className="isro-badge-dot" aria-hidden="true" />
          ISRO SIH 26175 TELEMETRY
        </div>

        <div className="isro-stage-title">{stageText}</div>

        {sourceLabel && (
          <div className="isro-source-label">
            Source: {sourceLabel}
          </div>
        )}

        {/* Telemetry is aria-hidden: it's decorative simulation, not real data */}
        <div className="isro-telemetry-text" aria-hidden="true">
          LAT: {telemetryLat} | LON: {telemetryLon} | ALT: {telemetryAlt} KM
        </div>

        <div
          className="isro-progress-track"
          role="progressbar"
          aria-valuenow={Math.round(progressPct)}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label="Processing progress"
        >
          <div
            className="isro-progress-fill"
            style={{ width: `${progressPct}%` }}
          >
            <div className="isro-progress-shimmer" />
          </div>
        </div>
      </div>
    </div>
  );
}
