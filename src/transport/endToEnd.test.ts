import { describe, it, expect } from "vitest";
import { execFile } from "child_process";
import { mkdtempSync, rmSync } from "fs";
import { tmpdir } from "os";
import { join } from "path";
import { BackendBridge } from "../backend/bridge";
import { FileInputSource } from "../input/source";
import { validateInputFile } from "../input/validation";
import { makeTestPng, makeClientFile } from "../input/testFixtures";
import { resolveInspection } from "../inspection/resolver";
import { calculateMeasurement } from "../measurement/calculator";
import { generateProfile } from "../profile/sampler";
import { applyHeightExaggeration } from "../display/types";
import { ServiceArtifactTransport } from "./transport";
import { resolveTerrainArtifact } from "./resolver";

const SUFFIXES = [".jpeg", ".jpg", ".png", ".tif", ".tiff"];
const bridge = new BackendBridge({ bridgeScript: "scripts/backend_bridge.py" });

function writeGeoTiff(dir: string): Promise<string> {
  const script = [
    "import numpy as np, rasterio",
    "from rasterio.crs import CRS",
    "from rasterio.transform import Affine",
    `p = ${JSON.stringify(join(dir, "scene.tif"))}`,
    "grid = np.arange(20, dtype='uint8').reshape(4, 5)",
    "with rasterio.open(p, 'w', driver='GTiff', height=4, width=5,",
    "    count=1, dtype='uint8', crs=CRS.from_string('EPSG:32643'),",
    "    transform=Affine(0.5, 0.0, 100.0, 0.0, -0.5, 200.0), nodata=0) as dst:",
    "    dst.write(grid, 1)",
    "print(p)",
  ].join("\n");
  const pythonBin =
    process.env.DEPTHWIZARD_PYTHON ||
    (process.platform === "win32"
      ? "C:\\Users\\Shivam\\AppData\\Local\\Programs\\Python\\Python312\\python.exe"
      : "python3");
  return new Promise((resolve, reject) => {
    execFile(pythonBin, ["-c", script], (err, stdout, stderr) => {
      if (err) {
        reject(new Error(`GeoTIFF fixture failed: ${stderr}`));
      } else {
        resolve(stdout.trim().split("\n").pop() as string);
      }
    });
  });
}

describe("LocalService-to-viewer terrain integration", () => {
  it("resolves real backend values without hardcoded payloads", async () => {
    const file = makeClientFile("tile.png", makeTestPng(4, 4), "image/png");
    const validated = await validateInputFile(file, { bridge, supportedSuffixes: SUFFIXES });
    try {
      const source = new FileInputSource({
        stagedPath: validated.stagedPath,
        metadata: validated.metadata,
      });
      const artifact = await source.load();
      expect(artifact.mesh.vertexCount).toBe(16);
      expect(artifact.elevation!.unit).toBe("meters");
      for (let i = 0; i < artifact.elevation!.grid.length; i++) {
        expect(artifact.elevation!.grid[i]).toBeGreaterThan(1);
      }
      for (let v = 0; v < artifact.mesh.vertexCount; v++) {
        expect(Number.isFinite(artifact.mesh.vertices[v * 3 + 1])).toBe(true);
      }
      expect(artifact.metadata.backend?.calibration_reference).toBe("synthetic-dev-ref");
    } finally {
      await validated.cleanup();
    }
  });

  it("preserves backend spatial metadata for georeferenced input", async () => {
    const dir = mkdtempSync(join(tmpdir(), "depthwiz-geo-"));
    try {
      const tiffPath = await writeGeoTiff(dir);
      const transport = new ServiceArtifactTransport();
      const bundle = await transport.fetchTerrain({ stagedPath: tiffPath });
      const artifact = resolveTerrainArtifact(bundle);
      expect(artifact.metadata.CRS).toBe("EPSG:32643");
      expect(artifact.metadata.transform).toBeDefined();
      expect(artifact.metadata.backend?.elevation_semantics).toBe("absolute_elevation_dsm");
      expect(artifact.elevation!.unit).toBe("meters");
      const inspection = resolveInspection(
        { u: 0.5, v: 0.5 },
        { x: 0, y: 0, z: 0 },
        artifact,
        "dsm"
      );
      expect(inspection).not.toBeNull();
      expect(Number.isFinite(inspection!.scientific.elevation)).toBe(true);
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  });

  it("keeps measurement and profile metric-safe on resolved artifacts", async () => {
    const file = makeClientFile("tile.png", makeTestPng(4, 4), "image/png");
    const validated = await validateInputFile(file, { bridge, supportedSuffixes: SUFFIXES });
    try {
      const artifact = await new FileInputSource({
        stagedPath: validated.stagedPath,
        metadata: validated.metadata,
      }).load();
      const mk = (x: number) => ({
        displayPosition: { x, y: 0, z: 0 },
        scientific: { elevation: 0 },
        uv: { u: 0, v: 0 },
        gridIndex: { col: 0, row: 0 },
        layerId: "dsm",
        artifactId: artifact.id,
      });
      const measurement = calculateMeasurement("distance", mk(0), mk(1), {
        units: "meters",
        source: "backend",
      });
      expect(measurement.units).toBe("meters");
      const profile = generateProfile(
        mk(0),
        mk(1),
        artifact.elevation,
        undefined,
        undefined,
        { units: "meters", source: "backend", elevationSemantics: "absolute_elevation_dsm" }
      );
      expect(profile.units).toBe("meters");
      expect(profile.points.length).toBeGreaterThan(0);
    } finally {
      await validated.cleanup();
    }
  });

  it("leaves scientific data untouched by display exaggeration", async () => {
    const file = makeClientFile("tile.png", makeTestPng(4, 4), "image/png");
    const validated = await validateInputFile(file, { bridge, supportedSuffixes: SUFFIXES });
    try {
      const artifact = await new FileInputSource({
        stagedPath: validated.stagedPath,
        metadata: validated.metadata,
      }).load();
      const before = Array.from(artifact.mesh.vertices);
      applyHeightExaggeration(artifact.mesh.vertices, 10);
      expect(Array.from(artifact.mesh.vertices)).toEqual(before);
    } finally {
      await validated.cleanup();
    }
  });
});
