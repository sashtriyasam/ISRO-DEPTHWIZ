import { BackendBridge } from "../backend/bridge";
import type { BackendInspection } from "../backend/bridge";
import type { ArtifactLoadOptions } from "../artifact/types";
import {
  formatSupportedList,
  type ClientFile,
  type InputMetadata,
  type InputValidationError,
} from "./types";

export function suffixOf(filename: string): string {
  const base = filename.split(/[\\/]/).pop() ?? filename;
  const dot = base.lastIndexOf(".");
  if (dot <= 0) {
    return "";
  }
  return base.slice(dot).toLowerCase();
}

export function checkClientSide(
  file: ClientFile,
  supportedSuffixes: readonly string[]
): InputValidationError | null {
  if (file.size === 0 || file.bytes.length === 0) {
    return {
      code: "empty_file",
      message: "The selected file is empty.",
      action: "Choose another file.",
    };
  }
  const suffix = suffixOf(file.name);
  if (!supportedSuffixes.includes(suffix)) {
    return {
      code: "unsupported_format",
      message: `Unsupported input format${suffix ? ` (${suffix})` : ""}.`,
      reason: `Supported formats: ${formatSupportedList(supportedSuffixes)}.`,
      action: "Choose another file.",
    };
  }
  return null;
}

export function mapInspectionToMetadata(
  inspection: BackendInspection,
  filename: string
): InputMetadata {
  const details =
    inspection.spatial.kind === "present" ? inspection.spatial.details : undefined;
  return {
    filename,
    format: inspection.detected_format,
    width: inspection.width,
    height: inspection.height,
    bandCount: inspection.band_count,
    dtype: inspection.dtype,
    georeferencing: inspection.georeferencing,
    crs: details?.crs ?? null,
    gsd: details?.resolution_gsd ?? null,
    nodata: details?.nodata ?? null,
    sizeBytes: inspection.handle.file_size,
    checksum: inspection.handle.sha256,
  };
}

export class InputValidationFailed extends Error {
  readonly validationError: InputValidationError;

  constructor(validationError: InputValidationError) {
    super(validationError.message);
    this.name = "InputValidationFailed";
    this.validationError = validationError;
  }
}

export class InputValidationCancelled extends Error {
  constructor() {
    super("Input validation cancelled");
    this.name = "InputValidationCancelled";
  }
}

export interface ValidateInputOptions extends ArtifactLoadOptions {
  bridge?: BackendBridge;
  supportedSuffixes: readonly string[];
}

export interface ValidatedInput {
  metadata: InputMetadata;
  stagedPath: string;
  cleanup: () => Promise<void>;
}

function mapBackendErrorCode(code: string): InputValidationError["code"] {
  if (code === "unsupported_format") {
    return "unsupported_format";
  }
  if (code === "environment_unsupported") {
    return "environment_unsupported";
  }
  return "invalid_input";
}

export async function validateInputFile(
  file: ClientFile,
  options: ValidateInputOptions
): Promise<ValidatedInput> {
  const bridge = options.bridge ?? new BackendBridge();
  const clientError = checkClientSide(file, options.supportedSuffixes);
  if (clientError) {
    throw new InputValidationFailed(clientError);
  }

  let stagedPath = "";
  let cleanup: () => Promise<void> = async () => undefined;
  try {
    const staged = await bridge.stageInputBytes(file.bytes, file.name);
    stagedPath = staged.path;
    cleanup = staged.cleanup;
  } catch (err) {
    throw new InputValidationFailed({
      code: "backend_unavailable",
      message: "The selected file could not be handed to the backend.",
      reason: err instanceof Error ? err.message : String(err),
      action: "Check the backend setup and try again.",
    });
  }

  let inspection: BackendInspection | undefined;
  try {
    const result = await bridge.inspectInputFile(stagedPath, {
      signal: options.signal,
      onStage: options.onStage,
    });
    if (!result.valid) {
      const code = mapBackendErrorCode(result.error?.code ?? "invalid_input");
      throw new InputValidationFailed({
        code,
        message:
          code === "unsupported_format"
            ? "Unsupported input format."
            : code === "environment_unsupported"
              ? "This input needs a backend reader that is unavailable here."
              : "Input could not be read.",
        reason: result.error?.message,
        action: "Choose another file.",
      });
    }
    inspection = result.inspection;
  } catch (err) {
    await cleanup();
    if (err instanceof InputValidationFailed) {
      throw err;
    }
    if (options.signal?.aborted) {
      throw new InputValidationCancelled();
    }
    throw new InputValidationFailed({
      code: "backend_unavailable",
      message: "Backend validation did not complete.",
      reason: err instanceof Error ? err.message : String(err),
      action: "Check the backend setup and try again.",
    });
  }

  if (!inspection) {
    await cleanup();
    throw new InputValidationFailed({
      code: "invalid_input",
      message: "Input could not be read.",
      reason: "The backend returned no inspection result.",
      action: "Choose another file.",
    });
  }

  if (options.signal?.aborted) {
    await cleanup();
    throw new InputValidationCancelled();
  }

  return {
    metadata: mapInspectionToMetadata(inspection, file.name),
    stagedPath,
    cleanup,
  };
}

export async function fetchSupportedSuffixes(bridge?: BackendBridge): Promise<string[]> {
  const active = bridge ?? new BackendBridge();
  try {
    const capabilities = await active.getCapabilities();
    return [...capabilities.supportedSuffixes];
  } catch (err) {
    throw new InputValidationFailed({
      code: "capabilities_unavailable",
      message: "Supported input formats could not be loaded from the backend.",
      reason: err instanceof Error ? err.message : String(err),
      action: "Check the backend setup and try again.",
    });
  }
}
