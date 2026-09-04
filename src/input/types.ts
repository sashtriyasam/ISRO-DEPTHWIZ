export interface ClientFile {
  name: string;
  size: number;
  mimeType: string;
  bytes: Uint8Array;
}

export interface InputMetadata {
  filename: string;
  format: string;
  width: number;
  height: number;
  bandCount: number | null;
  dtype: string | null;
  georeferencing: string;
  crs: string | null;
  gsd: number | null;
  nodata: number | null;
  sizeBytes: number | null;
  checksum: string | null;
}

export type InputValidationCode =
  | "empty_file"
  | "unsupported_format"
  | "invalid_input"
  | "environment_unsupported"
  | "backend_unavailable"
  | "capabilities_unavailable";

export interface InputValidationError {
  code: InputValidationCode;
  message: string;
  reason?: string;
  action: string;
}

export type InputState =
  | { status: "empty" }
  | { status: "selected"; file: ClientFile }
  | { status: "validating"; file: ClientFile }
  | {
      status: "validated";
      file: ClientFile;
      metadata: InputMetadata;
      stagedPath: string;
      cleanup: () => Promise<void>;
    }
  | { status: "invalid"; file: ClientFile | null; error: InputValidationError };

export const SUPPORTED_FORMAT_LABELS: Record<string, string> = {
  ".png": "PNG",
  ".jpg": "JPG",
  ".jpeg": "JPEG",
  ".tif": "TIFF",
  ".tiff": "GeoTIFF",
};

export function formatSupportedList(suffixes: readonly string[]): string {
  return suffixes
    .map((s) => SUPPORTED_FORMAT_LABELS[s] ?? s.replace(/^\./, "").toUpperCase())
    .join(", ");
}
