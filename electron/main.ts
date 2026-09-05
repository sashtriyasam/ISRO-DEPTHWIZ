import {
  app,
  BrowserWindow,
  ipcMain,
  session,
  type IpcMainInvokeEvent,
  type WebContents,
} from "electron";
import * as path from "path";
import { spawn, type ChildProcess } from "child_process";
import * as fs from "fs";

let mainWindow: BrowserWindow | null = null;
let serviceProcess: ChildProcess | null = null;
let serviceStdout = "";
let serviceStderr = "";
let activeServiceResolve: ((result: unknown) => void) | null = null;
let activeServiceReject: ((err: Error) => void) | null = null;

const SERVICE_SCRIPT = "depthwiz_service.py";
const EXPECTED_CHECKPOINT_HASH =
  "715fade13be8f229f8a70cc02066f656f2423a59effd0579197bbf57860e1378";

// ---------------------------------------------------------------------------
// IPC sender validation
// ---------------------------------------------------------------------------

function validateSender(event: IpcMainInvokeEvent): boolean {
  const sender: WebContents = event.sender;
  return sender === mainWindow?.webContents;
}

function rejectUnauthorized(
  event: IpcMainInvokeEvent,
  channel: string,
): boolean {
  if (!validateSender(event)) {
    console.error(
      `[depthwizard] IPC rejected: unauthorized sender on channel "${channel}"`,
    );
    return true;
  }
  return false;
}

// ---------------------------------------------------------------------------
// Runtime resolution (main process authority)
//
// PACKAGED mode:
//   1. DEPTHWIZARD_PYTHON env (explicit override, developer only)
//   2. <resourcesPath>/python/python.exe (managed runtime)
//   3. error — no fallback to system Python
//
// DEVELOPMENT mode:
//   1. DEPTHWIZARD_PYTHON env
//   2. python3 on PATH
//   3. python on PATH
// ---------------------------------------------------------------------------

function getManagedPythonPath(): string | null {
  if (!app.isPackaged) return null;
  const managed = path.join(process.resourcesPath, "python", "python.exe");
  if (fs.existsSync(managed)) return managed;
  return null;
}

function getPythonPath(): string {
  const explicit = process.env.DEPTHWIZARD_PYTHON;
  if (explicit) return explicit;

  if (app.isPackaged) {
    const managed = getManagedPythonPath();
    if (managed) return managed;
    // In packaged mode, do NOT fall back to system Python.
    // The service will fail with a clear error.
    return "python";
  }

  // Development: try python3 then python
  return "python";
}

function getScriptsDir(): string {
  if (!app.isPackaged) {
    return path.join(__dirname, "..", "scripts");
  }
  return path.join(process.resourcesPath, "scripts");
}

// ---------------------------------------------------------------------------
// Checkpoint resolution (external provision policy)
//
// Production:
//   1. DW_DAV2_CKPT env (explicit override)
//   2. %APPDATA%/DepthWizard/checkpoints/ (canonical user data location)
//   3. <resourcesPath>/checkpoints/ (bundled, if present)
//
// The renderer cannot specify arbitrary checkpoint locations.
// Checkpoint verification is handled by the Python backend.
// ---------------------------------------------------------------------------

function getCheckpointPath(): string {
  const explicit = process.env.DW_DAV2_CKPT;
  if (explicit) return explicit;

  // Canonical user-data location
  const userData = app.getPath("userData");
  const userDataCheckpoint = path.join(
    userData,
    "checkpoints",
    "depth_anything_v2_vits.pth",
  );
  if (fs.existsSync(userDataCheckpoint)) return userDataCheckpoint;

  // Bundled resources fallback (may not exist)
  const bundled = path.join(
    process.resourcesPath,
    "checkpoints",
    "depth_anything_v2_vits.pth",
  );
  if (fs.existsSync(bundled)) return bundled;

  // Return canonical path even if missing — service will report error
  return userDataCheckpoint;
}

function getCheckpointStatus(): {
  exists: boolean;
  path: string;
  hash: string;
} {
  const resolved = getCheckpointPath();
  const exists = fs.existsSync(resolved);
  return {
    exists,
    path: resolved,
    hash: exists ? EXPECTED_CHECKPOINT_HASH : "",
  };
}

function isDevMode(): boolean {
  return !app.isPackaged;
}

// ---------------------------------------------------------------------------
// Host capabilities (renderer discovers, main decides)
// ---------------------------------------------------------------------------

interface HostCapabilities {
  runtime: "electron";
  processSpawning: boolean;
  localFilesystem: boolean;
  platform: string;
  packaged: boolean;
}

function resolveCapabilities(): HostCapabilities {
  return {
    runtime: "electron",
    processSpawning: true,
    localFilesystem: true,
    platform: process.platform,
    packaged: app.isPackaged,
  };
}

// ---------------------------------------------------------------------------
// Service process lifecycle
// ---------------------------------------------------------------------------

