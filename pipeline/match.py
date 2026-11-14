"""Planetary analog matching: Earth-unit normalization, RBF dimension scoring over seven
dimensions (terrain, aridity, thermal, geology, dust, ice), five MSI presets, 150 km diversity
selection, ice-sheet cap, and mismatch reporting (T7 + T15).
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import logging
import math
import os
from pathlib import Path
import subprocess
import time

import numpy as np
import pandas as pd
from scipy.stats import rankdata

from .config import BODY_RADII_M, YUCA_PROJECT_DIR
from .dust import TROPICAL_LAT_DEG, S_dust, circular_diff
from .geology_rules import GEO_SIMILARITY
from .ice import S_ice

logger = logging.getLogger(__name__)

TOPO: list[str] = [
    "mean_slope_deg",
    "p90_slope_deg",
    "relief_m",
    "hypsometric_integral",
]
ROUGH: list[str] = ["detrended_std_m", "tri_m"]
LOG_FEATURES: list[str] = ["relief_m", "detrended_std_m", "tri_m"]
MATCH_FEATURES: list[str] = TOPO + ROUGH

DIMENSION_KEYS: tuple[str, ...] = (
    "topography",
    "roughness",
    "environment",
    "thermal",
    "geology",
    "dust",
    "ice",
)

DIMENSIONS: list[dict[str, object]] = [
    {
        "key": "topography",
        "label": "Topography",
        "description": "Slope, relief and hypsometry of the 32 km patch, in Earth units (robust z-scores).",
        "bodies": ["Moon", "Mars"],
        "source": "LOLA, MOLA, Copernicus GLO-90 (T2/T3/T5)",
    },
    {
        "key": "roughness",
        "label": "Roughness",
        "description": "Detrended elevation scatter and terrain ruggedness index of the patch.",
        "bodies": ["Moon", "Mars"],
        "source": "LOLA, MOLA, Copernicus GLO-90 (T2/T3/T5)",
    },
    {
        "key": "environment",
        "label": "Aridity (no vegetation)",
        "description": "Earth patches must be bare ground: penalises annual maximum NDVI above 0.10.",
        "bodies": ["Moon", "Mars"],
        "source": "MODIS MOD13C2 2023 (T6)",
    },
    {
        "key": "thermal",
        "label": "Day-night thermal contrast (rank)",
        "description": "Rank of the day-night temperature contrast within each planet (Mars THEMIS vs Earth MODIS LST).",
        "bodies": ["Mars"],
        "source": "THEMIS IR day/night, MODIS MOD11C3 (T3/T6)",
    },
    {
        "key": "geology",
        "label": "Surface materials (regional geology)",
        "description": "Similarity of regional lithology classes through a shared 8-class taxonomy (regional, not outcrop).",
        "bodies": ["Moon", "Mars"],
        "source": "GLiM (Earth), USGS SIM 3292 (Mars), USGS unified lunar map (Moon) (T14)",
    },
    {
        "key": "dust",
        "label": "Dust process and seasons (rank)",
        "description": "Within-planet dust level rank, seasonality rank and local peak season (phase dropped within 15 deg of the equator).",
        "bodies": ["Mars"],
        "source": "Montabone et al. CDOD 610 Pa (Mars), MODIS MOD08_M3 Deep Blue AOD (Earth) (T13)",
    },
    {
        "key": "ice",
        "label": "Cold traps and ice (rank)",
        "description": "Cold-trap rank and ice presence; Moon (Diviner targets) and Mars targets with mapped ice.",
        "bodies": ["Moon", "Mars"],
        "source": "LRO Diviner, MODIS MOD11C3, GLiM ice, curated SWIM hint (T12)",
    },
]

PRESETS: dict[str, dict[str, object]] = {
    "mobility_and_traction": {
        "label": "Rover mobility and traction",
        "applies_to": ["Moon", "Mars"],
        "weights": {
            "topography": 0.40,
            "roughness": 0.35,
            "environment": 0.10,
            "thermal": 0.00,
            "geology": 0.15,
            "dust": 0.00,
            "ice": 0.00,
        },
    },
    "construction_and_base": {
        "label": "Base construction and landing",
        "applies_to": ["Moon", "Mars"],
        "weights": {
            "topography": 0.45,
            "roughness": 0.20,
            "environment": 0.05,
            "thermal": 0.05,
            "geology": 0.25,
            "dust": 0.00,
            "ice": 0.00,
        },
    },
    "geology_and_materials": {
        "label": "Geology and surface materials",
        "applies_to": ["Moon", "Mars"],
        "weights": {
            "topography": 0.20,
            "roughness": 0.10,
            "environment": 0.10,
            "thermal": 0.00,
            "geology": 0.60,
            "dust": 0.00,
            "ice": 0.00,
        },
    },
    "dust_and_seasons": {
        "label": "Dust storms and seasons",
        "applies_to": ["Mars"],
        "weights": {
            "topography": 0.10,
            "roughness": 0.05,
            "environment": 0.15,
            "thermal": 0.20,
            "geology": 0.10,
            "dust": 0.40,
            "ice": 0.00,
        },
    },
    "isru_and_ice": {
        "label": "Water ice and cold traps (ISRU)",
        "applies_to": ["Moon", "Mars"],
        "weights": {
            "topography": 0.20,
            "roughness": 0.10,
            "environment": 0.05,
            "thermal": 0.00,
            "geology": 0.15,
            "dust": 0.00,
            "ice": 0.50,
        },
    },
}
PRESET_KEYS: tuple[str, ...] = tuple(PRESETS.keys())
ICE_CAP_EXEMPT_PRESETS: tuple[str, ...] = ("isru_and_ice",)

NDVI_FREE: float = 0.10
NDVI_SCALE: float = 0.10
THERMAL_UNIT: float = 0.15
POLAR_COLD_LST_C: float = -10.0
MAX_POLAR_PER_PRESET: int = 3
MAX_ICE_SURFACE_PER_PRESET: int = 3
MISMATCH_RANK: float = 0.30
MISMATCH_PHASE_DEG: float = 90.0
PHASE_UNIT_DEG: float = 60.0
TOP_N: int = 30
MIN_SEP_KM: float = 150.0
MISMATCH_Z: float = 1.5
MISMATCH_THERMAL: float = 0.30
MAD_FLOOR: float = 1e-6
MAD_TO_SIGMA: float = 1.4826
EARTH_RADIUS_KM: float = BODY_RADII_M["Earth"] / 1000.0


def format_earth_id(lat: float, lon: float) -> str:
    """Return a stable Earth patch identifier such as 'earth+31.8480-113.3900'."""
    lat_f = 0.0 if abs(float(lat)) < 0.00005 else float(lat)
    lon_f = 0.0 if abs(float(lon)) < 0.00005 else float(lon)
    return f"earth{lat_f:+08.4f}{lon_f:+09.4f}"


earth_id = format_earth_id


def preprocess_feature(values: np.ndarray | pd.Series, feature: str) -> np.ndarray:
    """Cast a feature column to float64 and apply log1p when configured."""
    arr = np.asarray(values, dtype=np.float64)
    if feature in LOG_FEATURES:
        out = np.full(arr.shape, np.nan, dtype=np.float64)
        valid = np.isfinite(arr) & (arr > -1.0)
        out[valid] = np.log1p(arr[valid])
        return out
    return arr


@dataclass
class Normalizer:
    """Robust Earth-based feature normalizer (median and 1.4826 * MAD after log1p)."""

    median: dict[str, float]
    scale: dict[str, float]

    @classmethod
    def fit_earth(cls, earth: pd.DataFrame) -> "Normalizer":
        """Fit medians and MAD scales exclusively on Earth candidate rows."""
        if earth.empty:
            raise ValueError("Cannot fit Normalizer on an empty Earth DataFrame.")
        medians: dict[str, float] = {}
        scales: dict[str, float] = {}
        for feat in MATCH_FEATURES:
            if feat not in earth.columns:
                raise KeyError(f"Missing match feature column in Earth data: {feat!r}")
            vals = preprocess_feature(earth[feat].to_numpy(dtype=np.float64), feat)
            valid = vals[np.isfinite(vals)]
            if valid.size == 0:
                raise ValueError(f"Earth feature {feat!r} has no finite values.")
            med = float(np.median(valid))
            mad = float(np.median(np.abs(valid - med)))
            sc = MAD_TO_SIGMA * mad
            if not np.isfinite(sc) or mad <= 0.0:
                logger.warning(
                    "MAD for Earth feature %s is %.6g; using floor %.1e",
                    feat,
                    mad,
                    MAD_FLOOR,
                )
                sc = MAD_FLOOR
            medians[feat] = med
            scales[feat] = sc
        return cls(median=medians, scale=scales)

    def transform(self, df: pd.DataFrame) -> np.ndarray:
        """Transform MATCH_FEATURES into an (n, 6) z-score matrix in Earth units."""
        n = len(df)
        z = np.empty((n, len(MATCH_FEATURES)), dtype=np.float64)
        for j, feat in enumerate(MATCH_FEATURES):
            if feat not in df.columns:
                raise KeyError(f"Missing match feature column in DataFrame: {feat!r}")
            vals = preprocess_feature(df[feat].to_numpy(dtype=np.float64), feat)
            z[:, j] = (vals - self.median[feat]) / self.scale[feat]
        return z

    def to_dict(self) -> dict[str, object]:
        """Serialize normalization parameters for universe JSON metadata."""
        return {
            "median": {k: float(v) for k, v in self.median.items()},
            "scale": {k: float(v) for k, v in self.scale.items()},
            "log1p": list(LOG_FEATURES),
        }


def thermal_ranks(
    earth: pd.DataFrame,
    mars_t3: pd.DataFrame,
    targets: pd.DataFrame,
) -> tuple[np.ndarray, np.ndarray]:
    """Compute percentile thermal ranks for Earth candidates and Moon/Mars targets."""
    lst = (
        pd.to_numeric(earth["lst_amplitude_c"], errors="coerce").to_numpy(dtype=np.float64)
        if "lst_amplitude_c" in earth.columns
        else np.full(len(earth), np.nan, dtype=np.float64)
    )
    zt_e = np.full(len(earth), np.nan, dtype=np.float64)
    finite_e = np.isfinite(lst)
    n_earth_finite = int(np.sum(finite_e))
    if n_earth_finite > 0:
        zt_e[finite_e] = rankdata(lst[finite_e], method="average") / float(n_earth_finite)

    mars_vals = (
        pd.to_numeric(mars_t3["themis_delta"], errors="coerce").to_numpy(dtype=np.float64)
        if (mars_t3 is not None and not mars_t3.empty and "themis_delta" in mars_t3.columns)
        else np.empty(0, dtype=np.float64)
    )
    mars_sorted = np.sort(mars_vals[np.isfinite(mars_vals)])
    n_mars = mars_sorted.size

    zt_t = np.full(len(targets), np.nan, dtype=np.float64)
    if targets.empty or n_mars == 0 or "themis_delta" not in targets.columns:
        return zt_e, zt_t

    bodies = targets["body"].astype(str).to_numpy()
    deltas = pd.to_numeric(targets["themis_delta"], errors="coerce").to_numpy(dtype=np.float64)
    for idx, (body, td) in enumerate(zip(bodies, deltas)):
        if body.strip().lower() != "mars" or not np.isfinite(td):
            continue
        left = int(np.searchsorted(mars_sorted, td, side="left"))
        right = int(np.searchsorted(mars_sorted, td, side="right"))
        eq = right - left
        if eq > 0:
            zt_t[idx] = (left + 0.5 * (eq + 1)) / float(n_mars)
        else:
            zt_t[idx] = float(left + 1) / float(n_mars + 1)
    return zt_e, zt_t


def dimension_scores(
    z_e: np.ndarray,
    z_t: np.ndarray,
    ndvi: np.ndarray | float,
    zt_e: np.ndarray | float,
    zt_t: float | None,
    sigma_scale: float = 1.0,
) -> dict[str, np.ndarray]:
    """Compute vectorized RBF dimension scores over Earth rows for one target."""
    if sigma_scale <= 0.0:
        raise ValueError(f"sigma_scale must be positive, got {sigma_scale}")
    z_e_arr = np.asarray(z_e, dtype=np.float64)
    if z_e_arr.ndim == 1:
        z_e_arr = z_e_arr.reshape(1, -1)
    z_t_arr = np.asarray(z_t, dtype=np.float64).reshape(-1)
    if z_e_arr.shape[1] != len(MATCH_FEATURES) or z_t_arr.shape[0] != len(MATCH_FEATURES):
        raise ValueError(
            f"Expected {len(MATCH_FEATURES)} features, got z_e={z_e_arr.shape} z_t={z_t_arr.shape}"
        )

    n = z_e_arr.shape[0]
    ndvi_arr = np.broadcast_to(np.asarray(ndvi, dtype=np.float64), (n,))
    zt_e_arr = np.broadcast_to(np.asarray(zt_e, dtype=np.float64), (n,))

    n_topo = len(TOPO)
    d_topo = np.sqrt(np.sum((z_e_arr[:, :n_topo] - z_t_arr[:n_topo]) ** 2, axis=1)) / math.sqrt(n_topo)
    d_rough = np.sqrt(np.sum((z_e_arr[:, n_topo:] - z_t_arr[n_topo:]) ** 2, axis=1)) / math.sqrt(len(ROUGH))

    denom_sigma2 = 2.0 * float(sigma_scale) ** 2
    s_topo = np.exp(-(d_topo ** 2) / denom_sigma2)
    s_rough = np.exp(-(d_rough ** 2) / denom_sigma2)

    s_env = np.ones(n, dtype=np.float64)
    finite_ndvi = np.isfinite(ndvi_arr)
    excess = np.maximum(0.0, ndvi_arr[finite_ndvi] - NDVI_FREE)
    s_env[finite_ndvi] = np.exp(-(excess ** 2) / (2.0 * (NDVI_SCALE ** 2)))

    s_therm = np.full(n, np.nan, dtype=np.float64)
    if zt_t is not None and np.isfinite(float(zt_t)):
        finite_zt_e = np.isfinite(zt_e_arr)
        d_t = np.abs(zt_e_arr[finite_zt_e] - float(zt_t)) / THERMAL_UNIT
        s_therm[finite_zt_e] = np.exp(-(d_t ** 2) / 2.0)

    return {
        "topography": s_topo,
        "roughness": s_rough,
        "environment": s_env,
        "thermal": s_therm,
    }


def _as_float(val: object) -> float:
    """Convert a possibly-null scalar to float (NaN for None/NA)."""
    if val is None:
        return float("nan")
    try:
        if pd.isna(val):
            return float("nan")
    except (TypeError, ValueError):
        pass
    return float(val)


def _as_class(val: object) -> str | None:
    """Return a geology class string or None for null-like values."""
    if val is None:
        return None
    try:
        if pd.isna(val):
            return None
    except (TypeError, ValueError):
        pass
    text = str(val).strip()
    return text or None


def geology_scores(earth_geo_class: np.ndarray, target_class: str | None) -> np.ndarray:
    """Similarity of every Earth patch class to the target class via GEO_SIMILARITY (NaN if null)."""
    n = len(earth_geo_class)
    out = np.full(n, np.nan, dtype=np.float64)
    tcls = _as_class(target_class)
    if tcls is None or tcls not in GEO_SIMILARITY:
        return out
    row = GEO_SIMILARITY[tcls]
    classes = pd.Series([_as_class(c) for c in earth_geo_class], dtype=object)
    mapped = classes.map(lambda c: row.get(c, np.nan) if c is not None else np.nan)
    return mapped.to_numpy(dtype=np.float64)


def dust_scores(
    body: str,
    e_level_rank: np.ndarray,
    e_season_rank: np.ndarray,
    e_phase_deg: np.ndarray,
    e_lat: np.ndarray,
    t_level_rank: float,
    t_season_rank: float,
    t_phase_deg: float,
    t_lat: float,
) -> np.ndarray:
    """Dust process similarity (Mars targets only); phase is dropped within 15 deg of the equator."""
    n = len(e_level_rank)
    if str(body).strip().lower() != "mars":
        return np.full(n, np.nan, dtype=np.float64)
    out = S_dust(
        e_level_rank,
        e_season_rank,
        e_phase_deg,
        float(t_level_rank),
        float(t_season_rank),
        float(t_phase_deg),
        lat_e=e_lat,
        lat_t=float(t_lat),
    )
    return np.asarray(out, dtype=np.float64)


def ice_scores(
    body: str,
    e_cold_rank: np.ndarray,
    e_ice: np.ndarray,
    t_cold_rank: float,
    t_ice: float,
) -> np.ndarray:
    """Cold-trap and ice similarity (Moon with Diviner; Mars only when ice_T > 0)."""
    n = len(e_cold_rank)
    t_ice_f = float(t_ice)
    if not np.isfinite(t_ice_f):
        return np.full(n, np.nan, dtype=np.float64)
    out = S_ice(
        str(body),
        e_cold_rank,
        e_ice,
        None if not np.isfinite(float(t_cold_rank)) else float(t_cold_rank),
        t_ice_f,
    )
    return np.asarray(out, dtype=np.float64)


def msi(
    scores: dict[str, np.ndarray | float],
    weights: dict[str, float],
) -> np.ndarray | float:
    """Compute weighted mean similarity over non-null weighted dimensions."""
    raw_arrays = {k: np.asarray(v, dtype=np.float64) for k, v in scores.items()}
    is_scalar = all(arr.ndim == 0 for arr in raw_arrays.values())
    if is_scalar:
        num = 0.0
        den = 0.0
        for dim, w in weights.items():
            if w <= 0.0 or dim not in raw_arrays:
                continue
            val = float(raw_arrays[dim])
            if np.isfinite(val):
                num += float(w) * val
                den += float(w)
        return float(num / den) if den > 0.0 else float("nan")

    length = max(arr.shape[0] for arr in raw_arrays.values() if arr.ndim >= 1)
    num_arr = np.zeros(length, dtype=np.float64)
    den_arr = np.zeros(length, dtype=np.float64)
    for dim, w in weights.items():
        if w <= 0.0 or dim not in raw_arrays:
            continue
        arr = np.broadcast_to(raw_arrays[dim], (length,))
        finite = np.isfinite(arr)
        num_arr[finite] += float(w) * arr[finite]
        den_arr[finite] += float(w)

    out = np.full(length, np.nan, dtype=np.float64)
    has_weight = den_arr > 0.0
    out[has_weight] = num_arr[has_weight] / den_arr[has_weight]
    return out


def haversine_km(
    lat1: float | np.ndarray,
    lon1: float | np.ndarray,
    lat2: float | np.ndarray,
    lon2: float | np.ndarray,
) -> np.ndarray | float:
    """Great-circle distance on Earth (R = 6371 km) in kilometres."""
    lat1_r = np.radians(lat1)
    lon1_r = np.radians(lon1)
    lat2_r = np.radians(lat2)
    lon2_r = np.radians(lon2)
    dlat = lat2_r - lat1_r
    dlon = lon2_r - lon1_r
    a = np.sin(dlat / 2.0) ** 2 + np.cos(lat1_r) * np.cos(lat2_r) * np.sin(dlon / 2.0) ** 2
    return EARTH_RADIUS_KM * 2.0 * np.arcsin(np.minimum(1.0, np.sqrt(a)))


def select_diverse(
    order: np.ndarray | list[int],
    lat: np.ndarray,
    lon: np.ndarray,
    polar: np.ndarray,
    n: int = TOP_N,
    min_sep_km: float = MIN_SEP_KM,
    max_polar: int = MAX_POLAR_PER_PRESET,
) -> list[int]:
    """Greedy walk over sorted candidate indices enforcing >= 150 km separation and polar cap."""
    lat_arr = np.asarray(lat, dtype=np.float64)
    lon_arr = np.asarray(lon, dtype=np.float64)
    polar_arr = np.asarray(polar, dtype=bool)
    accepted: list[int] = []
    acc_lats: list[float] = []
    acc_lons: list[float] = []
    polar_count = 0

    for raw_idx in order:
        idx = int(raw_idx)
        is_polar = bool(polar_arr[idx])
        if is_polar and polar_count >= max_polar:
            continue
        if accepted:
            dists = haversine_km(
                lat_arr[idx],
                lon_arr[idx],
                np.asarray(acc_lats, dtype=np.float64),
                np.asarray(acc_lons, dtype=np.float64),
            )
            if np.any(np.asarray(dists, dtype=np.float64) < min_sep_km):
                continue
        accepted.append(idx)
        acc_lats.append(float(lat_arr[idx]))
        acc_lons.append(float(lon_arr[idx]))
        if is_polar:
            polar_count += 1
        if len(accepted) >= n:
            break
    return accepted


def mismatches(
    e_row: pd.Series | dict[str, object],
    t_row: pd.Series | dict[str, object],
    z_e: np.ndarray,
    z_t: np.ndarray,
    zt_e: float,
    zt_t: float,
) -> list[dict[str, object]]:
    """List physical feature mismatches exceeding |z_diff| > 1.5 and Mars thermal delta > 0.30."""
    out: list[dict[str, object]] = []
    for i, feat in enumerate(MATCH_FEATURES):
        diff = float(z_e[i] - z_t[i])
        if not np.isfinite(diff) or abs(diff) <= MISMATCH_Z:
            continue
        out.append(
            {
                "feature": feat,
                "earth": round(float(e_row[feat]), 2),
                "target": round(float(t_row[feat]), 2),
                "z_diff": round(diff, 2),
            }
        )
    if np.isfinite(zt_e) and np.isfinite(zt_t) and abs(float(zt_e) - float(zt_t)) > MISMATCH_THERMAL:
        out.append(
            {
                "feature": "thermal_rank",
                "earth": round(float(zt_e), 2),
                "target": round(float(zt_t), 2),
                "z_diff": round((float(zt_e) - float(zt_t)) / THERMAL_UNIT, 2),
            }
        )
    return out


def layer_mismatches(
    body: str,
    e_geo: str | None,
    t_geo: str | None,
    e_level: float,
    t_level: float,
    e_season: float,
    t_season: float,
    e_phase: float,
    t_phase: float,
    e_lat: float,
    t_lat: float,
    e_cold: float,
    t_cold: float,
) -> list[dict[str, object]]:
    """T15 mismatches: geology class change, dust rank/phase gaps, and cold-rank gap."""
    out: list[dict[str, object]] = []
    e_cls, t_cls = _as_class(e_geo), _as_class(t_geo)
    if e_cls is not None and t_cls is not None and e_cls != t_cls:
        out.append({"feature": "geo_class", "earth": e_cls, "target": t_cls, "z_diff": None})

    if str(body).strip().lower() == "mars":
        for name, e_val, t_val in (
            ("dust_level_rank", e_level, t_level),
            ("dust_seasonality_rank", e_season, t_season),
        ):
            if np.isfinite(e_val) and np.isfinite(t_val) and abs(e_val - t_val) > MISMATCH_RANK:
                out.append(
                    {
                        "feature": name,
                        "earth": round(float(e_val), 2),
                        "target": round(float(t_val), 2),
                        "z_diff": round((float(e_val) - float(t_val)) / THERMAL_UNIT, 2),
                    }
                )
        tropical = (np.isfinite(e_lat) and abs(e_lat) < TROPICAL_LAT_DEG) or (
            np.isfinite(t_lat) and abs(t_lat) < TROPICAL_LAT_DEG
        )
        if (not tropical) and np.isfinite(e_phase) and np.isfinite(t_phase):
            gap = float(circular_diff(e_phase, t_phase))
            if gap > MISMATCH_PHASE_DEG:
                signed = ((float(e_phase) - float(t_phase) + 180.0) % 360.0) - 180.0
                out.append(
                    {
                        "feature": "dust_peak_phase_deg",
                        "earth": round(float(e_phase), 1),
                        "target": round(float(t_phase), 1),
                        "z_diff": round(signed / PHASE_UNIT_DEG, 2),
                    }
                )

    if np.isfinite(e_cold) and np.isfinite(t_cold) and abs(e_cold - t_cold) > MISMATCH_RANK:
        out.append(
            {
                "feature": "cold_rank",
                "earth": round(float(e_cold), 2),
                "target": round(float(t_cold), 2),
                "z_diff": round((float(e_cold) - float(t_cold)) / THERMAL_UNIT, 2),
            }
        )
    return out


LAYER_EARTH_COLUMNS: dict[str, tuple[str, list[str]]] = {
    "t14": ("geology_earth.parquet", ["glim_code", "geo_class", "ice_surface", "lava_tube_terrain"]),
    "t13": ("dust_earth.parquet", ["dust_level_rank", "dust_seasonality_rank", "dust_peak_phase_deg"]),
    "t12": ("ice_earth.parquet", ["cold_rank_E", "ice_E"]),
}
LAYER_TARGET_COLUMNS: dict[str, tuple[str, dict[str, str]]] = {
    "t14": (
        "geology_targets.parquet",
        {"unit": "geo_unit", "geo_class": "geo_class", "geo_class_share": "geo_class_share"},
    ),
    "t13": (
        "dust_targets.parquet",
        {
            "dust_level_rank": "dust_level_rank",
            "dust_seasonality_rank": "dust_seasonality_rank",
            "dust_peak_phase_deg": "dust_peak_phase_deg",
        },
    ),
    "t12": (
        "ice_targets.parquet",
        {"cold_rank_T": "cold_rank_T", "ice_T": "ice_T", "ice_source": "ice_source"},
    ),
}


def load_layers(
    earth: pd.DataFrame,
    targets: pd.DataFrame,
    t12_dir: Path,
    t13_dir: Path,
    t14_dir: Path,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Attach T12/T13/T14 Earth-patch and target columns (row-aligned, verified by lat/lon)."""
    dirs = {"t12": Path(t12_dir), "t13": Path(t13_dir), "t14": Path(t14_dir)}
    earth_out = earth.reset_index(drop=True).copy()
    lat = earth_out["lat"].to_numpy(dtype=np.float64)
    lon = earth_out["lon"].to_numpy(dtype=np.float64)
    for key, (fname, cols) in LAYER_EARTH_COLUMNS.items():
        layer = pd.read_parquet(dirs[key] / fname)
        if len(layer) != len(earth_out):
            raise ValueError(f"{dirs[key] / fname}: {len(layer)} rows != {len(earth_out)} Earth patches")
        if not (
            np.allclose(layer["lat"].to_numpy(dtype=np.float64), lat, atol=1e-6)
            and np.allclose(layer["lon"].to_numpy(dtype=np.float64), lon, atol=1e-6)
        ):
            raise ValueError(f"{dirs[key] / fname}: lat/lon are not aligned with the Earth patch table")
        for col in cols:
            if col in earth_out.columns:
                raise ValueError(f"Earth table already has column {col!r}")
            earth_out[col] = layer[col].reset_index(drop=True)

    targets_out = targets.reset_index(drop=True).copy()
    targets_out["target_id"] = targets_out["target_id"].astype(str)
    for key, (fname, colmap) in LAYER_TARGET_COLUMNS.items():
        layer = pd.read_parquet(dirs[key] / fname)
        layer = layer.assign(target_id=layer["target_id"].astype(str))
        sub = layer[["target_id", *colmap.keys()]].rename(columns=colmap)
        clash = [c for c in colmap.values() if c in targets_out.columns]
        if clash:
            raise ValueError(f"Targets table already has column(s) {clash}")
        targets_out = targets_out.merge(sub, on="target_id", how="left", validate="one_to_one")
    return earth_out, targets_out


