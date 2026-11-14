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

MARS_RAW_FILES: dict[str, str] = {
    "dem": "mars/Mars_MGS_MOLA_DEM_mosaic_global_463m.tif",
    "themis_day": "mars/Mars_ODY_THEMIS_IR_Day_Mosaic_100m.tif",
    "themis_night": "mars/Mars_MO_THEMIS-IR-Night_mosaic_60N60S_100m_v14.tif",
}

MOON_RAW_FILES: dict[str, str] = {
    "dem": "moon/Lunar_LRO_LOLA_Global_LDEM_118m.tif",
    "wac_reflectance": "moon/Lunar_LRO_LROC-WAC_Mosaic_global_100m_June2013.tif",
    "ice_south": "moon/Moon_IceFavorabilityIndex_90S000E_591mp.tif",
    "ice_north": "moon/Moon_IceFavorabilityIndex_90N000E_591mp.tif",
    "diviner_prp": "moon/diviner/dlre_prp_south.tab",
}

DIVINER_PARQUET_REL: str = "diviner_prp_south.parquet"

EARTH_RAW_FILES: dict[str, str] = {
    "ndvi_dir": "earth/modis/ndvi",
    "lst_dir": "earth/modis/lst",
    "roads": "earth/naturalearth/ne_10m_roads/ne_10m_roads.shp",
    "airports": "earth/naturalearth/ne_10m_airports/ne_10m_airports.shp",
    "countries": "earth/naturalearth/ne_10m_admin_0_countries/ne_10m_admin_0_countries.shp",
}

EARTH_DERIVED_FILES: dict[str, str] = {
    "ndvi_max": "ndvi_max_2023.tif",
    "lst": "lst_2023.tif",
}

MODIS_CMG_RES_DEG: float = 0.05
