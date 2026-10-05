import {
  app,
  BrowserWindow,
  ipcMain,
  session,
  type IpcMainInvokeEvent,
  type WebContents,
} from "electron";
import * as path from "path";
import * as crypto from "crypto";
import { spawn, type ChildProcess } from "child_process";
import * as fs from "fs";

let mainWindow: BrowserWindow | null = null;

// Python processes started by execute-service, keyed by renderer request id,
// so Cancel and app quit can terminate them (they were previously orphaned).
const runningExecutions = new Map<string, ChildProcess>();

// Cap on captured stdout: beyond this the JSON could not be held as one V8
// string anyway; the run is stopped with an actionable error instead.
const MAX_OUTPUT_CHARS = 400 * 1024 * 1024;

// Largest staged product the renderer may read back (e.g. texture.png).
const MAX_STAGED_READ_BYTES = 200 * 1024 * 1024;

// Staged temp dirs older than this are swept at startup (crash leftovers).
const STALE_STAGED_MS = 24 * 60 * 60 * 1000;

// Registry of staged temp directories so they can be cleaned up on crash/quit.
const stagedDirs = new Set<string>();

const SERVICE_SCRIPT = "depthwiz_service.py";
const DAV2_CHECKPOINT_FILE = "depth_anything_v2_vits.pth";
const SAT_CHECKPOINT_FILE = "depth_anything_v2_satellite.pth";
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
// Resolution priority:
//   1. DEPTHWIZARD_PYTHON env (explicit override)
//   2. Managed runtime created by scripts/setup_backend.bat in
//      %LOCALAPPDATA%/DepthWizard/runtime (engine + torch + DA-V2 extra)
//   3. python.org per-user installs (Python3XY): newest numeric version
//      first, 3.11+ only
//   4. py.exe launcher, then "python" on PATH
//
// The renderer cannot provide executable paths.
// The main process decides which executable is allowed.
// ---------------------------------------------------------------------------

const MIN_PYTHON_MINOR = 11;

function managedRuntimePython(): string | null {
  const localAppData = process.env.LOCALAPPDATA;
  if (process.platform !== "win32" || !localAppData) return null;
  const candidate = path.join(localAppData, "DepthWizard", "runtime", "Scripts", "python.exe");
  return fs.existsSync(candidate) ? candidate : null;
}

/**
 * Newest python.org folder (e.g. "Python312") with minor >= 11. Sorted
 * numerically: a string sort would rank "Python39" above "Python312".
 */
function pickNewestPythonDir(entries: string[]): string | null {
  let best: { entry: string; minor: number } | null = null;
  for (const entry of entries) {
    const match = entry.match(/^Python3(\d{1,2})$/i);
    if (!match) continue;
    const minor = Number(match[1]);
    if (minor < MIN_PYTHON_MINOR) continue;
    if (best === null || minor > best.minor) best = { entry, minor };
  }
  return best ? best.entry : null;
}

