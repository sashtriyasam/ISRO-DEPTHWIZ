"""
Validation for GAMUS records and loaded data.

Covers:
    pairing, shape, dtype, missing files, invalid values, class values,
    actionable error reporting without silent repair.

All validation works without requiring the full dataset — checks filesystem existence
and, when files are present and h5py available, probes array properties.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import List, Optional

from depthwizard.data.schemas import GAMUS_VALID_LABELS, GAMUS_SPLITS, GamusRecord, _strip_image_suffix, canonical_split


@dataclasses.dataclass
class ValidationIssue:
    level: str  # "error" or "warning"
    code: str  # machine-readable e.g. "missing_file", "shape_mismatch"
    message: str
    sample_id: Optional[str] = None
    field: Optional[str] = None

    def __str__(self) -> str:
        prefix = f"[{self.level}:{self.code}]"
        if self.sample_id:
            prefix += f" {self.sample_id}"
        if self.field:
            prefix += f" ({self.field})"
        return f"{prefix}: {self.message}"


@dataclasses.dataclass
class ValidationReport:
    issues: List[ValidationIssue]
    record_count: int

    @property
    def errors(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.level == "error"]

    @property
    def warnings(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.level == "warning"]

    @property
    def ok(self) -> bool:
        return len(self.errors) == 0

    def raise_if_errors(self) -> None:
        if not self.ok:
            msgs = "\n".join(str(e) for e in self.errors)
            raise ValueError(f"Validation failed with {len(self.errors)} error(s):\n{msgs}")

    def to_dict(self) -> dict:
        return {
            "record_count": self.record_count,
            "ok": self.ok,
            "errors": [dataclasses.asdict(e) for e in self.errors],
            "warnings": [dataclasses.asdict(e) for e in self.warnings],
        }


def _try_probe(path: Path):
    """Probe H5 file for shape/dtype/label values; returns (shape, dtype_str, arr_or_None, error_msg)."""
    try:
        import h5py  # type: ignore
        import numpy as np  # type: ignore
    except Exception as e:
        return (None, None, None, f"h5py/numpy not available: {e}")
    if not path.is_file():
        return (None, None, None, "file not found")
    try:
        with h5py.File(str(path), "r") as f:
            key = "image" if "image" in f else ("data" if "data" in f else None)
            if key is None:
                # fallback first key
                for k in f.keys():
                    if hasattr(f[k], "shape"):
                        key = k
                        break
            if key is None:
                return (None, None, None, "no dataset found in H5")
            dset = f[key]
            arr = dset[()]
            shape = getattr(arr, "shape", None) or getattr(dset, "shape", None)
            dtype = getattr(arr, "dtype", None) or getattr(dset, "dtype", None)
            dtype_str = str(dtype) if dtype is not None else None
            return (shape, dtype_str, arr, None)
    except Exception as e:
        return (None, None, None, str(e))


def validate_records(
    records: list[GamusRecord],
    root: Optional[Path | str] = None,
    *,
    check_files_exist: bool = True,
    check_pairing: bool = True,
    check_shape: bool = True,
    check_dtype: bool = True,
    check_classes: bool = True,
    probe_arrays: bool = False,
) -> ValidationReport:
    """Validate a list of GamusRecords.

    Args:
        records: Manifest records to validate.
        root: Dataset root for filesystem checks (if None, filesystem checks are skipped unless paths are absolute).
        check_files_exist: Verify image/height/label files exist under root.
        check_pairing: Verify sample_id ↔ path suffix consistency and split coherence.
        check_shape: Verify spatial compatibility (image vs height vs label) when probe_arrays True and files present.
        check_dtype: Verify expected dtypes were probed or manifest-declared (warning if unknown).
        check_classes: Validate semantic label values in [0..6] when probe_arrays True and label file present.
        probe_arrays: Whether to open H5 files to validate shapes/classes (requires h5py).

    Returns:
        ValidationReport with errors/warnings. Does not silently repair; caller decides to raise.

    Filesystem-independent checks (schema) always run.
    """
    issues: List[ValidationIssue] = []
    root_path = Path(root) if root is not None else None

    # Schema-level: duplicate sample_ids within same split?
    seen: dict[tuple[str, str], int] = {}
    for rec in records:
        key = (rec.split, rec.sample_id)
        seen[key] = seen.get(key, 0) + 1
    for (split, sid), cnt in seen.items():
        if cnt > 1:
            issues.append(
                ValidationIssue(
                    level="error",
                    code="duplicate_sample_id",
                    message=f"Duplicate sample_id '{sid}' in split '{split}' appears {cnt} times",
                    sample_id=sid,
                    field="sample_id",
                )
            )

    for rec in records:
        # Split canonicalization
        try:
            canonical_split(rec.split)
        except ValueError as e:
            issues.append(
                ValidationIssue(level="error", code="invalid_split", message=str(e), sample_id=rec.sample_id, field="split")
            )
        if rec.split not in GAMUS_SPLITS:
            # Already covered via canonical but keep
            pass

        # sample_id sanity
        if not rec.sample_id or not rec.sample_id.strip():
            issues.append(
                ValidationIssue(level="error", code="invalid_sample_id", message="Empty sample_id", field="sample_id")
            )
        if "/" in rec.sample_id or "\\" in rec.sample_id:
            issues.append(
                ValidationIssue(
                    level="error", code="invalid_sample_id", message="sample_id must not contain path separators", sample_id=rec.sample_id, field="sample_id"
                )
            )

        # Path pairing logic
        if check_pairing:
            # image_path should correspond to sample_id
            img_name = Path(rec.image_path).name
            derived = _strip_image_suffix(img_name)
            # derived may be None if not image-like
            if derived is None or derived != rec.sample_id:
                # Try lenient: check that sample_id appears as prefix
                if rec.sample_id not in img_name:
                    issues.append(
                        ValidationIssue(
                            level="error",
                            code="pairing_mismatch",
                            message=f"image_path '{rec.image_path}' does not match sample_id '{rec.sample_id}' (derived '{derived}')",
                            sample_id=rec.sample_id,
                            field="image_path",
                        )
                    )
            # Check that image_path contains expected split component
            if rec.split not in rec.image_path:
                issues.append(
                    ValidationIssue(
                        level="warning",
                        code="split_path_mismatch",
                        message=f"image_path '{rec.image_path}' does not contain split '{rec.split}'",
                        sample_id=rec.sample_id,
                        field="image_path",
                    )
                )
            for field_name, path_str, expected_suffix in [
                ("height_path", rec.height_path, "AGL.h5"),
                ("label_path", rec.label_path or "", "CLS.h5"),
            ]:
                if not path_str:
                    if field_name == "label_path":
                        continue  # nullable
                    issues.append(
                        ValidationIssue(level="error", code="missing_field", message=f"Missing {field_name}", sample_id=rec.sample_id, field=field_name)
                    )
                    continue
                if rec.sample_id not in Path(path_str).name:
                    issues.append(
                        ValidationIssue(
                            level="error",
                            code="pairing_mismatch",
                            message=f"{field_name} '{path_str}' does not match sample_id '{rec.sample_id}'",
                            sample_id=rec.sample_id,
                            field=field_name,
                        )
                    )
                if expected_suffix not in path_str:
                    issues.append(
                        ValidationIssue(
                            level="warning",
                            code="unexpected_suffix",
                            message=f"{field_name} '{path_str}' missing expected suffix '{expected_suffix}'",
                            sample_id=rec.sample_id,
                            field=field_name,
                        )
                    )

        # Filesystem existence
        if check_files_exist and root_path is not None:
            for field_name, path_str in [
                ("image_path", rec.image_path),
                ("height_path", rec.height_path),
                ("label_path", rec.label_path),
            ]:
                if path_str is None:
                    continue
                abs_path = (root_path / path_str) if not Path(path_str).is_absolute() else Path(path_str)
                if not abs_path.exists():
                    # If label missing in test split, downgrade to warning? Paper says all tiles annotated, so error.
                    level = "error"
                    issues.append(
                        ValidationIssue(
                            level=level,
                            code="missing_file",
                            message=f"Referenced file does not exist: {abs_path} (field {field_name})",
                            sample_id=rec.sample_id,
                            field=field_name,
                        )
                    )

        # Probing shapes/dtypes/classes
        if probe_arrays and root_path is not None:
            # Probe image
            img_abs = (root_path / rec.image_path) if not Path(rec.image_path).is_absolute() else Path(rec.image_path)
            h_abs = (root_path / rec.height_path) if not Path(rec.height_path).is_absolute() else Path(rec.height_path)
            lbl_abs = None
            if rec.label_path:
                lbl_abs = (root_path / rec.label_path) if not Path(rec.label_path).is_absolute() else Path(rec.label_path)

            img_shape, img_dtype, img_arr, img_err = _try_probe(img_abs) if img_abs.is_file() else (None, None, None, "not found")
            h_shape, h_dtype, h_arr, h_err = _try_probe(h_abs) if h_abs and h_abs.is_file() else (None, None, None, "not found")
            lbl_shape, lbl_dtype, lbl_arr, lbl_err = (None, None, None, None)
            if lbl_abs and lbl_abs.is_file():
                lbl_shape, lbl_dtype, lbl_arr, lbl_err = _try_probe(lbl_abs)

            if check_shape and img_shape is not None and h_shape is not None:
                # Spatial compatibility: first two dims should match
                if len(img_shape) >= 2 and len(h_shape) >= 2:
                    if img_shape[0] != h_shape[0] or img_shape[1] != h_shape[1]:
                        issues.append(
                            ValidationIssue(
                                level="error",
                                code="shape_mismatch",
                                message=f"Image shape {img_shape} vs height shape {h_shape} spatial mismatch",
                                sample_id=rec.sample_id,
                                field="height_path",
                            )
                        )
                if lbl_shape is not None and len(lbl_shape) >= 2:
                    if img_shape[0] != lbl_shape[0] or img_shape[1] != lbl_shape[1]:
                        issues.append(
                            ValidationIssue(
                                level="error",
                                code="shape_mismatch",
                                message=f"Image shape {img_shape} vs label shape {lbl_shape} spatial mismatch",
                                sample_id=rec.sample_id,
                                field="label_path",
                            )
                        )
            if check_dtype and img_dtype is not None:
                # Expect image uint8 3 channels; height float; but be lenient — warn vs error
                if "uint8" not in img_dtype.lower():
                    issues.append(
                        ValidationIssue(
                            level="warning",
                            code="unexpected_dtype",
                            message=f"Image dtype '{img_dtype}' unexpected (expected uint8)",
                            sample_id=rec.sample_id,
                            field="image_path",
                        )
                    )
            if check_classes and lbl_arr is not None:
                try:
                    import numpy as np  # type: ignore

                    uniq = np.unique(lbl_arr)
                    invalid = [int(v) for v in uniq if int(v) not in GAMUS_VALID_LABELS]
                    if invalid:
                        issues.append(
                            ValidationIssue(
                                level="error",
                                code="invalid_class_value",
                                message=f"Label contains invalid class values {invalid} (valid {sorted(GAMUS_VALID_LABELS)}), unique {sorted(map(int, uniq))[:12]}",
                                sample_id=rec.sample_id,
                                field="label_path",
                            )
                        )
                    # Also check shape dims: should be 2D
                    if lbl_arr.ndim not in (2, 3):
                        issues.append(
                            ValidationIssue(
                                level="warning",
                                code="unexpected_label_shape",
                                message=f"Label array ndim {lbl_arr.ndim} shape {lbl_arr.shape} unexpected (expected 2D HxW)",
                                sample_id=rec.sample_id,
                                field="label_path",
                            )
                        )
                except Exception as e:
                    issues.append(
                        ValidationIssue(
                            level="warning",
                            code="probe_failed",
                            message=f"Could not validate label classes: {e}",
                            sample_id=rec.sample_id,
                            field="label_path",
                        )
                    )
            # Height invalid values (nodata): GAMUS docs don't advertise a nodata sentinel, but we check for NaN/Inf extremes
            if h_arr is not None:
                try:
                    import numpy as np  # type: ignore

                    if h_arr.size > 0:
                        # Check for non-finite that aren't plausible height spikes?
                        # Use warning for inf/nan; actual nodata may be -9999 but not documented, so we only warn on extreme negative
                        if not np.all(np.isfinite(h_arr)):
                            # Allow? Warn
                            issues.append(
                                ValidationIssue(
                                    level="warning",
                                    code="non_finite_height",
                                    message="Height array contains non-finite (NaN/Inf) values",
                                    sample_id=rec.sample_id,
                                    field="height_path",
                                )
                            )
                except Exception:
                    pass

    return ValidationReport(issues=issues, record_count=len(records))


def validate_manifest_file(
    manifest_path: Path | str,
    root: Optional[Path | str] = None,
    probe_arrays: bool = False,
) -> ValidationReport:
    """Validate a manifest JSON file.

    Root defaults to manifest's `root` field if provided and `root` arg is None.
    """
    import json

    p = Path(manifest_path)
    data = json.loads(p.read_text(encoding="utf-8"))
    recs = [GamusRecord.from_dict(d) for d in data.get("records", [])]
    # Prefer explicit root arg, else manifest-declared root
    effective_root = root if root is not None else data.get("root")
    return validate_records(recs, root=effective_root, probe_arrays=probe_arrays)
