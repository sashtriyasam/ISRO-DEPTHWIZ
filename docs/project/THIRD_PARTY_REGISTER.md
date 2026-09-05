# DepthWizard — Third-Party Register

Provenance rule: model/runtime provenance distinguishes **checkpoint
hash**, **upstream repository revision**, **model license**, and
**runtime implementation**. Record all four before any accuracy or
distribution claim.

## Models

| Component                     | Upstream                                                                               | Revision / checkpoint                                                                                        | License                         | Note                                             |
| ----------------------------- | -------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ | ------------------------------- | ------------------------------------------------ |
| Depth Anything V2 Small       | `DepthAnything/Depth-Anything-V2` (+ local `depth_anything_v2` vendor dir, if present) | checkpoint hash recorded at runtime (see `docs/dav2-runtime-acceptance.md`); upstream rev pinned on adoption | Apache-2.0 (verify on adoption) | Relative-depth only; frozen for S19–S21 evidence |
| Future (DA-V3 / alternatives) | TBD by Shravan evaluation                                                              | TBD — no claim until recorded                                                                                | Must be recorded before merge   | Starts as research                               |

## Data

| Dataset             | Source / access                                                         | License / terms                        | Local handling                                                            |
| ------------------- | ----------------------------------------------------------------------- | -------------------------------------- | ------------------------------------------------------------------------- |
| GAMUS (experiments) | External download via preparation scripts (`docs/datasets/`, manifests) | Per-dataset terms; never redistributed | **Never committed** — manifests + checksums + deterministic fixtures only |
| DEM references      | External (operator-provided)                                            | Per-source terms                       | Same rule; source recorded in calibration provenance                      |

## Libraries / runtimes (pinned in `pyproject.toml` / `package.json`)

Python: `pydantic`, `Pillow`, `rasterio`, `numpy`; optional `torch`,
`torchvision`, `opencv-python` (`dav2` extra). Frontend: `react`,
`react-dom`, `three`. Dev: `pytest`, `mypy`, `ruff`, `vitest`,
`typescript`, `vite`, `eslint`.

## Never commit

Raw GAMUS tiles, large datasets, model checkpoints, Hugging Face
caches, generated huge rasters/meshes, secrets, local environments.
`.gitignore` already excludes `*.tif/*.tiff/*.geotiff/*.obj/*.ckpt/
*.pt/*.pth/*.safetensors`, `__pycache__`, `.venv`, `.env`.
Hugging Face cache dirs and `checkpoints/` output are covered by the
same policy (add explicit entries if a cache path appears in-tree).
