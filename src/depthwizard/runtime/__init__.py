"""Runtime packaging diagnostics (environment facts, never science).

Helpers for setup verification and runtime self-checks: interpreter
version, dependency availability (import discovery only, no heavy
imports), checkpoint resolution/verification, and upstream revision
reporting. Used by ``scripts/runtime_check.py`` and packaging tests.
"""

from depthwizard.runtime.diagnostics import (
    CHECKPOINT_FILE as CHECKPOINT_FILE,
)
from depthwizard.runtime.diagnostics import (
    CHECKPOINT_SHA256 as CHECKPOINT_SHA256,
)
from depthwizard.runtime.diagnostics import (
    CORE_MODULES as CORE_MODULES,
)
from depthwizard.runtime.diagnostics import (
    DAV2_MODULES as DAV2_MODULES,
)
from depthwizard.runtime.diagnostics import (
    MIN_PYTHON as MIN_PYTHON,
)
from depthwizard.runtime.diagnostics import (
    UPSTREAM_REVISION as UPSTREAM_REVISION,
)
from depthwizard.runtime.diagnostics import (
    UPSTREAM_URL as UPSTREAM_URL,
)
from depthwizard.runtime.diagnostics import (
    CheckStatus as CheckStatus,
)
from depthwizard.runtime.diagnostics import (
    availability_report as availability_report,
)
from depthwizard.runtime.diagnostics import (
    default_data_dir as default_data_dir,
)
from depthwizard.runtime.diagnostics import (
    resolve_checkpoint as resolve_checkpoint,
)
from depthwizard.runtime.diagnostics import (
    sha256_file as sha256_file,
)
from depthwizard.runtime.diagnostics import (
    upstream_revision as upstream_revision,
)
from depthwizard.runtime.diagnostics import (
    verify_checkpoint as verify_checkpoint,
)

__all__ = [
    "CHECKPOINT_FILE",
    "CHECKPOINT_SHA256",
    "CORE_MODULES",
    "DAV2_MODULES",
    "MIN_PYTHON",
    "UPSTREAM_REVISION",
    "UPSTREAM_URL",
    "CheckStatus",
    "availability_report",
    "default_data_dir",
    "resolve_checkpoint",
    "sha256_file",
    "upstream_revision",
    "verify_checkpoint",
]
