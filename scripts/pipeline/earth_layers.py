"""Global and local Earth layers (T6): MODIS NDVI/LST, logistics, country, and known analog catalog.

This module provides environmental and logistics feature extraction for Earth analog sites:
1. Vegetation Index (MODIS MOD13C2 0.05° CMG):
   - Computes annual Maximum Value Composite (MVC) NDVI across 12 monthly composites.
   - Evaluates vegetation masks (NDVI <= 0.25) to isolate arid/barren surfaces.
2. Land Surface Temperature (MODIS MOD11C3 0.05° CMG):
   - Calculates annual mean daytime LST, nighttime LST, and seasonal diurnal amplitude (°C).
3. Terrestrial Logistics Proximity:
   - Evaluates geodesic distance (km) to nearest roadway from Natural Earth 10m roads
     (densified to 0.02° segment intervals, excluding ferry routes) via BallTree spatial index.
   - Evaluates geodesic distance (km) and attributes (IATA code, name) of nearest commercial
     civilian airport from Natural Earth 10m airports (excluding military and spaceport sites).
4. Sovereign Border Attribution:
   - Points-in-polygon spatial join with Natural Earth 10m administrative country boundaries,
     with a 25 km coastal buffer for maritime/island analog sites.
5. Known Planetary Analogs Catalog:
   - Validates coordinates against curated field analog stations (Atacama, McMurdo Dry Valleys,
     Iceland volcanic fields, Hawaii basalt flows, Utah MDRS, etc.) to tag KNOWN_ANALOG vs NEW_CANDIDATE.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import subprocess
import time

import geopandas as gpd
import matplotlib

matplotlib.use("Agg")
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import rasterio
from rasterio.transform import from_origin
import shapely
from sklearn.neighbors import BallTree

from .config import (
    EARTH_DERIVED_FILES,
    EARTH_RAW_FILES,
    MODIS_CMG_RES_DEG,
    YUCA_PROJECT_DIR,
)

KNOWN_ANALOGS_JSON: Path = Path(__file__).resolve().parents[2] / "data" / "known_analogs.json"

NDVI_SDS: str = "CMG 0.05 Deg Monthly NDVI"
NDVI_FILL: int = -3000
NDVI_RAW_MIN: int = -2000
NDVI_RAW_MAX: int = 10000
NDVI_DIVISOR: float = 10000.0
NDVI_MIN_VALID: float = -0.3

LST_DAY_SDS: str = "LST_Day_CMG"
LST_NIGHT_SDS: str = "LST_Night_CMG"
LST_FILL: int = 0
LST_MIN_RAW: int = 7500
LST_SCALE: float = 0.02
KELVIN_0C: float = 273.15
MIN_MONTHS_LST: int = 3

MODIS_GRID_SHAPE: tuple[int, int] = (3600, 7200)
MIN_COS_LAT: float = 0.05

ROAD_DENSIFY_DEG: float = 0.02
AIRPORT_EXCLUDE_TYPES: set[str] = {
    "military",
    "military mid",
    "military major",
    "spaceport",
}
EARTH_RADIUS_KM: float = 6371.0

EARTH_ENV_COLUMNS: list[str] = [
    "ndvi_max",
    "lst_day_c",
    "lst_night_c",
    "lst_amplitude_c",
    "dist_road_km",
    "dist_airport_km",
    "nearest_airport_iata",
    "nearest_airport_name",
    "country",
    "known_region",
    "classification",
]

NUMERIC_ENV_COLUMNS: tuple[str, ...] = (
    "ndvi_max",
    "lst_day_c",
    "lst_night_c",
    "lst_amplitude_c",
    "dist_road_km",
    "dist_airport_km",
)

TEXT_ENV_COLUMNS: tuple[str, ...] = (
    "nearest_airport_iata",
    "nearest_airport_name",
    "country",
    "known_region",
    "classification",
)


def ndvi_from_raw(raw: np.ndarray) -> np.ndarray:
    """Convert raw int16 MOD13C2 NDVI counts to float32 NDVI in [-0.3, 1.0]; mask fill values as NaN."""
    arr = np.asarray(raw)
    valid = (arr != NDVI_FILL) & (arr >= NDVI_RAW_MIN) & (arr <= NDVI_RAW_MAX)
    out = np.full(arr.shape, np.nan, dtype=np.float32)
    if np.any(valid):
        scaled = arr[valid].astype(np.float64) / NDVI_DIVISOR
        scaled[scaled < NDVI_MIN_VALID] = np.nan
        out[valid] = scaled.astype(np.float32)
    return out


def lst_c_from_raw(raw: np.ndarray) -> np.ndarray:
    """Convert raw uint16 MOD11C3 counts to Celsius float32; mask fill and uncalibrated values as NaN."""
    arr = np.asarray(raw)
    valid = (arr != LST_FILL) & (arr >= LST_MIN_RAW) & np.isfinite(arr)
    out = np.full(arr.shape, np.nan, dtype=np.float32)
    if np.any(valid):
        temp_k = arr[valid].astype(np.float64) * LST_SCALE
        out[valid] = (temp_k - KELVIN_0C).astype(np.float32)
    return out


def running_nanmax(acc: np.ndarray | None, x: np.ndarray) -> np.ndarray:
    """Compute cumulative element-wise maximum ignoring NaN (np.fmax)."""
    arr = np.asarray(x, dtype=np.float32)
    if acc is None:
        return arr.copy()
    return np.fmax(acc, arr)


def running_sum_count(
    sum_: np.ndarray | None,
    cnt: np.ndarray | None,
    x: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Accumulate sum (float64) and count (uint8) of finite values in-place."""
    arr = np.asarray(x, dtype=np.float64)
    finite = np.isfinite(arr)
    if sum_ is None:
        sum_out = np.zeros(arr.shape, dtype=np.float64)
    else:
        sum_out = np.asarray(sum_, dtype=np.float64)
    if cnt is None:
        cnt_out = np.zeros(arr.shape, dtype=np.uint8)
    else:
        cnt_out = np.asarray(cnt, dtype=np.uint8)
    if np.any(finite):
        sum_out[finite] += arr[finite]
        cnt_out[finite] += 1
    return sum_out, cnt_out


def finalize_mean(
    sum_: np.ndarray,
    cnt: np.ndarray,
    min_count: int = MIN_MONTHS_LST,
) -> np.ndarray:
    """Compute mean array as float32; cells with count < min_count are set to NaN."""
    sum_arr = np.asarray(sum_, dtype=np.float64)
    cnt_arr = np.asarray(cnt)
    out = np.full(sum_arr.shape, np.nan, dtype=np.float32)
    ok = cnt_arr >= min_count
    if np.any(ok):
        out[ok] = (sum_arr[ok] / cnt_arr[ok]).astype(np.float32)
    return out


