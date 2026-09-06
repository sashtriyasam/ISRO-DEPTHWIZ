"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const electron_1 = require("electron");
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
    "show-backend-setup",
]);
function safeInvoke(channel, ...args) {
    if (!ALLOWED_CHANNELS.has(channel)) {
        return Promise.reject(new Error(`Blocked IPC channel: ${channel}`));
    }
    return electron_1.ipcRenderer.invoke(channel, ...args);
}
electron_1.contextBridge.exposeInMainWorld("depthwizard", {
    getHostCapabilities: () => safeInvoke("get-host-capabilities"),
    resolvePythonPath: () => safeInvoke("resolve-python-path"),
    resolveCheckpointPath: () => safeInvoke("resolve-checkpoint-path"),
    getCheckpointStatus: () => safeInvoke("get-checkpoint-status"),
    getScriptsDir: () => safeInvoke("get-scripts-dir"),
    launchService: (args) => safeInvoke("launch-service", args),
    terminateService: () => safeInvoke("terminate-service"),
    executeService: (args) => safeInvoke("execute-service", args),
    stageInputBytes: (args) => safeInvoke("stage-input-bytes", args),
    cleanupStagedInput: (args) => safeInvoke("cleanup-staged-input", args),
    showBackendSetup: () => safeInvoke("show-backend-setup"),
    // Push-model: main process sends stage updates during execute-service
    onStageUpdate: (callback) => {
        const handler = (_event, stage) => callback(stage);
        electron_1.ipcRenderer.on("service-stage-update", handler);
        return () => electron_1.ipcRenderer.removeListener("service-stage-update", handler);
    },
});
//# sourceMappingURL=preload.js.map