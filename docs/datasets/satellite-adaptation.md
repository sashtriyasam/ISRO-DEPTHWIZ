# Satellite-Adapted Depth Anything V2

Fine-tuning DA-V2 Small on orthophoto/satellite imagery paired with
metric nDSM/AGL height references from the GAMUS dataset.

## Rationale

The canonical DA-V2 Small backbone is trained on diverse indoor/outdoor
scenes but lacks satellite/orthophoto domain data. Fine-tuning on
GAMUS orthophotos (0.33 m GSD RGB) with LiDAR-derived nDSM/AGL height
references adapts the model to aerial perspective geometry while
preserving the DA-V2 scale-invariant loss property.

## Loss Function

Follows the DA-V2 paper (Scale-Invariant + Gradient loss):

```
L = L_SI + λ * L_grad
```

Where:
- **Scale-Invariant loss**: `L_SI = Var(log(pred) - log(target))`
  - Makes predictions scale-ambiguous (relative depth only)
  - Required so `FileBasedCalibrationProvider` can map to metric heights
- **Gradient loss**: `L_grad = |∇pred - ∇target|_1`
  - Preserves local surface detail and sharp boundaries
  - Weight λ = 0.1 (empirically chosen)

## Dataset: GAMUS

- **Source**: Hugging Face `earthflow/GAMUS` (CC-BY-4.0)
- **Tiles**: 1024×1024 RGB orthophoto (H5 key `image`) + nDSM/AGL height (H5 key `height`, float32 metres)
- **Reference semantic**: `HEIGHT_AGL_NDSM` (never absolute elevation)
- **Alignment**: `native-pixel` (exact shape match, no resampling)
- **Splits**: train/val/test per upstream manifest

## Training Procedure

1. **Base checkpoint**: DA-V2 Small (`depth_anything_v2_vits.pth`, SHA256 `715fade...`)
2. **Initialization**: Load base weights with `strict=False` (allows head adaptation)
3. **Optimizer**: AdamW, lr=1e-4, weight_decay=1e-4
4. **Precision**: Mixed FP16 on CUDA, FP32 on CPU/MPS
5. **Epochs**: 10 (configurable)
6. **Batch size**: 4 (configurable, limited by VRAM)

## Output Checkpoint

- **Path**: `checkpoints/depth_anything_v2_satellite.pth` (git-ignored)
- **Format**: PyTorch state_dict + metadata (epoch, args, base SHA256)
- **Provenance**: `SatelliteAdaptation-DepthAnythingV2` v2.0.0sat
- **Integration**: Used by `SatelliteDepthBackend` via `DW_DAV2_SAT_CKPT`

## Usage

```bash
# Prerequisites
pip install torch torchvision opencv-python h5py
# Download GAMUS tiles to <GAMUS_ROOT>/images/... + heights/...
export DW_DAV2_CKPT=/path/to/depth_anything_v2_vits.pth
export GAMUS_ROOT=/path/to/gamus

# Train
python scripts/train_satellite_adaptation.py \
    --gamus-root $GAMUS_ROOT \
    --manifest manifests/gamus.json \
    --split train \
    --output checkpoints/depth_anything_v2_satellite.pth \
    --epochs 10 --batch-size 4 --lr 1e-4

# Resume
python scripts/train_satellite_adaptation.py \
    --gamus-root $GAMUS_ROOT \
    --manifest manifests/gamus.json \
    --split train \
    --output checkpoints/depth_anything_v2_satellite.pth \
    --resume checkpoints/depth_anything_v2_satellite.pth

# Inference with satellite backend
export DW_DAV2_SAT_CKPT=checkpoints/depth_anything_v2_satellite.pth
python scripts/backend_bridge.py --terrain-file image.tif --backend depth-anything-v2-satellite
```

## Evaluation

After training, the fine-tuned checkpoint should be evaluated with the
canonical evaluation runner:

```bash
python scripts/evaluate.py --dataset gamus \
    --manifest manifests/gamus.json --split test \
    --backend depth-anything-v2-satellite \
    --gamus-root $GAMUS_ROOT --output results.json
```

Target metrics (vs DA-V2 Small baseline MAE 4.40m / RMSE 5.86m / R² 0.23):
- Reduced MAE/RMSE on orthophoto tiles
- Improved R² on AGL height prediction

## Checkpoint Verification

After training, update `src/depthwizard/backends/satellite.py`:

```python
CHECKPOINT_SHA256 = "<actual sha256 of fine-tuned checkpoint>"
```

Compute with: `sha256sum checkpoints/depth_anything_v2_satellite.pth`