def _normalize_lon(lon: np.ndarray) -> np.ndarray:
    """Normalize longitudes to the semi-open interval [-180, 180)."""
    return ((lon + 180.0) % 360.0) - 180.0


def cell_index(
    lat: np.ndarray | float,
    lon: np.ndarray | float,
    res: float = MODIS_CMG_RES_DEG,
) -> tuple[np.ndarray | int, np.ndarray | int]:
    """Return row and column indices of CMG grid cell containing (lat, lon)."""
    scalar = np.ndim(lat) == 0 and np.ndim(lon) == 0
    lat_arr = np.asarray(lat, dtype=np.float64)
    lon_arr = _normalize_lon(np.asarray(lon, dtype=np.float64))
    n_rows = int(round(180.0 / res))
    n_cols = int(round(360.0 / res))
    row = np.clip(np.floor((90.0 - lat_arr) / res).astype(np.int64), 0, n_rows - 1)
    col = np.clip(np.floor((lon_arr + 180.0) / res).astype(np.int64), 0, n_cols - 1)
    if scalar:
        return int(row), int(col)
    return row, col


def patch_window_stat(
    grid: np.ndarray,
    lat: np.ndarray | float,
    lon: np.ndarray | float,
    half_km: float,
    stat: str,
    res: float = MODIS_CMG_RES_DEG,
) -> np.ndarray:
    """Compute patch-level spatial statistic ('median', 'mean', or 'max') over CMG raster window."""
    if stat not in {"median", "mean", "max"}:
        raise ValueError(f"Invalid stat: {stat!r} (expected 'median', 'mean', or 'max')")
    grid_arr = np.asarray(grid)
    if grid_arr.ndim != 2:
        raise ValueError(f"grid must be 2D, has shape {grid_arr.shape}")
    _, n_cols = grid_arr.shape

    lat_arr = np.atleast_1d(np.asarray(lat, dtype=np.float64))
    lon_arr = _normalize_lon(np.atleast_1d(np.asarray(lon, dtype=np.float64)))
    if lat_arr.shape != lon_arr.shape:
        raise ValueError("lat and lon arrays must have identical shape")

    dlat = math.degrees(half_km / EARTH_RADIUS_KM)
    cos_lat = np.maximum(np.cos(np.radians(lat_arr)), MIN_COS_LAT)
    dlon = dlat / cos_lat

    row_top, _ = cell_index(np.clip(lat_arr + dlat, -90.0, 90.0), lon_arr, res=res)
    row_bot, _ = cell_index(np.clip(lat_arr - dlat, -90.0, 90.0), lon_arr, res=res)
    _, col_left = cell_index(lat_arr, lon_arr - dlon, res=res)
    _, col_right = cell_index(lat_arr, lon_arr + dlon, res=res)

    out = np.full(lat_arr.shape[0], np.nan, dtype=np.float32)
    valid_pts = np.isfinite(lat_arr) & np.isfinite(lon_arr)

    for i in np.flatnonzero(valid_pts):
        r0 = int(row_top[i])
        r1 = int(row_bot[i])
        if r0 > r1:
            r0, r1 = r1, r0
        c0 = int(col_left[i])
        c1 = int(col_right[i])

        if c0 <= c1:
            block = grid_arr[r0 : r1 + 1, c0 : c1 + 1]
        else:
            # Antimeridian wrap-around: patch crosses column n_cols - 1 -> 0
            span = (c1 - c0) % n_cols
            cols = (c0 + np.arange(span + 1, dtype=np.int64)) % n_cols
            block = grid_arr[r0 : r1 + 1, cols]

        vals = block[np.isfinite(block)]
        if vals.size == 0:
            continue
        if stat == "median":
            out[i] = float(np.median(vals))
        elif stat == "mean":
            out[i] = float(np.mean(vals))
        else:
            out[i] = float(np.max(vals))

    return out


def _list_monthly_hdfs(hdf_dir: Path, expected_count: int = 12) -> list[Path]:
    """List and validate the 12 monthly MODIS HDF4 files sorted by filename."""
    directory = Path(hdf_dir)
    if not directory.is_dir():
        raise FileNotFoundError(f"MODIS directory not found: {directory}")
    files = sorted(
        p for p in directory.iterdir() if p.is_file() and p.suffix.lower() == ".hdf"
    )
    if len(files) != expected_count:
        raise ValueError(
            f"Expected {expected_count} .hdf files in {directory}, found {len(files)}"
        )
    return files


def _read_hdf_sds(hdf_path: Path, sds_names: tuple[str, ...]) -> dict[str, np.ndarray]:
    """Read one or more Science Data Sets (SDS) from a MODIS HDF4 file using pyhdf."""
    from pyhdf.SD import SD, SDC  # lazy import: synthetic tests do not require pyhdf

    sd = SD(str(hdf_path), SDC.READ)
    try:
        out: dict[str, np.ndarray] = {}
        for name in sds_names:
            arr = sd.select(name).get()
            if arr.shape != MODIS_GRID_SHAPE:
                raise ValueError(
                    f"Unexpected shape for SDS {name!r} in {hdf_path.name}: "
                    f"{arr.shape} != {MODIS_GRID_SHAPE}"
                )
            out[name] = arr
        return out
    finally:
        sd.end()


def _write_cmg_geotiff(
    out_tif: Path,
    bands: list[tuple[str, np.ndarray]],
) -> Path:
    """Write an EPSG:4326 CMG 0.05° GeoTIFF atomically (.tmp.tif -> os.replace)."""
    out_path = Path(out_tif)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = out_path.with_suffix(".tmp.tif")

    height, width = MODIS_GRID_SHAPE
    profile = {
        "driver": "GTiff",
        "height": height,
        "width": width,
        "count": len(bands),
        "dtype": "float32",
        "crs": "EPSG:4326",
        "transform": from_origin(-180.0, 90.0, MODIS_CMG_RES_DEG, MODIS_CMG_RES_DEG),
        "nodata": np.nan,
        "compress": "deflate",
        "tiled": True,
        "BIGTIFF": "IF_SAFER",
    }
    try:
        with rasterio.open(tmp_path, "w", **profile) as dst:
            for idx, (desc, arr) in enumerate(bands, start=1):
                dst.write(np.asarray(arr, dtype=np.float32), idx)
                dst.set_band_description(idx, desc)
        os.replace(tmp_path, out_path)
    except Exception:
        if tmp_path.exists():
            tmp_path.unlink()
        raise
    return out_path


