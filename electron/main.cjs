"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
const electron_1 = require("electron");
const path = __importStar(require("path"));
const child_process_1 = require("child_process");
const fs = __importStar(require("fs"));
let mainWindow = null;
let serviceProcess = null;
let serviceStdout = "";
let serviceStderr = "";
let activeServiceResolve = null;
let activeServiceReject = null;
// Registry of staged temp directories so they can be cleaned up on crash/quit.
const stagedDirs = new Set();
const SERVICE_SCRIPT = "depthwiz_service.py";
const EXPECTED_CHECKPOINT_HASH = "715fade13be8f229f8a70cc02066f656f2423a59effd0579197bbf57860e1378";
// ---------------------------------------------------------------------------
// IPC sender validation
// ---------------------------------------------------------------------------
function validateSender(event) {
    const sender = event.sender;
    return sender === mainWindow?.webContents;
}
function rejectUnauthorized(event, channel) {
    if (!validateSender(event)) {
        console.error(`[depthwizard] IPC rejected: unauthorized sender on channel "${channel}"`);
        return true;
    }
    return false;
}
// ---------------------------------------------------------------------------
// Runtime resolution (main process authority)
//
// This application requires Python to be installed externally.
// No Python runtime is bundled with the installer.
//
// Resolution priority:
//   1. DEPTHWIZARD_PYTHON env (explicit override)
//   2. python on PATH (system Python)
//
// The renderer cannot provide executable paths.
// The main process decides which executable is allowed.
// ---------------------------------------------------------------------------
function getPythonPath() {
    const explicit = process.env.DEPTHWIZARD_PYTHON;
    if (explicit)
        return explicit;
    if (process.platform === "win32") {
        const localAppData = process.env.LOCALAPPDATA || "";
        if (localAppData) {
            const pyBase = path.join(localAppData, "Programs", "Python");
            if (fs.existsSync(pyBase)) {
                try {
                    const entries = fs.readdirSync(pyBase);
                    // Prefer higher version numbers (e.g. Python312 > Python310)
                    for (const entry of entries.reverse()) {
                        const candidate = path.join(pyBase, entry, "python.exe");
                        if (fs.existsSync(candidate))
                            return candidate;
                    }
                }
                catch {
                    /* noop */
                }
            }
        }
        const pyLauncher = path.join(process.env.SystemRoot || "C:\\Windows", "py.exe");
        if (fs.existsSync(pyLauncher))
            return pyLauncher;
    }
    return "python";
}
function getScriptsDir() {
    if (!electron_1.app.isPackaged) {
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
function getCheckpointPath() {
    const explicit = process.env.DW_DAV2_CKPT;
    if (explicit)
        return explicit;
    // Canonical user-data location
    const userData = electron_1.app.getPath("userData");
    const userDataCheckpoint = path.join(userData, "checkpoints", "depth_anything_v2_vits.pth");
    if (fs.existsSync(userDataCheckpoint))
        return userDataCheckpoint;
    // Bundled resources fallback (may not exist)
    const bundled = path.join(process.resourcesPath, "checkpoints", "depth_anything_v2_vits.pth");
    if (fs.existsSync(bundled))
        return bundled;
    // Return canonical path even if missing — service will report error
    return userDataCheckpoint;
}
function getCheckpointStatus() {
    const resolved = getCheckpointPath();
    const exists = fs.existsSync(resolved);
    return {
        exists,
        path: resolved,
        hash: exists ? EXPECTED_CHECKPOINT_HASH : "",
    };
}
function isDevMode() {
    return !electron_1.app.isPackaged;
}
function resolveCapabilities() {
    return {
        runtime: "electron",
        processSpawning: true,
        localFilesystem: true,
        platform: process.platform,
        packaged: electron_1.app.isPackaged,
    };
}
// ---------------------------------------------------------------------------
// Service process lifecycle
// ---------------------------------------------------------------------------
function killServiceProcess() {
    if (serviceProcess) {
        try {
            serviceProcess.kill();
        }
        catch {
            // Process already exited or access denied
        }
        serviceProcess = null;
        serviceStdout = "";
        serviceStderr = "";
        activeServiceResolve = null;
        activeServiceReject = null;
    }
}
function setupServiceListeners(proc) {
    serviceStdout = "";
    serviceStderr = "";
    proc.stdout?.on("data", (chunk) => {
        serviceStdout += chunk.toString();
    });
    proc.stderr?.on("data", (chunk) => {
        serviceStderr += chunk.toString();
    });
    proc.on("close", (code) => {
        if (activeServiceResolve && activeServiceReject) {
            if (code === 0) {
                try {
                    activeServiceResolve(JSON.parse(serviceStdout));
                }
                catch {
                    activeServiceReject(new Error(`Malformed service output: ${serviceStdout.slice(0, 500)}`));
                }
            }
            else {
                activeServiceReject(new Error(`Service exited with code ${code}: ${serviceStderr.slice(0, 500)}`));
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
// ---------------------------------------------------------------------------
function validateInputPath(inputPath) {
    if (!inputPath || typeof inputPath !== "string") {
        return "inputPath must be a non-empty string";
    }
    const trimmed = inputPath.trim();
    if (trimmed.length === 0) {
        return "inputPath must not be empty";
    }
    const segments = trimmed.split(/[\\/]/);
    if (segments.includes("..")) {
        return "inputPath must not contain .. segments";
    }
    const ext = path.extname(trimmed).toLowerCase();
    const dangerous = [".exe", ".bat", ".cmd", ".com", ".ps1", ".sh", ".vbs"];
    if (dangerous.includes(ext)) {
        return `inputPath must not be an executable (${ext})`;
    }
    return null;
}
// ---------------------------------------------------------------------------
// Staged-dir emergency cleanup (renderer crash / app quit)
// ---------------------------------------------------------------------------
function cleanAllStagedDirs() {
    for (const dir of stagedDirs) {
        try {
            fs.rmSync(dir, { recursive: true, force: true });
        }
        catch {
            /* noop */
        }
    }
    stagedDirs.clear();
}
// ---------------------------------------------------------------------------
// IPC handler registration
// ---------------------------------------------------------------------------
function registerIpcHandlers() {
    electron_1.ipcMain.handle("get-host-capabilities", (event) => {
        if (rejectUnauthorized(event, "get-host-capabilities"))
            return null;
        return resolveCapabilities();
    });
    electron_1.ipcMain.handle("resolve-python-path", (event) => {
        if (rejectUnauthorized(event, "resolve-python-path"))
            return null;
        return getPythonPath();
    });
    electron_1.ipcMain.handle("resolve-checkpoint-path", (event) => {
        if (rejectUnauthorized(event, "resolve-checkpoint-path"))
            return null;
        return getCheckpointPath();
    });
    electron_1.ipcMain.handle("get-checkpoint-status", (event) => {
        if (rejectUnauthorized(event, "get-checkpoint-status"))
            return null;
        return getCheckpointStatus();
    });
    electron_1.ipcMain.handle("get-scripts-dir", (event) => {
        if (rejectUnauthorized(event, "get-scripts-dir"))
            return null;
        return getScriptsDir();
    });
    electron_1.ipcMain.handle("stage-input-bytes", async (event, args) => {
        if (rejectUnauthorized(event, "stage-input-bytes")) {
            return { error: "unauthorized" };
        }
        try {
            const MAX_STAGE_SIZE = 500 * 1024 * 1024; // 500 MB maximum payload limit
            // Robust buffer construction:
            // Context bridge structured clone may convert Uint8Array to a plain
            // object with numeric string keys {"0":1,"1":2,...} on some Electron
            // builds. We normalise to a Buffer regardless of what arrives.
            let buffer;
            if (Buffer.isBuffer(args.bytes)) {
                buffer = args.bytes;
            }
            else if (args.bytes instanceof Uint8Array) {
                buffer = Buffer.from(args.bytes);
            }
            else if (Array.isArray(args.bytes)) {
                buffer = Buffer.from(args.bytes);
            }
            else if (args.bytes && typeof args.bytes === "object") {
                // Plain object with numeric keys — reconstruct as array
                const obj = args.bytes;
                const keys = Object.keys(obj).filter((k) => /^\d+$/.test(k));
                const len = keys.length;
                buffer = Buffer.allocUnsafe(len);
                for (let i = 0; i < len; i++) {
                    buffer[i] = obj[String(i)] ?? 0;
                }
            }
            else {
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
            const osTmp = electron_1.app.getPath("temp");
            const tempDir = fs.mkdtempSync(path.join(osTmp, "depthwiz-"));
            const targetPath = path.join(tempDir, trimmed);
            fs.writeFileSync(targetPath, buffer);
            stagedDirs.add(tempDir);
            return { path: targetPath };
        }
        catch (err) {
            return {
                error: `Failed to stage file: ${err instanceof Error ? err.message : String(err)}`,
            };
        }
    });
    electron_1.ipcMain.handle("show-backend-setup", (event) => {
        if (rejectUnauthorized(event, "show-backend-setup"))
            return;
        const setupBat = path.join(process.resourcesPath, "scripts", "setup_backend.bat");
        const setupExists = fs.existsSync(setupBat);
        const setupNote = setupExists
            ? `\n\nA setup script is included:\n  ${setupBat}\n\nDouble-click it to install automatically.`
            : "";
        void require("electron").dialog.showMessageBox({
            type: "info",
            title: "DepthWizard — Backend Setup Required",
            message: "Python backend dependencies are not installed.",
            detail: `DepthWizard requires Python 3.11+ with these packages:\n` +
                `  • pydantic\n  • Pillow\n  • rasterio\n  • numpy\n\n` +
                `Install Python from https://python.org then run:\n` +
                `  pip install pydantic Pillow rasterio numpy` +
                setupNote,
            buttons: ["OK"],
        });
    });
    electron_1.ipcMain.handle("cleanup-staged-input", async (event, args) => {
        if (rejectUnauthorized(event, "cleanup-staged-input")) {
            return { cleaned: false };
        }
        try {
            if (args.stagedPath && typeof args.stagedPath === "string") {
                const dir = path.dirname(args.stagedPath);
                const osTmp = electron_1.app.getPath("temp");
                const resolved = path.resolve(dir);
                const resolvedTmp = path.resolve(osTmp);
                if (stagedDirs.has(resolved) &&
                    path.basename(resolved).startsWith("depthwiz-") &&
                    path.dirname(resolved) === resolvedTmp) {
                    fs.rmSync(resolved, { recursive: true, force: true });
                    stagedDirs.delete(resolved);
                    return { cleaned: true };
                }
            }
        }
        catch {
            /* noop */
        }
        return { cleaned: false };
    });
    electron_1.ipcMain.handle("launch-service", async (event, args) => {
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
            serviceProcess = (0, child_process_1.spawn)(python, [script], {
                stdio: ["pipe", "pipe", "pipe"],
                env,
                windowsHide: true,
            });
            setupServiceListeners(serviceProcess);
            return { pid: serviceProcess.pid };
        }
        catch (err) {
            const msg = err instanceof Error ? err.message : String(err);
            if (msg.includes("ENOENT") || msg.includes("not found")) {
                return {
                    error: `Python not found at "${python}". Install Python 3.10+ and ensure it is on PATH, or set the DEPTHWIZARD_PYTHON environment variable.`,
                };
            }
            return { error: `Failed to spawn service: ${msg}` };
        }
    });
    electron_1.ipcMain.handle("terminate-service", (event) => {
        if (rejectUnauthorized(event, "terminate-service")) {
            return { terminated: false };
        }
        if (serviceProcess) {
            killServiceProcess();
            return { terminated: true };
        }
        return { terminated: false };
    });
    electron_1.ipcMain.handle("execute-service", async (event, args) => {
        if (rejectUnauthorized(event, "execute-service")) {
            return { error: "unauthorized" };
        }
        if (serviceProcess) {
            return { error: "Service already running" };
        }
        const python = getPythonPath();
        // ---------------------------------------------------------------------------
        // bridgeArgs allowlist
        // ---------------------------------------------------------------------------
        const ALLOWED_FLAGS = new Set([
            "--inspect", "--capabilities", "--backend", "--mode",
            "--terrain-file", "--terrain", "--synthetic",
        ]);
        const DANGEROUS_EXT = /\.(exe|bat|cmd|com|ps1|sh|vbs)$/i;
        const isBridgeArgs = typeof args.payload === "object" &&
            args.payload !== null &&
            "bridgeArgs" in args.payload &&
            Array.isArray(args.payload.bridgeArgs);
        if (isBridgeArgs) {
            const bridgeArgs = args.payload.bridgeArgs;
            for (const arg of bridgeArgs) {
                if (typeof arg !== "string") {
                    return { error: "bridgeArgs must be an array of strings" };
                }
                if (arg.startsWith("--") && !ALLOWED_FLAGS.has(arg)) {
                    return { error: `Disallowed bridgeArgs flag: ${arg}` };
                }
                if (arg.includes("..") || DANGEROUS_EXT.test(arg)) {
                    return { error: `Unsafe bridgeArg value: ${arg}` };
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
            let proc;
            let stdout = "";
            let stderr = "";
            let settled = false;
            const settle = (fn) => {
                if (!settled) {
                    settled = true;
                    fn();
                }
            };
            const timer = setTimeout(() => {
                settle(() => {
                    try {
                        proc.kill();
                    }
                    catch {
                        /* noop */
                    }
                    resolve({ error: "Service request timed out" });
                });
            }, timeoutMs);
            try {
                const spawnArgs = isBridgeArgs
                    ? [script, ...(args.payload.bridgeArgs)]
                    : [script];
                const stdioMode = isBridgeArgs
                    ? ["ignore", "pipe", "pipe"]
                    : ["pipe", "pipe", "pipe"];
                proc = (0, child_process_1.spawn)(python, spawnArgs, {
                    stdio: stdioMode,
                    env: { ...process.env },
                    windowsHide: true,
                });
            }
            catch (err) {
                clearTimeout(timer);
                const msg = err instanceof Error ? err.message : String(err);
                if (msg.includes("ENOENT") || msg.includes("not found")) {
                    resolve({
                        error: `Python not found at "${python}". Install Python 3.10+ and ensure it is on PATH, or set the DEPTHWIZARD_PYTHON environment variable.`,
                    });
                }
                else {
                    resolve({
                        error: `Failed to spawn service: ${msg}`,
                    });
                }
                return;
            }
            proc.stdout?.on("data", (chunk) => {
                stdout += chunk.toString();
            });
            let stderrBuffer = "";
            proc.stderr?.on("data", (chunk) => {
                const text = chunk.toString();
                stderr += text;
                stderrBuffer += text;
                const lines = stderrBuffer.split(/\r?\n/);
                stderrBuffer = lines.pop() ?? "";
                if (mainWindow && !mainWindow.isDestroyed()) {
                    for (const line of lines) {
                        if (line.startsWith("STAGE ")) {
                            mainWindow.webContents.send("service-stage-update", line.slice("STAGE ".length).trim());
                        }
                    }
                }
            });
            proc.on("close", (code) => {
                clearTimeout(timer);
                if (code === 0) {
                    settle(() => {
                        try {
                            resolve(JSON.parse(stdout));
                        }
                        catch {
                            resolve({
                                error: `Malformed service output: ${stdout.slice(0, 500)}`,
                            });
                        }
                    });
                }
                else {
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
                if (!isBridgeArgs) {
                    proc.stdin?.write(JSON.stringify(args.payload));
                    proc.stdin?.end();
                }
            }
            catch (err) {
                clearTimeout(timer);
                settle(() => {
                    resolve({
                        error: `Failed to write to service: ${err instanceof Error ? err.message : String(err)}`,
                    });
                });
            }
        });
    });
}
// ---------------------------------------------------------------------------
// Window creation with security hardening
// ---------------------------------------------------------------------------
function createWindow() {
    mainWindow = new electron_1.BrowserWindow({
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
                if (parsed.hostname === "localhost" ||
                    parsed.hostname === "127.0.0.1") {
                    return;
                }
            }
            catch {
                // Invalid URL — block
            }
        }
        event.preventDefault();
    });
    mainWindow.webContents.setWindowOpenHandler(() => {
        return { action: "deny" };
    });
    // CSP via session
    electron_1.session.defaultSession.webRequest.onHeadersReceived((details, callback) => {
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
    }
    else {
        mainWindow.loadFile(path.join(__dirname, "../dist/index.html"));
    }
    mainWindow.on("closed", () => {
        mainWindow = null;
    });
    mainWindow.webContents.on("render-process-gone", () => {
        console.error("[depthwizard] Renderer process crashed");
        killServiceProcess();
        // Clean up any staged temp files so they don't leak if the renderer
        // crashes before it can call cleanup-staged-input.
        cleanAllStagedDirs();
    });
}
// ---------------------------------------------------------------------------
// Application lifecycle
// ---------------------------------------------------------------------------
electron_1.app.whenReady().then(() => {
    registerIpcHandlers();
    createWindow();
    electron_1.app.on("activate", () => {
        if (electron_1.BrowserWindow.getAllWindows().length === 0) {
            createWindow();
        }
    });
});
electron_1.app.on("window-all-closed", () => {
    killServiceProcess();
    cleanAllStagedDirs();
    if (process.platform !== "darwin") {
        electron_1.app.quit();
    }
});
electron_1.app.on("before-quit", () => {
    killServiceProcess();
    cleanAllStagedDirs();
});
electron_1.app.on("will-quit", () => {
    killServiceProcess();
    cleanAllStagedDirs();
});
//# sourceMappingURL=main.js.map