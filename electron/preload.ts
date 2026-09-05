import { contextBridge, ipcRenderer } from "electron";

contextBridge.exposeInMainWorld("depthwizard", {
  getHostCapabilities: () => ipcRenderer.invoke("get-host-capabilities"),
  resolvePythonPath: () => ipcRenderer.invoke("resolve-python-path"),
  resolveCheckpointPath: () => ipcRenderer.invoke("resolve-checkpoint-path"),
  getScriptsDir: () => ipcRenderer.invoke("get-scripts-dir"),
  launchService: (args: { inputPath?: string; targetSemantics?: string }) =>
    ipcRenderer.invoke("launch-service", args),
  terminateService: () => ipcRenderer.invoke("terminate-service"),
});
