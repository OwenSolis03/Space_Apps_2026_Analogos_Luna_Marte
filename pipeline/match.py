"""Planetary analog matching: Earth-unit normalization, RBF dimension scoring,
MSI presets, 150 km diversity selection, polar cap, and mismatch reporting (T7).
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
from sklearn.neighbors import NearestNeighbors

from .config import BODY_RADII_M, YUCA_PROJECT_DIR

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

PRESETS: dict[str, dict[str, object]] = {
    "mobility_and_traction": {
        "label": "Rover mobility and traction",
        "weights": {
            "topography": 0.45,
            "roughness": 0.40,
            "environment": 0.15,
            "thermal": 0.00,
        },
    },
    "construction_and_base": {
        "label": "Base construction and landing",
        "weights": {
            "topography": 0.55,
            "roughness": 0.25,
            "environment": 0.10,
            "thermal": 0.10,
        },
    },
    "dust_and_thermal": {
        "label": "Dust and thermal environment",
        "weights": {
            "topography": 0.15,
            "roughness": 0.15,
            "environment": 0.40,
            "thermal": 0.30,
        },
    },
}
PRESET_KEYS: tuple[str, ...] = tuple(PRESETS.keys())

NDVI_FREE: float = 0.10
NDVI_SCALE: float = 0.10
THERMAL_UNIT: float = 0.15
POLAR_COLD_LST_C: float = -10.0
MAX_POLAR_PER_PRESET: int = 3
TOP_N: int = 30
MIN_SEP_KM: float = 150.0
POOL_K: int = 2000
POOL_K_RETRY: int = 8000
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


def _knn_embedding(z_matrix: np.ndarray) -> np.ndarray:
    """Scale z matrix so Euclidean distance equals sqrt(d_topo^2 + d_rough^2)."""
    n_topo = len(TOPO)
    n_rough = len(ROUGH)
    return np.column_stack(
        [
            z_matrix[:, :n_topo] / math.sqrt(n_topo),
            z_matrix[:, n_topo:] / math.sqrt(n_rough),
        ]
    )


def _sort_order_by_msi(pool_indices: np.ndarray, msi_vals: np.ndarray) -> np.ndarray:
    """Return local pool positions sorted by MSI descending (NaNs last)."""
    safe_msi = np.where(np.isfinite(msi_vals), msi_vals, -np.inf)
    return np.argsort(-safe_msi, kind="mergesort")


def _select_target_analogs(
    z_e_pool: np.ndarray,
    z_t: np.ndarray,
    ndvi_pool: np.ndarray,
    zt_e_pool: np.ndarray,
    zt_t: float,
    lat_pool: np.ndarray,
    lon_pool: np.ndarray,
    polar_pool: np.ndarray,
    pool_idx: np.ndarray,
    sigma_scale: float,
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray], dict[str, list[int]]]:
    """Score a target's candidate pool and select diverse top-N lists per preset."""
    scores = dimension_scores(
        z_e_pool,
        z_t,
        ndvi_pool,
        zt_e_pool,
        zt_t,
        sigma_scale=sigma_scale,
    )
    msi_by_preset: dict[str, np.ndarray] = {}
    selected_global: dict[str, list[int]] = {}
    for preset_key in PRESET_KEYS:
        weights = PRESETS[preset_key]["weights"]
        msi_vals = np.asarray(msi(scores, weights), dtype=np.float64)
        msi_by_preset[preset_key] = msi_vals
        local_order = _sort_order_by_msi(pool_idx, msi_vals)
        chosen_local = select_diverse(
            local_order,
            lat_pool,
            lon_pool,
            polar_pool,
            n=TOP_N,
            min_sep_km=MIN_SEP_KM,
            max_polar=MAX_POLAR_PER_PRESET,
        )
        selected_global[preset_key] = [int(pool_idx[pos]) for pos in chosen_local]
    return scores, msi_by_preset, selected_global