def build_ndvi_max(ndvi_dir: Path, out_tif: Path) -> Path:
    """Build 2-band GeoTIFF (ndvi_max, n_months) from 12 monthly MOD13C2 HDF files."""
    files = _list_monthly_hdfs(ndvi_dir)
    ndvi_max: np.ndarray | None = None
    n_months = np.zeros(MODIS_GRID_SHAPE, dtype=np.uint8)

    for hdf_path in files:
        raw = _read_hdf_sds(hdf_path, (NDVI_SDS,))[NDVI_SDS]
        ndvi = ndvi_from_raw(raw)
        ndvi_max = running_nanmax(ndvi_max, ndvi)
        n_months[np.isfinite(ndvi)] += 1

    assert ndvi_max is not None
    return _write_cmg_geotiff(
        out_tif,
        [("ndvi_max", ndvi_max), ("n_months", n_months.astype(np.float32))],
    )


def build_lst(lst_dir: Path, out_tif: Path) -> Path:
    """Build 3-band GeoTIFF (lst_day_c, lst_night_c, lst_amplitude_c) from 12 monthly MOD11C3 HDF files."""
    files = _list_monthly_hdfs(lst_dir)
    sum_day: np.ndarray | None = None
    cnt_day: np.ndarray | None = None
    sum_night: np.ndarray | None = None
    cnt_night: np.ndarray | None = None

    for hdf_path in files:
        sds_map = _read_hdf_sds(hdf_path, (LST_DAY_SDS, LST_NIGHT_SDS))
        day_c = lst_c_from_raw(sds_map[LST_DAY_SDS])
        night_c = lst_c_from_raw(sds_map[LST_NIGHT_SDS])
        sum_day, cnt_day = running_sum_count(sum_day, cnt_day, day_c)
        sum_night, cnt_night = running_sum_count(sum_night, cnt_night, night_c)

    assert sum_day is not None and cnt_day is not None
    assert sum_night is not None and cnt_night is not None
    lst_day_c = finalize_mean(sum_day, cnt_day, min_count=MIN_MONTHS_LST)
    lst_night_c = finalize_mean(sum_night, cnt_night, min_count=MIN_MONTHS_LST)
    lst_amplitude_c = (lst_day_c - lst_night_c).astype(np.float32)

    return _write_cmg_geotiff(
        out_tif,
        [
            ("lst_day_c", lst_day_c),
            ("lst_night_c", lst_night_c),
            ("lst_amplitude_c", lst_amplitude_c),
        ],
    )


def ensure_cache(project_dir: Path, force: bool = False) -> dict[str, Path]:
    """Construct missing cache GeoTIFFs in data/derived/. Never overwrites existing files unless forced."""
    proj = Path(project_dir)
    raw_dir = proj / "data" / "raw"
    derived_dir = proj / "data" / "derived"
    ndvi_out = derived_dir / EARTH_DERIVED_FILES["ndvi_max"]
    lst_out = derived_dir / EARTH_DERIVED_FILES["lst"]

    if force:
        existing = [p for p in (ndvi_out, lst_out) if p.exists()]
        if existing:
            to_del = proj / "_to_delete"
            raise FileExistsError(
                f"Existing cache files ({', '.join(str(p) for p in existing)}). "
                f"Cluster policy requires moving old files to {to_del}/ manually."
            )

    if not ndvi_out.exists():
        print(f"[T6] Building maximum NDVI cache -> {ndvi_out}", flush=True)
        build_ndvi_max(raw_dir / EARTH_RAW_FILES["ndvi_dir"], ndvi_out)
    else:
        print(f"[T6] NDVI cache already exists, reusing: {ndvi_out}", flush=True)

    if not lst_out.exists():
        print(f"[T6] Building mean annual LST cache -> {lst_out}", flush=True)
        build_lst(raw_dir / EARTH_RAW_FILES["lst_dir"], lst_out)
    else:
        print(f"[T6] LST cache already exists, reusing: {lst_out}", flush=True)

    return {"ndvi_max": ndvi_out, "lst": lst_out}


