import { useCallback, useEffect, useRef, useState } from "react";
import { BackendBridge } from "../../backend/bridge";
import { FixtureSource } from "../../artifact/FixtureSource";
import type { ArtifactSource } from "../../artifact/types";
import {
  fetchSupportedSuffixes,
  validateInputFile,
  InputValidationFailed,
  InputValidationCancelled,
} from "../../input/validation";
import { formatSupportedList } from "../../input/types";
import { FileInputSource } from "../../input/source";
import type {
  ClientFile,
  InputMetadata,
  InputState,
  InputValidationError,
} from "../../input/types";

interface InputWorkspaceProps {
  bridge?: BackendBridge;
  processingRunning: boolean;
  onGenerate: (source: ArtifactSource) => void;
}

function readFileBytes(file: File): Promise<ArrayBuffer> {
  if (typeof file.arrayBuffer === "function") {
    return file.arrayBuffer();
  }
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as ArrayBuffer);
    reader.onerror = () => reject(reader.error ?? new Error("File read failed"));
    reader.readAsArrayBuffer(file);
  });
}

async function toClientFile(file: File): Promise<ClientFile> {
  const buffer = await readFileBytes(file);
  return {
    name: file.name,
    size: file.size,
    mimeType: file.type,
    bytes: new Uint8Array(buffer),
  };
}

const FIXTURE_METADATA: InputMetadata = {
  filename: "Built-in development fixture",
  format: "development fixture",
  width: 8,
  height: 8,
  bandCount: null,
  dtype: null,
  georeferencing: "synthetic fixture (not scientific output)",
  crs: null,
  gsd: null,
  nodata: null,
  sizeBytes: null,
  checksum: null,
};

