import { contextBridge, ipcRenderer } from "electron";

const ALLOWED_CHANNELS = new Set([
  "get-host-capabilities",
  "resolve-python-path",
  "resolve-checkpoint-path",
  "get-checkpoint-status",
  "get-scripts-dir",
  "launch-service",
  "terminate-service",
  "execute-service",
  "stage-input-bytes",
  "cleanup-staged-input",
]);

function safeInvoke(channel: string, ...args: unknown[]): Promise<unknown> {
  if (!ALLOWED_CHANNELS.has(channel)) {
    return Promise.reject(new Error(`Blocked IPC channel: ${channel}`));
  }
  return ipcRenderer.invoke(channel, ...args);
}

contextBridge.exposeInMainWorld("depthwizard", {
  getHostCapabilities: () => safeInvoke("get-host-capabilities"),
  resolvePythonPath: () => safeInvoke("resolve-python-path"),
  resolveCheckpointPath: () => safeInvoke("resolve-checkpoint-path"),
  getCheckpointStatus: () => safeInvoke("get-checkpoint-status"),
  getScriptsDir: () => safeInvoke("get-scripts-dir"),
  launchService: (args: { inputPath?: string; targetMode?: string }) =>
    safeInvoke("launch-service", args),
  terminateService: () => safeInvoke("terminate-service"),
  executeService: (args: { payload: unknown; timeoutMs?: number }) =>
    safeInvoke("execute-service", args),
  stageInputBytes: (args: { bytes: Uint8Array; filename: string }) =>
    safeInvoke("stage-input-bytes", args),
  cleanupStagedInput: (args: { stagedPath: string }) =>
    safeInvoke("cleanup-staged-input", args),
  // Push-model: main process sends stage updates during execute-service
  onStageUpdate: (callback: (stage: string) => void) => {
    const handler = (_event: Electron.IpcRendererEvent, stage: string) =>
      callback(stage);
    ipcRenderer.on("service-stage-update", handler);
    return () => ipcRenderer.removeListener("service-stage-update", handler);
  },
});