def _read_vector(source: Path | str | gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Load GeoDataFrame from path or return defensive copy, standardizing to EPSG:4326."""
    gdf = source.copy() if isinstance(source, gpd.GeoDataFrame) else gpd.read_file(source)
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4326")
    elif not gdf.crs.is_geographic or gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs("EPSG:4326")
    return gdf


def _clean_iata(val: object) -> str | None:
    """Normalize airport IATA code; empty, NaN or '-' become None."""
    if val is None or pd.isna(val):
        return None
    s = str(val).strip()
    if not s or s == "-":
        return None
    return s


def _clean_str(val: object) -> str | None:
    if val is None or pd.isna(val):
        return None
    s = str(val).strip()
    return s if s else None


class Logistics:
    """Spatial BallTree indices (Haversine metric) for road networks and commercial airports."""

    def __init__(
        self,
        roads_shp: Path | str | gpd.GeoDataFrame,
        airports_shp: Path | str | gpd.GeoDataFrame,
    ) -> None:
        roads = _read_vector(roads_shp)
        if "featurecla" in roads.columns:
            roads = roads[roads["featurecla"] != "Ferry"]
        roads = roads[roads.geometry.notna() & ~roads.geometry.is_empty]

        densified = shapely.segmentize(roads.geometry.to_numpy(), ROAD_DENSIFY_DEG)
        road_xy = shapely.get_coordinates(densified)
        if road_xy.size == 0:
            raise ValueError("No road vertices remained after filtering ferries")
        road_xy = road_xy[np.isfinite(road_xy).all(axis=1)]
        print(
            f"[Logistics] road vertices after segmentizing ({ROAD_DENSIFY_DEG}°): "
            f"{len(road_xy):,}",
            flush=True,
        )
        road_latlon_rad = np.column_stack(
            [np.radians(road_xy[:, 1]), np.radians(road_xy[:, 0])]
        )
        self._road_tree = BallTree(road_latlon_rad, metric="haversine")

        airports = _read_vector(airports_shp)
        airports = airports[airports.geometry.notna() & ~airports.geometry.is_empty]
        if "type" in airports.columns:
            ap_types = (
                airports["type"]
                .fillna("")
                .astype(str)
                .str.strip()
                .str.lower()
            )
            airports = airports[~ap_types.isin(AIRPORT_EXCLUDE_TYPES)]
        airports = airports.reset_index(drop=True)
        if len(airports) == 0:
            raise ValueError("No airports remained after filtering military and spaceport categories")

        if (airports.geometry.geom_type == "Point").all():
            ap_lat = airports.geometry.y.to_numpy()
            ap_lon = airports.geometry.x.to_numpy()
        else:
            centroids = airports.to_crs("EPSG:4087").centroid.to_crs("EPSG:4326")
            ap_lat = centroids.y.to_numpy()
            ap_lon = centroids.x.to_numpy()
        ap_latlon_rad = np.column_stack([np.radians(ap_lat), np.radians(ap_lon)])
        self._airport_tree = BallTree(ap_latlon_rad, metric="haversine")
        self._airport_iata = np.array(
            [
                _clean_iata(v)
                for v in (
                    airports["iata_code"]
                    if "iata_code" in airports.columns
                    else [None] * len(airports)
                )
            ],
            dtype=object,
        )
        self._airport_name = np.array(
            [
                _clean_str(v)
                for v in (
                    airports["name"]
                    if "name" in airports.columns
                    else [None] * len(airports)
                )
            ],
            dtype=object,
        )

    def dist_road_km(self, lat: np.ndarray | float, lon: np.ndarray | float) -> np.ndarray:
        """Haversine distance (km, float32) to nearest densified road vertex."""
        lat_arr = np.atleast_1d(np.asarray(lat, dtype=np.float64))
        lon_arr = np.atleast_1d(np.asarray(lon, dtype=np.float64))
        out = np.full(lat_arr.shape[0], np.nan, dtype=np.float32)
        valid = np.isfinite(lat_arr) & np.isfinite(lon_arr)
        if np.any(valid):
            q = np.column_stack(
                [np.radians(lat_arr[valid]), np.radians(lon_arr[valid])]
            )
            dist_rad, _ = self._road_tree.query(q, k=1)
            out[valid] = (dist_rad[:, 0] * EARTH_RADIUS_KM).astype(np.float32)
        return out

    def nearest_airport(
        self,
        lat: np.ndarray | float,
        lon: np.ndarray | float,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Return (dist_km float32, iata object, name object); empty IATA or '-' becomes None."""
        lat_arr = np.atleast_1d(np.asarray(lat, dtype=np.float64))
        lon_arr = np.atleast_1d(np.asarray(lon, dtype=np.float64))
        n = lat_arr.shape[0]
        dist_out = np.full(n, np.nan, dtype=np.float32)
        iata_out = np.full(n, None, dtype=object)
        name_out = np.full(n, None, dtype=object)
        valid = np.isfinite(lat_arr) & np.isfinite(lon_arr)
        if np.any(valid):
            q = np.column_stack(
                [np.radians(lat_arr[valid]), np.radians(lon_arr[valid])]
            )
            dist_rad, idx = self._airport_tree.query(q, k=1)
            nn = idx[:, 0]
            dist_out[valid] = (dist_rad[:, 0] * EARTH_RADIUS_KM).astype(np.float32)
            iata_out[valid] = self._airport_iata[nn]
            name_out[valid] = self._airport_name[nn]
        return dist_out, iata_out, name_out


class Countries:
    """Sovereign country polygon lookup with spatial index and coastal tolerance buffer (<= 25 km)."""

    def __init__(self, countries_shp: Path | str | gpd.GeoDataFrame) -> None:
        gdf = _read_vector(countries_shp)
        if "ADMIN" not in gdf.columns:
            raise ValueError("Country vector layer must contain 'ADMIN' attribute column")
        gdf = gdf[["ADMIN", "geometry"]]
        gdf = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty].reset_index(drop=True)
        self._gdf = gdf
        _ = self._gdf.sindex
        self._gdf_4087 = self._gdf.to_crs("EPSG:4087")
        _ = self._gdf_4087.sindex

    def lookup(
        self,
        lat: np.ndarray | float,
        lon: np.ndarray | float,
        max_coast_km: float = 25.0,
    ) -> np.ndarray:
        """Return sovereign country ADMIN string for points within polygon or within max_coast_km offshore."""
        lat_arr = np.atleast_1d(np.asarray(lat, dtype=np.float64))
        lon_arr = np.atleast_1d(np.asarray(lon, dtype=np.float64))
        n = lat_arr.shape[0]
        out = np.full(n, None, dtype=object)
        valid = np.isfinite(lat_arr) & np.isfinite(lon_arr)
        if not np.any(valid):
            return out

        valid_idx = np.flatnonzero(valid)
        pts = gpd.GeoDataFrame(
            {"_idx": valid_idx},
            geometry=gpd.points_from_xy(lon_arr[valid], lat_arr[valid]),
            crs="EPSG:4326",
        )
        within = gpd.sjoin(pts, self._gdf, how="inner", predicate="within")
        if len(within) > 0:
            within = within.drop_duplicates(subset="_idx", keep="first")
            for idx, admin in zip(within["_idx"].to_numpy(), within["ADMIN"]):
                out[idx] = _clean_str(admin)

        missing = np.array([out[i] is None for i in valid_idx], dtype=bool)
        if np.any(missing):
            pts_miss = pts.iloc[missing].to_crs("EPSG:4087")
            nearest = gpd.sjoin_nearest(
                pts_miss,
                self._gdf_4087,
                how="inner",
                max_distance=max_coast_km * 1000.0,
            )
            if len(nearest) > 0:
                nearest = nearest.drop_duplicates(subset="_idx", keep="first")
                for idx, admin in zip(nearest["_idx"].to_numpy(), nearest["ADMIN"]):
                    out[idx] = _clean_str(admin)

        return out


