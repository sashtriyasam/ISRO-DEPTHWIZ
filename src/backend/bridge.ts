import type { BackendDepthResult, BackendTerrainProduct } from "./types";
import { adaptBackendResult, type AdapterResult } from "./adapter";
import { adaptTerrainProduct } from "./meshAdapter";

export interface BridgeError {
  code: string;
  message: string;
  phase: "process" | "transport" | "validation" | "adapter";
}

export interface BridgeResult {
  success: boolean;
  artifact?: AdapterResult["artifact"];
  errors: BridgeError[];
  warnings: string[];
}

const BRIDGE_TIMEOUT_MS = 30_000;

function validateTransportShape(data: unknown): BackendDepthResult {
  if (typeof data !== "object" || data === null) {
    throw new Error("Transport data is not an object");
  }

  const obj = data as Record<string, unknown>;

  if (!obj.model_name || typeof obj.model_name !== "string") {
    throw new Error("Missing or invalid model_name");
  }

  if (!obj.output_resolution || typeof obj.output_resolution !== "object") {
    throw new Error("Missing or invalid output_resolution");
  }

  const res = obj.output_resolution as Record<string, unknown>;
  if (typeof res.width !== "number" || typeof res.height !== "number") {
    throw new Error("Invalid output_resolution dimensions");
  }

  if (!Array.isArray(obj.depth_values)) {
    throw new Error("Missing or invalid depth_values");
  }

  if (!obj.depth_scale || typeof obj.depth_scale !== "string") {
    throw new Error("Missing or invalid depth_scale");
  }

  if (!obj.elevation_semantics || typeof obj.elevation_semantics !== "string") {
    throw new Error("Missing or invalid elevation_semantics");
  }

  if (!obj.georeferencing || typeof obj.georeferencing !== "string") {
    throw new Error("Missing or invalid georeferencing");
  }

  if (!obj.spatial || typeof obj.spatial !== "object") {
    throw new Error("Missing or invalid spatial context");
  }

  return obj as unknown as BackendDepthResult;
}

function validateTerrainShape(data: unknown): BackendTerrainProduct {
  if (typeof data !== "object" || data === null) {
    throw new Error("Transport data is not an object");
  }
  const obj = data as Record<string, unknown>;
  if (obj.kind !== "terrain") {
    throw new Error(`Expected terrain product, got kind '${String(obj.kind)}'`);
  }
  if (!obj.dsm || typeof obj.dsm !== "object") {
    throw new Error("Missing or invalid dsm section");
  }
  if (!obj.mesh || typeof obj.mesh !== "object") {
    throw new Error("Missing or invalid mesh section");
  }
  if (!obj.depth_result || typeof obj.depth_result !== "object") {
    throw new Error("Missing or invalid depth_result section");
  }
  return obj as unknown as BackendTerrainProduct;
}

export interface BridgeExecutionHooks {
  onStage?: (stage: string) => void;
  signal?: AbortSignal;
}

export interface BackendBridgeOptions {
  pythonPath?: string;
  bridgeScript?: string;
  timeoutMs?: number;
}

export class OperationCancelledError extends Error {
  constructor() {
    super("Operation cancelled");
    this.name = "OperationCancelledError";
  }
}

export class BackendBridge {
  private pythonPath: string;
  private bridgeScript: string;
  private timeoutMs: number;
  private isNode: boolean;

  constructor(options: BackendBridgeOptions = {}) {
    this.pythonPath = options.pythonPath ?? "python";
    this.bridgeScript = options.bridgeScript ?? "scripts/backend_bridge.py";
    this.timeoutMs = options.timeoutMs ?? BRIDGE_TIMEOUT_MS;
    this.isNode = typeof process !== "undefined" && typeof process.versions !== "undefined" && typeof process.versions.node !== "undefined";
  }

  async executeSynthetic(width = 8, height = 8, hooks: BridgeExecutionHooks = {}): Promise<BridgeResult> {
    return this.execute(["--synthetic", String(width), String(height)], hooks);
  }

  async executeWithInput(inputPath: string, hooks: BridgeExecutionHooks = {}): Promise<BridgeResult> {
    return this.execute([inputPath], hooks);
  }

  async executeTerrain(width = 8, height = 8, hooks: BridgeExecutionHooks = {}): Promise<BridgeResult> {
    const errors: BridgeError[] = [];
    const warnings: string[] = [];

    if (!this.isNode) {
      errors.push({
        code: "BROWSER_ENVIRONMENT",
        message: "Backend bridge requires Node.js environment (Tauri/Electron)",
        phase: "process",
      });
      return { success: false, errors, warnings };
    }

    if (hooks.signal?.aborted) {
      errors.push({ code: "OPERATION_CANCELLED", message: "Operation cancelled", phase: "process" });
      return { success: false, errors, warnings };
    }

    try {
      const jsonData = await this.spawnPython(["--terrain", String(width), String(height)], hooks);
      let validated: BackendTerrainProduct;
      try {
        validated = validateTerrainShape(jsonData);
      } catch (err) {
        errors.push({
          code: "TRANSPORT_INVALID",
          message: err instanceof Error ? err.message : "Invalid terrain transport data",
          phase: "transport",
        });
        return { success: false, errors, warnings };
      }
      const adapterResult = adaptTerrainProduct(validated);
      if (!adapterResult.success) {
        for (const e of adapterResult.errors) {
          errors.push({ code: e.code, message: e.message, phase: "adapter" });
        }
        return { success: false, errors, warnings };
      }
      warnings.push(...adapterResult.warnings);
      return { success: true, artifact: adapterResult.artifact, errors: [], warnings };
    } catch (err) {
      return this.toProcessError(err);
    }
  }

