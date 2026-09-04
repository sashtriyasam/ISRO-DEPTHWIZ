import { describe, it, expect } from "vitest";
import { readdirSync, readFileSync, statSync } from "fs";
import { join, resolve } from "path";

const SRC_ROOT = resolve(__dirname, "..");

function sourceFiles(dir: string): string[] {
  const entries = readdirSync(dir);
  const files: string[] = [];
  for (const entry of entries) {
    const full = join(dir, entry);
    if (statSync(full).isDirectory()) {
      if (entry === "depthwizard") {
        continue;
      }
      files.push(...sourceFiles(full));
    } else if (/\.(ts|tsx)$/.test(entry) && !entry.endsWith(".test.ts") && !entry.endsWith(".test.tsx")) {
      files.push(full);
    }
  }
  return files;
}

function readSources(dirs: string[]): Array<{ file: string; content: string }> {
  const files: string[] = [];
  for (const dir of dirs) {
    files.push(...sourceFiles(join(SRC_ROOT, dir)));
  }
  return files.map((file) => ({ file, content: readFileSync(file, "utf-8") }));
}

const NODE_BUILTINS = [
  "child_process",
  "fs/promises",
  'from "fs"',
  "from 'fs'",
  'from "os"',
  "from 'os'",
  'from "path"',
  "from 'path'",
  "require(",
];

describe("UI boundary: no Node-specific imports outside the host seam", () => {
  const uiFiles = readSources(["components", "app", "viewer", "input", "processing", "flythrough"]);

  for (const pattern of NODE_BUILTINS) {
    it(`no UI source imports ${pattern}`, () => {
      const offenders = uiFiles.filter(({ content }) => content.includes(pattern));
      expect(offenders.map(({ file }) => file)).toEqual([]);
    });
  }

  it("UI reads host facts only through the host module", () => {
    const hostUsers = uiFiles.filter(({ content }) => content.includes("detectHost"));
    const names = hostUsers.map(({ file }) => file);
    expect(names.some((name) => name.includes("InputWorkspace"))).toBe(true);
  });
});

describe("host boundary: no scientific semantics inside", () => {
  const hostFiles = readSources(["host"]);
  const scienceTerms = ["elevation", "semantics", "dsm", "agl", "rdsm", "calibrat", "crs", "mesh"];

  for (const term of scienceTerms) {
    it(`host module never mentions ${term}`, () => {
      const offenders = hostFiles.filter(({ content }) =>
        content.toLowerCase().includes(term)
      );
      expect(offenders.map(({ file }) => file)).toEqual([]);
    });
  }

  it("host capability never implies production backend availability", () => {
    const combined = hostFiles.map(({ content }) => content).join("\n").toLowerCase();
    expect(combined).not.toContain("production");
    expect(combined).not.toContain("model");
    expect(combined).not.toContain("synthetic");
  });
});
