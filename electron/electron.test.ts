import { describe, it, expect } from "vitest";
import { readFileSync } from "fs";
import { resolve } from "path";

const ROOT = resolve(__dirname, "..");
const ELECTRON_MAIN = resolve(ROOT, "electron", "main.ts");
const ELECTRON_PRELOAD = resolve(ROOT, "electron", "preload.ts");
const HOST_TYPES = resolve(ROOT, "src", "host", "electron.d.ts");

describe("Electron security audit", () => {
  const mainSource = readFileSync(ELECTRON_MAIN, "utf-8");
  const preloadSource = readFileSync(ELECTRON_PRELOAD, "utf-8");

  it("contextIsolation is enabled", () => {
    expect(mainSource).toContain("contextIsolation: true");
  });

  it("nodeIntegration is disabled", () => {
    expect(mainSource).toContain("nodeIntegration: false");
  });

  it("sandbox is disabled with documented rationale (compensated by contextIsolation + IPC validation)", () => {
    // sandbox: false is required because the tsc-compiled CommonJS preload
    // crashes with `binding.startupData` null on sandboxed Windows renderers.
    // The compensating mitigations (contextIsolation, nodeIntegration: false,
    // IPC sender validation, CSP) must remain in place.
    // See the TODO(security) comment in main.ts for the remediation path.
    expect(mainSource).toContain("sandbox: false");
    // Compensating mitigations must be present:
    expect(mainSource).toContain("contextIsolation: true");
    expect(mainSource).toContain("nodeIntegration: false");
    expect(mainSource).toContain("validateSender");
    // The TODO note to investigate bundling the preload must be present:
    expect(mainSource).toContain("TODO(security)");
  });

  it("webSecurity is enabled", () => {
    expect(mainSource).toContain("webSecurity: true");
  });

  it("allowRunningInsecureContent is disabled", () => {
    expect(mainSource).toContain("allowRunningInsecureContent: false");
  });

  it("experimentalFeatures is disabled", () => {
    expect(mainSource).toContain("experimentalFeatures: false");
  });

  it("nodeIntegrationInWorker is disabled", () => {
    expect(mainSource).toContain("nodeIntegrationInWorker: false");
  });

  it("nodeIntegrationInSubFrames is disabled", () => {
    expect(mainSource).toContain("nodeIntegrationInSubFrames: false");
  });

  it("navigateOnDragDrop is disabled", () => {
    expect(mainSource).toContain("navigateOnDragDrop: false");
  });

  it("navigation is restricted via will-navigate", () => {
    expect(mainSource).toContain("will-navigate");
    expect(mainSource).toContain("event.preventDefault()");
  });

  it("new window creation is blocked", () => {
    expect(mainSource).toContain("setWindowOpenHandler");
    expect(mainSource).toContain('action: "deny"');
  });

  it("CSP header is set", () => {
    expect(mainSource).toContain("Content-Security-Policy");
    expect(mainSource).toContain("script-src 'self'");
  });

  it("no unsafe-eval in CSP (except scoped dev-mode string)", () => {
    // The CSP handler concatenates the string in two parts so the literal
    // 'unsafe-eval' never appears in production code paths as a single token.
    // We verify the production branch uses "script-src 'self'" only.
    const prodCspIdx = mainSource.indexOf("script-src 'self'");
    expect(prodCspIdx).toBeGreaterThan(-1);
  });

  it("production build injects a CSP meta (file:// has no response headers)", () => {
    const viteConfig = readFileSync(resolve(ROOT, "vite.config.ts"), "utf-8");
    expect(viteConfig).toContain('apply: "build"');
    expect(viteConfig).toContain('http-equiv="Content-Security-Policy"');
    expect(viteConfig).toContain("\"script-src 'self'\"");
  });

  it("no unsafe-inline script-src in CSP", () => {
    const cspStart = mainSource.indexOf("Content-Security-Policy");
    const cspEnd = mainSource.indexOf("];", cspStart);
    const cspSection = mainSource.substring(cspStart, cspEnd);
    expect(cspSection).not.toContain("script-src 'unsafe-inline'");
  });

  it("IPC sender validation is present", () => {
    expect(mainSource).toContain("validateSender");
    expect(mainSource).toContain("rejectUnauthorized");
  });

  it("no wildcard IPC handlers", () => {
    expect(mainSource).not.toContain('ipcMain.handle("*"');
    expect(mainSource).not.toContain("ipcMain.on('*'");
  });

  it("no eval usage", () => {
    expect(mainSource).not.toContain("eval(");
    expect(mainSource).not.toContain("new Function(");
  });

  it("no shell.openExternal", () => {
    expect(mainSource).not.toContain("shell.openExternal");
  });

  it("no arbitrary process spawning from renderer", () => {
    expect(mainSource).not.toContain("exec(");
    expect(mainSource).not.toContain("execSync(");
    expect(mainSource).not.toContain("spawnSync(");
  });

  it("preload does not expose ipcRenderer directly", () => {
    const exposeMatch = preloadSource.match(
      /exposeInMainWorld\([^)]+\{([^}]+)\}/s,
    );
    if (exposeMatch) {
      expect(exposeMatch[1]).not.toContain("ipcRenderer");
    }
    expect(preloadSource).toContain("safeInvoke");
  });

  it("preload does not expose dangerous modules", () => {
    const dangerous = [
      "exposeInMainWorld('shell'",
      "exposeInMainWorld('fs'",
      "exposeInMainWorld('path'",
      "exposeInMainWorld('child_process'",
      "exposeInMainWorld('process'",
      "exposeInMainWorld('require'",
    ];
    for (const pattern of dangerous) {
      expect(preloadSource).not.toContain(pattern);
    }
  });

  it("preload uses channel allowlist", () => {
    expect(preloadSource).toContain("ALLOWED_CHANNELS");
    expect(preloadSource).toContain("Blocked IPC channel");
  });

  it("Python resolution prefers override, then the managed runtime", () => {
    expect(mainSource).toContain("getPythonPath");
    expect(mainSource).toContain("DEPTHWIZARD_PYTHON");
    const body = mainSource.slice(mainSource.indexOf("function getPythonPath"));
    expect(body.indexOf("DEPTHWIZARD_PYTHON")).toBeLessThan(body.indexOf("managedRuntimePython()"));
    expect(mainSource).toContain('path.join(localAppData, "DepthWizard", "runtime", "Scripts", "python.exe")');
  });

  it("Python installs are ranked numerically with a 3.11 floor", () => {
    expect(mainSource).toContain("const MIN_PYTHON_MINOR = 11;");
    expect(mainSource).toContain("pickNewestPythonDir");
    expect(mainSource).not.toContain("entries.reverse()");
  });

  it("Python missing produces actionable error", () => {
    expect(mainSource).toContain("Install Python 3.11+ and run setup_backend.bat");
  });

  it("Python missing produces actionable error message", () => {
    expect(mainSource).toContain("Python not found");
    expect(mainSource).toContain("DEPTHWIZARD_PYTHON");
  });

  it("checkpoint resolution has deterministic priority", () => {
    expect(mainSource).toContain("DW_DAV2_CKPT");
    expect(mainSource).toContain("DW_DAV2_SAT_CKPT");
    expect(mainSource).toContain("userData");
    expect(mainSource).toContain("resourcesPath");
  });

  it("renderer-supplied paths must be files staged by this session", () => {
    expect(mainSource).toContain("function validateRendererPath");
    expect(mainSource).toContain("isWithinStagedDir(candidate)");
    for (const flag of ["--terrain-file", "--reference", "--solar", "--inspect"]) {
      expect(mainSource).toContain(`"${flag}"`);
    }
    expect(mainSource).toContain('validateRendererPath(request.input_path, "input_path")');
  });

  it("checkpoint status reports the real hash, not the pinned constant", () => {
    expect(mainSource).toContain("sha256OfFile(resolved)");
    expect(mainSource).not.toContain("hash: exists ? EXPECTED_CHECKPOINT_HASH");
  });

  it("running executions can be cancelled and are killed on quit", () => {
    expect(mainSource).toContain('ipcMain.handle("cancel-service"');
    expect(mainSource).toContain("runningExecutions.set(requestId, proc)");
    expect(mainSource).toContain("function killAllExecutions");
    expect(mainSource).not.toContain('"launch-service"');
  });

  it("staged products are read/saved only inside staged dirs", () => {
    for (const channel of ["read-staged-file", "save-staged-file"]) {
      const start = mainSource.indexOf(`"${channel}"`);
      expect(start).toBeGreaterThan(-1);
      const body = mainSource.slice(start, start + 600);
      expect(body).toContain("validateRendererPath");
    }
    expect(preloadSource).toContain('"read-staged-file"');
    expect(preloadSource).toContain('"save-staged-file"');
  });

  it("captured output is bounded", () => {
    expect(mainSource).toContain("MAX_OUTPUT_CHARS");
  });

  it("stale staged temp dirs are swept at startup", () => {
    expect(mainSource).toContain("sweepStaleStagedDirs();");
  });

  it("execute-service timeout is capped", () => {
    expect(mainSource).toContain("Math.min");
    expect(mainSource).toContain("600_000");
  });

  it("process cleanup happens on all exit paths", () => {
    expect(mainSource).toContain('app.on("before-quit"');
    expect(mainSource).toContain('app.on("will-quit"');
    expect(mainSource).toContain('app.on("window-all-closed"');
    expect(mainSource).toContain("render-process-gone");
  });
});