@dataclass
class EarthArrays:
    """Per-Earth-patch arrays used by the vectorised scorer."""

    z_e: np.ndarray
    ndvi: np.ndarray
    zt_e: np.ndarray
    lat: np.ndarray
    lon: np.ndarray
    ice_surface: np.ndarray
    geo_class: np.ndarray
    dust_level_rank: np.ndarray
    dust_season_rank: np.ndarray
    dust_phase: np.ndarray
    cold_rank: np.ndarray
    ice_e: np.ndarray


@dataclass
class TargetVec:
    """One target's scoring inputs."""

    body: str
    z_t: np.ndarray
    zt_t: float
    lat: float
    geo_class: str | None
    dust_level_rank: float
    dust_season_rank: float
    dust_phase: float
    cold_rank: float
    ice_t: float


def _num_col(df: pd.DataFrame, name: str) -> np.ndarray:
    if name in df.columns:
        return pd.to_numeric(df[name], errors="coerce").to_numpy(dtype=np.float64)
    return np.full(len(df), np.nan, dtype=np.float64)


def build_earth_arrays(earth_df: pd.DataFrame, z_e: np.ndarray, zt_e: np.ndarray) -> EarthArrays:
    """Collect scoring arrays from an Earth table (layer columns may be missing -> null scores)."""
    n = len(earth_df)
    if "geo_class" in earth_df.columns:
        geo = np.array([_as_class(c) for c in earth_df["geo_class"]], dtype=object)
    else:
        geo = np.full(n, None, dtype=object)
    if "ice_surface" in earth_df.columns:
        ice_surface = earth_df["ice_surface"].fillna(False).to_numpy(dtype=bool)
    else:
        ice_surface = np.zeros(n, dtype=bool)
    return EarthArrays(
        z_e=z_e,
        ndvi=_num_col(earth_df, "ndvi_max"),
        zt_e=zt_e,
        lat=_num_col(earth_df, "lat"),
        lon=_num_col(earth_df, "lon"),
        ice_surface=ice_surface,
        geo_class=geo,
        dust_level_rank=_num_col(earth_df, "dust_level_rank"),
        dust_season_rank=_num_col(earth_df, "dust_seasonality_rank"),
        dust_phase=_num_col(earth_df, "dust_peak_phase_deg"),
        cold_rank=_num_col(earth_df, "cold_rank_E"),
        ice_e=_num_col(earth_df, "ice_E"),
    )


