import { useEffect, useRef, useState } from "react";
import type { ElevationProfile } from "../../profile/types";

interface ProfileChartProps {
  profile: ElevationProfile;
}

const PADDING = { top: 20, right: 20, bottom: 30, left: 50 };

export function ProfileChart({ profile }: ProfileChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ width: 300, height: 150 });

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width } = entry.contentRect;
        if (width > 0) {
          setSize({ width, height: Math.max(120, Math.min(180, width * 0.5)) });
        }
      }
    });
    observer.observe(container);
    return () => observer.disconnect();
  }, []);

  const { width, height } = size;
  const plotWidth = width - PADDING.left - PADDING.right;
  const plotHeight = height - PADDING.top - PADDING.bottom;

  const unitSuffix = profile.units === "meters" ? "m" : profile.units;
  const valueLabel = profile.elevationSemantics === "relative_depth"
    ? "Relative depth"
    : profile.elevationSemantics === "height_agl_ndsm"
      ? "Height"
      : "Elevation";

  if (profile.points.length === 0) return null;

  const minDist = 0;
  const maxDist = profile.totalDistance;
  const minElev = profile.minElevation;
  const maxElev = profile.maxElevation;
  const elevRange = maxElev - minElev || 1;

  function distToX(d: number): number {
    return PADDING.left + (d - minDist) / (maxDist - minDist || 1) * plotWidth;
  }

  function elevToY(e: number): number {
    return PADDING.top + plotHeight - ((e - minElev) / elevRange) * plotHeight;
  }

  const pathData = profile.points
    .map((p, i) => `${i === 0 ? "M" : "L"} ${distToX(p.cumulativeDistance).toFixed(2)} ${elevToY(p.elevation).toFixed(2)}`)
    .join(" ");

  const tickCount = 5;
  const distTicks = Array.from({ length: tickCount }, (_, i) => minDist + (i / (tickCount - 1)) * (maxDist - minDist));
  const elevTicks = Array.from({ length: tickCount }, (_, i) => minElev + (i / (tickCount - 1)) * elevRange);

  return (
    <div ref={containerRef} style={{ width: "100%" }}>
      <svg
        width={width}
        height={height}
        viewBox={`0 0 ${width} ${height}`}
        style={{ display: "block" }}
        role="img"
        aria-label={`${valueLabel} profile from point A to point B, path length ${profile.totalDistance.toFixed(2)}, minimum ${profile.minElevation.toFixed(2)}, maximum ${profile.maxElevation.toFixed(2)}, units ${unitSuffix}`}
      >
        <rect x={PADDING.left} y={PADDING.top} width={plotWidth} height={plotHeight} fill="var(--color-bg-tertiary)" rx={2} />

        {distTicks.map((d, i) => (
          <g key={`dist-${i}`}>
            <line x1={distToX(d)} y1={PADDING.top} x2={distToX(d)} y2={PADDING.top + plotHeight} stroke="var(--color-border-subtle)" strokeWidth={0.5} />
            <text x={distToX(d)} y={height - 5} textAnchor="middle" fill="var(--color-text-muted)" fontSize={9} fontFamily="var(--font-mono)">
              {d.toFixed(1)}
            </text>
          </g>
        ))}

        {elevTicks.map((e, i) => (
          <g key={`elev-${i}`}>
            <line x1={PADDING.left} y1={elevToY(e)} x2={PADDING.left + plotWidth} y2={elevToY(e)} stroke="var(--color-border-subtle)" strokeWidth={0.5} />
            <text x={PADDING.left - 5} y={elevToY(e) + 3} textAnchor="end" fill="var(--color-text-muted)" fontSize={9} fontFamily="var(--font-mono)">
              {e.toFixed(2)}
            </text>
          </g>
        ))}

        <path d={pathData} fill="none" stroke="var(--color-accent)" strokeWidth={1.5} strokeLinejoin="round" />

        <circle cx={distToX(0)} cy={elevToY(profile.points[0].elevation)} r={3} fill="#44aaff" />
        <circle cx={distToX(profile.totalDistance)} cy={elevToY(profile.points[profile.points.length - 1].elevation)} r={3} fill="#44ff88" />

        <text x={width / 2} y={height - 2} textAnchor="middle" fill="var(--color-text-muted)" fontSize={9} fontFamily="var(--font-mono)">
          Distance ({unitSuffix})
        </text>
        <text x={5} y={height / 2} textAnchor="middle" fill="var(--color-text-muted)" fontSize={9} fontFamily="var(--font-mono)" transform={`rotate(-90, 5, ${height / 2})`}>
          {valueLabel} ({unitSuffix})
        </text>
      </svg>
    </div>
  );
}
