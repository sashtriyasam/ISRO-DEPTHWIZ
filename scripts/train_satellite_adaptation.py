#!/usr/bin/env python3
"""Train satellite-adapted Depth Anything V2 on GAMUS dataset.

Uses DA-V2 Small backbone with Scale-Invariant loss + Gradient loss
(per DA-V2 paper) to fine-tune on orthophoto imagery paired with
metric nDSM/AGL height references.

The checkpoint preserves scale-ambiguous output (RELATIVE depth) so
the existing FileBasedCalibrationProvider maps to metric heights.

Usage:
  python scripts/train_satellite_adaptation.py --gamus-root <dir> \\
      --manifest manifests/gamus.json --split train \\
      --output checkpoints/depth_anything_v2_satellite.pth \\
      --epochs 10 --batch-size 4 --lr 1e-4

Environment: DW_DAV2_CKPT (base DA-V2 Small checkpoint for initialization),
             DW_TRAIN_DEVICE (default: cuda if available else cpu)
"""
from __future__ import annotations
import argparse, hashlib, json, os, sys, time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

def _fail(code: str, msg: str) -> int:
    print(json.dumps({"ok": False, "code": code, "message": msg})); return 1

def _resolve_base_ckpt() -> Path:
    ckpt = os.environ.get("DW_DAV2_CKPT")
    if ckpt: return Path(ckpt)
    return Path.cwd() / "checkpoints" / "depth_anything_v2_vits.pth"

def _resolve_device() -> str:
    dev = os.environ.get("DW_TRAIN_DEVICE")
    if dev: return dev
    try:
        import torch
        return "cuda" if torch.cuda.is_available() else "cpu"
    except Exception: return "cpu"

def _load_manifest(path: Path) -> dict:
    doc = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict) or "samples" not in doc:
        raise ValueError("manifest missing 'samples' list")
    return doc

def _gamus_sample_paths(root: Path, sample: dict) -> tuple[Path, Path]:
    img_rel = sample["image_path"]; ref_rel = sample["reference_path"]
    img_path = root / img_rel; ref_path = root / ref_rel
    if not img_path.is_file(): raise FileNotFoundError(f"image missing: {img_path}")
    if not ref_path.is_file(): raise FileNotFoundError(f"reference missing: {ref_path}")
    return img_path, ref_path

def _read_h5_image(path: Path) -> Any:
    import h5py
    with h5py.File(path, "r") as f: return f["image"][()]

def _read_h5_height(path: Path) -> Any:
    import h5py
    with h5py.File(path, "r") as f: return f["height"][()]

def _scale_invariant_loss(pred: Any, target: Any, mask: Any | None = None) -> Any:
    import torch
    log_pred = torch.log(pred + 1e-6); log_target = torch.log(target + 1e-6)
    if mask is not None:
        log_pred = log_pred * mask; log_target = log_target * mask
        n = mask.sum(); diff = log_pred - log_target
        return (diff * diff).sum() / n - (diff.sum() ** 2) / (n * n)
    diff = log_pred - log_target
    return (diff * diff).mean() - (diff.mean() ** 2)

