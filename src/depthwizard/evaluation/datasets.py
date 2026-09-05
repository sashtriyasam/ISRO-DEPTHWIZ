"""Dataset abstraction: manifest-identified samples, no data committed.

An ``EvaluationSample`` carries everything needed to reproduce one
comparison (paths are manifest-relative; checksums bind content).
Dataset adapters read established on-disk layouts; they never download.
"""

from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import numpy as np
from pydantic import BaseModel, ConfigDict, Field

from depthwizard.contracts.semantics import ElevationSemantics


class EvaluationSample(BaseModel):
    """One reproducible evaluation unit (metadata only, no arrays)."""

    model_config = ConfigDict(frozen=True)

    sample_id: str = Field(min_length=1)
    dataset_name: str = Field(min_length=1)
    split: str = Field(min_length=1)
    image_path: str = Field(min_length=1, description="Manifest-relative image path.")
    reference_path: str = Field(min_length=1, description="Manifest-relative reference path.")
    input_checksum: str | None = None
    reference_checksum: str | None = None
    source: dict[str, str] = Field(
        default_factory=dict, description="Provenance strings (release, tile, city)."
    )


class ReferenceInfo(BaseModel):
    """Loaded reference surface with its declared meaning."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    values: Any = Field(description="2D float array, metric reference surface.")
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    units: str = Field(description="Must be explicit metric units ('meters').")
    semantics: ElevationSemantics = Field(description="Declared reference meaning.")
    crs: str | None = Field(
        default=None, description="CRS identifier, when the raster carries one."
    )
    valid_mask: Any = Field(description="2D bool array: reference pixels usable for scoring.")


class LoadedSample(BaseModel):
    """In-memory sample payload (orchestration only, never serialized)."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    sample: EvaluationSample
    image_rgb: Any = Field(description="HWC uint8 RGB array.")
    reference: ReferenceInfo


class EvaluationDataset(ABC):
    """Minimal dataset adapter contract (read-only, no downloads)."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Dataset identifier (matches manifest entries)."""

    @abstractmethod
    def list_samples(self) -> list[EvaluationSample]:
        """Enumerate manifest samples in deterministic order."""

    @abstractmethod
    def load_sample(self, sample: EvaluationSample) -> LoadedSample:
        """Load image + reference arrays for one sample."""


def sha256_file(path: Path) -> str:
    """Stream a file's SHA-256 hex digest."""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1048576), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_h5_array(path: Path) -> np.ndarray:
    """Read an H5 tile probing keys ``image`` then ``data`` then first dataset."""
    import h5py

    with h5py.File(path, "r") as handle:
        for key in ("image", "data"):
            if key in handle and isinstance(handle[key], h5py.Dataset):
                return np.array(handle[key])
        for value in handle.values():
            if isinstance(value, h5py.Dataset):
                return np.array(value)
    raise ValueError(f"no readable dataset in {path.name}")


class GamusDataset(EvaluationDataset):
    """GAMUS tile reader (independent implementation from the documented layout).

    Layout ``<root>/images/<split>/*_RGB.h5`` + ``heights/<split>/*_AGL.h5``.
    RGB is uint8 (H, W, 3); height is floating-point AGL in meters.
    GAMUS tiles carry no CRS/transform: grids are pixel-native and must
    match the prediction shape exactly (see ``alignment``).
    """

    def __init__(
        self, root: Path, split: str, manifest: list[EvaluationSample] | None = None
    ) -> None:
        """Bind a dataset root, split, and optional manifest filter."""
        self._root = root
        self._split = split
        self._manifest = manifest

    @property
    def name(self) -> str:
        """Dataset identifier."""
        return "gamus"

    def list_samples(self) -> list[EvaluationSample]:
        """Enumerate samples (manifest order, else directory scan)."""
        if self._manifest is not None:
            return sorted(self._manifest, key=lambda sample: sample.sample_id)
        images = sorted((self._root / "images" / self._split).glob("*_RGB.h5"))
        samples = []
        for image_path in images:
            stem = image_path.name[: -len("_RGB.h5")]
            samples.append(
                EvaluationSample(
                    sample_id=f"gamus-{self._split}-{stem}",
                    dataset_name="gamus",
                    split=self._split,
                    image_path=str(image_path.relative_to(self._root)),
                    reference_path=str(Path("heights") / self._split / f"{stem}_AGL.h5"),
                )
            )
        return samples

    def load_sample(self, sample: EvaluationSample) -> LoadedSample:
        """Load RGB + AGL reference for one manifest sample."""
        image_file = self._root / sample.image_path
        reference_file = self._root / sample.reference_path
        if not image_file.is_file():
            raise FileNotFoundError(f"image missing: {image_file.name}")
        if not reference_file.is_file():
            raise FileNotFoundError(f"reference missing: {reference_file.name}")
        rgb = _read_h5_array(image_file)
        if rgb.ndim != 3 or rgb.shape[2] < 3:
            raise ValueError(f"expected HWC RGB in {image_file.name}, got shape {rgb.shape}")
        rgb = np.ascontiguousarray(rgb[:, :, :3]).astype(np.uint8)
        height, width = rgb.shape[:2]
        agl = _read_h5_array(reference_file)
        agl = np.asarray(agl, dtype=np.float64)
        if agl.ndim == 3:
            agl = agl.reshape(agl.shape[0], agl.shape[1], -1)[:, :, 0]
        if agl.shape != (height, width):
            raise ValueError(
                f"reference shape {agl.shape} != image shape {(height, width)} "
                f"for {sample.sample_id}"
            )
        finite = np.isfinite(agl)
        reference = ReferenceInfo(
            values=np.ascontiguousarray(agl),
            width=width,
            height=height,
            units="meters",
            semantics=ElevationSemantics.HEIGHT_AGL_NDSM,
            crs=None,
            valid_mask=np.ascontiguousarray(finite),
        )
        return LoadedSample(sample=sample, image_rgb=np.ascontiguousarray(rgb), reference=reference)
