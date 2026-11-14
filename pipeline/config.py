"""Constantes y rutas compartidas para el pipeline v2."""

from pathlib import Path

PATCH_SIZE_KM: float = 32.0
PATCH_RES_M: float = 500.0
PATCH_PIXELS: int = 64
MIN_VALID_FRAC: float = 0.90
MAX_ABS_ELEV_M: float = 1e5
WINDOW_MARGIN_PX: int = 2

WGS84_SEMI_MAJOR_M: float = 6378137.0

BODY_RADII_M: dict[str, float] = {
    "Earth": 6371000.0,
    "Moon": 1737400.0,
    "Mars": 3396190.0,
}

FEATURE_NAMES: list[str] = [
    "mean_slope_deg",
    "p90_slope_deg",
    "relief_m",
    "hypsometric_integral",
    "detrended_std_m",
    "tri_m",
    "mean_elev_m",
]

YUCA_PROJECT_DIR: Path = Path("/lustre/proyectos/p089")
RAW_DATA_DIR: Path = YUCA_PROJECT_DIR / "data" / "raw"
DERIVED_DATA_DIR: Path = YUCA_PROJECT_DIR / "data" / "derived"
RUNS_DIR: Path = YUCA_PROJECT_DIR / "runs"
