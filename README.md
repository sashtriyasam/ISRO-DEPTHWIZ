# ISRO-DEPTHWIZ

DepthWizard — Single-View Height Estimation and 3D Flythrough

## Getting Started

```bash
npm install
npm run dev
```

## Development

- `npm run dev` — Start development server
- `npm run build` — Production build
- `npm run test` — Run tests
- `npm run typecheck` — TypeScript type checking

## Documentation

See [docs/milestone-01.md](docs/milestone-01.md) for architecture details.

## Python scientific engine (`src/depthwizard/`)

Contracts, ingestion, depth backends, calibration, height semantics,
DSM/mesh raster engines, GeoTIFF export, geospatial primitives, DEM
references, reference controls, pipeline orchestration, local service.

```bash
python -m pytest        # full Python suite (src layout on pythonpath)
python -m ruff check src tests
python -m ruff format --check src tests
python -m mypy src tests
```

Milestone docs: [python-engine](docs/python-engine.md),
[ingestion](docs/ingestion.md), [backend](docs/backend.md),
[calibration](docs/calibration.md), [height-semantics](docs/height-semantics.md),
[dsm-engine](docs/dsm-engine.md), [geotiff-export](docs/geotiff-export.md),
[mesh-engine](docs/mesh-engine.md), [pipeline](docs/pipeline.md),
[local-service](docs/local-service.md), [geospatial](docs/geospatial.md),
[dem-reference](docs/dem-reference.md),
[reference-controls](docs/reference-controls.md).
