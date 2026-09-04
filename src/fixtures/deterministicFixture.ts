import type { SceneArtifact, ElevationData, LayerPayloads } from "../types/scene";

const GRID_SIZE = 8;
const CELL_SIZE = 1.0;

function createSyntheticHeightGrid(): Float32Array {
  const grid = new Float32Array(GRID_SIZE * GRID_SIZE);
  for (let z = 0; z < GRID_SIZE; z++) {
    for (let x = 0; x < GRID_SIZE; x++) {
      const nx = (x / (GRID_SIZE - 1)) * 2 - 1;
      const nz = (z / (GRID_SIZE - 1)) * 2 - 1;
      const h =
        0.4 * Math.sin(nx * Math.PI) * Math.sin(nz * Math.PI) +
        0.15 * Math.cos(nx * 2.5) * Math.cos(nz * 2.5) +
        0.05 * Math.sin(nx * 4.0 + nz * 3.0);
      grid[z * GRID_SIZE + x] = h;
    }
  }
  return grid;
}

function createSyntheticRDSM(dsmGrid: Float32Array): Float32Array {
  const rdsm = new Float32Array(dsmGrid.length);
  let min = Infinity;
  for (let i = 0; i < dsmGrid.length; i++) {
    if (dsmGrid[i] < min) min = dsmGrid[i];
  }
  for (let i = 0; i < dsmGrid.length; i++) {
    rdsm[i] = dsmGrid[i] - min;
  }
  return rdsm;
}

function createSyntheticAGL(dsmGrid: Float32Array): Float32Array {
  const agl = new Float32Array(dsmGrid.length);
  for (let i = 0; i < dsmGrid.length; i++) {
    agl[i] = Math.max(0, dsmGrid[i] * 0.3 + 0.05 * Math.sin(i * 0.5));
  }
  return agl;
}

function buildMeshFromGrid(
  grid: Float32Array,
  size: number,
  cellSize: number
): { vertices: Float32Array; indices: Uint32Array; normals: Float32Array; uvs: Float32Array } {
  const vertexCount = size * size;
  const vertices = new Float32Array(vertexCount * 3);
  const normals = new Float32Array(vertexCount * 3);
  const uvs = new Float32Array(vertexCount * 2);
  const indexCount = (size - 1) * (size - 1) * 6;
  const indices = new Uint32Array(indexCount);

  const halfExtent = ((size - 1) * cellSize) / 2;

  for (let z = 0; z < size; z++) {
    for (let x = 0; x < size; x++) {
      const i = z * size + x;
      const px = x * cellSize - halfExtent;
      const py = grid[i];
      const pz = z * cellSize - halfExtent;

      vertices[i * 3] = px;
      vertices[i * 3 + 1] = py;
      vertices[i * 3 + 2] = pz;

      uvs[i * 2] = x / (size - 1);
      uvs[i * 2 + 1] = z / (size - 1);
    }
  }

  for (let z = 0; z < size - 1; z++) {
    for (let x = 0; x < size - 1; x++) {
      const i = z * size + x;
      const ti = (z * (size - 1) + x) * 6;
      indices[ti] = i;
      indices[ti + 1] = i + size;
      indices[ti + 2] = i + 1;
      indices[ti + 3] = i + 1;
      indices[ti + 4] = i + size;
      indices[ti + 5] = i + size + 1;
    }
  }

  const tmpNormals = new Float32Array(vertexCount * 3);
  for (let z = 0; z < size - 1; z++) {
    for (let x = 0; x < size - 1; x++) {
      const i0 = z * size + x;
      const i1 = i0 + 1;
      const i2 = i0 + size;
      const i3 = i0 + size + 1;

      const ax = vertices[i1 * 3] - vertices[i0 * 3];
      const ay = vertices[i1 * 3 + 1] - vertices[i0 * 3 + 1];
      const az = vertices[i1 * 3 + 2] - vertices[i0 * 3 + 2];
      const bx = vertices[i2 * 3] - vertices[i0 * 3];
      const by = vertices[i2 * 3 + 1] - vertices[i0 * 3 + 1];
      const bz = vertices[i2 * 3 + 2] - vertices[i0 * 3 + 2];
      const nx1 = ay * bz - az * by;
      const ny1 = az * bx - ax * bz;
      const nz1 = ax * by - ay * bx;

      const cx = vertices[i3 * 3] - vertices[i1 * 3];
      const cy = vertices[i3 * 3 + 1] - vertices[i1 * 3 + 1];
      const cz = vertices[i3 * 3 + 2] - vertices[i1 * 3 + 2];
      const dx = vertices[i2 * 3] - vertices[i1 * 3];
      const dy = vertices[i2 * 3 + 1] - vertices[i1 * 3 + 1];
      const dz = vertices[i2 * 3 + 2] - vertices[i1 * 3 + 2];
      const nx2 = cy * dz - cz * dy;
      const ny2 = cz * dx - cx * dz;
      const nz2 = cx * dy - cy * dx;

      for (const idx of [i0, i1, i2, i3]) {
        tmpNormals[idx * 3] += nx1 + nx2;
        tmpNormals[idx * 3 + 1] += ny1 + ny2;
        tmpNormals[idx * 3 + 2] += nz1 + nz2;
      }
    }
  }

  for (let i = 0; i < vertexCount; i++) {
    const nx = tmpNormals[i * 3];
    const ny = tmpNormals[i * 3 + 1];
    const nz = tmpNormals[i * 3 + 2];
    const len = Math.sqrt(nx * nx + ny * ny + nz * nz) || 1;
    normals[i * 3] = nx / len;
    normals[i * 3 + 1] = ny / len;
    normals[i * 3 + 2] = nz / len;
  }

  return { vertices, indices, normals, uvs };
}

function createElevationData(grid: Float32Array): ElevationData {
  return {
    grid,
    width: GRID_SIZE,
    height: GRID_SIZE,
    cellSize: CELL_SIZE,
    unit: "meters",
  };
}

export function createDeterministicFixture(): SceneArtifact {
  const grid = createSyntheticHeightGrid();
  const { vertices, indices, normals, uvs } = buildMeshFromGrid(grid, GRID_SIZE, CELL_SIZE);

  const halfExtent = ((GRID_SIZE - 1) * CELL_SIZE) / 2;

  const elevation = createElevationData(grid);

  const rdsmGrid = createSyntheticRDSM(grid);
  const aglGrid = createSyntheticAGL(grid);

  const layers: LayerPayloads = {
    rdsm: createElevationData(rdsmGrid),
    agl: createElevationData(aglGrid),
  };

  return {
    id: "dev-fixture-001",
    label: "Deterministic Test Terrain",
    mesh: {
      vertices,
      indices,
      normals,
      uvs,
      vertexCount: GRID_SIZE * GRID_SIZE,
      indexCount: (GRID_SIZE - 1) * (GRID_SIZE - 1) * 6,
    },
    elevation,
    layers,
    metadata: {
      CRS: "TEST-CRS-001",
      transform: {
        originX: -halfExtent,
        originY: -halfExtent,
        pixelWidth: CELL_SIZE,
        pixelHeight: CELL_SIZE,
      },
      bounds: {
        minX: -halfExtent,
        minY: -halfExtent,
        minZ: Math.min(...grid),
        maxX: halfExtent,
        maxY: Math.max(...grid),
        maxZ: halfExtent,
      },
      units: { spatial: "meters", elevation: "meters" },
      source: "deterministic-fixture",
      description:
        "Synthetic sinusoidal terrain for renderer validation. Not scientific output.",
    },
  };
}
