import { describe, it, expect } from "vitest";
import { execFile } from "child_process";
import { mkdtempSync, rmSync, writeFileSync } from "fs";
import { tmpdir } from "os";
import { join } from "path";
import { BackendBridge } from "./bridge";
import { FileInputSource } from "../input/source";
import { validateInputFile } from "../input/validation";
import { makeTestPng, makeClientFile } from "../input/testFixtures";
import { ServiceArtifactTransport } from "../transport/transport";
import { LocalServiceClient } from "../service/client";
import { SubprocessServiceTransport } from "../service/transport";
import { resolveTerrainArtifact } from "../transport/resolver";
import { calculateMeasurement } from "../measurement/calculator";
import { applyHeightExaggeration } from "../display/types";
import {
  computeDisplayBounds,
  computeFrameCameraPosition,
} from "../camera/sceneBounds";
import * as THREE from "three";

/**
 * Real DA-V2 desktop acceptance.
 *
 * Gated: runs only with DW_DAV2_ACCEPT=1, a working Python interpreter
 * (DW_PYTHON), the pinned upstream DA-V2 source on PYTHONPATH, and an
 * external checkpoint (DW_DAV2_CKPT). Exercises the genuine desktop
 * consumption path — FileInputSource → ServiceArtifactTransport →
 * BackendBridge → backend_bridge.py --backend depth-anything-v2-small →
 * meshAdapter → SceneArtifact → camera/measurement/display — with real
 * model output. No synthetic substitute anywhere in this file.
 */
const ACCEPT = process.env.DW_DAV2_ACCEPT === "1";
const PYTHON = process.env.DW_PYTHON ?? "python";
const BACKEND = "depth-anything-v2-small";
const SUFFIXES = [".jpeg", ".jpg", ".png", ".tif", ".tiff"];

function realBridge(): BackendBridge {
  return new BackendBridge({
    pythonPath: PYTHON,
    bridgeScript: "scripts/backend_bridge.py",
    backend: BACKEND,
    timeoutMs: 180_000,
  });
}

function realTransport(): ServiceArtifactTransport {
  return new ServiceArtifactTransport({
    bridge: realBridge(),
    serviceClient: new LocalServiceClient(
      new SubprocessServiceTransport({
        pythonPath: PYTHON,
        timeoutMs: 180_000,
      }),
    ),
  });
}

function writeRgbGeoTiff(dir: string): Promise<string> {
  const script = [
    "import numpy as np, rasterio",
    "from rasterio.crs import CRS",
    "from rasterio.transform import Affine",
    `p = ${JSON.stringify(join(dir, "scene.tif"))}`,
    "r = np.tile(np.arange(16, dtype='uint8').reshape(4, 4), (1, 1))",
    "g = np.tile(np.linspace(0, 255, 16, dtype='uint8').reshape(4, 4), (1, 1))",
    "b = np.full((4, 4), 128, dtype='uint8')",
    "with rasterio.open(p, 'w', driver='GTiff', height=4, width=4,",
    "    count=3, dtype='uint8', crs=CRS.from_string('EPSG:32643'),",
    "    transform=Affine(0.5, 0.0, 100.0, 0.0, -0.5, 200.0)) as dst:",
    "    dst.write(r, 1); dst.write(g, 2); dst.write(b, 3)",
    "print(p)",
  ].join("\n");
  return new Promise((resolve, reject) => {
    execFile(PYTHON, ["-c", script], (err, stdout, stderr) => {
      if (err) {
        reject(new Error(`RGB GeoTIFF fixture failed: ${stderr}`));
      } else {
        resolve(stdout.trim().split("\n").pop() as string);
      }
    });
  });
}