def score_target(ea: EarthArrays, tv: TargetVec, sigma_scale: float = 1.0) -> dict[str, np.ndarray]:
    """Score all Earth patches on the seven dimensions for one target."""
    scores = dimension_scores(ea.z_e, tv.z_t, ea.ndvi, ea.zt_e, tv.zt_t, sigma_scale=sigma_scale)
    scores["geology"] = geology_scores(ea.geo_class, tv.geo_class)
    scores["dust"] = dust_scores(
        tv.body,
        ea.dust_level_rank,
        ea.dust_season_rank,
        ea.dust_phase,
        ea.lat,
        tv.dust_level_rank,
        tv.dust_season_rank,
        tv.dust_phase,
        tv.lat,
    )
    scores["ice"] = ice_scores(tv.body, ea.cold_rank, ea.ice_e, tv.cold_rank, tv.ice_t)
    return scores


def select_by_preset(
    scores: dict[str, np.ndarray],
    ea: EarthArrays,
    presets: dict[str, dict[str, object]] | None = None,
) -> tuple[dict[str, np.ndarray], dict[str, list[int]]]:
    """MSI per preset over the whole Earth table and the diverse top-N lists (ice cap except ISRU)."""
    presets = presets or PRESETS
    msi_by_preset: dict[str, np.ndarray] = {}
    selected: dict[str, list[int]] = {}
    for pkey, spec in presets.items():
        msi_vals = np.asarray(msi(scores, spec["weights"]), dtype=np.float64)
        msi_by_preset[pkey] = msi_vals
        order = np.argsort(-np.where(np.isfinite(msi_vals), msi_vals, -np.inf), kind="mergesort")
        order = order[np.isfinite(msi_vals[order])]
        cap = TOP_N if pkey in ICE_CAP_EXEMPT_PRESETS else MAX_ICE_SURFACE_PER_PRESET
        selected[pkey] = select_diverse(
            order,
            ea.lat,
            ea.lon,
            ea.ice_surface,
            n=TOP_N,
            min_sep_km=MIN_SEP_KM,
            max_polar=cap,
        )
    return msi_by_preset, selected


