"""PROTOTERRA - Pipeline v2 package.

Provides geomorphometric extraction, planetary archetype discovery, multi-criteria
matching, geological categorization, dust/ice classification, and dataset export
for Earth, Moon, and Mars analog environments.
"""

from .config import (
    BODY_RADII_M,
    FEATURE_NAMES,
    MAX_ABS_ELEV_M,
    MIN_VALID_FRAC,
    PATCH_PIXELS,
    PATCH_RES_M,
    PATCH_SIZE_KM,
)

__all__ = [
    "BODY_RADII_M",
    "FEATURE_NAMES",
    "MAX_ABS_ELEV_M",
    "MIN_VALID_FRAC",
    "PATCH_PIXELS",
    "PATCH_RES_M",
    "PATCH_SIZE_KM",
]