class KnownRegions:
    """Curated planetary analog field station catalog indexed by bounding boxes."""

    def __init__(self, json_path: Path = KNOWN_ANALOGS_JSON) -> None:
        path = Path(json_path)
        payload = json.loads(path.read_text(encoding="utf-8"))
        regions = payload.get("regions")
        if not isinstance(regions, list) or len(regions) == 0:
            raise ValueError(f"Invalid or empty 'regions' list in {path}")

        seen_ids: set[str] = set()
        validated: list[dict] = []
        for reg in regions:
            reg_id = reg.get("id")
            if not isinstance(reg_id, str) or not reg_id.strip():
                raise ValueError(f"Region missing valid 'id': {reg}")
            if reg_id in seen_ids:
                raise ValueError(f"Duplicate region id: {reg_id!r}")
            seen_ids.add(reg_id)

            bbox = reg.get("bbox")
            if not isinstance(bbox, list) or len(bbox) != 4:
                raise ValueError(f"Invalid bbox in region {reg_id!r}: {bbox}")
            lon_min, lat_min, lon_max, lat_max = (float(v) for v in bbox)
            if not (-180.0 <= lon_min < lon_max <= 180.0):
                raise ValueError(
                    f"Longitude out of bounds or inverted in {reg_id!r}: [{lon_min}, {lon_max}]"
                )
            if not (-90.0 <= lat_min < lat_max <= 90.0):
                raise ValueError(
                    f"Latitude out of bounds or inverted in {reg_id!r}: [{lat_min}, {lat_max}]"
                )

            source_url = reg.get("source_url")
            if not isinstance(source_url, str) or not source_url.strip():
                raise ValueError(f"Empty source_url in region {reg_id!r}")

            validated.append(reg)

        self.regions = validated
        self._by_id = {reg["id"]: reg for reg in validated}

    def lookup(self, lat: np.ndarray | float, lon: np.ndarray | float) -> np.ndarray:
        """Return the id of the first known region whose bounding box contains (lat, lon), or None."""
        lat_arr = np.atleast_1d(np.asarray(lat, dtype=np.float64))
        lon_arr = np.atleast_1d(np.asarray(lon, dtype=np.float64))
        lon_wrapped = np.where(
            (lon_arr < -180.0) | (lon_arr > 180.0),
            _normalize_lon(lon_arr),
            lon_arr,
        )
        out = np.full(lat_arr.shape[0], None, dtype=object)
        unmatched = np.isfinite(lat_arr) & np.isfinite(lon_wrapped)

        for reg in self.regions:
            if not np.any(unmatched):
                break
            lon_min, lat_min, lon_max, lat_max = reg["bbox"]
            hit = (
                unmatched
                & (lon_wrapped >= lon_min)
                & (lon_wrapped <= lon_max)
                & (lat_arr >= lat_min)
                & (lat_arr <= lat_max)
            )
            if np.any(hit):
                out[hit] = reg["id"]
                unmatched[hit] = False

        return out

    def name_of(self, region_id: str) -> str:
        """Return human-readable display name of a known analog region."""
        return str(self._by_id[region_id]["name"])


class EarthLayers:
    """Unified facade of Earth environmental layers for pre-filtering and sampling in T5."""

    def __init__(
        self,
        *,
        ndvi_max: np.ndarray | None = None,
        lst_day_c: np.ndarray | None = None,
        lst_night_c: np.ndarray | None = None,
        lst_amplitude_c: np.ndarray | None = None,
        logistics: Logistics | None = None,
        countries: Countries | None = None,
        known_regions: KnownRegions | None = None,
        res: float = MODIS_CMG_RES_DEG,
    ) -> None:
        self.ndvi_max = ndvi_max
        self.lst_day_c = lst_day_c
        self.lst_night_c = lst_night_c
        self.lst_amplitude_c = lst_amplitude_c
        self.logistics = logistics
        self.countries = countries
        self.known_regions = known_regions
        self.res = float(res)

    @classmethod
    def from_project(
        cls,
        project_dir: Path = YUCA_PROJECT_DIR,
        need: set[str] | None = None,
    ) -> "EarthLayers":
        """Load Earth environmental layers from data/derived/ and data/raw/.

        Parameters:
            project_dir: Base directory on filesystem.
            need: Optional subset of layers to load (e.g. {'ndvi'} for T5 candidate pre-filtering).

        Raises:
            FileNotFoundError: If cache files are missing from data/derived/.
        """
        proj = Path(project_dir)
        raw_dir = proj / "data" / "raw"
        derived_dir = proj / "data" / "derived"
        requested = (
            {"ndvi", "lst", "logistics", "countries", "known_regions"}
            if need is None
            else set(need)
        )

        ndvi_max = None
        if "ndvi" in requested:
            ndvi_path = derived_dir / EARTH_DERIVED_FILES["ndvi_max"]
            if not ndvi_path.exists():
                raise FileNotFoundError(
                    f"Missing NDVI cache ({ndvi_path}). Run jobs/t6_earth_layers.slurm first."
                )
            with rasterio.open(ndvi_path) as ds:
                ndvi_max = ds.read(1).astype(np.float32, copy=False)

        lst_day_c = lst_night_c = lst_amplitude_c = None
        if "lst" in requested:
            lst_path = derived_dir / EARTH_DERIVED_FILES["lst"]
            if not lst_path.exists():
                raise FileNotFoundError(
                    f"Missing LST cache ({lst_path}). Run jobs/t6_earth_layers.slurm first."
                )
            with rasterio.open(lst_path) as ds:
                lst_day_c = ds.read(1).astype(np.float32, copy=False)
                lst_night_c = ds.read(2).astype(np.float32, copy=False)
                lst_amplitude_c = ds.read(3).astype(np.float32, copy=False)

        logistics = None
        if "logistics" in requested:
            logistics = Logistics(
                raw_dir / EARTH_RAW_FILES["roads"],
                raw_dir / EARTH_RAW_FILES["airports"],
            )

        countries = None
        if "countries" in requested:
            countries = Countries(raw_dir / EARTH_RAW_FILES["countries"])

        known_regions = None
        if "known_regions" in requested:
            known_regions = KnownRegions()

        return cls(
            ndvi_max=ndvi_max,
            lst_day_c=lst_day_c,
            lst_night_c=lst_night_c,
            lst_amplitude_c=lst_amplitude_c,
            logistics=logistics,
            countries=countries,
            known_regions=known_regions,
            res=MODIS_CMG_RES_DEG,
        )

    @classmethod
    def from_arrays(
        cls,
        *,
        ndvi_max: np.ndarray,
        lst_day_c: np.ndarray,
        lst_night_c: np.ndarray,
        lst_amplitude_c: np.ndarray | None = None,
        logistics: Logistics | None = None,
        countries: Countries | None = None,
        known_regions: KnownRegions | None = None,
        res: float | None = None,
    ) -> "EarthLayers":
        """In-memory constructor for unit tests."""
        ndvi_arr = np.asarray(ndvi_max, dtype=np.float32)
        day_arr = np.asarray(lst_day_c, dtype=np.float32)
        night_arr = np.asarray(lst_night_c, dtype=np.float32)
        amp_arr = (
            (day_arr - night_arr).astype(np.float32)
            if lst_amplitude_c is None
            else np.asarray(lst_amplitude_c, dtype=np.float32)
        )
        grid_res = (
            MODIS_CMG_RES_DEG
            if res is None and ndvi_arr.shape == MODIS_GRID_SHAPE
            else (180.0 / ndvi_arr.shape[0] if res is None else float(res))
        )
        return cls(
            ndvi_max=ndvi_arr,
            lst_day_c=day_arr,
            lst_night_c=night_arr,
            lst_amplitude_c=amp_arr,
            logistics=logistics,
            countries=countries,
            known_regions=known_regions,
            res=grid_res,
        )

    def ndvi_prefilter(
        self,
        lat: np.ndarray | float,
        lon: np.ndarray | float,
        half_km: float = 16.0,
    ) -> np.ndarray:
        """Median ndvi_max across the patch footprint; T5 pre-filtering discards values > 0.25."""
        if self.ndvi_max is None:
            raise RuntimeError("ndvi_max layer not loaded in this instance")
        return patch_window_stat(
            self.ndvi_max, lat, lon, half_km=half_km, stat="median", res=self.res
        )

    def sample(
        self,
        lat: np.ndarray | float,
        lon: np.ndarray | float,
        half_km: float = 16.0,
    ) -> pd.DataFrame:
        """Sample all EARTH_ENV_COLUMNS in the specified point order."""
        if (
            self.ndvi_max is None
            or self.lst_day_c is None
            or self.lst_night_c is None
            or self.lst_amplitude_c is None
        ):
            raise RuntimeError("Missing NDVI/LST grids for sampling")

        lat_arr = np.atleast_1d(np.asarray(lat, dtype=np.float64))
        lon_arr = np.atleast_1d(np.asarray(lon, dtype=np.float64))
        n = lat_arr.shape[0]

        ndvi = patch_window_stat(
            self.ndvi_max, lat_arr, lon_arr, half_km=half_km, stat="median", res=self.res
        )
        lst_day = patch_window_stat(
            self.lst_day_c, lat_arr, lon_arr, half_km=half_km, stat="mean", res=self.res
        )
        lst_night = patch_window_stat(
            self.lst_night_c, lat_arr, lon_arr, half_km=half_km, stat="mean", res=self.res
        )
        lst_amp = patch_window_stat(
            self.lst_amplitude_c, lat_arr, lon_arr, half_km=half_km, stat="mean", res=self.res
        )

        if self.logistics is not None:
            dist_road = self.logistics.dist_road_km(lat_arr, lon_arr)
            dist_ap, ap_iata, ap_name = self.logistics.nearest_airport(lat_arr, lon_arr)
        else:
            dist_road = np.full(n, np.nan, dtype=np.float32)
            dist_ap = np.full(n, np.nan, dtype=np.float32)
            ap_iata = np.full(n, None, dtype=object)
            ap_name = np.full(n, None, dtype=object)

        country = (
            self.countries.lookup(lat_arr, lon_arr)
            if self.countries is not None
            else np.full(n, None, dtype=object)
        )
        known_reg = (
            self.known_regions.lookup(lat_arr, lon_arr)
            if self.known_regions is not None
            else np.full(n, None, dtype=object)
        )
        classification = np.where(
            pd.notna(known_reg), "KNOWN_ANALOG", "NEW_CANDIDATE"
        )

        df = pd.DataFrame(
            {
                "ndvi_max": pd.Series(ndvi, dtype="float32"),
                "lst_day_c": pd.Series(lst_day, dtype="float32"),
                "lst_night_c": pd.Series(lst_night, dtype="float32"),
                "lst_amplitude_c": pd.Series(lst_amp, dtype="float32"),
                "dist_road_km": pd.Series(dist_road, dtype="float32"),
                "dist_airport_km": pd.Series(dist_ap, dtype="float32"),
                "nearest_airport_iata": pd.Series(ap_iata, dtype="string"),
                "nearest_airport_name": pd.Series(ap_name, dtype="string"),
                "country": pd.Series(country, dtype="string"),
                "known_region": pd.Series(known_reg, dtype="string"),
                "classification": pd.Series(classification, dtype="string"),
            }
        )
        return df[EARTH_ENV_COLUMNS]


