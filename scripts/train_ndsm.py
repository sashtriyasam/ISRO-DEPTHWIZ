#!/usr/bin/env python3
"""Fine-tune Depth Anything V2 Small to predict nDSM (metres above ground).

Data: crops from scripts/prepare_ndsm_dataset.py (RGB + LiDAR nDSM at
0.35-2 m GSD). The backbone is initialised from the pinned DA-V2 Small
checkpoint and trained end to end with a lower encoder learning rate.

Loss: L1 on nDSM + gradient L1 (sharp building/canopy edges).
Validation: whole sites held out (--val-sites); the swisstopo benchmark
sites are excluded from the dataset entirely.

Outputs a weights-only checkpoint ({"model": state_dict}) and a JSON
training record (per-epoch train/val MAE, RMSE) next to it.

Usage:
  python scripts/train_ndsm.py --data data/ndsm --out checkpoints/depthwizard_ndsm_vits.pth
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)
ENCODER_CONFIG = {"encoder": "vits", "features": 64, "out_channels": [48, 96, 192, 384]}
DEFAULT_VAL_SITES = ("lucerne", "jura_forest", "thurgau_fields", "davos", "gamus_val")
#: GAMUS tile numbers (PHL_xxxx etc.) held out for validation (~8% of tiles).
GAMUS_VAL_TILES = frozenset(str(n) for n in range(0, 10000) if n % 13 == 0)


def _site_of(path: Path) -> str:
    """Swiss crops are <site>_<gsd>m_<i>; GAMUS crops validate on whole tiles."""
    if path.name.startswith("gamus_"):
        return "gamus_val" if path.name.split("_")[2] in GAMUS_VAL_TILES else "gamus"
    return path.name.rsplit("_", 2)[0]


class NdsmCrops:
    """Map-style dataset over .npz crops with nadir augmentations."""

    def __init__(self, files: list[Path], size: int, augment: bool) -> None:
        self.files = files
        self.size = size
        self.augment = augment

    def __len__(self) -> int:
        return len(self.files)

    def __getitem__(self, index: int):  # type: ignore[no-untyped-def]
        import torch

        data = np.load(self.files[index])
        rgb = data["rgb"].astype(np.float32) / 255.0
        ndsm = data["ndsm"].astype(np.float32)
        s = self.size
        if rgb.shape[0] > s:  # random crop to the training size
            r = random.randint(0, rgb.shape[0] - s) if self.augment else (rgb.shape[0] - s) // 2
            c = random.randint(0, rgb.shape[1] - s) if self.augment else (rgb.shape[1] - s) // 2
            rgb, ndsm = rgb[r : r + s, c : c + s], ndsm[r : r + s, c : c + s]
        if self.augment:
            k = random.randint(0, 3)  # nadir imagery has no preferred orientation
            rgb, ndsm = np.rot90(rgb, k), np.rot90(ndsm, k)
            if random.random() < 0.5:
                rgb, ndsm = rgb[:, ::-1], ndsm[:, ::-1]
            gain = np.random.uniform(0.8, 1.2, size=3).astype(np.float32)
            rgb = np.clip(rgb * gain + np.random.uniform(-0.05, 0.05), 0.0, 1.0)
        rgb = (rgb - MEAN) / STD
        x = torch.from_numpy(np.ascontiguousarray(rgb.transpose(2, 0, 1)))
        y = torch.from_numpy(np.ascontiguousarray(ndsm))
        return x, y


def _gradient_loss(pred, target):  # type: ignore[no-untyped-def]
    dx_p = pred[:, :, 1:] - pred[:, :, :-1]
    dx_t = target[:, :, 1:] - target[:, :, :-1]
    dy_p = pred[:, 1:, :] - pred[:, :-1, :]
    dy_t = target[:, 1:, :] - target[:, :-1, :]
    return (dx_p - dx_t).abs().mean() + (dy_p - dy_t).abs().mean()


def _build_model(base_checkpoint: Path):  # type: ignore[no-untyped-def]
    import torch

    from depthwizard.runtime.diagnostics import ensure_dav2_source_on_path

    ensure_dav2_source_on_path()
    from depth_anything_v2.dpt import DepthAnythingV2

    model = DepthAnythingV2(**ENCODER_CONFIG)
    state = torch.load(str(base_checkpoint), map_location="cpu", weights_only=True)
    missing, unexpected = model.load_state_dict(state, strict=False)
    if [k for k in missing if not k.startswith("depth_head.")] or unexpected:
        raise SystemExit(
            f"base checkpoint mismatch: missing={missing[:3]} unexpected={unexpected[:3]}"
        )
    return model


def evaluate(model, loader, device: str) -> dict[str, float]:  # type: ignore[no-untyped-def]
    import torch

    model.eval()
    abs_sum = sq_sum = 0.0
    count = 0
    with torch.no_grad():
        for x, y in loader:
            x, y = x.to(device), y.to(device)
            with torch.autocast(device_type="cuda", dtype=torch.float16, enabled=device == "cuda"):
                pred = model(x).float()
            err = pred - y
            abs_sum += float(err.abs().sum())
            sq_sum += float((err**2).sum())
            count += err.numel()
    model.train()
    return {"mae": abs_sum / count, "rmse": math.sqrt(sq_sum / count)}


def main(argv: list[str] | None = None) -> int:
    import torch
    from torch.utils.data import DataLoader

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", nargs="+", default=["data/ndsm"])
    parser.add_argument("--base", default=str(ROOT / "checkpoints" / "depth_anything_v2_vits.pth"))
    parser.add_argument("--out", default=str(ROOT / "checkpoints" / "depthwizard_ndsm_vits.pth"))
    parser.add_argument("--size", type=int, default=392)
    parser.add_argument("--batch", type=int, default=4)
    parser.add_argument("--epochs", type=int, default=12)
    parser.add_argument("--lr-head", type=float, default=2e-4)
    parser.add_argument("--lr-encoder", type=float, default=2e-5)
    parser.add_argument("--grad-weight", type=float, default=0.5)
    parser.add_argument("--val-sites", nargs="*", default=list(DEFAULT_VAL_SITES))
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--seed", type=int, default=26175)
    args = parser.parse_args(argv)
    if args.size % 14:
        raise SystemExit("--size must be a multiple of 14 (ViT patch)")

    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    device = "cuda" if torch.cuda.is_available() else "cpu"

    files = sorted(f for folder in args.data for f in Path(folder).glob("*.npz"))
    val_files = [f for f in files if _site_of(f) in set(args.val_sites)]
    train_files = [f for f in files if _site_of(f) not in set(args.val_sites)]
    if not train_files or not val_files:
        raise SystemExit(
            f"need train and val crops (train={len(train_files)} val={len(val_files)})"
        )

    train_loader = DataLoader(
        NdsmCrops(train_files, args.size, augment=True),
        batch_size=args.batch,
        shuffle=True,
        num_workers=args.workers,
        drop_last=True,
        pin_memory=device == "cuda",
        persistent_workers=args.workers > 0,
    )
    val_loader = DataLoader(
        NdsmCrops(val_files, args.size, augment=False), batch_size=args.batch, num_workers=0
    )

    model = _build_model(Path(args.base)).to(device)
    encoder = [p for n, p in model.named_parameters() if n.startswith("pretrained.")]
    head = [p for n, p in model.named_parameters() if not n.startswith("pretrained.")]
    optimizer = torch.optim.AdamW(
        [{"params": encoder, "lr": args.lr_encoder}, {"params": head, "lr": args.lr_head}],
        weight_decay=1e-4,
    )
    total_steps = args.epochs * len(train_loader)
    scheduler = torch.optim.lr_scheduler.OneCycleLR(
        optimizer,
        max_lr=[args.lr_encoder, args.lr_head],
        total_steps=total_steps,
        pct_start=0.1,
    )
    scaler = torch.amp.GradScaler("cuda", enabled=device == "cuda")

    record = {
        "args": vars(args),
        "device": torch.cuda.get_device_name(0) if device == "cuda" else "cpu",
        "train_crops": len(train_files),
        "val_crops": len(val_files),
        "epochs": [],
    }
    baseline = evaluate(model, val_loader, device)
    print(json.dumps({"epoch": 0, "val": baseline}), flush=True)
    best = math.inf
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    for epoch in range(1, args.epochs + 1):
        started = time.perf_counter()
        running = 0.0
        for x, y in train_loader:
            x, y = x.to(device, non_blocking=True), y.to(device, non_blocking=True)
            with torch.autocast(device_type="cuda", dtype=torch.float16, enabled=device == "cuda"):
                pred = model(x)
            pred = pred.float()
            loss = (pred - y).abs().mean() + args.grad_weight * _gradient_loss(pred, y)
            optimizer.zero_grad(set_to_none=True)
            scaler.scale(loss).backward()
            scaler.unscale_(optimizer)
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            scaler.step(optimizer)
            scaler.update()
            scheduler.step()
            running += float(loss.detach())
        val = evaluate(model, val_loader, device)
        entry = {
            "epoch": epoch,
            "train_loss": running / len(train_loader),
            "val": val,
            "seconds": round(time.perf_counter() - started, 1),
        }
        record["epochs"].append(entry)
        print(json.dumps(entry), flush=True)
        if val["rmse"] < best:
            best = val["rmse"]
            torch.save({"model": model.state_dict()}, str(out))
            record["best"] = entry
    out.with_suffix(".json").write_text(json.dumps(record, indent=2))
    import hashlib

    digest = hashlib.sha256(out.read_bytes()).hexdigest()
    print(json.dumps({"checkpoint": str(out), "sha256": digest, "best": record.get("best")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
