import { app, BrowserWindow, ipcMain } from "electron";
import * as path from "path";
import { spawn, type ChildProcess } from "child_process";

let mainWindow: BrowserWindow | null = null;
let serviceProcess: ChildProcess | null = null;

const SERVICE_SCRIPT = "depthwiz_service.py";
const BRIDGE_SCRIPT = "backend_bridge.py";

interface HostCapabilities {
  runtime: "electron";
  processSpawning: boolean;
  localFilesystem: boolean;
  platform: string;
}

function getPythonPath(): string {
  const explicit = process.env.DEPTHWIZARD_PYTHON;
  if (explicit) return explicit;
  return "python";
}

function getScriptsDir(): string {
  return path.join(process.resourcesPath, "scripts");
}

function getCheckpointPath(): string {
  const explicit = process.env.DW_DAV2_CKPT;
  if (explicit) return explicit;
  const appData = app.getPath("userData");
  return path.join(appData, "checkpoints", "depth_anything_v2_vits.pth");
}

function resolveCapabilities(): HostCapabilities {
  return {
    runtime: "electron",
    processSpawning: true,
    localFilesystem: true,
    platform: process.platform,
  };
}

function registerIpcHandlers(): void {
  ipcMain.handle("get-host-capabilities", () => {
    return resolveCapabilities();
  });

  ipcMain.handle("resolve-python-path", () => {
    return getPythonPath();
  });

  ipcMain.handle("resolve-checkpoint-path", () => {
    return getCheckpointPath();
  });

  ipcMain.handle("get-scripts-dir", () => {
    return getScriptsDir();
  });

  ipcMain.handle(
    "launch-service",
    async (_event, args: { inputPath?: string; targetMode?: string }) => {
      if (serviceProcess) {
        return { error: "Service already running" };
      }

      const python = getPythonPath();
      const script = path.join(getScriptsDir(), SERVICE_SCRIPT);

      const env = { ...process.env };
      if (args.targetMode) {
        env.DW_TARGET_MODE = args.targetMode;
      }

      serviceProcess = spawn(python, [script], {
        stdio: ["pipe", "pipe", "pipe"],
        env,
      });

      const pid = serviceProcess.pid;
      return { pid };
    },
  );

  ipcMain.handle("terminate-service", () => {
    if (serviceProcess) {
      serviceProcess.kill();
      serviceProcess = null;
      return { terminated: true };
    }
    return { terminated: false };
  });

  ipcMain.invoke;
}

function createWindow(): void {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    title: "DepthWizard",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
    },
  });

  if (process.env.NODE_ENV === "development" || process.env.VITE_DEV_SERVER_URL) {
    mainWindow.loadURL(process.env.VITE_DEV_SERVER_URL || "http://localhost:5173");
  } else {
    mainWindow.loadFile(path.join(__dirname, "../dist/index.html"));
  }

  mainWindow.on("closed", () => {
    mainWindow = null;
  });
}

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
  if (serviceProcess) {
    serviceProcess.kill();
    serviceProcess = null;
  }
  if (process.platform !== "darwin") {
    app.quit();
  }
});

app.on("before-quit", () => {
  if (serviceProcess) {
    serviceProcess.kill();
    serviceProcess = null;
  }
});