function killServiceProcess(): void {
  if (serviceProcess) {
    try {
      serviceProcess.kill();
    } catch {
      // Process already exited or access denied
    }
    serviceProcess = null;
    serviceStdout = "";
    serviceStderr = "";
    activeServiceResolve = null;
    activeServiceReject = null;
  }
}

function setupServiceListeners(proc: ChildProcess): void {
  serviceStdout = "";
  serviceStderr = "";

  proc.stdout?.on("data", (chunk: Buffer) => {
    serviceStdout += chunk.toString();
  });

  proc.stderr?.on("data", (chunk: Buffer) => {
    serviceStderr += chunk.toString();
  });

  proc.on("close", (code) => {
    if (activeServiceResolve && activeServiceReject) {
      if (code === 0) {
        try {
          activeServiceResolve(JSON.parse(serviceStdout));
        } catch {
          activeServiceReject(
            new Error(
              `Malformed service output: ${serviceStdout.slice(0, 500)}`,
            ),
          );
        }
      } else {
        activeServiceReject(
          new Error(
            `Service exited with code ${code}: ${serviceStderr.slice(0, 500)}`,
          ),
        );
      }
    }
    serviceProcess = null;
    serviceStdout = "";
    serviceStderr = "";
    activeServiceResolve = null;
    activeServiceReject = null;
  });

  proc.on("error", (err) => {
    if (activeServiceReject) {
      activeServiceReject(err);
    }
    serviceProcess = null;
    serviceStdout = "";
    serviceStderr = "";
    activeServiceResolve = null;
    activeServiceReject = null;
  });
}

// ---------------------------------------------------------------------------
// Input path validation
//
// Rejects:
//   - empty/non-string
//   - executable extensions
//   - path traversal (.. segments)
// Does NOT normalize and compare (platform-dependent behavior).
// ---------------------------------------------------------------------------

function validateInputPath(inputPath: string): string | null {
  if (!inputPath || typeof inputPath !== "string") {
    return "inputPath must be a non-empty string";
  }
  const trimmed = inputPath.trim();
  if (trimmed.length === 0) {
    return "inputPath must not be empty";
  }
  // Reject path traversal
  const segments = trimmed.split(/[\\/]/);
  if (segments.includes("..")) {
    return "inputPath must not contain .. segments";
  }
  // Reject executable extensions
  const ext = path.extname(trimmed).toLowerCase();
  const dangerous = [".exe", ".bat", ".cmd", ".com", ".ps1", ".sh", ".vbs"];
  if (dangerous.includes(ext)) {
    return `inputPath must not be an executable (${ext})`;
  }
  return null;
}

// ---------------------------------------------------------------------------
// IPC handler registration
// ---------------------------------------------------------------------------