def match_all(
    earth: pd.DataFrame,
    targets: pd.DataFrame,
    mars_t3: pd.DataFrame,
    sigma_scale: float = 1.0,
    target_ids: list[str] | None = None,
    normalizer: Normalizer | None = None,
    meta_out: dict[str, object] | None = None,
) -> pd.DataFrame:
    """Run candidate search, RBF scoring, diversity filtering, and mismatch extraction for targets."""
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
    ndvi_e = (
        pd.to_numeric(earth_df["ndvi_max"], errors="coerce").to_numpy(dtype=np.float64)
        if "ndvi_max" in earth_df.columns
        else np.full(len(earth_df), np.nan, dtype=np.float64)
    )
    lst_day = (
        pd.to_numeric(earth_df["lst_day_c"], errors="coerce").to_numpy(dtype=np.float64)
        if "lst_day_c" in earth_df.columns
        else np.full(len(earth_df), np.nan, dtype=np.float64)
    )
    polar_e = lst_day < POLAR_COLD_LST_C
    lat_e = pd.to_numeric(earth_df["lat"], errors="coerce").to_numpy(dtype=np.float64)
    lon_e = pd.to_numeric(earth_df["lon"], errors="coerce").to_numpy(dtype=np.float64)
    earth_ids = earth_df["earth_id"].astype(str).to_numpy()
    earth_records = earth_df[MATCH_FEATURES].to_dict(orient="records")

    knn_e = _knn_embedding(z_e)
    knn_t_all = _knn_embedding(z_t_all)
    n_earth = len(earth_df)
    nn = NearestNeighbors(metric="euclidean", algorithm="auto").fit(knn_e)

    retry_targets: list[str] = []
    rows: list[dict[str, object]] = []

    for t_idx, t_row in targets_df.iterrows():
        tid = str(t_row["target_id"])
        z_t = z_t_all[t_idx]
        if not np.all(np.isfinite(z_t)):
            logger.warning("Skipping target %s with non-finite terrain features", tid)
            continue
        q_vec = knn_t_all[t_idx : t_idx + 1]
        k_init = min(POOL_K, n_earth)
        pool_idx = nn.kneighbors(q_vec, n_neighbors=k_init, return_distance=False)[0]
        retry_used = False

        scores, msi_by_preset, selected_global = _select_target_analogs(
            z_e[pool_idx],
            z_t,
            ndvi_e[pool_idx],
            zt_e[pool_idx],
            float(zt_t_all[t_idx]),
            lat_e[pool_idx],
            lon_e[pool_idx],
            polar_e[pool_idx],
            pool_idx,
            sigma_scale=sigma_scale,
        )

        min_count = min(len(v) for v in selected_global.values())
        k_retry = min(POOL_K_RETRY, n_earth)
        if min_count < TOP_N and k_retry > k_init:
            logger.info(
                "Target %s got min %d/%d analogs in k=%d pool; retrying with k=%d",
                tid,
                min_count,
                TOP_N,
                k_init,
                k_retry,
            )
            pool_idx = nn.kneighbors(q_vec, n_neighbors=k_retry, return_distance=False)[0]
            retry_used = True
            retry_targets.append(tid)
            scores, msi_by_preset, selected_global = _select_target_analogs(
                z_e[pool_idx],
                z_t,
                ndvi_e[pool_idx],
                zt_e[pool_idx],
                float(zt_t_all[t_idx]),
                lat_e[pool_idx],
                lon_e[pool_idx],
                polar_e[pool_idx],
                pool_idx,
                sigma_scale=sigma_scale,
            )

        global_to_pool_pos = {int(g_idx): pos for pos, g_idx in enumerate(pool_idx.tolist())}
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
        zt_t_val = float(zt_t_all[t_idx])

        for g_idx in union_ordered:
            pos = global_to_pool_pos[g_idx]
            sel_presets = [pkey for pkey in PRESET_KEYS if g_idx in preset_ranks[pkey]]
            mm = mismatches(
                earth_records[g_idx],
                t_phys,
                z_e[g_idx],
                z_t,
                float(zt_e[g_idx]),
                zt_t_val,
            )
            rec: dict[str, object] = {
                "target_id": tid,
                "earth_id": str(earth_ids[g_idx]),
                "lat": float(lat_e[g_idx]),
                "lon": float(lon_e[g_idx]),
                "rank_mobility_and_traction": preset_ranks["mobility_and_traction"].get(g_idx, pd.NA),
                "rank_construction_and_base": preset_ranks["construction_and_base"].get(g_idx, pd.NA),
                "rank_dust_and_thermal": preset_ranks["dust_and_thermal"].get(g_idx, pd.NA),
                "selected_by": ",".join(sel_presets),
                "S_topography": float(scores["topography"][pos]),
                "S_roughness": float(scores["roughness"][pos]),
                "S_environment": float(scores["environment"][pos]),
                "S_thermal": float(scores["thermal"][pos]),
                "msi_mobility_and_traction": float(msi_by_preset["mobility_and_traction"][pos]),
                "msi_construction_and_base": float(msi_by_preset["construction_and_base"][pos]),
                "msi_dust_and_thermal": float(msi_by_preset["dust_and_thermal"][pos]),
                "polar_cold": bool(polar_e[g_idx]),
                "mismatches_json": json.dumps(mm, allow_nan=False),
                "retry_used": bool(retry_used),
            }
            rows.append(rec)

    out_df = pd.DataFrame(rows)
    for col in (
        "rank_mobility_and_traction",
        "rank_construction_and_base",
        "rank_dust_and_thermal",
    ):
        if col in out_df.columns:
            out_df[col] = pd.array(out_df[col], dtype="Int64")

    if meta_out is not None:
        meta_out.update(
            {
                "sigma_scale": float(sigma_scale),
                "earth_patches_evaluated": int(n_earth),
                "normalization": norm.to_dict(),
                "retry_targets": retry_targets,
                "targets_matched": int(len(targets_df)),
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
