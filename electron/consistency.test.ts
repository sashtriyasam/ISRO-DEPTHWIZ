import { describe, it, expect } from "vitest";
import { readFileSync } from "fs";
import { resolve } from "path";

const ROOT = resolve(__dirname, "..");
const read = (rel: string) => readFileSync(resolve(ROOT, rel), "utf-8");

/** Values that must stay identical across the TS host and the Python engine. */
describe("cross-language constants", () => {
  it("Electron pins the same DA-V2 checkpoint hash as the Python backend", () => {
    const electronHash = /EXPECTED_CHECKPOINT_HASH =\s*"([0-9a-f]{64})"/.exec(read("electron/main.ts"));
    const pythonHash = /CHECKPOINT_SHA256 = "([0-9a-f]{64})"/.exec(
      read("src/depthwizard/backends/depth_anything_v2.py"),
    );
    expect(electronHash?.[1]).toBeDefined();
    expect(electronHash?.[1]).toBe(pythonHash?.[1]);
  });

  it("package.json, pyproject.toml and version.py agree on the release version", () => {
    const npmVersion = JSON.parse(read("package.json")).version as string;
    const pyproject = /^version = "([^"]+)"/m.exec(read("pyproject.toml"))?.[1];
    const engine = /__version__\s*=\s*"([^"]+)"/.exec(read("src/depthwizard/version.py"))?.[1];
    expect(pyproject).toBe(npmVersion);
    expect(engine).toBe(npmVersion);
  });
});