def target_vec_from_row(t_row: pd.Series, z_t: np.ndarray, zt_t: float) -> TargetVec:
    """Build a TargetVec from a targets-table row that carries the layer columns."""
    return TargetVec(
        body=str(t_row["body"]),
        z_t=z_t,
        zt_t=float(zt_t),
        lat=_as_float(t_row.get("lat")),
        geo_class=_as_class(t_row.get("geo_class")),
        dust_level_rank=_as_float(t_row.get("dust_level_rank")),
        dust_season_rank=_as_float(t_row.get("dust_seasonality_rank")),
        dust_phase=_as_float(t_row.get("dust_peak_phase_deg")),
        cold_rank=_as_float(t_row.get("cold_rank_T")),
        ice_t=_as_float(t_row.get("ice_T")),
    )


def match_all(
    earth: pd.DataFrame,
    targets: pd.DataFrame,
    mars_t3: pd.DataFrame,
    sigma_scale: float = 1.0,
    target_ids: list[str] | None = None,
    normalizer: Normalizer | None = None,
    meta_out: dict[str, object] | None = None,
) -> pd.DataFrame:
    """Score the whole Earth table per target on 7 dimensions and select diverse top-N per preset."""
    earth_df = earth.reset_index(drop=True).copy()
    if "earth_id" not in earth_df.columns:
        earth_df["earth_id"] = [
            format_earth_id(la, lo)
            for la, lo in zip(earth_df["lat"].to_numpy(), earth_df["lon"].to_numpy())
        ]

    targets_df = targets.reset_index(drop=True).copy()
    if "status" in targets_df.columns:
        not_ok = targets_df[targets_df["status"] != "ok"]
        for _, bad in not_ok.iterrows():
            logger.warning(
                "Skipping target %s with status=%r",
                bad.get("target_id", "?"),
                bad.get("status"),
            )
        targets_df = targets_df[targets_df["status"] == "ok"].reset_index(drop=True)

    if target_ids is not None:
        wanted = set(target_ids)
        targets_df = targets_df[targets_df["target_id"].isin(wanted)].reset_index(drop=True)

    norm = normalizer or Normalizer.fit_earth(earth_df)
    z_e = norm.transform(earth_df)
    z_t_all = norm.transform(targets_df)

    finite_earth_mask = np.all(np.isfinite(z_e), axis=1)
    if not np.all(finite_earth_mask):
        n_dropped = int(np.sum(~finite_earth_mask))
        logger.warning("Dropping %d Earth rows with non-finite matching features", n_dropped)
        earth_df = earth_df.loc[finite_earth_mask].reset_index(drop=True)
        z_e = z_e[finite_earth_mask]

    zt_e, zt_t_all = thermal_ranks(earth_df, mars_t3, targets_df)
    ea = build_earth_arrays(earth_df, z_e, zt_e)
    lst_day = _num_col(earth_df, "lst_day_c")
    polar_cold_e = lst_day < POLAR_COLD_LST_C
    earth_ids = earth_df["earth_id"].astype(str).to_numpy()
    earth_records = earth_df[MATCH_FEATURES].to_dict(orient="records")
    n_earth = len(earth_df)

    rows: list[dict[str, object]] = []
    for t_idx, t_row in targets_df.iterrows():
        tid = str(t_row["target_id"])
        z_t = z_t_all[t_idx]
        if not np.all(np.isfinite(z_t)):
            logger.warning("Skipping target %s with non-finite terrain features", tid)
            continue
        tv = target_vec_from_row(t_row, z_t, float(zt_t_all[t_idx]))
        scores = score_target(ea, tv, sigma_scale=sigma_scale)
        msi_by_preset, selected_global = select_by_preset(scores, ea)

        preset_ranks: dict[str, dict[int, int]] = {
            pkey: {g_idx: rank_i for rank_i, g_idx in enumerate(g_list, start=1)}
            for pkey, g_list in selected_global.items()
        }
        union_ordered: list[int] = []
        seen_union: set[int] = set()
        for pkey in PRESET_KEYS:
            for g_idx in selected_global[pkey]:
                if g_idx not in seen_union:
                    seen_union.add(g_idx)
                    union_ordered.append(g_idx)

        t_phys = {feat: t_row[feat] for feat in MATCH_FEATURES}
        for g_idx in union_ordered:
            sel_presets = [pkey for pkey in PRESET_KEYS if g_idx in preset_ranks[pkey]]
            mm = mismatches(
                earth_records[g_idx],
                t_phys,
                z_e[g_idx],
                z_t,
                float(zt_e[g_idx]),
                tv.zt_t,
            )
            mm.extend(
                layer_mismatches(
                    tv.body,
                    ea.geo_class[g_idx],
                    tv.geo_class,
                    float(ea.dust_level_rank[g_idx]),
                    tv.dust_level_rank,
                    float(ea.dust_season_rank[g_idx]),
                    tv.dust_season_rank,
                    float(ea.dust_phase[g_idx]),
                    tv.dust_phase,
                    float(ea.lat[g_idx]),
                    tv.lat,
                    float(ea.cold_rank[g_idx]),
                    tv.cold_rank,
                )
            )
            rec: dict[str, object] = {
                "target_id": tid,
                "earth_id": str(earth_ids[g_idx]),
                "lat": float(ea.lat[g_idx]),
                "lon": float(ea.lon[g_idx]),
                "selected_by": ",".join(sel_presets),
            }
            for pkey in PRESET_KEYS:
                rec[f"rank_{pkey}"] = preset_ranks[pkey].get(g_idx, pd.NA)
            for dim in DIMENSION_KEYS:
                rec[f"S_{dim}"] = float(scores[dim][g_idx])
            for pkey in PRESET_KEYS:
                rec[f"msi_{pkey}"] = float(msi_by_preset[pkey][g_idx])
            rec["polar_cold"] = bool(polar_cold_e[g_idx])
            rec["ice_surface"] = bool(ea.ice_surface[g_idx])
            rec["mismatches_json"] = json.dumps(mm, allow_nan=False)
            rec["retry_used"] = False
            rows.append(rec)

    out_df = pd.DataFrame(rows)
    for pkey in PRESET_KEYS:
        col = f"rank_{pkey}"
        if col in out_df.columns:
            out_df[col] = pd.array(out_df[col], dtype="Int64")

    if meta_out is not None:
        meta_out.update(
            {
                "sigma_scale": float(sigma_scale),
                "earth_patches_evaluated": int(n_earth),
                "normalization": norm.to_dict(),
                "retry_targets": [],
                "targets_matched": int(len(targets_df)),
                "candidate_pool": "none (whole Earth scored per target)",
            }
        )
    return out_df


