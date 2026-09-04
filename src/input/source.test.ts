import { describe, it, expect } from "vitest";
import { BackendBridge } from "../backend/bridge";
import { BackendOperationError } from "../backend/source";
import { ArtifactTransportFailure } from "../transport/types";
import type { ArtifactTransport } from "../transport/transport";
import { validateInputFile } from "./validation";
import { FileInputSource } from "./source";
import { makeTestPng, makeCorruptBytes, makeClientFile } from "./testFixtures";

const SUFFIXES = [".jpeg", ".jpg", ".png", ".tif", ".tiff"];
const bridge = new BackendBridge({ bridgeScript: "scripts/backend_bridge.py" });

describe("FileInputSource", () => {
  it("produces a viewer-ready terrain artifact from a validated file", async () => {
    const file = makeClientFile("tile.png", makeTestPng(4, 4), "image/png");
    const validated = await validateInputFile(file, { bridge, supportedSuffixes: SUFFIXES });
    try {
      const source = new FileInputSource({
        stagedPath: validated.stagedPath,
        metadata: validated.metadata,
      });
      expect(source.label).toBe("tile.png");
      expect(source.id).toMatch(/^file-[0-9a-f]{16}$/);
      const artifact = await source.load();
      expect(artifact.elevation!.width).toBe(4);
      expect(artifact.elevation!.height).toBe(4);
      expect(artifact.elevation!.unit).toBe("meters");
      expect(artifact.mesh.vertexCount).toBe(16);
      expect(artifact.metadata.backend!.elevation_semantics).toBe("absolute_elevation_dsm");
    } finally {
      await validated.cleanup();
    }
  });

  it("maps service failures to structured backend errors", async () => {
    const bridge = new BackendBridge({ bridgeScript: "scripts/backend_bridge.py" });
    const staged = await bridge.stageInputBytes(makeCorruptBytes(), "corrupt.png");
    try {
      const source = new FileInputSource({
        stagedPath: staged.path,
        metadata: {
          filename: "corrupt.png",
          format: "png",
          width: 0,
          height: 0,
          bandCount: null,
          dtype: null,
          georeferencing: "non_georeferenced",
          crs: null,
          gsd: null,
          nodata: null,
          sizeBytes: 0,
          checksum: null,
        },
      });
      await source.load();
      expect.fail("should have thrown");
    } catch (err) {
      expect(err).toBeInstanceOf(BackendOperationError);
      const errors = (err as BackendOperationError).bridgeErrors;
      expect(errors[0].code).toBe("InvalidInputError");
      expect(errors[0].phase).toBe("process");
    } finally {
      await staged.cleanup();
    }
  });

  it("refuses to render when the service reports no mesh", async () => {
    const file = makeClientFile("tile.png", makeTestPng(4, 4), "image/png");
    const validated = await validateInputFile(file, { bridge, supportedSuffixes: SUFFIXES });
    try {
      const stubTransport: ArtifactTransport = {
        fetchTerrain: async () => {
          throw new ArtifactTransportFailure({
            code: "ARTIFACT_UNAVAILABLE",
            message: "Service completed without an available mesh artifact",
            stage: null,
          });
        },
      };
      const source = new FileInputSource({
        stagedPath: validated.stagedPath,
        metadata: validated.metadata,
        transport: stubTransport,
      });
      await source.load();
      expect.fail("should have thrown");
    } catch (err) {
      expect(err).toBeInstanceOf(BackendOperationError);
      expect((err as BackendOperationError).bridgeErrors[0].code).toBe("ARTIFACT_UNAVAILABLE");
    } finally {
      await validated.cleanup();
    }
  });

  it("creates stable identities per file content", async () => {
    const first = await validateInputFile(
      makeClientFile("a.png", makeTestPng(4, 4)),
      { bridge, supportedSuffixes: SUFFIXES }
    );
    const second = await validateInputFile(
      makeClientFile("b.png", makeTestPng(4, 4)),
      { bridge, supportedSuffixes: SUFFIXES }
    );
    try {
      const idA = new FileInputSource({ stagedPath: first.stagedPath, metadata: first.metadata }).id;
      const idB = new FileInputSource({ stagedPath: second.stagedPath, metadata: second.metadata }).id;
      expect(idA).toBe(idB);
    } finally {
      await first.cleanup();
      await second.cleanup();
    }
  });
});