def _check_raster_metadata(tif_path: Path, expected_bands: int) -> tuple[bool, dict]:
    expected_transform = from_origin(-180.0, 90.0, MODIS_CMG_RES_DEG, MODIS_CMG_RES_DEG)
    with rasterio.open(tif_path) as ds:
        ok_shape = ds.shape == MODIS_GRID_SHAPE
        ok_crs = ds.crs is not None and ds.crs.to_epsg() == 4326
        ok_transform = tuple(ds.transform)[:6] == tuple(expected_transform)[:6]
        ok_bands = ds.count == expected_bands
        info = {
            "shape": list(ds.shape),
            "crs": str(ds.crs),
            "bands": ds.count,
            "transform": list(ds.transform)[:6],
        }
    return bool(ok_shape and ok_crs and ok_transform and ok_bands), info


def _render_control_plots(layers: EarthLayers, out_dir: Path) -> list[Path]:
    """Generates the 3 diagnostic control PNG maps described in section 6.3."""
    out_dir.mkdir(parents=True, exist_ok=True)
    extent = (-180.0, 180.0, -90.0, 90.0)
    ndvi_sub = layers.ndvi_max[::4, ::4]
    amp_sub = layers.lst_amplitude_c[::4, ::4]
    paths: list[Path] = []

    # 1. map_ndvi_max.png
    fig, ax = plt.subplots(figsize=(14, 7), dpi=180)
    cmap_ndvi = plt.get_cmap("YlGn").copy()
    cmap_ndvi.set_bad("#e6eef5")
    im = ax.imshow(
        ndvi_sub,
        cmap=cmap_ndvi,
        vmin=0.0,
        vmax=0.9,
        extent=extent,
        origin="upper",
        interpolation="nearest",
    )
    ax.contour(
        ndvi_sub,
        levels=[0.25],
        colors="red",
        linewidths=0.45,
        extent=extent,
        origin="upper",
    )
    fig.colorbar(im, ax=ax, shrink=0.72, label="MODIS MOD13C2 2023 Max NDVI")
    ax.set_title("2023 Annual Maximum NDVI (4× subsampled) + 0.25 contour in red")
    ax.set_xlabel("Longitude (°)")
    ax.set_ylabel("Latitude (°)")
    p1 = out_dir / "map_ndvi_max.png"
    fig.tight_layout()
    fig.savefig(p1)
    plt.close(fig)
    paths.append(p1)

    # 2. map_lst_amplitude.png
    fig, ax = plt.subplots(figsize=(14, 7), dpi=180)
    cmap_amp = plt.get_cmap("magma").copy()
    cmap_amp.set_bad("#1b263b")
    im = ax.imshow(
        amp_sub,
        cmap=cmap_amp,
        vmin=0.0,
        vmax=35.0,
        extent=extent,
        origin="upper",
        interpolation="nearest",
    )
    fig.colorbar(im, ax=ax, shrink=0.72, label="LST Mean Diurnal Amplitude (°C)")
    ax.set_title("MODIS MOD11C3 2023 Surface Thermal Amplitude (Day − Night, 4× subsampled)")
    ax.set_xlabel("Longitude (°)")
    ax.set_ylabel("Latitude (°)")
    p2 = out_dir / "map_lst_amplitude.png"
    fig.tight_layout()
    fig.savefig(p2)
    plt.close(fig)
    paths.append(p2)

    # 3. map_known_analogs.png
    fig, ax = plt.subplots(figsize=(16, 8), dpi=200)
    cmap_gray = plt.get_cmap("Greys").copy()
    cmap_gray.set_bad("#e8eef5")
    ax.imshow(
        ndvi_sub,
        cmap=cmap_gray,
        vmin=0.0,
        vmax=0.9,
        extent=extent,
        origin="upper",
        interpolation="nearest",
    )
    # Small label offsets to prevent collision in SW US / North Atlantic.
    label_offsets = {
        "utah-mdrs": (1.5, 2.2),
        "meteor-crater": (1.8, -3.2),
        "mojave": (-18.0, -3.5),
        "lanzarote": (-16.0, -3.0),
        "rio-tinto": (1.5, 1.5),
    }
    for reg in layers.known_regions.regions:
        lon_min, lat_min, lon_max, lat_max = reg["bbox"]
        rect = mpatches.Rectangle(
            (lon_min, lat_min),
            lon_max - lon_min,
            lat_max - lat_min,
            linewidth=1.3,
            edgecolor="red",
            facecolor="none",
        )
        ax.add_patch(rect)
        dx, dy = label_offsets.get(reg["id"], (1.2, 1.0))
        ax.text(
            lon_max + dx if dx > 0 else lon_min + dx,
            lat_max + dy if dy > 0 else lat_min + dy,
            reg["id"],
            fontsize=7.5,
            fontweight="bold",
            color="darkred",
            bbox={"boxstyle": "round,pad=0.15", "facecolor": "white", "alpha": 0.78, "edgecolor": "none"},
        )
    ax.set_xlim(-180.0, 180.0)
    ax.set_ylim(-90.0, 90.0)
    ax.set_title("Known Planetary Analog Regions (12 bounding boxes over grayscale NDVI)")
    ax.set_xlabel("Longitude (°)")
    ax.set_ylabel("Latitude (°)")
    p3 = out_dir / "map_known_analogs.png"
    fig.tight_layout()
    fig.savefig(p3)
    plt.close(fig)
    paths.append(p3)

    return paths