export function InputWorkspace({ bridge, processingRunning, onGenerate }: InputWorkspaceProps) {
  const bridgeRef = useRef<BackendBridge | null>(null);
  if (!bridgeRef.current) {
    bridgeRef.current = bridge ?? new BackendBridge();
  }
  const [suffixes, setSuffixes] = useState<string[] | null>(null);
  const [capabilitiesError, setCapabilitiesError] = useState<string | null>(null);
  const [inputState, setInputState] = useState<InputState>({ status: "empty" });
  const [dragActive, setDragActive] = useState(false);
  const validationRef = useRef<AbortController | null>(null);
  const stagedRef = useRef<(() => Promise<void>) | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const loadCapabilities = useCallback(async () => {
    setCapabilitiesError(null);
    try {
      const list = await fetchSupportedSuffixes(bridgeRef.current!);
      setSuffixes(list);
    } catch (err) {
      setCapabilitiesError(err instanceof Error ? err.message : String(err));
      setSuffixes(null);
    }
  }, []);

  useEffect(() => {
    void loadCapabilities();
  }, [loadCapabilities]);

  useEffect(() => {
    const prevent = (e: DragEvent) => e.preventDefault();
    window.addEventListener("dragover", prevent);
    window.addEventListener("drop", prevent);
    return () => {
      window.removeEventListener("dragover", prevent);
      window.removeEventListener("drop", prevent);
      validationRef.current?.abort();
      const cleanup = stagedRef.current;
      stagedRef.current = null;
      if (cleanup) {
        void cleanup();
      }
    };
  }, []);

  const releaseStaged = useCallback(async () => {
    const cleanup = stagedRef.current;
    stagedRef.current = null;
    if (cleanup) {
      await cleanup();
    }
  }, []);

  const runValidation = useCallback(
    async (file: ClientFile, allowed: readonly string[]) => {
      validationRef.current?.abort();
      const controller = new AbortController();
      validationRef.current = controller;
      setInputState({ status: "validating", file });
      try {
        const result = await validateInputFile(file, {
          bridge: bridgeRef.current!,
          supportedSuffixes: allowed,
          signal: controller.signal,
        });
        if (validationRef.current !== controller) {
          await result.cleanup();
          return;
        }
        validationRef.current = null;
        stagedRef.current = result.cleanup;
        setInputState({
          status: "validated",
          file,
          metadata: result.metadata,
          stagedPath: result.stagedPath,
          cleanup: result.cleanup,
        });
      } catch (err) {
        if (validationRef.current !== controller) {
          return;
        }
        validationRef.current = null;
        if (err instanceof InputValidationCancelled || controller.signal.aborted) {
          setInputState({ status: "selected", file });
          return;
        }
        const error: InputValidationError =
          err instanceof InputValidationFailed
            ? err.validationError
            : {
                code: "invalid_input" as const,
                message: "Input could not be read.",
                reason: err instanceof Error ? err.message : String(err),
                action: "Choose another file.",
              };
        setInputState({ status: "invalid", file, error });
      }
    },
    []
  );

  const handleFiles = useCallback(
    async (files: FileList | File[]) => {
      const first = files[0];
      if (!first || !suffixes || processingRunning) {
        return;
      }
      await releaseStaged();
      const clientFile = await toClientFile(first);
      await runValidation(clientFile, suffixes);
    },
    [suffixes, releaseStaged, runValidation, processingRunning]
  );

  const handleUseFixture = useCallback(async () => {
    if (processingRunning) {
      return;
    }
    validationRef.current?.abort();
    validationRef.current = null;
    await releaseStaged();
    setInputState({
      status: "validated",
      file: { name: "Built-in development fixture", size: 0, mimeType: "", bytes: new Uint8Array(0) },
      metadata: FIXTURE_METADATA,
      stagedPath: "",
      cleanup: async () => undefined,
    });
  }, [releaseStaged, processingRunning]);

  const handleClear = useCallback(async () => {
    if (processingRunning) {
      return;
    }
    validationRef.current?.abort();
    validationRef.current = null;
    await releaseStaged();
    setInputState({ status: "empty" });
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  }, [releaseStaged, processingRunning]);

  const handleGenerate = useCallback(() => {
    if (inputState.status !== "validated" || processingRunning) {
      return;
    }
    if (inputState.stagedPath) {
      const source = new FileInputSource({
        stagedPath: inputState.stagedPath,
        metadata: inputState.metadata,
      });
      onGenerate(source);
    } else {
      onGenerate(new FixtureSource());
    }
  }, [inputState, processingRunning, onGenerate]);

  const acceptAttr = suffixes ? suffixes.join(",") : undefined;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--spacing-md)" }}>
      <div style={sectionLabelStyle}>Input</div>

      {capabilitiesError && (
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--spacing-xs)" }}>
          <div style={errorStyle}>Supported formats could not be loaded: {capabilitiesError}</div>
          <button onClick={() => void loadCapabilities()} style={actionButtonStyle}>
            Retry
          </button>
        </div>
      )}

      <input
        ref={fileInputRef}
        type="file"
        accept={acceptAttr}
        disabled={!suffixes || processingRunning}
        onChange={(e) => {
          if (e.target.files && e.target.files.length > 0) {
            void handleFiles(e.target.files);
          }
        }}
        aria-label="Open input file"
        style={{ fontSize: "var(--font-size-xs)" }}
      />

      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragActive(true);
        }}
        onDragLeave={() => setDragActive(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragActive(false);
          if (e.dataTransfer.files.length > 0) {
            void handleFiles(e.dataTransfer.files);
          }
        }}
        style={{
          ...dropZoneStyle,
          borderColor: dragActive ? "var(--color-text-secondary)" : "var(--color-border-subtle)",
        }}
      >
        Drop an input file here, or use the file control above.
      </div>

      <div style={{ display: "flex", gap: "var(--spacing-xs)" }}>
        <button onClick={() => void handleUseFixture()} style={actionButtonStyle} disabled={processingRunning}>
          Use development fixture
        </button>
        {(inputState.status === "validated" || inputState.status === "invalid") && (
          <button onClick={() => void handleClear()} style={actionButtonStyle} disabled={processingRunning}>
            Clear
          </button>
        )}
      </div>

      {suffixes && (
        <div style={mutedStyle}>Supported: {formatSupportedList(suffixes)}</div>
      )}

      {inputState.status === "validating" && (
        <div style={mutedStyle}>Validating {inputState.file.name} with the backend…</div>
      )}

      {inputState.status === "invalid" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--spacing-xs)" }} role="alert">
          <div style={errorStyle}>{inputState.error.message}</div>
          {inputState.error.reason && <div style={mutedStyle}>{inputState.error.reason}</div>}
          <div style={mutedStyle}>{inputState.error.action}</div>
        </div>
      )}

      {inputState.status === "validated" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--spacing-sm)" }}>
          <DataRow label="Status" value="Validated" />
          <DataRow label="File" value={inputState.metadata.filename} />
          <DataRow label="Format" value={inputState.metadata.format} />
          <DataRow
            label="Dimensions"
            value={`${inputState.metadata.width}×${inputState.metadata.height}`}
          />
          <DataRow
            label="Bands"
            value={inputState.metadata.bandCount === null ? "—" : String(inputState.metadata.bandCount)}
          />
          <DataRow label="Type" value={inputState.metadata.dtype ?? "—"} />
          <DataRow label="Reference" value={inputState.metadata.georeferencing} />
          <DataRow label="CRS" value={inputState.metadata.crs ?? "Not available"} />
          <DataRow
            label="GSD"
            value={inputState.metadata.gsd === null ? "—" : String(inputState.metadata.gsd)}
          />
          <button
            onClick={handleGenerate}
            style={primaryButtonStyle}
            disabled={processingRunning}
            aria-label="Generate terrain"
          >
            {processingRunning ? "Processing…" : "Generate terrain"}
          </button>
        </div>
      )}
    </div>
  );
}

function DataRow({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "var(--spacing-sm)" }}>
      <span style={{ fontSize: "var(--font-size-xs)", color: "var(--color-text-muted)" }}>{label}</span>
      <span style={{ fontSize: "var(--font-size-xs)", color: "var(--color-text-primary)", textAlign: "right", wordBreak: "break-all" }}>{value}</span>
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

const errorStyle: React.CSSProperties = {
  fontSize: "var(--font-size-xs)",
  color: "var(--color-status-error)",
};

const actionButtonStyle: React.CSSProperties = {
  padding: "var(--spacing-xs) var(--spacing-sm)",
  fontSize: "var(--font-size-xs)",
  borderRadius: "var(--radius-sm)",
  background: "var(--color-bg-tertiary)",
  color: "var(--color-text-secondary)",
  border: "1px solid var(--color-border-subtle)",
  cursor: "pointer",
  lineHeight: 1.4,
};

const primaryButtonStyle: React.CSSProperties = {
  ...actionButtonStyle,
  background: "var(--color-bg-secondary)",
  color: "var(--color-text-primary)",
};

const dropZoneStyle: React.CSSProperties = {
  border: "1px dashed var(--color-border-subtle)",
  borderRadius: "var(--radius-sm)",
  padding: "var(--spacing-md)",
  fontSize: "var(--font-size-xs)",
  color: "var(--color-text-muted)",
  textAlign: "center",
};
