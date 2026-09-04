import { describe, it, expect } from "vitest";
import { BackendBridge } from "../backend/bridge";
import type { BackendTerrainProduct } from "../backend/types";
import { LocalServiceClient } from "../service/client";
import { SubprocessServiceTransport } from "../service/transport";
import { makeTestPng } from "../input/testFixtures";
import { ServiceArtifactTransport } from "./transport";
import { ArtifactTransportFailure } from "./types";
import { verifyBundle } from "./verify";

const bridge = new BackendBridge({ bridgeScript: "scripts/backend_bridge.py" });

async function realBundle(width = 4, height = 4): Promise<{
  response: Awaited<ReturnType<LocalServiceClient["executeService"]>>["response"];
  terrain: BackendTerrainProduct;
}> {
  const client = new LocalServiceClient();
  const staged = await bridge.stageInputBytes(makeTestPng(width, height), "tile.png");
  try {
    const { response } = await client.executeService({ inputPath: staged.path });
    if (!response.success) {
      throw new Error("service fixture failed");
    }
    const terrain = await bridge.fetchTerrainPayload(staged.path);
    return { response, terrain };
  } finally {
    await staged.cleanup();
  }
}

describe("verifyBundle", () => {
  it("accepts a consistent real bundle", async () => {
    const bundle = await realBundle();
    expect(() => verifyBundle(bundle)).not.toThrow();
  });

  it("rejects checksum linkage breaks", async () => {
    const bundle = await realBundle();
    const tampered: typeof bundle = {
      response: bundle.response,
      terrain: {
        ...bundle.terrain,
        mesh: { ...bundle.terrain.mesh, source_checksum: "0".repeat(64) },
      },
    };
    try {
      verifyBundle(tampered);
      expect.fail("should have thrown");
    } catch (err) {
      expect(err).toBeInstanceOf(ArtifactTransportFailure);
      expect((err as ArtifactTransportFailure).transportError.code).toBe("CHECKSUM_MISMATCH");
    }
    expect(() => verifyBundle(bundle)).not.toThrow();
  });

  it("rejects descriptor/payload disagreements", async () => {
    const bundle = await realBundle();
    const tampered = {
      ...bundle,
      response: {
        ...bundle.response,
        artifacts: bundle.response.artifacts.map((a) =>
          a.kind === "mesh" ? { ...a, semantics: "height_agl_ndsm" } : a
        ),
      },
    };
    try {
      verifyBundle(tampered);
      expect.fail("should have thrown");
    } catch (err) {
      expect((err as ArtifactTransportFailure).transportError.code).toBe("DESCRIPTOR_MISMATCH");
    }
  });

  it("rejects missing mesh descriptors", async () => {
    const bundle = await realBundle();
    const stripped = {
      ...bundle,
      response: {
        ...bundle.response,
        artifacts: bundle.response.artifacts.filter((a) => a.kind !== "mesh"),
      },
    };
    try {
      verifyBundle(stripped);
      expect.fail("should have thrown");
    } catch (err) {
      expect((err as ArtifactTransportFailure).transportError.code).toBe("ARTIFACT_UNAVAILABLE");
    }
  });
});

describe("ServiceArtifactTransport", () => {
  it("fetches verified bundles through the service boundary", async () => {
    const transport = new ServiceArtifactTransport();
    const staged = await bridge.stageInputBytes(makeTestPng(4, 4), "tile.png");
    try {
      const bundle = await transport.fetchTerrain({ stagedPath: staged.path });
      expect(bundle.response.success).toBe(true);
      expect(bundle.terrain.mesh.vertex_count).toBe(16);
      expect(() => verifyBundle(bundle)).not.toThrow();
    } finally {
      await staged.cleanup();
    }
  });

  it("surfaces backend domain failures without flattening", async () => {
    const transport = new ServiceArtifactTransport();
    const staged = await bridge.stageInputBytes(new Uint8Array([1, 2, 3]), "bad.png");
    try {
      await transport.fetchTerrain({ stagedPath: staged.path });
      expect.fail("should have thrown");
    } catch (err) {
      expect(err).toBeInstanceOf(ArtifactTransportFailure);
      expect((err as ArtifactTransportFailure).transportError.code).toBe("InvalidInputError");
    } finally {
      await staged.cleanup();
    }
  });

  it("maps pre-aborted operations to cancellation", async () => {
    const transport = new ServiceArtifactTransport();
    const controller = new AbortController();
    controller.abort();
    try {
      await transport.fetchTerrain({ stagedPath: "tile.png" }, { signal: controller.signal });
      expect.fail("should have thrown");
    } catch (err) {
      expect((err as ArtifactTransportFailure).transportError.code).toBe("OPERATION_CANCELLED");
    }
  });

  it("returns field-equivalent payloads across repeated fetches", async () => {
    const transport = new ServiceArtifactTransport();
    const staged = await bridge.stageInputBytes(makeTestPng(4, 4), "tile.png");
    try {
      const first = await transport.fetchTerrain({ stagedPath: staged.path });
      const second = await transport.fetchTerrain({ stagedPath: staged.path });
      expect(first.terrain.mesh.vertices).toEqual(second.terrain.mesh.vertices);
      expect(first.terrain.mesh.indices).toEqual(second.terrain.mesh.indices);
      expect(first.terrain.dsm.values).toEqual(second.terrain.dsm.values);
      expect(first.response.summary.input_checksum).toBe(second.response.summary.input_checksum);
    } finally {
      await staged.cleanup();
    }
  });

  it("cancels a live fetch and terminates the owned process", async () => {
    const transport = new ServiceArtifactTransport();
    const staged = await bridge.stageInputBytes(makeTestPng(8, 8), "tile.png");
    try {
      const controller = new AbortController();
      await expect(
        transport.fetchTerrain(
          { stagedPath: staged.path },
          {
            signal: controller.signal,
            onStage: () => controller.abort(),
          }
        )
      ).rejects.toSatisfy((err: unknown) => {
        expect(err).toBeInstanceOf(ArtifactTransportFailure);
        expect((err as ArtifactTransportFailure).transportError.code).toBe("OPERATION_CANCELLED");
        return true;
      });
    } finally {
      await staged.cleanup();
    }
  });

  it("reports service unavailability on a browser-only host without spawning", async () => {
    const transport = new ServiceArtifactTransport({
      serviceClient: new LocalServiceClient(
        new SubprocessServiceTransport({
          host: { runtime: "browser", processSpawning: false, localFilesystem: false },
        })
      ),
    });
    try {
      await transport.fetchTerrain({ stagedPath: "tile.png" });
      expect.fail("should have thrown");
    } catch (err) {
      expect(err).toBeInstanceOf(ArtifactTransportFailure);
      expect((err as ArtifactTransportFailure).transportError.code).toBe("SERVICE_UNAVAILABLE");
    }
  });
});