def run_checks(project_dir: Path, out_dir: Path) -> dict:
    """Executes the 13 verification checks of section 6, writes t6_checks.json and 3 PNG maps."""
    proj = Path(project_dir)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    derived_dir = proj / "data" / "derived"
    ndvi_tif = derived_dir / EARTH_DERIVED_FILES["ndvi_max"]
    lst_tif = derived_dir / EARTH_DERIVED_FILES["lst"]

    ok_ndvi_meta, meta_ndvi = _check_raster_metadata(ndvi_tif, expected_bands=2)
    ok_lst_meta, meta_lst = _check_raster_metadata(lst_tif, expected_bands=3)

    layers = EarthLayers.from_project(proj)

    ref_points = [
        ("sahara_dz", 26.0, 3.0),
        ("sahara_eg", 24.0, 28.0),
        ("atacama", -24.5, -69.3),
        ("amazonia", -3.5, -62.0),
        ("congo", 0.5, 20.0),
        ("hermosillo", 29.07, -110.96),
        ("mdrs", 38.4064, -110.7919),
        ("dry_valleys", -77.5, 162.0),
    ]
    ref_df = layers.sample(
        np.array([p[1] for p in ref_points]),
        np.array([p[2] for p in ref_points]),
    )
    ref_df.index = [p[0] for p in ref_points]

    ndvi_grid = layers.ndvi_max
    finite_mask = np.isfinite(ndvi_grid)
    finite_frac = float(np.mean(finite_mask))
    row_lats = 90.0 - (np.arange(ndvi_grid.shape[0]) + 0.5) * MODIS_CMG_RES_DEG
    cos_w = np.cos(np.radians(row_lats))
    finite_frac_cos = float((finite_mask.mean(axis=1) * cos_w).sum() / cos_w.sum())
    grid_le_025_frac = float(np.mean(finite_mask & (ndvi_grid <= 0.25)))
    land_le_025_frac = float(np.mean(ndvi_grid[finite_mask] <= 0.25)) if np.any(finite_mask) else 0.0

    # Benchmark of 10,000 random land points (check 13)
    rng = np.random.default_rng(42)
    land_rows, land_cols = np.where(finite_mask)
    n_bench = min(10_000, len(land_rows))
    sel = rng.choice(len(land_rows), size=n_bench, replace=False)
    bench_lats = 90.0 - (land_rows[sel] + 0.5) * MODIS_CMG_RES_DEG
    bench_lons = -180.0 + (land_cols[sel] + 0.5) * MODIS_CMG_RES_DEG
    t0 = time.perf_counter()
    _ = layers.sample(bench_lats, bench_lons)
    bench_sec = float(time.perf_counter() - t0)

    def _val(row_name: str, col: str):
        v = ref_df.loc[row_name, col]
        if pd.isna(v):
            return None
        return float(v) if col in NUMERIC_ENV_COLUMNS else str(v)

    checks: list[dict] = [
        {
            "id": 1,
            "name": "cache_metadata",
            "kind": "hard",
            "passed": bool(ok_ndvi_meta and ok_lst_meta),
            "observed": {"ndvi": meta_ndvi, "lst": meta_lst},
            "expected": "3600x7200 EPSG:4326 from_origin(-180,90,0.05,0.05)",
        },
        {
            "id": 2,
            "name": "ndvi_sahara",
            "kind": "hard",
            "passed": bool(
                (_val("sahara_dz", "ndvi_max") is not None and _val("sahara_dz", "ndvi_max") < 0.12)
                and (_val("sahara_eg", "ndvi_max") is not None and _val("sahara_eg", "ndvi_max") < 0.12)
            ),
            "observed": {"dz": _val("sahara_dz", "ndvi_max"), "eg": _val("sahara_eg", "ndvi_max")},
            "expected": "< 0.12 for both",
        },
        {
            "id": 3,
            "name": "ndvi_atacama",
            "kind": "hard",
            "passed": bool(
                _val("atacama", "ndvi_max") is not None and _val("atacama", "ndvi_max") < 0.10
            ),
            "observed": _val("atacama", "ndvi_max"),
            "expected": "< 0.10",
        },
        {
            "id": 4,
            "name": "ndvi_tropical_forests",
            "kind": "hard",
            "passed": bool(
                (_val("amazonia", "ndvi_max") is not None and _val("amazonia", "ndvi_max") > 0.70)
                and (_val("congo", "ndvi_max") is not None and _val("congo", "ndvi_max") > 0.70)
            ),
            "observed": {"amazonia": _val("amazonia", "ndvi_max"), "congo": _val("congo", "ndvi_max")},
            "expected": "> 0.70 for both",
        },
        {
            "id": 5,
            "name": "dist_road_hermosillo",
            "kind": "hard",
            "passed": bool(
                _val("hermosillo", "dist_road_km") is not None
                and _val("hermosillo", "dist_road_km") < 5.0
            ),
            "observed": _val("hermosillo", "dist_road_km"),
            "expected": "< 5 km",
        },
        {
            "id": 6,
            "name": "countries_lookup",
            "kind": "hard",
            "passed": bool(
                _val("hermosillo", "country") == "Mexico"
                and _val("atacama", "country") == "Chile"
                and _val("sahara_dz", "country") == "Algeria"
            ),
            "observed": {
                "hermosillo": _val("hermosillo", "country"),
                "atacama": _val("atacama", "country"),
                "sahara_dz": _val("sahara_dz", "country"),
            },
            "expected": {"hermosillo": "Mexico", "atacama": "Chile", "sahara_dz": "Algeria"},
        },
        {
            "id": 7,
            "name": "known_region_lookup",
            "kind": "hard",
            "passed": bool(
                _val("mdrs", "known_region") == "utah-mdrs"
                and _val("hermosillo", "known_region") is None
            ),
            "observed": {
                "mdrs": _val("mdrs", "known_region"),
                "hermosillo": _val("hermosillo", "known_region"),
            },
            "expected": {"mdrs": "utah-mdrs", "hermosillo": None},
        },
        {
            "id": 8,
            "name": "ndvi_finite_land_frac",
            "kind": "hard",
            "passed": bool(finite_frac_cos > 0.25),
            "observed": {
                "cos_weighted": round(finite_frac_cos, 4),
                "unweighted": round(finite_frac, 4),
            },
            "expected": "> 0.25 (cos(lat)-weighted)",
        },
        {
            "id": 9,
            "name": "lst_day_dry_valleys",
            "kind": "soft",
            "passed": bool(
                _val("dry_valleys", "lst_day_c") is not None
                and _val("dry_valleys", "lst_day_c") < 0.0
            ),
            "observed": _val("dry_valleys", "lst_day_c"),
            "expected": "< 0 °C",
        },
        {
            "id": 10,
            "name": "lst_amp_sahara_vs_amazonia",
            "kind": "soft",
            "passed": bool(
                _val("sahara_dz", "lst_amplitude_c") is not None
                and _val("amazonia", "lst_amplitude_c") is not None
                and _val("sahara_dz", "lst_amplitude_c") > 15.0
                and _val("sahara_dz", "lst_amplitude_c") > _val("amazonia", "lst_amplitude_c")
            ),
            "observed": {
                "sahara_dz": _val("sahara_dz", "lst_amplitude_c"),
                "amazonia": _val("amazonia", "lst_amplitude_c"),
            },
            "expected": "sahara > 15 °C and sahara > amazonia",
        },
        {
            "id": 11,
            "name": "dist_road_dry_valleys",
            "kind": "soft",
            "passed": bool(
                _val("dry_valleys", "dist_road_km") is not None
                and _val("dry_valleys", "dist_road_km") > 1000.0
            ),
            "observed": _val("dry_valleys", "dist_road_km"),
            "expected": "> 1000 km",
        },
        {
            "id": 12,
            "name": "ndvi_prefilter_pass_frac",
            "kind": "soft",
            "passed": bool(grid_le_025_frac > 0.0),
            "observed": {
                "grid_frac_le_025": round(grid_le_025_frac, 4),
                "land_frac_le_025": round(land_le_025_frac, 4),
            },
            "expected": "informative report (~40k-120k patches expected in T5)",
        },
        {
            "id": 13,
            "name": "sample_10k_runtime_s",
            "kind": "soft",
            "passed": bool(bench_sec < 30.0),
            "observed": round(bench_sec, 3),
            "expected": "< 30 s",
        },
    ]

    hard_checks = [c for c in checks if c["kind"] == "hard"]
    soft_checks = [c for c in checks if c["kind"] == "soft"]
    hard_passed = sum(1 for c in hard_checks if c["passed"])
    soft_passed = sum(1 for c in soft_checks if c["passed"])

    plots = _render_control_plots(layers, out)

    try:
        commit = (
            subprocess.check_output(
                ["git", "-C", str(Path(__file__).resolve().parents[2]), "rev-parse", "--short", "HEAD"],
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip()
        )
    except Exception:
        commit = "unknown"

    report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "commit": commit,
        "summary": {
            "hard_passed": hard_passed,
            "hard_total": len(hard_checks),
            "soft_passed": soft_passed,
            "soft_total": len(soft_checks),
        },
        "checks": checks,
        "plots": [str(p) for p in plots],
    }

    checks_path = out / "t6_checks.json"
    checks_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print("\n=== T6 Verification Checks ===")
    for c in checks:
        status = "PASS" if c["passed"] else "FAIL"
        print(
            f"[{status}] #{c['id']:2d} ({c['kind']:4s}) {c['name']:<26s} "
            f"obs={c['observed']} | exp={c['expected']}"
        )
    print(
        f"Summary: hard {hard_passed}/{len(hard_checks)}, "
        f"soft {soft_passed}/{len(soft_checks)} -> {checks_path}"
    )
    return report


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Earth environmental layer caching and T6 verification."
    )
    parser.add_argument("--project-dir", type=Path, default=YUCA_PROJECT_DIR)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--build", action="store_true", help="Build missing MODIS GeoTIFF caches.")
    parser.add_argument("--check", action="store_true", help="Run acceptance checks and generate control plots.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.build:
        ensure_cache(args.project_dir)
    if args.check:
        report = run_checks(args.project_dir, args.out_dir)
        summary = report["summary"]
        if summary["hard_passed"] < summary["hard_total"]:
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