  private async execute(args: string[], hooks: BridgeExecutionHooks = {}): Promise<BridgeResult> {
    const errors: BridgeError[] = [];
    const warnings: string[] = [];

    if (!this.isNode) {
      errors.push({
        code: "BROWSER_ENVIRONMENT",
        message: "Backend bridge requires Node.js environment (Tauri/Electron)",
        phase: "process",
      });
      return { success: false, errors, warnings };
    }

    if (hooks.signal?.aborted) {
      errors.push({ code: "OPERATION_CANCELLED", message: "Operation cancelled", phase: "process" });
      return { success: false, errors, warnings };
    }

    try {
      const jsonData = await this.spawnPython(args, hooks);
      return this.processTransportData(jsonData, errors, warnings);
    } catch (err) {
      return this.toProcessError(err);
    }
  }

  private toProcessError(err: unknown): BridgeResult {
    const errors: BridgeError[] = [];
    const warnings: string[] = [];

    if (err instanceof OperationCancelledError) {
      errors.push({ code: "OPERATION_CANCELLED", message: "Operation cancelled", phase: "process" });
      return { success: false, errors, warnings };
    }

    const message = err instanceof Error ? err.message : String(err);

    if (message.includes("ENOENT") || message.includes("spawn")) {
      errors.push({
        code: "BACKEND_UNAVAILABLE",
        message: "Python executable not found or not accessible",
        phase: "process",
      });
    } else if (message.includes("timeout")) {
      errors.push({
        code: "BACKEND_TIMEOUT",
        message: `Backend execution timed out after ${this.timeoutMs}ms`,
        phase: "process",
      });
    } else {
      errors.push({
        code: "BACKEND_ERROR",
        message,
        phase: "process",
      });
    }

    return { success: false, errors, warnings };
  }

  private async spawnPython(args: string[], hooks: BridgeExecutionHooks = {}): Promise<unknown> {
    const { spawn } = await import("child_process");

    return new Promise((resolve, reject) => {
      let stdout = "";
      let stderr = "";
      let killed = false;
      let settled = false;

      const proc = spawn(this.pythonPath, [this.bridgeScript, ...args], {
        stdio: ["ignore", "pipe", "pipe"],
        windowsHide: true,
      });

      const settle = (fn: () => void) => {
        if (!settled) {
          settled = true;
          fn();
        }
      };

      const onAbort = () => {
        killed = true;
        proc.kill();
        settle(() => reject(new OperationCancelledError()));
      };
      if (hooks.signal) {
        if (hooks.signal.aborted) {
          proc.kill();
          reject(new OperationCancelledError());
          return;
        }
        hooks.signal.addEventListener("abort", onAbort, { once: true });
      }

      const timer = setTimeout(() => {
        killed = true;
        proc.kill();
        settle(() => reject(new Error("timeout")));
      }, this.timeoutMs);

      proc.stdout?.on("data", (chunk: Buffer) => {
        stdout += chunk.toString();
      });

      proc.stderr?.on("data", (chunk: Buffer) => {
        const text = chunk.toString();
        stderr += text;
        if (hooks.onStage) {
          for (const line of text.split(/\r?\n/)) {
            if (line.startsWith("STAGE ")) {
              hooks.onStage(line.slice("STAGE ".length).trim());
            }
          }
        }
      });

      proc.on("close", (code) => {
        clearTimeout(timer);
        hooks.signal?.removeEventListener("abort", onAbort);
        if (killed) return;

        if (code !== 0) {
          settle(() => reject(new Error(`Python process exited with code ${code}: ${stderr}`)));
          return;
        }

        try {
          const data = JSON.parse(stdout);
          if (data && typeof data === "object" && "error" in data) {
            settle(() => reject(new Error(`Backend error: ${(data as Record<string, unknown>).error}`)));
            return;
          }
          settle(() => resolve(data));
        } catch {
          settle(() => reject(new Error(`Failed to parse backend output: ${stdout.slice(0, 200)}`)));
        }
      });

      proc.on("error", (err) => {
        clearTimeout(timer);
        hooks.signal?.removeEventListener("abort", onAbort);
        settle(() => reject(err));
      });
    });
  }

  private processTransportData(
    data: unknown,
    errors: BridgeError[],
    warnings: string[]
  ): BridgeResult {
    let validated: BackendDepthResult;

    try {
      validated = validateTransportShape(data);
    } catch (err) {
      errors.push({
        code: "TRANSPORT_INVALID",
        message: err instanceof Error ? err.message : "Invalid transport data",
        phase: "transport",
      });
      return { success: false, errors, warnings };
    }

    const adapterResult = adaptBackendResult(validated);

    if (!adapterResult.success) {
      for (const e of adapterResult.errors) {
        errors.push({
          code: e.code,
          message: e.message,
          phase: "adapter",
        });
      }
      return { success: false, errors, warnings };
    }

    warnings.push(...adapterResult.warnings);

    return {
      success: true,
      artifact: adapterResult.artifact,
      errors: [],
      warnings,
    };
  }
}