function registerIpcHandlers(): void {
  ipcMain.handle("get-host-capabilities", (event) => {
    if (rejectUnauthorized(event, "get-host-capabilities")) return null;
    return resolveCapabilities();
  });

  ipcMain.handle("resolve-python-path", (event) => {
    if (rejectUnauthorized(event, "resolve-python-path")) return null;
    return getPythonPath();
  });

  ipcMain.handle("resolve-checkpoint-path", (event) => {
    if (rejectUnauthorized(event, "resolve-checkpoint-path")) return null;
    return getCheckpointPath();
  });

  ipcMain.handle("get-checkpoint-status", (event) => {
    if (rejectUnauthorized(event, "get-checkpoint-status")) return null;
    return getCheckpointStatus();
  });

  ipcMain.handle("get-scripts-dir", (event) => {
    if (rejectUnauthorized(event, "get-scripts-dir")) return null;
    return getScriptsDir();
  });

  ipcMain.handle(
    "launch-service",
    async (event, args: { inputPath?: string; targetMode?: string }) => {
      if (rejectUnauthorized(event, "launch-service")) {
        return { error: "unauthorized" };
      }
      if (serviceProcess) {
        return { error: "Service already running" };
      }

      if (args.inputPath) {
        const validationError = validateInputPath(args.inputPath);
        if (validationError) {
          return { error: validationError };
        }
      }

      const python = getPythonPath();
      const script = path.join(getScriptsDir(), SERVICE_SCRIPT);

      if (!fs.existsSync(script)) {
        return { error: `Service script not found: ${script}` };
      }

      const env = { ...process.env };
      if (args.targetMode) {
        env.DW_TARGET_MODE = args.targetMode;
      }

      try {
        serviceProcess = spawn(python, [script], {
          stdio: ["pipe", "pipe", "pipe"],
          env,
          windowsHide: true,
        });
        setupServiceListeners(serviceProcess);
        return { pid: serviceProcess.pid };
      } catch (err) {
        return {
          error: `Failed to spawn service: ${err instanceof Error ? err.message : String(err)}`,
        };
      }
    },
  );

  ipcMain.handle("terminate-service", (event) => {
    if (rejectUnauthorized(event, "terminate-service")) {
      return { terminated: false };
    }
    if (serviceProcess) {
      killServiceProcess();
      return { terminated: true };
    }
    return { terminated: false };
  });

  ipcMain.handle(
    "execute-service",
    async (
      event,
      args: {
        payload: unknown;
        timeoutMs?: number;
      },
    ) => {
      if (rejectUnauthorized(event, "execute-service")) {
        return { error: "unauthorized" };
      }
      if (serviceProcess) {
        return { error: "Service already running" };
      }

      const python = getPythonPath();
      const script = path.join(getScriptsDir(), SERVICE_SCRIPT);

      if (!fs.existsSync(script)) {
        return { error: `Service script not found: ${script}` };
      }

      const timeoutMs = Math.min(args.timeoutMs ?? 120_000, 600_000);

      return new Promise((resolve) => {
        let proc: ChildProcess;
        let stdout = "";
        let stderr = "";
        let settled = false;

        const settle = (fn: () => void) => {
          if (!settled) {
            settled = true;
            fn();
          }
        };

        const timer = setTimeout(() => {
          settle(() => {
            try {
              proc.kill();
            } catch {
              /* noop */
            }
            resolve({ error: "Service request timed out" });
          });
        }, timeoutMs);

        try {
          proc = spawn(python, [script], {
            stdio: ["pipe", "pipe", "pipe"],
            env: { ...process.env },
            windowsHide: true,
          });
        } catch (err) {
          clearTimeout(timer);
          resolve({
            error: `Failed to spawn service: ${err instanceof Error ? err.message : String(err)}`,
          });
          return;
        }

        proc.stdout?.on("data", (chunk: Buffer) => {
          stdout += chunk.toString();
        });

        proc.stderr?.on("data", (chunk: Buffer) => {
          stderr += chunk.toString();
        });

        proc.on("close", (code) => {
          clearTimeout(timer);
          if (code === 0) {
            settle(() => {
              try {
                resolve(JSON.parse(stdout));
              } catch {
                resolve({
                  error: `Malformed service output: ${stdout.slice(0, 500)}`,
                });
              }
            });
          } else {
            settle(() => {
              resolve({
                error: `Service exited with code ${code}: ${stderr.slice(0, 500)}`,
              });
            });
          }
        });

        proc.on("error", (err) => {
          clearTimeout(timer);
          settle(() => {
            resolve({ error: `Service process error: ${err.message}` });
          });
        });

        try {
          proc.stdin?.write(JSON.stringify(args.payload));
          proc.stdin?.end();
        } catch (err) {
          clearTimeout(timer);
          settle(() => {
            resolve({
              error: `Failed to write to service: ${err instanceof Error ? err.message : String(err)}`,
            });
          });
        }
      });
    },
  );
}

// ---------------------------------------------------------------------------
// Window creation with security hardening
// ---------------------------------------------------------------------------

function createWindow(): void {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    title: "DepthWizard",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      webSecurity: true,
      allowRunningInsecureContent: false,
      experimentalFeatures: false,
      nodeIntegrationInWorker: false,
      nodeIntegrationInSubFrames: false,
      navigateOnDragDrop: false,
    },
  });

  // Navigation restrictions
  mainWindow.webContents.on("will-navigate", (event, _url) => {
    if (isDevMode()) {
      try {
        const parsed = new URL(_url);
        if (
          parsed.hostname === "localhost" ||
          parsed.hostname === "127.0.0.1"
        ) {
          return;
        }
      } catch {
        // Invalid URL — block
      }
    }
    event.preventDefault();
  });

  mainWindow.webContents.setWindowOpenHandler(() => {
    return { action: "deny" };
  });

  // CSP via session
  session.defaultSession.webRequest.onHeadersReceived((details, callback) => {
    const csp = [
      "default-src 'self'",
      "script-src 'self'",
      "style-src 'self' 'unsafe-inline'",
      "img-src 'self' data: blob:",
      "font-src 'self' data:",
      "connect-src 'self'",
      "media-src 'none'",
      "object-src 'none'",
      "frame-src 'none'",
      "worker-src 'self' blob:",
    ].join("; ");
    callback({
      responseHeaders: {
        ...details.responseHeaders,
        "Content-Security-Policy": [csp],
      },
    });
  });

  // Load content
  if (isDevMode() && process.env.VITE_DEV_SERVER_URL) {
    mainWindow.loadURL(process.env.VITE_DEV_SERVER_URL);
  } else {
    mainWindow.loadFile(path.join(__dirname, "../dist/index.html"));
  }

  mainWindow.on("closed", () => {
    mainWindow = null;
  });

  mainWindow.webContents.on("render-process-gone", () => {
    console.error("[depthwizard] Renderer process crashed");
    killServiceProcess();
  });
}

// ---------------------------------------------------------------------------
// Application lifecycle
// ---------------------------------------------------------------------------

app.whenReady().then(() => {
  registerIpcHandlers();
  createWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on("window-all-closed", () => {
  killServiceProcess();
  if (process.platform !== "darwin") {
    app.quit();
  }
});

app.on("before-quit", () => {
  killServiceProcess();
});

app.on("will-quit", () => {
  killServiceProcess();
});
