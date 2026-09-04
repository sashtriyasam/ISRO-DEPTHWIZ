import { describe, it, expect } from "vitest";
import { BackendBridge } from "../backend/bridge";
import {
  suffixOf,
  checkClientSide,
  mapInspectionToMetadata,
  validateInputFile,
  fetchSupportedSuffixes,
  fetchServiceSuffixes,
  InputValidationFailed,
} from "./validation";
import { makeTestPng, makeCorruptBytes, makeClientFile } from "./testFixtures";

const SUFFIXES = [".jpeg", ".jpg", ".png", ".tif", ".tiff"];
const bridge = new BackendBridge({ bridgeScript: "scripts/backend_bridge.py" });

describe("client-side input checks", () => {
  it("accepts supported extensions case-insensitively", () => {
    const file = makeClientFile("Scene.PNG", makeTestPng(2, 2), "image/png");
    expect(checkClientSide(file, SUFFIXES)).toBeNull();
  });

  it("rejects unsupported extensions", () => {
    const file = makeClientFile("notes.txt", new TextEncoder().encode("hi"), "text/plain");
    const error = checkClientSide(file, SUFFIXES);
    expect(error).not.toBeNull();
    expect(error!.code).toBe("unsupported_format");
    expect(error!.action).toBeTruthy();
  });

  it("rejects files without an extension", () => {
    const file = makeClientFile("noextension", makeTestPng(2, 2));
    expect(checkClientSide(file, SUFFIXES)?.code).toBe("unsupported_format");
  });

  it("rejects empty files", () => {
    const file = makeClientFile("empty.png", new Uint8Array(0), "image/png");
    expect(checkClientSide(file, SUFFIXES)?.code).toBe("empty_file");
  });

  it("does not trust MIME type alone", () => {
    const file = makeClientFile("image.png", makeTestPng(2, 2), "text/plain");
    expect(checkClientSide(file, SUFFIXES)).toBeNull();
  });
});

describe("suffixOf", () => {
  it("extracts lowercase suffixes and strips directories", () => {
    expect(suffixOf("C:\\images\\Scene.JPG")).toBe(".jpg");
    expect(suffixOf("/tmp/a/scene.TIFF")).toBe(".tiff");
    expect(suffixOf("noext")).toBe("");
    expect(suffixOf(".hidden")).toBe("");
  });
});

describe("backend capabilities", () => {
  it("loads the supported suffix list from the real backend", async () => {
    const suffixes = await fetchSupportedSuffixes(bridge);
    expect(suffixes).toEqual([".jpeg", ".jpg", ".png", ".tif", ".tiff"]);
  });

  it("loads the same suffix list from the service contract", async () => {
    const suffixes = await fetchServiceSuffixes();
    expect(suffixes).toEqual([".jpeg", ".jpg", ".png", ".tif", ".tiff"]);
  });
});

describe("backend input validation", () => {
  it("validates a real PNG through the backend", async () => {
    const file = makeClientFile("valid.png", makeTestPng(6, 5), "image/png");
    const result = await validateInputFile(file, { bridge, supportedSuffixes: SUFFIXES });
    try {
      expect(result.metadata.filename).toBe("valid.png");
      expect(result.metadata.format).toBe("png");
      expect(result.metadata.width).toBe(6);
      expect(result.metadata.height).toBe(5);
      expect(result.metadata.bandCount).toBe(3);
      expect(result.metadata.georeferencing).toBe("non_georeferenced");
      expect(result.metadata.crs).toBeNull();
      expect(result.metadata.checksum).toMatch(/^[0-9a-f]{64}$/);
      expect(result.stagedPath.endsWith("valid.png")).toBe(true);
    } finally {
      await result.cleanup();
    }
  });

  it("maps corrupt files to invalid_input with the backend reason", async () => {
    const file = makeClientFile("corrupt.png", makeCorruptBytes(), "image/png");
    try {
      await validateInputFile(file, { bridge, supportedSuffixes: SUFFIXES });
      expect.fail("should have thrown");
    } catch (err) {
      expect(err).toBeInstanceOf(InputValidationFailed);
      const validationError = (err as InputValidationFailed).validationError;
      expect(validationError.code).toBe("invalid_input");
      expect(validationError.reason).toBeTruthy();
      expect(validationError.action).toBeTruthy();
    }
  });

  it("maps backend unsupported formats without inventing codes", async () => {
    const file = makeClientFile("notes.txt", new TextEncoder().encode("hello"), "text/plain");
    try {
      await validateInputFile(file, { bridge, supportedSuffixes: [".png", ".txt"] });
      expect.fail("should have thrown");
    } catch (err) {
      expect(err).toBeInstanceOf(InputValidationFailed);
      expect((err as InputValidationFailed).validationError.code).toBe("unsupported_format");
    }
  });

  it("rejects empty files before touching the backend", async () => {
    const file = makeClientFile("empty.png", new Uint8Array(0), "image/png");
    try {
      await validateInputFile(file, { bridge, supportedSuffixes: SUFFIXES });
      expect.fail("should have thrown");
    } catch (err) {
      expect((err as InputValidationFailed).validationError.code).toBe("empty_file");
    }
  });
});

describe("mapInspectionToMetadata", () => {
  it("never invents CRS or units", () => {
    const metadata = mapInspectionToMetadata(
      {
        handle: { source_path: "a.png", display_name: "a.png", file_size: 10, sha256: "x" },
        detected_format: "png",
        width: 2,
        height: 2,
        band_count: 3,
        dtype: "RGB",
        georeferencing: "non_georeferenced",
        spatial: { kind: "not_applicable" },
        source_format_metadata: {},
        status: "valid",
      },
      "a.png"
    );
    expect(metadata.crs).toBeNull();
    expect(metadata.gsd).toBeNull();
    expect(metadata.nodata).toBeNull();
    expect(metadata.format).toBe("png");
  });
});
