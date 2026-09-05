import { contextBridge, ipcRenderer } from "electron";

const ALLOWED_CHANNELS = new Set([
  "get-host-capabilities",
  "resolve-python-path",
  "resolve-checkpoint-path",
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
  launchService: (args: { inputPath?: string; targetMode?: string }) =>
    safeInvoke("launch-service", args),
  terminateService: () => safeInvoke("terminate-service"),
  executeService: (args: { payload: unknown; timeoutMs?: number }) =>
    safeInvoke("execute-service", args),
});