def _git_short_sha(repo_dir: Path) -> str:
    try:
        res = subprocess.run(
            ["git", "-C", str(repo_dir), "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        return res.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Match planetary targets to Earth analogs (T7).")
    p.add_argument("--t3-dir", type=Path, default=YUCA_PROJECT_DIR / "runs" / "2242278")
    p.add_argument("--t4-dir", type=Path, default=YUCA_PROJECT_DIR / "runs" / "2242423")
    p.add_argument("--t5-dir", type=Path, required=True)
    p.add_argument("--t12-dir", type=Path, required=True, help="T12 ice run directory")
    p.add_argument("--t13-dir", type=Path, required=True, help="T13 dust run directory")
    p.add_argument("--t14-dir", type=Path, required=True, help="T14 geology run directory")
    p.add_argument("--out-dir", type=Path, required=True)
    p.add_argument("--sigma-scale", type=float, default=1.0)
    p.add_argument("--targets", type=str, default=None, help="Comma-separated target_id list")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="[%(levelname)s] %(name)s: %(message)s",
    )
    t0 = time.perf_counter()
    args = _parse_args(argv)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    earth_path = args.t5_dir / "features_earth.parquet"
    targets_path = args.t4_dir / "targets.parquet"
    mars_path = args.t3_dir / "features_mars.parquet"

    logger.info("Loading Earth patches from %s", earth_path)
    earth = pd.read_parquet(earth_path)
    logger.info("Loading targets from %s", targets_path)
    targets = pd.read_parquet(targets_path)
    logger.info("Loading Mars T3 features from %s", mars_path)
    mars_t3 = pd.read_parquet(mars_path, columns=["themis_delta"])
    logger.info(
        "Attaching T12 %s, T13 %s and T14 %s layers", args.t12_dir, args.t13_dir, args.t14_dir
    )
    earth, targets = load_layers(earth, targets, args.t12_dir, args.t13_dir, args.t14_dir)

    target_filter = (
        [tok.strip() for tok in args.targets.split(",") if tok.strip()]
        if args.targets
        else None
    )

    meta: dict[str, object] = {}
    matches_df = match_all(
        earth=earth,
        targets=targets,
        mars_t3=mars_t3,
        sigma_scale=args.sigma_scale,
        target_ids=target_filter,
        meta_out=meta,
    )
    elapsed_s = time.perf_counter() - t0

    meta.update(
        {
            "t3_dir": str(args.t3_dir),
            "t4_dir": str(args.t4_dir),
            "t5_dir": str(args.t5_dir),
            "t12_dir": str(args.t12_dir),
            "t13_dir": str(args.t13_dir),
            "t14_dir": str(args.t14_dir),
            "slurm_job_id": os.environ.get("SLURM_JOB_ID"),
            "commit": _git_short_sha(Path(__file__).resolve().parents[1]),
            "match_runtime_s": round(elapsed_s, 3),
        }
    )

    matches_out = args.out_dir / "matches.parquet"
    meta_out_path = args.out_dir / "matches_meta.json"
    matches_df.to_parquet(matches_out, index=False)
    with open(meta_out_path, "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2, allow_nan=False)

    logger.info(
        "Wrote %d match rows (%d targets) to %s in %.2fs",
        len(matches_df),
        meta.get("targets_matched", 0),
        matches_out,
        elapsed_s,
    )


if __name__ == "__main__":
    main()
