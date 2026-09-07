import { describe, it, expect } from "vitest";
import { execFile } from "child_process";
import { mkdtempSync, rmSync, readFileSync, existsSync } from "fs";
import { tmpdir } from "os";
import { join, resolve } from "path";

const REPO_ROOT = resolve(__dirname, "..", "..");
const SCRIPTS_DIR = join(REPO_ROOT, "scripts");

const PYTHON_BIN = (() => {
  if (process.env.DEPTHWIZARD_PYTHON) return process.env.DEPTHWIZARD_PYTHON;
  if (process.platform === "win32" && process.env.LOCALAPPDATA) {
    const candidate = join(process.env.LOCALAPPDATA, "Programs", "Python", "Python312", "python.exe");
    if (existsSync(candidate)) return candidate;
  }
  return process.platform === "win32" ? "python" : "python3";
})();

function runPython(args: string[], input?: string): Promise<{ stdout: string; stderr: string }> {
  return new Promise((resolvePromise, reject) => {
    const proc = execFile(PYTHON_BIN, args, { cwd: REPO_ROOT }, (err, stdout, stderr) => {
      if (err) {
        reject(new Error(`python ${args.join(" ")} failed: ${stderr.slice(0, 500)}`));
      } else {
        resolvePromise({ stdout, stderr });
      }
    });
    if (input !== undefined) {
      proc.stdin?.write(input);
      proc.stdin?.end();
    }
  });
}

describe("no duplicate scientific implementation in desktop glue", () => {
  const bridge = readFileSync(join(SCRIPTS_DIR, "backend_bridge.py"), "utf-8");
  const service = readFileSync(join(SCRIPTS_DIR, "depthwiz_service.py"), "utf-8");

  it("bridge scripts contain no depth-generation formula", () => {
    for (const [name, content] of [["backend_bridge.py", bridge], ["depthwiz_service.py", service]] as const) {
      expect(content, name).not.toContain("def synthetic_depth_values");
      expect(content, name).not.toContain("math.sin");
      expect(content, name).not.toContain("math.cos");
    }
  });

  it("bridge scripts contain no mesh/DSM/calibration mathematics", () => {
    for (const [name, content] of [["backend_bridge.py", bridge], ["depthwiz_service.py", service]] as const) {
      expect(content, name).not.toContain("def rasterize_");
      expect(content, name).not.toContain("def build_terrain_mesh");
      expect(content, name).not.toContain("triangles");
      expect(content, name).not.toContain("least squares");
      expect(content, name).not.toContain("normal equations");
    }
  });

  it("only the canonical integration layer serializes transport shapes", () => {
    expect(bridge).toContain("from depthwizard.integration import");
    expect(bridge).toContain("terrain_product");
    expect(bridge).toContain("to_json_text");
    expect(existsSync(join(SCRIPTS_DIR, "dw_serialize.py"))).toBe(false);
  });
});

describe("canonical wire compatibility", () => {
  it("bridge terrain output validates through the canonical wire decoder", async () => {
    const dir = mkdtempSync(join(tmpdir(), "depthwiz-canonical-"));
    try {
      const outPath = join(dir, "terrain.json");
      const { stdout } = await runPython([
        "scripts/backend_bridge.py",
        "--terrain",
        "4",
        "4",
      ]);
      const parsed = JSON.parse(stdout);
      expect(parsed.kind).toBe("terrain");
      const checkScript = [
        "import json, sys",
        "from depthwizard.integration.wire import terrain_product_from_json, is_json_safe",
        "doc = json.load(open(sys.argv[1]))",
        "doc.pop('stages', None)",
        "product = terrain_product_from_json(json.dumps(doc))",
        "assert is_json_safe(doc)",
        "print(product.mesh.vertex_count, product.dsm.width, product.mesh.semantics)",
      ].join("\n");
      const { stdout: check } = await new Promise<{ stdout: string; stderr: string }>(
        (resolvePromise, reject) => {
          require("fs").writeFileSync(outPath, JSON.stringify(parsed));
          execFile(PYTHON_BIN, ["-c", checkScript, outPath], { cwd: REPO_ROOT }, (err, stdout, stderr) => {
            if (err) {
              reject(new Error(`canonical validation failed: ${stderr.slice(0, 800)}`));
            } else {
              resolvePromise({ stdout, stderr });
            }
          });
        }
      );
      expect(check.trim()).toBe("16 4 absolute_elevation_dsm");
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  });

  it("canonical decoder rejects mismatched semantics without frontend help", async () => {
    await expect(
      runPython(["-c", "from depthwizard.integration.wire import terrain_product_from_json; terrain_product_from_json('{\"kind\": \"nope\"}')"])
    ).rejects.toThrow();
  });
});
