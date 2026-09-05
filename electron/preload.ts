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
});
