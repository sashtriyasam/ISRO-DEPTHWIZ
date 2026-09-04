"""Depth inference boundary — backend interface and result contract.

Shared interfaces: changes here require Shravan + Shivam review (AGENTS.md).

Scientific guardrails (enforced, see M3 spec):
    Rule A: relative model output is NEVER metric height.
    Rule B: no silent scale conversion (metric access raises).
    Rule E: no calibration lives here (evaluation-only affine alignment is in
        `depthwizard.eval`, clearly separated from production calibration).
"""

from depthwizard.depth.base import DepthBackend, DepthResult

__all__ = ["DepthBackend", "DepthResult"]
