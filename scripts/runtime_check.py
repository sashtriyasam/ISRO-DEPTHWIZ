#!/usr/bin/env python3
"""DepthWizard runtime self-check (setup verification, never provisioning).

Validates the local runtime without downloading, installing, or
contacting the network:

  python scripts/runtime_check.py [--checkpoint PATH] [--device NAME]
      [--require-dav2] [--pretty]

Checks: interpreter version, core/optional dependency discoverability
(no heavy imports except an optional device probe), upstream DA-V2
source revision, checkpoint existence + SHA-256, backend/service
importability.

Exit 0 when every requested check passes, 1 when any check fails,
2 on CLI misuse. Stdout carries one JSON document; diagnostics go to
stderr. Reports location labels, never raw absolute paths.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from depthwizard.runtime.diagnostics import (  # noqa: E402
    CHECKPOINT_SHA256,
    MIN_PYTHON,
    availability_report,
    module_available,
    resolve_checkpoint,
    verify_checkpoint,
)


def check_device(name: str | None) -> dict[str, object]:
    """Probe a torch device (imports torch; requested explicitly only)."""
    if not module_available("torch"):
        return {"requested": name, "available": False, "code": "DEVICE_TORCH_MISSING"}
    import torch  # noqa: E402

    if name in (None, "cpu"):
        return {"requested": name or "cpu", "available": True, "code": "OK"}
    if name == "cuda":
        available = bool(torch.cuda.is_available())
        return {
            "requested": name,
            "available": available,
            "code": "OK" if available else "DEVICE_UNAVAILABLE",
        }
    if name == "mps":
        available = bool(getattr(torch.backends, "mps", None) is not None)
        available = available and bool(torch.backends.mps.is_available())
        return {
            "requested": name,
            "available": available,
            "code": "OK" if available else "DEVICE_UNAVAILABLE",
        }
    return {"requested": name, "available": False, "code": "DEVICE_UNKNOWN"}


def main(argv: list[str] | None = None) -> int:
    """Run the self-check and emit the JSON report."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", default=None, help="explicit checkpoint path")
    parser.add_argument("--device", default=None, help="probe a torch device")
    parser.add_argument(
        "--require-dav2",
        action="store_true",
        help="fail unless the full DA-V2 runtime is available",
    )
    parser.add_argument("--pretty", action="store_true", help="indent JSON output")
    args = parser.parse_args(argv)

    report = availability_report()
    failures: list[str] = []

    python = report["python"]
    assert isinstance(python, dict)
    if not python["meets_minimum"]:
        failures.append(
            f"PYTHON_VERSION_UNSUPPORTED: {python['version']} < {MIN_PYTHON[0]}.{MIN_PYTHON[1]}"
        )

    core = report["core_modules"]
    assert isinstance(core, dict)
    missing_core = sorted(name for name, ok in core.items() if not ok)
    if missing_core:
        failures.append(f"CORE_DEPENDENCY_MISSING: {', '.join(missing_core)}")
    if not report["core_ready"]:
        failures.append("CORE_BACKEND_UNIMPORTABLE: synthetic/service import failed")

    if args.require_dav2 or args.device:
        dav2 = report["dav2_modules"]
        assert isinstance(dav2, dict)
        missing = sorted(name for name, ok in dav2.items() if not ok)
        if missing:
            failures.append(f"DAV2_DEPENDENCY_MISSING: {', '.join(missing)}")
        if not report["dav2_source_present"]:
            failures.append("DAV2_SOURCE_MISSING: upstream source not discoverable")
        checkpoint_info = report["checkpoint"]
        assert isinstance(checkpoint_info, dict)
        if str(checkpoint_info["code"]) != "OK":
            failures.append(f"{checkpoint_info['code']}: checkpoint not verified")

    if args.checkpoint:
        status = verify_checkpoint(Path(args.checkpoint), CHECKPOINT_SHA256)
        report["explicit_checkpoint"] = {
            "ok": status.ok,
            "code": status.code,
            "detail": status.detail,
        }
        if not status.ok:
            failures.append(f"{status.code}: explicit checkpoint rejected")

    if args.device:
        device = check_device(args.device)
        report["device"] = device
        if not device["available"]:
            failures.append(f"{device['code']}: device {args.device} unavailable")
    else:
        _path, location = resolve_checkpoint(args.checkpoint)
        report["checkpoint_location"] = location

    report["healthy"] = not failures
    report["failures"] = failures
    print(json.dumps(report, indent=2 if args.pretty else None))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
