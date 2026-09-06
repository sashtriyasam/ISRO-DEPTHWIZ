import type { BridgeExecutionHooks } from "../backend/bridge";
import { OperationCancelledError } from "../backend/bridge";
import {
  detectHost,
  type HostCapabilities,
  type HostDetectionOverrides,
} from "../host/host";

export interface ServiceTransportOptions {
  pythonPath?: string;
  serviceScript?: string;
  timeoutMs?: number;
  host?: HostDetectionOverrides;
}

export interface ServiceTransport {
  invoke(payload: unknown, hooks?: BridgeExecutionHooks): Promise<unknown>;
}

const SERVICE_TIMEOUT_MS = 120_000;

function defaultPythonExecutable(): string {
  if (typeof process !== "undefined") {
    if (process.env.DEPTHWIZARD_PYTHON) {
      return process.env.DEPTHWIZARD_PYTHON;
    }
    if (process.platform === "win32") {
      const candidate = "C:\\Users\\Shivam\\AppData\\Local\\Programs\\Python\\Python312\\python.exe";
      try {
        if (require("fs").existsSync(candidate)) return candidate;
      } catch {
        /* noop */
      }
    }
  }
  return "python";
}

export class SubprocessServiceTransport implements ServiceTransport {
  private pythonPath: string;
  private serviceScript: string;
  private timeoutMs: number;
  private host: HostCapabilities;

  constructor(options: ServiceTransportOptions = {}) {
    this.pythonPath = options.pythonPath ?? defaultPythonExecutable();

    this.serviceScript = options.serviceScript ?? "scripts/depthwiz_service.py";
    this.timeoutMs = options.timeoutMs ?? SERVICE_TIMEOUT_MS;
    this.host = detectHost(options.host);
  }

  get hostCapabilities(): HostCapabilities {
    return this.host;
  }

  async invoke(
    payload: unknown,
    hooks: BridgeExecutionHooks = {},
  ): Promise<unknown> {
    if (typeof window !== "undefined" && window.depthwizard?.executeService) {
      if (hooks.signal?.aborted) {
        throw new OperationCancelledError();
      }
      return await window.depthwizard.executeService({
        payload,
        timeoutMs: this.timeoutMs,
      });
    }
    if (!this.host.processSpawning) {
      throw new Error(
        "Service transport requires a desktop host with process spawning",
      );
    }
    if (hooks.signal?.aborted) {
      throw new OperationCancelledError();
    }
    const { spawn } = await import("child_process");
    return new Promise((resolve, reject) => {
      let stdout = "";
      let stderr = "";
      let settled = false;
      const proc = spawn(this.pythonPath, [this.serviceScript], {
        stdio: ["pipe", "pipe", "pipe"],
        windowsHide: true,
      });
      const settle = (fn: () => void) => {
        if (!settled) {
          settled = true;
          fn();
        }
      };
      const onAbort = () => {
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
        proc.kill();
        settle(() => reject(new Error("service request timed out")));
      }, this.timeoutMs);
      proc.stdout?.on("data", (chunk: Buffer) => {
        stdout += chunk.toString();
      });
      proc.stderr?.on("data", (chunk: Buffer) => {
        stderr += chunk.toString();
      });
      proc.on("close", (code) => {
        clearTimeout(timer);
        hooks.signal?.removeEventListener("abort", onAbort);
        if (code !== 0) {
          settle(() =>
            reject(
              new Error(
                `Service process exited with code ${code}: ${stderr.slice(0, 500)}`,
              ),
            ),
          );
          return;
        }
        try {
          settle(() => resolve(JSON.parse(stdout)));
        } catch {
          settle(() =>
            reject(
              new Error(`Malformed service output: ${stdout.slice(0, 200)}`),
            ),
          );
        }
      });
      proc.on("error", (err) => {
        clearTimeout(timer);
        hooks.signal?.removeEventListener("abort", onAbort);
        settle(() => reject(err));
      });
      try {
        proc.stdin?.write(JSON.stringify(payload));
        proc.stdin?.end();
      } catch (err) {
        clearTimeout(timer);
        settle(() => reject(err));
      }
    });
  }
}
