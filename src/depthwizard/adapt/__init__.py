"""Frozen-backbone adaptation for GAMUS nDSM/AGL height (M4, research only).

Stage A: frozen DA-V2-Small representations -> lightweight trainable head.
The backbone is NEVER unfrozen here (see `freeze_backbone` + tests).
Output semantics: metric GAMUS nDSM/AGL prediction for scientific evaluation
only — not a replacement for Shivam's final calibration architecture.
"""

from depthwizard.adapt.model import AdaptedDepthModel

__all__ = ["AdaptedDepthModel"]