function getPythonPath(): string {
  const explicit = process.env.DEPTHWIZARD_PYTHON;
  if (explicit) return explicit;

  const managed = managedRuntimePython();
  if (managed) return managed;

  if (process.platform === "win32") {
    const localAppData = process.env.LOCALAPPDATA || "";
    if (localAppData) {
      const pyBase = path.join(localAppData, "Programs", "Python");
      if (fs.existsSync(pyBase)) {
        try {
          const newest = pickNewestPythonDir(fs.readdirSync(pyBase));
          if (newest) {
            const candidate = path.join(pyBase, newest, "python.exe");
            if (fs.existsSync(candidate)) return candidate;
          }
        } catch {
          /* noop */
        }
      }
    }
    const pyLauncher = path.join(
      process.env.SystemRoot || "C:\\Windows",
      "py.exe",
    );
    if (fs.existsSync(pyLauncher)) return pyLauncher;
  }
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
//   1. DW_DAV2_CKPT / DW_DAV2_SAT_CKPT env (explicit override)
//   2. %APPDATA%/DepthWizard/checkpoints/ (canonical user data location)
//   3. <resourcesPath>/checkpoints/ (bundled, if present)
//   4. repo-dev checkpoints/ (unpackaged checkout only)
//
// The renderer cannot specify arbitrary checkpoint locations.
// Checkpoint verification is handled by the Python backend.
// ---------------------------------------------------------------------------

function resolveNamedCheckpoint(
  envName: string,
  fileName: string,
): string {
  const explicit = process.env[envName];
  if (explicit) return explicit;

  const userData = app.getPath("userData");
  const userDataCheckpoint = path.join(userData, "checkpoints", fileName);
  if (fs.existsSync(userDataCheckpoint)) return userDataCheckpoint;

  const bundled = path.join(process.resourcesPath, "checkpoints", fileName);
  if (fs.existsSync(bundled)) return bundled;

  if (!app.isPackaged) {
    const repoDev = path.join(__dirname, "..", "checkpoints", fileName);
    if (fs.existsSync(repoDev)) return repoDev;
  }

  // Return canonical path even if missing — service will report error
  return userDataCheckpoint;
}

function getCheckpointPath(): string {
  return resolveNamedCheckpoint("DW_DAV2_CKPT", DAV2_CHECKPOINT_FILE);
}

function getSatelliteCheckpointPath(): string {
  return resolveNamedCheckpoint("DW_DAV2_SAT_CKPT", SAT_CHECKPOINT_FILE);
}

function withCheckpointEnv(
  base: NodeJS.ProcessEnv = process.env,
): NodeJS.ProcessEnv {
  const env = { ...base };
  // Synthetic dev calibration is test infrastructure: a packaged build must
  // never fabricate metric references, whatever the user's environment says.
  if (app.isPackaged) {
    delete env.DW_DEV_CALIBRATION;
  }
  const dav2 = getCheckpointPath();
  if (fs.existsSync(dav2)) {
    env.DW_DAV2_CKPT = dav2;
  }
  const satellite = getSatelliteCheckpointPath();
  if (fs.existsSync(satellite)) {
    env.DW_DAV2_SAT_CKPT = satellite;
  }
  return env;
}

async function sha256OfFile(filePath: string): Promise<string> {
  return new Promise((resolve, reject) => {
    const hash = crypto.createHash("sha256");
    fs.createReadStream(filePath)
      .on("data", (chunk) => hash.update(chunk))
      .on("end", () => resolve(hash.digest("hex")))
      .on("error", reject);
  });
}

async function getCheckpointStatus(): Promise<{
  exists: boolean;
  path: string;
  hash: string;
  verified: boolean;
}> {
  const resolved = getCheckpointPath();
  if (!fs.existsSync(resolved)) {
    return { exists: false, path: resolved, hash: "", verified: false };
  }
  // Report the file's actual digest; "verified" only when it matches the pin.
  const hash = await sha256OfFile(resolved);
  return { exists: true, path: resolved, hash, verified: hash === EXPECTED_CHECKPOINT_HASH };
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
// Execution tracking (cancel + quit cleanup)
// ---------------------------------------------------------------------------

function killExecution(requestId: string): boolean {
  const proc = runningExecutions.get(requestId);
  if (!proc) return false;
  try {
    proc.kill();
  } catch {
    // Process already exited or access denied
  }
  runningExecutions.delete(requestId);
  return true;
}

function killAllExecutions(): void {
  for (const requestId of [...runningExecutions.keys()]) {
    killExecution(requestId);
  }
}

// ---------------------------------------------------------------------------
// Input path validation
// ---------------------------------------------------------------------------

function isWithinStagedDir(candidate: string): boolean {
  const resolved = path.resolve(candidate);
  for (const dir of stagedDirs) {
    if (resolved.startsWith(dir + path.sep)) return true;
  }
  return false;
}

/**
 * Every file the renderer asks Python to read must be one it staged through
 * stage-input-bytes. An extension blocklist was meaningless (Python never
 * executes inputs) and absolute paths elsewhere on disk were allowed.
 */
function validateRendererPath(candidate: unknown, label: string): string | null {
  if (typeof candidate !== "string" || candidate.trim().length === 0) {
    return `${label} must be a non-empty string`;
  }
  if (!isWithinStagedDir(candidate)) {
    return `${label} must be a file staged by this app session`;
  }
  return null;
}

// ---------------------------------------------------------------------------
// Staged-dir emergency cleanup (renderer crash / app quit)
// ---------------------------------------------------------------------------

function sweepStaleStagedDirs(): void {
  const osTmp = app.getPath("temp");
  let entries: string[] = [];
  try {
    entries = fs.readdirSync(osTmp);
  } catch {
    return;
  }
  const cutoff = Date.now() - STALE_STAGED_MS;
  for (const entry of entries) {
    if (!entry.startsWith("depthwiz-")) continue;
    const dir = path.join(osTmp, entry);
    try {
      if (fs.statSync(dir).mtimeMs < cutoff) {
        fs.rmSync(dir, { recursive: true, force: true });
      }
    } catch {
      /* noop */
    }
  }
}

function cleanAllStagedDirs(): void {
  for (const dir of stagedDirs) {
    try {
      fs.rmSync(dir, { recursive: true, force: true });
    } catch {
      /* noop */
    }
  }
  stagedDirs.clear();
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

  ipcMain.handle("get-checkpoint-status", async (event) => {
    if (rejectUnauthorized(event, "get-checkpoint-status")) return null;
    return getCheckpointStatus();
  });

  ipcMain.handle("get-scripts-dir", (event) => {
    if (rejectUnauthorized(event, "get-scripts-dir")) return null;
    return getScriptsDir();
  });

  ipcMain.handle(
    "stage-input-bytes",
    async (
      event,
      args: {
        bytes: Uint8Array | Buffer | Record<string, number> | number[];
        filename: string;
      },
    ) => {
      if (rejectUnauthorized(event, "stage-input-bytes")) {
        return { error: "unauthorized" };
      }
      try {
        const MAX_STAGE_SIZE = 500 * 1024 * 1024; // 500 MB maximum payload limit

        // Robust buffer construction:
        // Context bridge structured clone may convert Uint8Array to a plain
        // object with numeric string keys {"0":1,"1":2,...} on some Electron
        // builds. We normalize to a Buffer regardless of what arrives.
        let buffer: Buffer;
        if (Buffer.isBuffer(args.bytes)) {
          buffer = args.bytes;
        } else if (args.bytes instanceof Uint8Array) {
          buffer = Buffer.from(args.bytes);
        } else if (Array.isArray(args.bytes)) {
          buffer = Buffer.from(args.bytes as number[]);
        } else if (args.bytes && typeof args.bytes === "object") {
          // Plain object with numeric keys — reconstruct as array
          const obj = args.bytes as Record<string, number>;
          const keys = Object.keys(obj).filter((k) => /^\d+$/.test(k));
          const len = keys.length;
          buffer = Buffer.allocUnsafe(len);
          for (let i = 0; i < len; i++) {
            buffer[i] = obj[String(i)] ?? 0;
          }
        } else {
          return { error: "bytes field is missing or has an unexpected type" };
        }

        const byteCount = buffer.length;
        if (byteCount > MAX_STAGE_SIZE) {
          return { error: "Staged payload exceeds maximum limit of 500 MB." };
        }
        if (byteCount === 0) {
          return { error: "bytes field is empty — file may not have been read correctly" };
        }
        const base = path.basename(args.filename || "input");
        const trimmed = base.slice(-128) || "input";
        const osTmp = app.getPath("temp");
        const tempDir = fs.mkdtempSync(path.join(osTmp, "depthwiz-"));
        const targetPath = path.join(tempDir, trimmed);
        fs.writeFileSync(targetPath, buffer);
        stagedDirs.add(path.resolve(tempDir));
        return { path: targetPath };
      } catch (err) {
        return {
          error: `Failed to stage file: ${err instanceof Error ? err.message : String(err)}`,
        };
      }
    },
  );

  ipcMain.handle("show-backend-setup", (event) => {
    if (rejectUnauthorized(event, "show-backend-setup")) return;
    const setupBat = path.join(process.resourcesPath, "scripts", "setup_backend.bat");
    const setupExists = fs.existsSync(setupBat);
    const setupNote = setupExists
      ? `\n\nA setup script is included:\n  ${setupBat}\n\nDouble-click it to install automatically.`
      : "";
    void require("electron").dialog.showMessageBox({
      type: "info",
      title: "DepthWizard — Backend Setup Required",
      message: "Python backend dependencies are not installed.",
      detail:
        `DepthWizard needs Python 3.11+ (https://python.org) and a one-time ` +
        `setup that creates a managed runtime with the depth model ` +
        `(torch, Depth Anything V2 source and its SHA-verified checkpoint).` +
        setupNote,
      buttons: ["OK"],
    });
  });

  ipcMain.handle(
    "cleanup-staged-input",
    async (event, args: { stagedPath: string }) => {
      if (rejectUnauthorized(event, "cleanup-staged-input")) {
        return { cleaned: false };
      }
      try {
        if (args.stagedPath && typeof args.stagedPath === "string") {
          const dir = path.dirname(args.stagedPath);
          const osTmp = app.getPath("temp");
          const resolved = path.resolve(dir);
          const resolvedTmp = path.resolve(osTmp);
          if (
            stagedDirs.has(resolved) &&
            path.basename(resolved).startsWith("depthwiz-") &&
            path.dirname(resolved) === resolvedTmp
          ) {
            fs.rmSync(resolved, { recursive: true, force: true });
            stagedDirs.delete(resolved);
            return { cleaned: true };
          }
        }
      } catch {
        /* noop */
      }
      return { cleaned: false };
    },
  );

  // Products written beside a staged input (texture.png, dsm.tif) are read or
  // saved only through these two channels, and only inside staged dirs.
  ipcMain.handle("read-staged-file", async (event, args: { path?: unknown }) => {
    if (rejectUnauthorized(event, "read-staged-file")) {
      return { error: "unauthorized" };
    }
    const pathError = validateRendererPath(args?.path, "path");
    if (pathError) return { error: pathError };
    try {
      const filePath = args.path as string;
      const size = fs.statSync(filePath).size;
      if (size > MAX_STAGED_READ_BYTES) {
        return { error: `Staged file too large to read (${size} bytes)` };
      }
      return { bytes: new Uint8Array(fs.readFileSync(filePath)) };
    } catch (err) {
      return { error: `Failed to read staged file: ${err instanceof Error ? err.message : String(err)}` };
    }
  });

  ipcMain.handle(
    "save-staged-file",
    async (event, args: { path?: unknown; defaultName?: unknown }) => {
      if (rejectUnauthorized(event, "save-staged-file")) {
        return { error: "unauthorized" };
      }
      const pathError = validateRendererPath(args?.path, "path");
      if (pathError) return { error: pathError };
      const source = args.path as string;
      const defaultName =
        typeof args.defaultName === "string" && args.defaultName.trim()
          ? path.basename(args.defaultName)
          : path.basename(source);
      const { dialog } = require("electron") as typeof import("electron");
      const choice = await dialog.showSaveDialog({
        title: "Export DSM",
        defaultPath: defaultName,
        filters: [{ name: "GeoTIFF", extensions: ["tif", "tiff"] }],
      });
      if (choice.canceled || !choice.filePath) {
        return { saved: false };
      }
      try {
        fs.copyFileSync(source, choice.filePath);
        return { saved: true, path: choice.filePath };
      } catch (err) {
        return { error: `Export failed: ${err instanceof Error ? err.message : String(err)}` };
      }
    },
  );

  ipcMain.handle("cancel-service", (event, args: { requestId?: unknown }) => {
    if (rejectUnauthorized(event, "cancel-service")) {
      return { cancelled: false };
    }
    if (typeof args?.requestId !== "string") {
      return { cancelled: false };
    }
    return { cancelled: killExecution(args.requestId) };
  });

  ipcMain.handle(
    "execute-service",
    async (
      event,
      args: {
        payload: unknown;
        timeoutMs?: number;
        requestId?: string;
      },
    ) => {
      if (rejectUnauthorized(event, "execute-service")) {
        return { error: "unauthorized" };
      }
      const requestId =
        typeof args.requestId === "string" && args.requestId.length > 0
          ? args.requestId
          : crypto.randomUUID();

      const python = getPythonPath();

      // ---------------------------------------------------------------------------
      // bridgeArgs allowlist
      // ---------------------------------------------------------------------------
      const ALLOWED_FLAGS = new Set([
        "--inspect", "--capabilities", "--backend", "--mode",
        "--terrain-file", "--terrain", "--synthetic",
        "--mesh-levels", "--calibration-method", "--reference",
        "--diagnostics", "--solar", "--sun-elevation", "--sun-azimuth",
        "--min-area", "--gsd", "--assume-north-up", "--auto-reference",
      ]);
      // Flags whose next argument is a file the renderer staged.
      const PATH_FLAGS = new Set(["--terrain-file", "--reference", "--solar", "--inspect"]);

      const isBridgeArgs =
        typeof args.payload === "object" &&
        args.payload !== null &&
        "bridgeArgs" in args.payload &&
        Array.isArray((args.payload as { bridgeArgs: unknown }).bridgeArgs);

      if (isBridgeArgs) {
        const bridgeArgs = (args.payload as { bridgeArgs: unknown[] }).bridgeArgs;
        for (let i = 0; i < bridgeArgs.length; i++) {
          const arg = bridgeArgs[i];
          if (typeof arg !== "string") {
            return { error: "bridgeArgs must be an array of strings" };
          }
          if (arg.startsWith("--") && !ALLOWED_FLAGS.has(arg)) {
            return { error: `Disallowed bridgeArgs flag: ${arg}` };
          }
          if (PATH_FLAGS.has(arg)) {
            const pathError = validateRendererPath(bridgeArgs[i + 1], `${arg} path`);
            if (pathError) return { error: pathError };
          }
        }
      } else if (typeof args.payload === "object" && args.payload !== null) {
        const request = (args.payload as { request?: Record<string, unknown> }).request;
        if (request) {
          const inputError = validateRendererPath(request.input_path, "input_path");
          if (inputError) return { error: inputError };
          if (request.calibration_reference_path != null) {
            const refError = validateRendererPath(
              request.calibration_reference_path,
              "calibration_reference_path",
            );
            if (refError) return { error: refError };
          }
          if (request.geotiff_path != null) {
            return { error: "geotiff_path must be chosen through the export dialog" };
          }
        }
      }

      const scriptName = isBridgeArgs ? "backend_bridge.py" : SERVICE_SCRIPT;
      const script = path.join(getScriptsDir(), scriptName);

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
          const spawnArgs = isBridgeArgs
            ? [script, ...((args.payload as { bridgeArgs: string[] }).bridgeArgs)]
            : [script];
          const stdioMode: ("pipe" | "ignore")[] = isBridgeArgs
            ? ["ignore", "pipe", "pipe"]
            : ["pipe", "pipe", "pipe"];

          proc = spawn(python, spawnArgs, {
            stdio: stdioMode as ("pipe" | "ignore")[],
            env: withCheckpointEnv(),
            windowsHide: true,
          });
          runningExecutions.set(requestId, proc);
        } catch (err) {
          clearTimeout(timer);
          const msg = err instanceof Error ? err.message : String(err);
          if (msg.includes("ENOENT") || msg.includes("not found")) {
            resolve({
              error: `Python not found at "${python}". Install Python 3.11+ and run setup_backend.bat, or set the DEPTHWIZARD_PYTHON environment variable.`,
            });
          } else {
            resolve({
              error: `Failed to spawn service: ${msg}`,
            });
          }
          return;
        }

        proc.stdout?.on("data", (chunk: Buffer) => {
          stdout += chunk.toString();
          if (stdout.length > MAX_OUTPUT_CHARS) {
            killExecution(requestId);
            settle(() =>
              resolve({
                error:
                  "Backend output exceeded the desktop transfer limit; use a smaller " +
                  "input or a coarser mesh LOD.",
              }),
            );
          }
        });

        let stderrBuffer = "";
        proc.stderr?.on("data", (chunk: Buffer) => {
          const text = chunk.toString();
          stderr = (stderr + text).slice(-64 * 1024);
          stderrBuffer += text;
          const lines = stderrBuffer.split(/\r?\n/);
          stderrBuffer = lines.pop() ?? "";
          if (mainWindow && !mainWindow.isDestroyed()) {
            for (const line of lines) {
              if (line.startsWith("STAGE ")) {
                mainWindow.webContents.send(
                  "service-stage-update",
                  line.slice("STAGE ".length).trim(),
                );
              }
            }
          }
        });

        proc.on("close", (code, signal) => {
          clearTimeout(timer);
          runningExecutions.delete(requestId);
          if (signal !== null) {
            settle(() => resolve({ error: "Operation cancelled" }));
            return;
          }
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
          runningExecutions.delete(requestId);
          settle(() => {
            resolve({ error: `Service process error: ${err.message}` });
          });
        });

        try {
          if (!isBridgeArgs) {
            proc.stdin?.write(JSON.stringify(args.payload));
            proc.stdin?.end();
          }
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
    minWidth: 1024,
    minHeight: 640,
    title: "DepthWizard",
    webPreferences: {
      preload: path.join(__dirname, fs.existsSync(path.join(__dirname, "preload.cjs")) ? "preload.cjs" : "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      // sandbox: false is required because the preload script uses CommonJS
      // `require` (compiled from TypeScript by tsc, not ESM-bundled). Electron's
      // sandboxed renderer restricts `require` in preloads to a subset that
      // excludes `contextBridge` calls with complex objects on some Windows
      // builds, causing a `binding.startupData` null crash.
      // Mitigations in place: contextIsolation: true, nodeIntegration: false,
      // IPC sender validation on every handler, CSP via session headers,
      // navigation locked to localhost in dev mode.
      // TODO(security): investigate bundling the preload with esbuild/vite so
      // it can run under sandbox: true.
      sandbox: false,
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
    void mainWindow.loadURL(process.env.VITE_DEV_SERVER_URL);
  } else {
    void mainWindow.loadFile(path.join(__dirname, "../dist/index.html"));
  }

  mainWindow.on("closed", () => {
    mainWindow = null;
  });

  mainWindow.webContents.on("render-process-gone", () => {
    console.error("[depthwizard] Renderer process crashed");
    killAllExecutions();
    // Clean up any staged temp files so they don't leak if the renderer
    // crashes before it can call cleanup-staged-input.
    cleanAllStagedDirs();
  });
}

// ---------------------------------------------------------------------------
// Application lifecycle
// ---------------------------------------------------------------------------

app.whenReady().then(() => {
  sweepStaleStagedDirs();
  registerIpcHandlers();
  createWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on("window-all-closed", () => {
  killAllExecutions();
  cleanAllStagedDirs();
  if (process.platform !== "darwin") {
    app.quit();
  }
});

app.on("before-quit", () => {
  killAllExecutions();
  cleanAllStagedDirs();
});

app.on("will-quit", () => {
  killAllExecutions();
  cleanAllStagedDirs();
});