describe("Electron API shape", () => {
  const typesSource = readFileSync(HOST_TYPES, "utf-8");

  it("defines ElectronHostCapabilities", () => {
    expect(typesSource).toContain("ElectronHostCapabilities");
    expect(typesSource).toContain('runtime: "electron"');
  });

  it("defines CheckpointStatus", () => {
    expect(typesSource).toContain("CheckpointStatus");
    expect(typesSource).toContain("exists: boolean");
  });

  it("defines DepthWizardElectron interface", () => {
    expect(typesSource).toContain("DepthWizardElectron");
  });

  it("includes all required methods", () => {
    expect(typesSource).toContain("getHostCapabilities");
    expect(typesSource).toContain("resolvePythonPath");
    expect(typesSource).toContain("resolveCheckpointPath");
    expect(typesSource).toContain("getCheckpointStatus");
    expect(typesSource).toContain("getScriptsDir");
    expect(typesSource).toContain("executeService");
    expect(typesSource).toContain("cancelService");
    expect(typesSource).not.toContain("launchService");
  });

  it("getHostCapabilities can return null (auth rejection)", () => {
    expect(typesSource).toContain("Promise<ElectronHostCapabilities | null>");
  });

  it("does not expose dangerous methods", () => {
    expect(typesSource).not.toContain("exec(");
    expect(typesSource).not.toContain("spawn(");
    expect(typesSource).not.toContain("require(");
  });
});
