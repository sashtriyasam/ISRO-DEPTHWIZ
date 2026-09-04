"""
Configuration for GAMUS dataset foundation.

Uses repository's established mechanism: `GamusConfig` (env `GAMUS_ROOT` or JSON file),
not hardcoded absolute paths. Supports dataset root, manifest location, dev-subset params.

Example JSON (`configs/gamus.example.json`):
    {
      "root": "./data/gamus",
      "manifest": "./manifests/gamus.manifest.json",
      "split": "train",
      "dev_subset_size": 20,
      "dev_seed": "depthwizard-m1",
      "validation_strict": true
    }

Environment overrides:
    GAMUS_ROOT, GAMUS_MANIFEST, GAMUS_SPLIT, GAMUS_DEV_SIZE, GAMUS_DEV_SEED

Shared interfaces: changes here require Shravan + Shivam review.
"""

from __future__ import annotations

import dataclasses
import json
import os
from pathlib import Path
from typing import Optional


@dataclasses.dataclass
class GamusConfig:
    """Minimal dataset configuration.

    Attributes:
        root: Dataset root directory (contains images/, heights/, classes/).
              Resolved from explicit arg, then GAMUS_ROOT env, then config JSON, else Path("data/gamus").
        manifest: Path to manifest JSON (relative to project or absolute).
        split: Default split for operations (train|val|test, canonicalized).
        dev_subset_size: Number of samples in deterministic dev subset.
        dev_seed: Hash seed for deterministic subset selection.
        dev_split_source: Split from which dev subset is drawn.
        validation_strict: If True, validation raises on first error; if False, collects.
    """

    root: Path = dataclasses.field(default_factory=lambda: Path(os.environ.get("GAMUS_ROOT", "data/gamus")))
    manifest: Path = dataclasses.field(
        default_factory=lambda: Path(os.environ.get("GAMUS_MANIFEST", "manifests/gamus.manifest.json"))
    )
    split: str = dataclasses.field(default_factory=lambda: os.environ.get("GAMUS_SPLIT", "train"))
    dev_subset_size: int = dataclasses.field(
        default_factory=lambda: int(os.environ.get("GAMUS_DEV_SIZE", "20"))
    )
    dev_seed: str = dataclasses.field(default_factory=lambda: os.environ.get("GAMUS_DEV_SEED", "depthwizard-m1"))
    dev_split_source: str = dataclasses.field(
        default_factory=lambda: os.environ.get("GAMUS_DEV_SPLIT", "train")
    )
    validation_strict: bool = True

    def __post_init__(self) -> None:
        # Normalize paths
        self.root = Path(self.root)
        self.manifest = Path(self.manifest)
        # Normalize split
        from depthwizard.data.schemas import canonical_split

        try:
            self.split = canonical_split(self.split)
        except ValueError:
            # allow empty/invalid during tests — validation will catch
            pass
        try:
            self.dev_split_source = canonical_split(self.dev_split_source)
        except ValueError:
            pass
        if self.dev_subset_size < 0:
            raise ValueError("dev_subset_size must be >= 0")

    @classmethod
    def from_json(cls, path: Path | str) -> "GamusConfig":
        p = Path(path)
        data = json.loads(p.read_text(encoding="utf-8"))
        # Support both flat and nested keys ("dataset": {...})
        if "dataset" in data and isinstance(data["dataset"], dict):
            data = {**data, **data["dataset"]}
        # Map known keys
        kwargs: dict = {}
        if "root" in data:
            kwargs["root"] = Path(data["root"])
        if "manifest" in data:
            kwargs["manifest"] = Path(data["manifest"])
        if "split" in data:
            kwargs["split"] = str(data["split"])
        if "dev_subset_size" in data:
            kwargs["dev_subset_size"] = int(data["dev_subset_size"])
        if "devSize" in data and "dev_subset_size" not in kwargs:
            kwargs["dev_subset_size"] = int(data["devSize"])
        if "dev_seed" in data:
            kwargs["dev_seed"] = str(data["dev_seed"])
        if "devSeed" in data and "dev_seed" not in kwargs:
            kwargs["dev_seed"] = str(data["devSeed"])
        if "dev_split_source" in data:
            kwargs["dev_split_source"] = str(data["dev_split_source"])
        if "validation_strict" in data:
            kwargs["validation_strict"] = bool(data["validation_strict"])
        # Env overrides still apply if not explicitly set in JSON? We apply env after.
        # Construct then overlay env where env var is set
        cfg = cls(**kwargs) if kwargs else cls()
        # Env vars take precedence if set
        if os.environ.get("GAMUS_ROOT"):
            cfg.root = Path(os.environ["GAMUS_ROOT"])
        if os.environ.get("GAMUS_MANIFEST"):
            cfg.manifest = Path(os.environ["GAMUS_MANIFEST"])
        return cfg

    def to_dict(self) -> dict:
        return {
            "root": str(self.root.as_posix()),
            "manifest": str(self.manifest.as_posix()),
            "split": self.split,
            "dev_subset_size": self.dev_subset_size,
            "dev_seed": self.dev_seed,
            "dev_split_source": self.dev_split_source,
            "validation_strict": self.validation_strict,
        }

    def to_json(self, path: Path | str, indent: int = 2) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(self.to_dict(), indent=indent, sort_keys=True) + "\n", encoding="utf-8")

    def resolve_root(self) -> Path:
        """Return absolute root path, resolving relative to project root if needed.

        Project root is inferred as parent of `src/` when running from repo.
        Falls back to cwd.
        """
        if self.root.is_absolute():
            return self.root
        # Try to resolve relative to project root (isro depth wizard)
        # Walk up from this file: .../src/depthwizard/data/config.py -> .../src -> project root
        try:
            project_root = Path(__file__).resolve().parents[3]
            # Heuristic: project root contains `src` and `configs`
            if (project_root / "src").exists():
                return (project_root / self.root).resolve()
        except Exception:
            pass
        return (Path.cwd() / self.root).resolve()

    def exists(self) -> bool:
        return self.resolve_root().exists()
