import { useCallback, useRef, useState } from "react";
import { BackendBridge, type ValidationReport } from "../../backend/bridge";

export interface ValidationPanelProps {
  /** Staged product raster of the current run (dsm.tif or rdsm.tif). */
  productPath?: string;
  bridge?: BackendBridge;
}

const REFERENCE_SUFFIXES = [".tif", ".tiff"];

function readBytes(file: File): Promise<ArrayBuffer> {
  if (typeof file.arrayBuffer === "function") return file.arrayBuffer();
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as ArrayBuffer);
    reader.onerror = () => reject(reader.error ?? new Error("File read failed"));
    reader.readAsArrayBuffer(file);
  });
}

function fmt(value: number | null | undefined, digits = 2, unit = ""): string {
  return value === null || value === undefined ? "—" : `${value.toFixed(digits)}${unit}`;
}

/**
 * Validate the produced heights against a reference raster (LiDAR DSM, DEM).
 * Metric products report RMSE/MAE/bias/correlation in metres; relative
 * products report scale-free correlation only.
 */
export function ValidationPanel({ productPath, bridge }: ValidationPanelProps) {
  const bridgeRef = useRef<BackendBridge>(bridge ?? new BackendBridge());
  const [report, setReport] = useState<ValidationReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const onReference = useCallback(
    async (file: File) => {
      if (!productPath) return;
      const lower = file.name.toLowerCase();
      if (!REFERENCE_SUFFIXES.some((s) => lower.endsWith(s))) {
        setError("Reference must be a GeoTIFF height raster (LiDAR DSM or DEM).");
        return;
      }
      setBusy(true);
      setError(null);
      setReport(null);
      let cleanup: (() => Promise<void>) | undefined;
      try {
        const bytes = new Uint8Array(await readBytes(file));
        const staged = await bridgeRef.current.stageInputBytes(bytes, file.name);
        cleanup = staged.cleanup;
        setReport(await bridgeRef.current.executeValidate(productPath, staged.path));
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
      } finally {
        setBusy(false);
        if (cleanup) void cleanup();
      }
    },
    [productPath],
  );

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--spacing-sm)" }}>
      <div style={labelStyle}>Validate against reference</div>
      {!productPath ? (
        <div style={mutedStyle}>Generate terrain first; then attach a reference DSM/DEM.</div>
      ) : (
        <input
          type="file"
          accept={REFERENCE_SUFFIXES.join(",")}
          aria-label="Reference height raster"
          disabled={busy}
          onChange={(e) => {
            const picked = e.target.files?.[0];
            if (picked) void onReference(picked);
          }}
          style={{ fontSize: "var(--font-size-xs)" }}
        />
      )}
      {busy && <div style={mutedStyle}>Aligning reference and computing metrics…</div>}
      {error && (
        <div role="alert" style={errorStyle}>
          {error}
        </div>
      )}
      {report && (
        <table style={{ fontSize: "var(--font-size-xs)", borderCollapse: "collapse" }}>
          <tbody>
            <Row label="Coverage" value={fmt(report.coverage * 100, 1, " %")} />
            <Row label="RMSE" value={fmt(report.native.rmse, 2, " m")} />
            <Row label="MAE" value={fmt(report.native.mae, 2, " m")} />
            <Row label="Bias" value={fmt(report.native.bias, 2, " m")} />
            <Row label="Pearson r" value={fmt(report.native.pearson_r, 3)} />
            <Row label="Spearman ρ" value={fmt(report.native.spearman_rho, 3)} />
            {report.coarse && (
              <Row
                label={`RMSE @ ${report.coarse.block_m.toFixed(0)} m`}
                value={fmt(report.coarse.rmse, 2, " m")}
              />
            )}
          </tbody>
        </table>
      )}
      {report?.note && <div style={mutedStyle}>{report.note}</div>}
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <tr>
      <td style={{ color: "var(--color-text-muted)", paddingRight: "var(--spacing-sm)" }}>{label}</td>
      <td style={{ fontFamily: "var(--font-mono)", textAlign: "right" }}>{value}</td>
    </tr>
  );
}

const labelStyle: React.CSSProperties = {
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
const errorStyle: React.CSSProperties = {
  fontSize: "var(--font-size-xs)",
  color: "var(--color-status-error)",
};
