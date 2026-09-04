import { describe, it, expect } from "vitest";
import { mkdtempSync, writeFileSync, rmSync } from "fs";
import { tmpdir } from "os";
import { join } from "path";
import { LocalServiceClient } from "./client";
import { ServiceWireError } from "./validator";
import { makeTestPng, makeCorruptBytes } from "../input/testFixtures";

function stageTempFile(name: string, bytes: Uint8Array): { path: string; cleanup: () => void } {
  const dir = mkdtempSync(join(tmpdir(), "depthwiz-svc-"));
  const path = join(dir, name);
  writeFileSync(path, bytes);
  return { path, cleanup: () => rmSync(dir, { recursive: true, force: true }) };
}

describe("LocalServiceClient request construction", () => {
  const client = new LocalServiceClient();

  it("builds wire requests with only backend-supported fields", () => {
    const request = client.buildRequest({ inputPath: "tile.png" });
    expect(request).toEqual({
      contract_version: "1",
      input_path: "tile.png",
      target_semantics: "absolute_elevation_dsm",
      backend: "synthetic-depth",
      preprocessor: "identity",
      build_mesh: true,
      geotiff_path: null,
      export_compression: "deflate",
      export_overwrite: false,
    });
  });

  it("rejects empty input paths without spawning", () => {
    expect(() => client.buildRequest({ inputPath: "  " })).toThrow(ServiceWireError);
  });
});

describe("LocalServiceClient live wire round-trip", () => {
  const client = new LocalServiceClient();

  it("discovers real capabilities (contract v1)", async () => {
    const capabilities = await client.capabilities();
    expect(capabilities.contract_version).toBe("1");
    expect(capabilities.supported_input_formats).toEqual([".jpeg", ".jpg", ".png", ".tif", ".tiff"]);
    expect(capabilities.supported_target_semantics).toContain("absolute_elevation_dsm");
    expect(capabilities.available_backends).toContain("synthetic-depth");
    expect(capabilities.mesh_supported).toBe(true);
  });

  it("executes TypeScript request → Python service → validated response", async () => {
    const staged = stageTempFile("tile.png", makeTestPng(4, 4));
    try {
      const { request, response } = await client.executeService({ inputPath: staged.path });
      expect(request.input_path).toBe(staged.path);
      expect(response.success).toBe(true);
      expect(response.final_state).toBe("completed");
      expect(response.states).toContain("mesh_generation");
      expect(response.failure).toBeNull();
      const mesh = response.artifacts.find((a) => a.kind === "mesh");
      expect(mesh?.available).toBe(true);
      expect(mesh?.persisted).toBe(false);
      expect(mesh?.path).toBeNull();
      expect(mesh?.semantics).toBe("absolute_elevation_dsm");
      expect(mesh?.units).toBe("meters");
      expect(response.summary.backend_name).toBe("synthetic-depth");
      expect(response.summary.calibration_method).toBe("scale_offset");
      expect(response.summary.calibration_reference).toBe("synthetic-dev-ref");
      expect(response.summary.input_checksum).toMatch(/^[0-9a-f]{64}$/);
    } finally {
      staged.cleanup();
    }
  });

  it("maps backend failures with domain categories and stages", async () => {
    const staged = stageTempFile("corrupt.png", makeCorruptBytes());
    try {
      const { response } = await client.executeService({ inputPath: staged.path });
      expect(response.success).toBe(false);
      expect(response.final_state).toBe("failed");
      expect(response.failure?.code).toBe("InvalidInputError");
      expect(response.failure?.stage).toBe("input_validated");
      expect(response.failure?.message).toBeTruthy();
    } finally {
      staged.cleanup();
    }
  });

  it("maps pre-aborted operations to cancellation", async () => {
    const controller = new AbortController();
    controller.abort();
    await expect(
      client.executeService({ inputPath: "tile.png" }, { signal: controller.signal })
    ).rejects.toThrow();
  });
});
