import { describe, it, expect, vi, afterEach } from "vitest";
import { invokeElectronExecution, OperationCancelledError } from "./bridge";

type HostMock = {
  executeService: ReturnType<typeof vi.fn>;
  cancelService: ReturnType<typeof vi.fn>;
  onStageUpdate: ReturnType<typeof vi.fn>;
};

function installHost(executeImpl: (args: { requestId?: string }) => Promise<unknown>): HostMock {
  const host: HostMock = {
    executeService: vi.fn(executeImpl),
    cancelService: vi.fn(async () => ({ cancelled: true })),
    onStageUpdate: vi.fn(() => () => undefined),
  };
  (window as unknown as { depthwizard: unknown }).depthwizard = host;
  return host;
}

afterEach(() => {
  delete (window as unknown as { depthwizard?: unknown }).depthwizard;
});

describe("invokeElectronExecution", () => {
  it("surfaces the main-process error instead of a generic envelope error", async () => {
    installHost(async () => ({ error: 'Python not found at "python".' }));
    await expect(invokeElectronExecution({ capabilities: true }, 1000)).rejects.toThrow(
      'Python not found at "python".',
    );
  });

  it("cancels the running process when the signal aborts", async () => {
    const controller = new AbortController();
    let release: (value: unknown) => void = () => undefined;
    const host = installHost(
      () =>
        new Promise((resolve) => {
          release = resolve;
        }),
    );
    const pending = invokeElectronExecution({ bridgeArgs: ["--capabilities"] }, 1000, {
      signal: controller.signal,
    });
    controller.abort();
    release({ error: "Operation cancelled" });
    await expect(pending).rejects.toBeInstanceOf(OperationCancelledError);
    const { requestId } = host.executeService.mock.calls[0][0] as { requestId: string };
    expect(requestId).toBeTruthy();
    expect(host.cancelService).toHaveBeenCalledWith({ requestId });
  });

  it("returns successful results unchanged", async () => {
    installHost(async () => ({ capabilities: { contract_version: "1" } }));
    await expect(invokeElectronExecution({ capabilities: true }, 1000)).resolves.toEqual({
      capabilities: { contract_version: "1" },
    });
  });
});