describe.skipIf(!ACCEPT)("real DA-V2 desktop acceptance", () => {
  it("loads a real DA-V2 terrain artifact through the desktop source", async () => {
    const file = makeClientFile("tile.png", makeTestPng(32, 32), "image/png");
    const bridge = realBridge();
    const validated = await validateInputFile(file, {
      bridge,
      supportedSuffixes: SUFFIXES,
    });
    try {
      const artifact = await new FileInputSource({
        stagedPath: validated.stagedPath,
        metadata: validated.metadata,
        transport: realTransport(),
        backend: BACKEND,
      }).load();
      expect(artifact.id).toContain("depth-anything-v2-small");
      expect(artifact.metadata.backend?.model_name).toBe(
        "depth-anything-v2-small",
      );
      expect(artifact.metadata.backend?.depth_scale).toBe("metric");
      expect(artifact.elevation!.unit).toBe("meters");
      expect(artifact.elevation!.width).toBe(32);
      expect(artifact.elevation!.height).toBe(32);
      expect(artifact.mesh.vertexCount).toBe(32 * 32);
      for (let v = 0; v < artifact.mesh.vertexCount; v++) {
        expect(Number.isFinite(artifact.mesh.vertices[v * 3 + 1])).toBe(true);
      }
      expect(artifact.metadata.backend?.calibration_reference).toBeDefined();
    } finally {
      await validated.cleanup();
    }
  }, 180_000);

  it("frames the real terrain and keeps measurement metric-safe", async () => {
    const file = makeClientFile("tile.png", makeTestPng(16, 16), "image/png");
    const bridge = realBridge();
    const validated = await validateInputFile(file, {
      bridge,
      supportedSuffixes: SUFFIXES,
    });
    try {
      const artifact = await new FileInputSource({
        stagedPath: validated.stagedPath,
        metadata: validated.metadata,
        transport: realTransport(),
        backend: BACKEND,
      }).load();
      const geometry = new THREE.BufferGeometry();
      geometry.setAttribute(
        "position",
        new THREE.BufferAttribute(artifact.mesh.vertices, 3),
      );
      const mesh = new THREE.Mesh(geometry, new THREE.MeshBasicMaterial());
      const bounds = computeDisplayBounds([mesh]);
      expect(Number.isFinite(bounds.sphere.radius)).toBe(true);
      expect(bounds.sphere.radius).toBeGreaterThan(0);
      const framed = computeFrameCameraPosition(bounds, 60, 16 / 9);
      expect(Number.isFinite(framed.position.x)).toBe(true);
      expect(Number.isFinite(framed.position.y)).toBe(true);
      expect(Number.isFinite(framed.position.z)).toBe(true);
      const before = Array.from(artifact.mesh.vertices);
      applyHeightExaggeration(artifact.mesh.vertices, 10);
      expect(Array.from(artifact.mesh.vertices)).toEqual(before);
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
    } finally {
      await validated.cleanup();
    }
  }, 180_000);

  it("preserves CRS and transform for a real georeferenced DA-V2 artifact", async () => {
    const dir = mkdtempSync(join(tmpdir(), "depthwiz-dav2-geo-"));
    try {
      const tiffPath = await writeRgbGeoTiff(dir);
      const transport = realTransport();
      const bundle = await transport.fetchTerrain({
        stagedPath: tiffPath,
        backend: BACKEND,
      });
      const artifact = resolveTerrainArtifact(bundle);
      expect(artifact.metadata.backend?.model_name).toBe(
        "depth-anything-v2-small",
      );
      expect(artifact.metadata.CRS).toBe("EPSG:32643");
      expect(artifact.metadata.transform).toBeDefined();
      expect(artifact.metadata.transform!.originX).toBeCloseTo(100.0);
      expect(artifact.metadata.transform!.originY).toBeCloseTo(200.0);
      expect(artifact.metadata.transform!.pixelWidth).toBeCloseTo(0.5);
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  }, 180_000);

  it("fails loudly for an unknown backend without synthetic substitution", async () => {
    const dir = mkdtempSync(join(tmpdir(), "depthwiz-dav2-neg-"));
    const pngPath = join(dir, "tile.png");
    writeFileSync(pngPath, makeTestPng(8, 8));
    try {
      const bridge = new BackendBridge({
        pythonPath: PYTHON,
        bridgeScript: "scripts/backend_bridge.py",
        backend: "bogus-backend",
        timeoutMs: 60_000,
      });
      const result = await bridge.executeTerrainFile(pngPath);
      expect(result.success).toBe(false);
      expect(result.errors.length).toBeGreaterThan(0);
      expect(result.artifact).toBeUndefined();
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  }, 120_000);
});
