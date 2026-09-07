#!/usr/bin/env python3
"""Provision a managed DepthWizard runtime (host-invocable, JSON status).

Establishes ``<runtime-dir>`` as an isolated virtual environment,
installs the project (core or ``[dav2]``), provisions the pinned
DA-V2 source and SHA-verified checkpoint into the host data dir, then
reports provision -> verify -> launch-readiness as one JSON document.

Provisioning steps (pip, git clone, checkpoint fetch) may use the
network. Runtime inference afterwards must not.

Exit 0 when the requested runtime is ready, 1 when any step fails,
2 on CLI misuse. Stdout carries the status document (location labels,
never absolute paths); human diagnostics go to stderr.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from depthwizard.runtime.provision import (  # noqa: E402
    CORE_MODE,
    DAV2_MODE,
    ProvisionRequest,
    provision,
)


def main(argv: list[str] | None = None) -> int:
    """Parse host arguments, provision, and emit the status document."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-dir", required=True, help="managed runtime directory")
    parser.add_argument("--mode", default=CORE_MODE, choices=(CORE_MODE, DAV2_MODE))
    parser.add_argument("--python", default=None, help="base interpreter for the venv")
    parser.add_argument("--project-root", default=None, help="project source directory")
    parser.add_argument("--data-dir", default=None, help="host data directory override")
    parser.add_argument(
        "--checkpoint-src", default=None, help="local checkpoint file to verify+store"
    )
    parser.add_argument(
        "--fetch-checkpoint",
        action="store_true",
        help="download ONLY the fixed checkpoint identity, then verify",
    )
    parser.add_argument("--skip-pip", action="store_true", help="skip package installation")
    parser.add_argument("--pretty", action="store_true", help="indent JSON output")
    args = parser.parse_args(argv)

    request = ProvisionRequest(
        runtime_dir=Path(args.runtime_dir),
        mode=args.mode,
        python=Path(args.python) if args.python else None,
        project_root=Path(args.project_root) if args.project_root else None,
        data_dir=Path(args.data_dir) if args.data_dir else None,
        checkpoint_src=Path(args.checkpoint_src) if args.checkpoint_src else None,
        fetch_checkpoint=args.fetch_checkpoint,
        skip_pip=args.skip_pip,
    )
    status = provision(request)
    print(json.dumps(status.to_dict(), indent=2 if args.pretty else None))
    return 0 if status.ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