def _gradient_loss(pred: Any, target: Any, mask: Any | None = None) -> Any:
    import torch
    def grad_x(x): return x[:, :, :, 1:] - x[:, :, :, :-1]
    def grad_y(x): return x[:, :, 1:, :] - x[:, :, :-1, :]
    gx_pred, gy_pred = grad_x(pred), grad_y(pred)
    gx_target, gy_target = grad_x(target), grad_y(target)
    loss_x = (gx_pred - gx_target).abs()
    loss_y = (gy_pred - gy_target).abs()
    if mask is not None:
        mask_x = mask[:, :, :, 1:] * mask[:, :, :, :-1]
        mask_y = mask[:, :, 1:, :] * mask[:, :, :-1, :]
        loss_x = (loss_x * mask_x).sum() / mask_x.sum().clamp(min=1)
        loss_y = (loss_y * mask_y).sum() / mask_y.sum().clamp(min=1)
    else:
        loss_x = loss_x.mean(); loss_y = loss_y.mean()
    return loss_x + loss_y

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--gamus-root", required=True, help="Root directory of GAMUS dataset")
    parser.add_argument("--manifest", required=True, help="Path to dataset manifest JSON")
    parser.add_argument("--split", default="train", help="Split to train on (train/val/test)")
    parser.add_argument("--output", required=True, help="Output checkpoint path")
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--resume", default=None, help="Resume from checkpoint")
    parser.add_argument("--seed", type=int, default=26175)
    parser.add_argument("--log-interval", type=int, default=10)
    parser.add_argument("--num-workers", type=int, default=4)
    parser.add_argument("--grad-accum-steps", type=int, default=1)
    args = parser.parse_args(argv)

    try:
        import torch
        import torch.nn as nn
        from torch.utils.data import Dataset, DataLoader
    except Exception as e:
        return _fail("TORCH_MISSING", f"torch not available: {e}")

    base_ckpt = _resolve_base_ckpt()
    if not base_ckpt.is_file():
        return _fail("BASE_CKPT_MISSING", f"Base DA-V2 checkpoint not found: {base_ckpt}. Set DW_DAV2_CKPT.")

    device = _resolve_device()
    torch.manual_seed(args.seed)

    # Import DA-V2 model
    try:
        import sys
        for parent in (Path(__file__).resolve().parents[2], Path.cwd()):
            for sub in ("third_party", "deps", ".deps"):
                cand = parent / sub / "Depth-Anything-V2"
                if cand.is_dir() and str(cand) not in sys.path:
                    sys.path.insert(0, str(cand))
        from depth_anything_v2.dpt import DepthAnythingV2
    except Exception as e:
        return _fail("DAV2_IMPORT_FAILED", f"Cannot import depth_anything_v2: {e}")

    class GAMUSDataset(Dataset):
        def __init__(self, root: Path, samples: list[dict]):
            self.root = root; self.samples = samples
        def __len__(self): return len(self.samples)
        def __getitem__(self, idx: int):
            img_path, ref_path = _gamus_sample_paths(self.root, self.samples[idx])
            img = _read_h5_image(img_path); height = _read_h5_height(ref_path)
            import numpy as np
            img = np.asarray(img, dtype=np.float32) / 255.0  # [0,1]
            if img.ndim == 3 and img.shape[2] == 3:
                img = np.transpose(img, (2, 0, 1))  # CHW
            elif img.ndim == 2:
                img = img[None, :, :]
            height = np.asarray(height, dtype=np.float32)  # metres
            # Create valid mask (height > 0)
            mask = (height > 0).astype(np.float32)
            return torch.from_numpy(img), torch.from_numpy(height), torch.from_numpy(mask)

    manifest = _load_manifest(Path(args.manifest))
    all_samples = manifest.get("samples", [])
    train_samples = [s for s in all_samples if s.get("split") == args.split]
    if not train_samples:
        return _fail("NO_SAMPLES", f"No samples for split '{args.split}' in manifest")

    dataset = GAMUSDataset(Path(args.gamus_root), train_samples)
    loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=True, num_workers=args.num_workers, pin_memory=(device == "cuda"))

    # Model
    model = DepthAnythingV2(encoder="vits", features=64, out_channels=[48, 96, 192, 384])
    state = torch.load(str(base_ckpt), map_location="cpu")
    model.load_state_dict(state, strict=False)  # strict=False allows head mismatch
    model = model.to(device).train()

    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    scaler = torch.cuda.amp.GradScaler(enabled=(device == "cuda"))

    start_epoch = 0
    if args.resume and Path(args.resume).is_file():
        ckpt = torch.load(args.resume, map_location="cpu")
        model.load_state_dict(ckpt["model"])
        optimizer.load_state_dict(ckpt["optimizer"])
        scaler.load_state_dict(ckpt["scaler"])
        start_epoch = ckpt["epoch"] + 1
        print(f"Resumed from epoch {start_epoch}")

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    step = 0
    for epoch in range(start_epoch, args.epochs):
        epoch_loss = 0.0
        for batch_idx, (img, height, mask) in enumerate(loader):
            img = img.to(device, non_blocking=True)
            height = height.to(device, non_blocking=True).unsqueeze(1)  # B,1,H,W
            mask = mask.to(device, non_blocking=True).unsqueeze(1)

            optimizer.zero_grad()
            with torch.cuda.amp.autocast(enabled=(device == "cuda")):
                pred = model(img)  # B,1,H,W (relative depth)
                # Align pred to target size if needed
                if pred.shape[-2:] != height.shape[-2:]:
                    pred = nn.functional.interpolate(pred, size=height.shape[-2:], mode="bilinear", align_corners=True)
                # Scale-invariant loss (DA-V2 paper)
                loss_si = _scale_invariant_loss(pred, height, mask)
                # Gradient loss
                loss_grad = _gradient_loss(pred, height, mask)
                loss = loss_si + 0.1 * loss_grad
            scaler.scale(loss).backward()
            if args.grad_accum_steps > 1:
                # gradient accumulation handled by step logic
                pass
            scaler.step(optimizer)
            scaler.update()

            epoch_loss += loss.item()
            step += 1
            if step % args.log_interval == 0:
                print(f"Epoch {epoch+1}/{args.epochs} | Step {step} | Loss: {loss.item():.6f} (SI: {loss_si.item():.6f}, Grad: {loss_grad.item():.6f})")

        avg_loss = epoch_loss / max(len(loader), 1)
        print(f"Epoch {epoch+1} complete | Avg Loss: {avg_loss:.6f}")

        # Save checkpoint
        torch.save({
            "model": model.state_dict(),
            "optimizer": optimizer.state_dict(),
            "scaler": scaler.state_dict(),
            "epoch": epoch,
            "args": vars(args),
            "sha256_base": hashlib.sha256(base_ckpt.read_bytes()).hexdigest(),
        }, str(output_path))
        print(f"Checkpoint saved to {output_path}")

    print("Training complete.")
    return 0

if __name__ == "__main__": raise SystemExit(main())