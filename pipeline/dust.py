"""Dust process and seasonal phase (T13): Mars Montabone CDOD (610 Pa) & Earth MOD08_M3 AOD."""

from __future__ import annotations

import argparse
import calendar
from datetime import date, timedelta
import json
import logging
import os
from pathlib import Path
import re
import subprocess
import time

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import rankdata

from .config import YUCA_PROJECT_DIR

logger = logging.getLogger(__name__)

MARS_DUST_REL: Path = Path("mars/dust_montabone")
EARTH_AOD_REL: Path = Path("earth/modis/aod")
EXPECTED_AOD_SDS: str = "Deep_Blue_Aerosol_Optical_Depth_550_Land_Mean_Mean"

STORM_YEARS: tuple[int, ...] = (25, 28, 34)
MIN_VALID_BINS_EARTH: int = 9
MIN_VALID_BINS_MARS: int = 9
DUST_RANK_SIGMA: float = 0.15
DUST_PHASE_SIGMA_DEG: float = 60.0
SEASONALITY_EPS: float = 1e-6


def Ls_E(doy: float | np.ndarray) -> float | np.ndarray:
    """Approximate Earth solar longitude (deg, 0 = March equinox) from day-of-year."""
    arr = np.asarray(doy, dtype=np.float64)
    out = ((arr - 79.5) / 365.2422 * 360.0) % 360.0
    if np.ndim(doy) == 0:
        return float(out)
    return out


earth_ls = Ls_E


def local_phase(
    ls_deg: float | np.ndarray,
    lat: float | np.ndarray,
) -> float | np.ndarray:
    """Shift southern hemisphere solar longitude by +180 deg so summer aligns across hemispheres."""
    ls_arr = np.asarray(ls_deg, dtype=np.float64)
    lat_arr = np.asarray(lat, dtype=np.float64)
    out = np.where(lat_arr < 0.0, (ls_arr + 180.0) % 360.0, ls_arr % 360.0)
    if np.ndim(ls_deg) == 0 and np.ndim(lat) == 0:
        return float(out)
    return out


def circular_diff(
    a_deg: float | np.ndarray,
    b_deg: float | np.ndarray,
) -> float | np.ndarray:
    """Smallest angular separation on a 360 deg circle, in [0, 180]."""
    diff = np.abs((np.asarray(a_deg, dtype=np.float64) - np.asarray(b_deg, dtype=np.float64)) % 360.0)
    out = np.minimum(diff, 360.0 - diff)
    if np.ndim(a_deg) == 0 and np.ndim(b_deg) == 0:
        return float(out)
    return out


def compute_curve_metrics(
    curve: np.ndarray,
    lat: float | np.ndarray,
    min_valid_bins: int = 9,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Compute (dust_level, dust_seasonality, dust_peak_phase_deg, n_valid_bins) along axis 0 (12 bins)."""
    c = np.asarray(curve, dtype=np.float64)
    if c.shape[0] != 12:
        raise ValueError(f"Expected 12 Ls bins on axis 0, got shape {c.shape}")

    finite = np.isfinite(c)
    n_valid = np.sum(finite, axis=0)
    ok = n_valid >= min_valid_bins

    flat_c = c.reshape(12, -1)
    flat_ok = ok.ravel()
    m = flat_c.shape[1]

    level = np.full(m, np.nan, dtype=np.float64)
    seasonality = np.full(m, np.nan, dtype=np.float64)
    peak_ls = np.full(m, np.nan, dtype=np.float64)

    if np.any(flat_ok):
        sub = flat_c[:, flat_ok]
        mean_v = np.nanmean(sub, axis=0)
        min_v = np.nanmin(sub, axis=0)
        max_v = np.nanmax(sub, axis=0)
        sub_zero = np.where(np.isfinite(sub), sub, -np.inf)
        peak_bin = np.argmax(sub_zero, axis=0)

        level[flat_ok] = mean_v
        seasonality[flat_ok] = (max_v - min_v) / (mean_v + SEASONALITY_EPS)
        peak_ls[flat_ok] = 30.0 * peak_bin.astype(np.float64) + 15.0

    spatial_shape = c.shape[1:]
    level_out = level.reshape(spatial_shape)
    season_out = seasonality.reshape(spatial_shape)
    peak_ls_out = peak_ls.reshape(spatial_shape)
    lat_arr = np.broadcast_to(np.asarray(lat, dtype=np.float64), spatial_shape)

    phase_out = np.full(spatial_shape, np.nan, dtype=np.float64)
    if np.any(ok):
        phase_out[ok] = local_phase(peak_ls_out[ok], lat_arr[ok])

    if c.ndim == 1:
        return (
            np.asarray(float(level_out)),
            np.asarray(float(season_out)),
            np.asarray(float(phase_out)),
            np.asarray(int(n_valid)),
        )
    return level_out, season_out, phase_out, n_valid


def S_dust(
    r_level_e: float | np.ndarray,
    r_season_e: float | np.ndarray,
    phase_e_deg: float | np.ndarray,
    r_level_t: float,
    r_season_t: float,
    phase_t_deg: float,
) -> float | np.ndarray:
    """RBF dust similarity across within-planet level rank, seasonality rank, and local phase."""
    rl_e = np.asarray(r_level_e, dtype=np.float64)
    rs_e = np.asarray(r_season_e, dtype=np.float64)
    ph_e = np.asarray(phase_e_deg, dtype=np.float64)

    scalar_input = (rl_e.ndim == 0 and rs_e.ndim == 0 and ph_e.ndim == 0)
    if not (
        np.isfinite(r_level_t)
        and np.isfinite(r_season_t)
        and np.isfinite(phase_t_deg)
    ):
        nan_out = np.full(np.broadcast_shapes(rl_e.shape, rs_e.shape, ph_e.shape), np.nan, dtype=np.float64)
        return float("nan") if scalar_input else nan_out

    valid = np.isfinite(rl_e) & np.isfinite(rs_e) & np.isfinite(ph_e)
    shape = np.broadcast_shapes(rl_e.shape, rs_e.shape, ph_e.shape)
    out = np.full(shape, np.nan, dtype=np.float64)
    if np.any(valid):
        rl_b, rs_b, ph_b = np.broadcast_arrays(rl_e, rs_e, ph_e)
        d_level = np.abs(rl_b[valid] - float(r_level_t)) / DUST_RANK_SIGMA
        d_season = np.abs(rs_b[valid] - float(r_season_t)) / DUST_RANK_SIGMA
        d_phase = circular_diff(ph_b[valid], float(phase_t_deg)) / DUST_PHASE_SIGMA_DEG
        out[valid] = np.exp(-(d_level ** 2 + d_season ** 2 + d_phase ** 2) / 6.0)

    if scalar_input:
        return float(out)
    return out


score_dust = S_dust


def _rank_pct(values: np.ndarray) -> np.ndarray:
    arr = np.asarray(values, dtype=np.float64)
    out = np.full(arr.shape, np.nan, dtype=np.float64)
    finite = np.isfinite(arr)
    n = int(np.sum(finite))
    if n > 0:
        out[finite] = rankdata(arr[finite], method="average") / float(n)
    return out


def _searchsorted_rank(sorted_ref: np.ndarray, val: float) -> float:
    n = sorted_ref.size
    if n == 0 or not np.isfinite(val):
        return float("nan")
    left = int(np.searchsorted(sorted_ref, val, side="left"))
    right = int(np.searchsorted(sorted_ref, val, side="right"))
    eq = right - left
    if eq > 0:
        return float((left + 0.5 * (eq + 1)) / float(n))
    return float((left + 1) / float(n + 1))


def _normalize_lon_180(lon: np.ndarray) -> np.ndarray:
    return ((np.asarray(lon, dtype=np.float64) + 180.0) % 360.0) - 180.0


def _sample_grid_nearest(
    grid_lat: np.ndarray,
    grid_lon: np.ndarray,
    field: np.ndarray,
    pts_lat: np.ndarray,
    pts_lon: np.ndarray,
) -> np.ndarray:
    """Sample nearest grid cell for (pts_lat, pts_lon) handling arbitrary lat/lon ordering."""
    glat = np.asarray(grid_lat, dtype=np.float64)
    glon = _normalize_lon_180(grid_lon)

    lat_idx = np.argmin(np.abs(pts_lat[:, None] - glat[None, :]), axis=1)
    # Circular longitude distance on [-180, 180)
    plon = _normalize_lon_180(pts_lon)
    dlon = np.abs(plon[:, None] - glon[None, :])
    dlon = np.minimum(dlon, 360.0 - dlon)
    lon_idx = np.argmin(dlon, axis=1)
    return field[lat_idx, lon_idx]


def _inspect_montabone_vars(ds) -> dict[str, object]:
    """Print NetCDF3 dataset structure and identify lat, lon, Ls, and 610 Pa CDOD variables."""
    logger.info("Montabone NetCDF3 dataset summary:\n%s", ds)
    for name in list(ds.coords) + [v for v in ds.data_vars if v not in ds.coords]:
        var = ds[name]
        logger.info("  var=%s dims=%s shape=%s attrs=%s", name, var.dims, var.shape, dict(var.attrs))

    all_names = list(ds.coords) + list(ds.data_vars)
    lat_cands = [n for n in all_names if n.lower() in ("lat", "latitude")]
    lon_cands = [n for n in all_names if n.lower() in ("lon", "longitude")]
    if len(lat_cands) != 1 or len(lon_cands) != 1:
        raise RuntimeError(
            f"Ambiguous lat/lon coordinates in Montabone dataset: lat={lat_cands}, lon={lon_cands}. "
            f"Available={all_names}"
        )
    lat_name, lon_name = lat_cands[0], lon_cands[0]

    # Identify Ls 1D variable/coord
    ls_cands: list[str] = []
    for n in all_names:
        v = ds[n]
        if v.ndim != 1:
            continue
        lname = str(v.attrs.get("long_name", "")).lower()
        if n.lower() in ("ls", "l_s", "solar_longitude") or "solar longitude" in lname:
            ls_cands.append(n)
    if len(ls_cands) != 1:
        raise RuntimeError(
            f"Ambiguous Mars solar longitude (Ls) variable in Montabone dataset: {ls_cands}. "
            f"Available={all_names}"
        )
    ls_name = ls_cands[0]
    time_dim = ds[ls_name].dims[0]

    # Identify 3D (time, lat, lon) 610 Pa CDOD variable strictly without guessing
    ignore_tokens = ("err", "unc", "std", "rms", "flag", "count", "mask", "stat", "weight")
    vars_3d = [
        n
        for n in ds.data_vars
        if ds[n].ndim == 3 and set(ds[n].dims) == {time_dim, ds[lat_name].dims[0], ds[lon_name].dims[0]}
    ]
    cands_610: list[str] = []
    for n in vars_3d:
        v = ds[n]
        meta_txt = " ".join(
            [
                n,
                str(v.attrs.get("long_name", "")),
                str(v.attrs.get("description", "")),
                str(v.attrs.get("title", "")),
            ]
        ).lower()
        if any(tok in meta_txt for tok in ignore_tokens):
            continue
        if "610" in meta_txt:
            cands_610.append(n)

    if len(cands_610) != 1:
        var_details = {n: dict(ds[n].attrs) for n in ds.data_vars}
        raise RuntimeError(
            f"Expected exactly 1 non-error 610 Pa CDOD variable in Montabone NetCDF, found {cands_610}. "
            f"3D vars={vars_3d}, all data_vars={var_details}"
        )

    cdod_name = cands_610[0]
    info = {
        "lat_var": lat_name,
        "lon_var": lon_name,
        "ls_var": ls_name,
        "time_dim": time_dim,
        "cdod_610_var": cdod_name,
        "cdod_attrs": {str(k): str(v) for k, v in ds[cdod_name].attrs.items()},
        "all_3d_vars": vars_3d,
    }
    logger.info("[META] Selected Mars Montabone variable: %s (%s)", cdod_name, info["cdod_attrs"])
    return info


def _split_martian_years(ls_vals: np.ndarray, fname: str) -> list[tuple[int, np.ndarray]]:
    """Return list of (MY_int, index_array) from filename or Ls wrap detection."""
    m = re.search(r"MY(\d+)", fname, flags=re.IGNORECASE)
    if m:
        return [(int(m.group(1)), np.arange(ls_vals.size, dtype=np.int64))]

    # Multi-year combined file: split whenever Ls wraps backwards across 360 -> 0
    wraps = np.flatnonzero(np.diff(ls_vals) < -180.0) + 1
    boundaries = [0, *wraps.tolist(), ls_vals.size]
    segments: list[tuple[int, np.ndarray]] = []
    for k in range(len(boundaries) - 1):
        idx = np.arange(boundaries[k], boundaries[k + 1], dtype=np.int64)
        if idx.size > 0:
            segments.append((24 + k, idx))
    return segments


def build_mars_dust_climatology(
    mars_dust_dir: Path,
) -> dict[str, object]:
    """Compute MY24-MY36 median 12-bin CDOD climatology and storm-year boost."""
    import xarray as xr  # lazy import so lightweight syntax checks don't fail if unused

    nc_files = sorted(mars_dust_dir.rglob("*.nc"))
    if not nc_files:
        raise FileNotFoundError(f"No .nc files found in {mars_dust_dir}")

    logger.info("Found %d Montabone NetCDF3 files in %s", len(nc_files), mars_dust_dir)
    var_info: dict[str, object] | None = None
    grid_lat: np.ndarray | None = None
    grid_lon: np.ndarray | None = None

    # Store per-MY (12, nlat, nlon) bin means
    my_curves: dict[int, np.ndarray] = {}

    for nc_path in nc_files:
        with xr.open_dataset(nc_path, engine="scipy") as ds:
            if var_info is None:
                var_info = _inspect_montabone_vars(ds)
                grid_lat = np.asarray(ds[str(var_info["lat_var"])].values, dtype=np.float64)
                grid_lon = np.asarray(ds[str(var_info["lon_var"])].values, dtype=np.float64)

            lat_name = str(var_info["lat_var"])
            lon_name = str(var_info["lon_var"])
            time_dim = str(var_info["time_dim"])
            ls_name = str(var_info["ls_var"])
            cdod_name = str(var_info["cdod_610_var"])

            ls_arr = np.asarray(ds[ls_name].values, dtype=np.float64)
            da = ds[cdod_name].transpose(
                time_dim, ds[lat_name].dims[0], ds[lon_name].dims[0]
            )
            data = np.asarray(da.values, dtype=np.float64)

        segments = _split_martian_years(ls_arr, nc_path.name)
        for my_num, idx_slice in segments:
            sub_ls = ls_arr[idx_slice]
            sub_data = data[idx_slice]
            bins = np.floor((sub_ls % 360.0) / 30.0).astype(np.int64) % 12
            curve_my = np.full((12, sub_data.shape[1], sub_data.shape[2]), np.nan, dtype=np.float64)
            for b in range(12):
                mask = bins == b
                if np.any(mask):
                    curve_my[b] = np.nanmean(sub_data[mask], axis=0)
            my_curves[my_num] = curve_my
            logger.info(
                "Loaded MY%d from %s: %d timesteps, raw range=[%.4f, %.4f]",
                my_num,
                nc_path.name,
                len(idx_slice),
                float(np.nanmin(sub_data)),
                float(np.nanmax(sub_data)),
            )

    assert var_info is not None and grid_lat is not None and grid_lon is not None
    years_sorted = sorted(my_curves.keys())
    stack = np.stack([my_curves[y] for y in years_sorted], axis=0)  # (nyears, 12, nlat, nlon)
    median_curve = np.nanmedian(stack, axis=0)  # (12, nlat, nlon)

    lat_2d = np.broadcast_to(grid_lat[:, None], median_curve.shape[1:])
    dust_level, dust_seasonality, dust_peak_phase_deg, n_valid = compute_curve_metrics(
        median_curve, lat_2d, min_valid_bins=MIN_VALID_BINS_MARS
    )

    # Global area-weighted mean CDOD per Martian Year (Check #3)
    cos_w = np.maximum(0.0, np.cos(np.radians(grid_lat)))[:, None]
    per_year_global_mean: dict[int, float] = {}
    yearly_cell_levels: dict[int, np.ndarray] = {}
    for y_idx, my_num in enumerate(years_sorted):
        c_my = stack[y_idx]
        cell_mean = np.nanmean(c_my, axis=0)
        yearly_cell_levels[my_num] = cell_mean
        valid_cell = np.isfinite(cell_mean)
        weights_2d = np.broadcast_to(cos_w, cell_mean.shape)
        if np.any(valid_cell):
            per_year_global_mean[my_num] = float(
                np.sum(cell_mean[valid_cell] * weights_2d[valid_cell])
                / np.sum(weights_2d[valid_cell])
            )
        else:
            per_year_global_mean[my_num] = float("nan")

    # Storm year boost: mean(MY25, MY28, MY34) / median(all years)
    present_storms = [y for y in STORM_YEARS if y in yearly_cell_levels]
    all_year_levels = np.stack([yearly_cell_levels[y] for y in years_sorted], axis=0)
    median_year_level = np.nanmedian(all_year_levels, axis=0)
    if present_storms:
        storm_mean = np.nanmean(
            np.stack([yearly_cell_levels[y] for y in present_storms], axis=0), axis=0
        )
        storm_year_boost = storm_mean / (median_year_level + SEASONALITY_EPS)
    else:
        storm_year_boost = np.full(median_year_level.shape, np.nan, dtype=np.float64)

    # Global-mean seasonal curve across the whole planet (Check #4)
    curve_weights = np.broadcast_to(cos_w[None, :, :], median_curve.shape)
    global_curve = np.full(12, np.nan, dtype=np.float64)
    for b in range(12):
        sub_b = median_curve[b]
        fin = np.isfinite(sub_b)
        if np.any(fin):
            global_curve[b] = float(
                np.sum(sub_b[fin] * curve_weights[b][fin]) / np.sum(curve_weights[b][fin])
            )

    return {
        "var_info": var_info,
        "years": years_sorted,
        "grid_lat": grid_lat,
        "grid_lon": grid_lon,
        "dust_level": dust_level,
        "dust_seasonality": dust_seasonality,
        "dust_peak_phase_deg": dust_peak_phase_deg,
        "n_valid_bins": n_valid,
        "storm_year_boost": storm_year_boost,
        "per_year_global_mean": per_year_global_mean,
        "global_curve": global_curve,
    }


def _parse_modis_date(hdf_path: Path) -> tuple[int, int, float]:
    """Extract (year, month, mid_month_doy) from MOD08_M3 filename .AYYYYDDD."""
    m = re.search(r"\.A(\d{4})(\d{3})\.", hdf_path.name)
    if not m:
        raise ValueError(f"Could not parse .AYYYYDDD. timestamp from MOD08 filename: {hdf_path.name}")
    year = int(m.group(1))
    start_doy = int(m.group(2))
    dt = date(year, 1, 1) + timedelta(days=start_doy - 1)
    days_in_month = calendar.monthrange(year, dt.month)[1]
    mid_doy = float(start_doy) + 0.5 * float(days_in_month - 1)
    return year, dt.month, mid_doy


def build_earth_aod_climatology(aod_dir: Path) -> dict[str, object]:
    """Compute 2019-2023 MOD08_M3 Deep Blue 550 nm AOD climatology per 1x1 deg cell."""
    from pyhdf.SD import SD, SDC  # lazy import: synthetic tests don't require pyhdf

    hdf_files = sorted(p for p in aod_dir.glob("*.hdf") if p.is_file() and p.stat().st_size > 0)
    if not hdf_files:
        raise FileNotFoundError(f"No MOD08_M3 .hdf files found in {aod_dir}")

    logger.info("Found %d MOD08_M3 .hdf files in %s", len(hdf_files), aod_dir)

    sds_meta: dict[str, object] = {}
    grid_lat: np.ndarray | None = None
    grid_lon: np.ndarray | None = None

    # Inspect first granule strictly before batch processing
    first_sd = SD(str(hdf_files[0]), SDC.READ)
    try:
        all_sds = sorted(first_sd.datasets().keys())
        deep_blue_550 = [
            name for name in all_sds if "deep_blue" in name.lower() and "550" in name
        ]
        logger.info("MOD08_M3 SDS names matching Deep_Blue & 550: %s", deep_blue_550)
        if EXPECTED_AOD_SDS not in all_sds:
            raise RuntimeError(
                f"Required SDS {EXPECTED_AOD_SDS!r} not found in {hdf_files[0].name}. "
                f"Deep_Blue+550 candidates={deep_blue_550}, total SDS={len(all_sds)}"
            )

        sds_obj = first_sd.select(EXPECTED_AOD_SDS)
        attrs = dict(sds_obj.attributes())
        logger.info("[META] %s attributes: %s", EXPECTED_AOD_SDS, attrs)
        fill_val = attrs.get("_FillValue")
        scale_factor = float(attrs["scale_factor"])
        add_offset = float(attrs["add_offset"])
        valid_range = attrs.get("valid_range")
        sds_meta = {
            "sds_name": EXPECTED_AOD_SDS,
            "deep_blue_550_sds": deep_blue_550,
            "_FillValue": float(fill_val) if fill_val is not None else None,
            "scale_factor": scale_factor,
            "add_offset": add_offset,
            "valid_range": [float(v) for v in valid_range] if valid_range is not None else None,
        }

        if "YDim" in all_sds and "XDim" in all_sds:
            grid_lat = np.asarray(first_sd.select("YDim").get(), dtype=np.float64)
            grid_lon = np.asarray(first_sd.select("XDim").get(), dtype=np.float64)
        else:
            grid_lat = 89.5 - np.arange(180, dtype=np.float64)
            grid_lon = -179.5 + np.arange(360, dtype=np.float64)
        logger.info(
            "[META] MOD08_M3 grid lat[0]=%.2f lat[-1]=%.2f (len=%d), lon[0]=%.2f lon[-1]=%.2f (len=%d)",
            float(grid_lat[0]),
            float(grid_lat[-1]),
            len(grid_lat),
            float(grid_lon[0]),
            float(grid_lon[-1]),
            len(grid_lon),
        )
    finally:
        first_sd.end()

    assert grid_lat is not None and grid_lon is not None
    scale_factor = float(sds_meta["scale_factor"])
    add_offset = float(sds_meta["add_offset"])
    fill_val = sds_meta["_FillValue"]
    valid_range = sds_meta["valid_range"]

    # Collect arrays per (Ls_bin -> list of grids across the 5 years)
    bin_samples: dict[int, list[np.ndarray]] = {b: [] for b in range(12)}
    sahara_summer_means: list[float] = []

    for hdf_path in hdf_files:
        year, month, mid_doy = _parse_modis_date(hdf_path)
        ls_deg = float(Ls_E(mid_doy))
        ls_bin = int(math.floor(ls_deg / 30.0)) % 12

        sd = SD(str(hdf_path), SDC.READ)
        try:
            raw = np.asarray(sd.select(EXPECTED_AOD_SDS).get(), dtype=np.float64)
        finally:
            sd.end()

        if raw.shape != (180, 360):
            raise ValueError(f"Unexpected MOD08 shape {raw.shape} in {hdf_path.name}")

        valid = np.isfinite(raw)
        if fill_val is not None:
            valid &= raw != float(fill_val)
        if valid_range is not None and len(valid_range) == 2:
            valid &= (raw >= float(valid_range[0])) & (raw <= float(valid_range[1]))

        aod = np.full(raw.shape, np.nan, dtype=np.float64)
        aod[valid] = (raw[valid] - add_offset) * scale_factor

        if month in (6, 7, 8):
            lat_mask = (grid_lat >= 15.0) & (grid_lat <= 25.0)
            lon_mask = (grid_lon >= -5.0) & (grid_lon <= 15.0)
            sah_sub = aod[np.ix_(lat_mask, lon_mask)]
            if np.any(np.isfinite(sah_sub)):
                sahara_summer_means.append(float(np.nanmean(sah_sub)))

        bin_samples[ls_bin].append(aod)

    sahara_check = float(np.mean(sahara_summer_means)) if sahara_summer_means else float("nan")
    logger.info(
        "[META] Earth MOD08_M3 summer Sahara mean AOD check: %.4f (expected ~0.3-0.8)",
        sahara_check,
    )

    median_curve = np.full((12, 180, 360), np.nan, dtype=np.float64)
    for b in range(12):
        if bin_samples[b]:
            median_curve[b] = np.nanmedian(np.stack(bin_samples[b], axis=0), axis=0)

    lat_2d = np.broadcast_to(grid_lat[:, None], (180, 360))
    dust_level, dust_seasonality, dust_peak_phase_deg, n_valid = compute_curve_metrics(
        median_curve, lat_2d, min_valid_bins=MIN_VALID_BINS_EARTH
    )

    return {
        "sds_meta": sds_meta,
        "n_files": len(hdf_files),
        "sahara_summer_aod": sahara_check,
        "grid_lat": grid_lat,
        "grid_lon": grid_lon,
        "dust_level": dust_level,
        "dust_seasonality": dust_seasonality,
        "dust_peak_phase_deg": dust_peak_phase_deg,
        "n_valid_bins": n_valid,
    }


def _render_dust_maps(
    mars_clim: dict[str, object],
    earth_clim: dict[str, object],
    out_dir: Path,
) -> list[str]:
    """Write map_dust_level_{earth,mars}.png and map_dust_peak_phase_{earth,mars}.png."""
    written: list[str] = []
    configs = [
        (
            "Earth MOD08_M3 Annual Dust Level (AOD 550 nm)",
            earth_clim["grid_lat"],
            earth_clim["grid_lon"],
            earth_clim["dust_level"],
            "YlOrRd",
            None,
            None,
            "AOD 550 nm",
            "map_dust_level_earth.png",
        ),
        (
            "Mars Montabone CDOD Level (610 Pa, MY24-MY36 median)",
            mars_clim["grid_lat"],
            mars_clim["grid_lon"],
            mars_clim["dust_level"],
            "YlOrRd",
            None,
            None,
            "CDOD 610 Pa",
            "map_dust_level_mars.png",
        ),
        (
            "Earth MOD08_M3 Local Dust Peak Phase (deg)",
            earth_clim["grid_lat"],
            earth_clim["grid_lon"],
            earth_clim["dust_peak_phase_deg"],
            "twilight",
            0.0,
            360.0,
            "Local Ls (deg)",
            "map_dust_peak_phase_earth.png",
        ),
        (
            "Mars Montabone Local Dust Peak Phase (deg)",
            mars_clim["grid_lat"],
            mars_clim["grid_lon"],
            mars_clim["dust_peak_phase_deg"],
            "twilight",
            0.0,
            360.0,
            "Local Ls (deg)",
            "map_dust_peak_phase_mars.png",
        ),
    ]

    for title, glat, glon, grid, cmap, vmin, vmax, cbar_label, fname in configs:
        lat_a = np.asarray(glat, dtype=np.float64)
        lon_a = _normalize_lon_180(np.asarray(glon, dtype=np.float64))
        arr = np.asarray(grid, dtype=np.float64)
        # Ensure north-up and ascending lon for plotting with imshow
        if lat_a[0] < lat_a[-1]:
            lat_a = lat_a[::-1]
            arr = arr[::-1, :]
        lon_order = np.argsort(lon_a)
        lon_a = lon_a[lon_order]
        arr = arr[:, lon_order]

        fig, ax = plt.subplots(figsize=(10, 4.8), dpi=150)
        cmap_obj = plt.get_cmap(cmap).copy()
        cmap_obj.set_bad(color="#e5e7eb")
        masked = np.ma.masked_invalid(arr)
        im = ax.imshow(
            masked,
            extent=[-180.0, 180.0, -90.0, 90.0],
            origin="upper",
            cmap=cmap_obj,
            vmin=vmin,
            vmax=vmax,
            aspect="auto",
        )
        ax.set_title(title)
        ax.set_xlabel("Longitude (deg)")
        ax.set_ylabel("Latitude (deg)")
        cbar = fig.colorbar(im, ax=ax, shrink=0.85)
        cbar.set_label(cbar_label)
        fig.tight_layout()
        out_path = out_dir / fname
        fig.savefig(out_path)
        plt.close(fig)
        written.append(fname)
    return written


def _safe_round(v: object, digits: int = 4) -> float | None:
    try:
        fv = float(v)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    if not math.isfinite(fv):
        return None
    return round(fv, digits)


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


def run_dust(
    project_dir: Path,
    t3_dir: Path,
    t4_dir: Path,
    t5_dir: Path,
    out_dir: Path,
) -> dict[str, object]:
    """Build T13 dust tables (Mars, Earth, targets), maps, and verification checks."""
    t0 = time.perf_counter()
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = project_dir / "data" / "raw"

    # 1. Climatologies
    mars_clim = build_mars_dust_climatology(raw_dir / MARS_DUST_REL)
    earth_clim = build_earth_aod_climatology(raw_dir / EARTH_AOD_REL)

    # 2. Sample T3 Mars patches + compute within-Mars ranks
    mars_t3 = pd.read_parquet(t3_dir / "features_mars.parquet", columns=["lat", "lon"])
    m_lat = mars_t3["lat"].to_numpy(dtype=np.float64)
    m_lon = mars_t3["lon"].to_numpy(dtype=np.float64)
    m_level = _sample_grid_nearest(
        mars_clim["grid_lat"], mars_clim["grid_lon"], mars_clim["dust_level"], m_lat, m_lon
    )
    m_season = _sample_grid_nearest(
        mars_clim["grid_lat"], mars_clim["grid_lon"], mars_clim["dust_seasonality"], m_lat, m_lon
    )
    m_phase = _sample_grid_nearest(
        mars_clim["grid_lat"], mars_clim["grid_lon"], mars_clim["dust_peak_phase_deg"], m_lat, m_lon
    )
    m_boost = _sample_grid_nearest(
        mars_clim["grid_lat"], mars_clim["grid_lon"], mars_clim["storm_year_boost"], m_lat, m_lon
    )
    m_level_rank = _rank_pct(m_level)
    m_season_rank = _rank_pct(m_season)

    dust_mars_df = pd.DataFrame(
        {
            "lat": m_lat,
            "lon": m_lon,
            "dust_level": m_level.astype(np.float32),
            "dust_seasonality": m_season.astype(np.float32),
            "dust_peak_phase_deg": m_phase.astype(np.float32),
            "storm_year_boost": m_boost.astype(np.float32),
            "dust_level_rank": m_level_rank.astype(np.float32),
            "dust_seasonality_rank": m_season_rank.astype(np.float32),
        }
    )
    dust_mars_df.to_parquet(out_dir / "dust_mars.parquet", index=False)
    logger.info("Wrote dust_mars.parquet (%d rows)", len(dust_mars_df))

    # 3. Sample T5 Earth patches + compute within-Earth ranks
    earth_t5 = pd.read_parquet(t5_dir / "features_earth.parquet", columns=["lat", "lon"])
    e_lat = earth_t5["lat"].to_numpy(dtype=np.float64)
    e_lon = earth_t5["lon"].to_numpy(dtype=np.float64)
    e_level = _sample_grid_nearest(
        earth_clim["grid_lat"], earth_clim["grid_lon"], earth_clim["dust_level"], e_lat, e_lon
    )
    e_season = _sample_grid_nearest(
        earth_clim["grid_lat"], earth_clim["grid_lon"], earth_clim["dust_seasonality"], e_lat, e_lon
    )
    e_phase = _sample_grid_nearest(
        earth_clim["grid_lat"], earth_clim["grid_lon"], earth_clim["dust_peak_phase_deg"], e_lat, e_lon
    )
    e_bins = _sample_grid_nearest(
        earth_clim["grid_lat"], earth_clim["grid_lon"], earth_clim["n_valid_bins"], e_lat, e_lon
    )
    e_level_rank = _rank_pct(e_level)
    e_season_rank = _rank_pct(e_season)

    dust_earth_df = pd.DataFrame(
        {
            "lat": e_lat,
            "lon": e_lon,
            "dust_level": e_level.astype(np.float32),
            "dust_seasonality": e_season.astype(np.float32),
            "dust_peak_phase_deg": e_phase.astype(np.float32),
            "n_valid_bins": e_bins.astype(np.int16),
            "dust_level_rank": e_level_rank.astype(np.float32),
            "dust_seasonality_rank": e_season_rank.astype(np.float32),
        }
    )
    dust_earth_df.to_parquet(out_dir / "dust_earth.parquet", index=False)
    logger.info(
        "Wrote dust_earth.parquet (%d rows, valid dust=%d)",
        len(dust_earth_df),
        int(np.sum(np.isfinite(e_level))),
    )

    # 4. Sample T4 targets (Mars via searchsorted against T3 Mars distribution; Moon null)
    targets_df = pd.read_parquet(t4_dir / "targets.parquet", columns=["target_id", "body", "lat", "lon"])
    m_level_sorted = np.sort(m_level[np.isfinite(m_level)])
    m_season_sorted = np.sort(m_season[np.isfinite(m_season)])

    target_rows: list[dict[str, object]] = []
    for _, row in targets_df.iterrows():
        tid = str(row["target_id"])
        body = str(row["body"]).strip().capitalize()
        if body != "Mars":
            target_rows.append(
                {
                    "target_id": tid,
                    "dust_level": np.float32(np.nan),
                    "dust_seasonality": np.float32(np.nan),
                    "dust_peak_phase_deg": np.float32(np.nan),
                    "storm_year_boost": np.float32(np.nan),
                    "dust_level_rank": np.float32(np.nan),
                    "dust_seasonality_rank": np.float32(np.nan),
                }
            )
            continue

        tl = float(row["lat"])
        tg = float(row["lon"])
        lv = float(_sample_grid_nearest(mars_clim["grid_lat"], mars_clim["grid_lon"], mars_clim["dust_level"], np.array([tl]), np.array([tg]))[0])
        ss = float(_sample_grid_nearest(mars_clim["grid_lat"], mars_clim["grid_lon"], mars_clim["dust_seasonality"], np.array([tl]), np.array([tg]))[0])
        ph = float(_sample_grid_nearest(mars_clim["grid_lat"], mars_clim["grid_lon"], mars_clim["dust_peak_phase_deg"], np.array([tl]), np.array([tg]))[0])
        bst = float(_sample_grid_nearest(mars_clim["grid_lat"], mars_clim["grid_lon"], mars_clim["storm_year_boost"], np.array([tl]), np.array([tg]))[0])
        target_rows.append(
            {
                "target_id": tid,
                "dust_level": np.float32(lv),
                "dust_seasonality": np.float32(ss),
                "dust_peak_phase_deg": np.float32(ph),
                "storm_year_boost": np.float32(bst),
                "dust_level_rank": np.float32(_searchsorted_rank(m_level_sorted, lv)),
                "dust_seasonality_rank": np.float32(_searchsorted_rank(m_season_sorted, ss)),
            }
        )

    dust_targets_df = pd.DataFrame(target_rows)
    dust_targets_df["target_id"] = dust_targets_df["target_id"].astype("string")
    dust_targets_df.to_parquet(out_dir / "dust_targets.parquet", index=False)
    logger.info("Wrote dust_targets.parquet (%d rows)", len(dust_targets_df))

    # 5. Diagnostic maps
    map_files = _render_dust_maps(mars_clim, earth_clim, out_dir)

    # 6. T13 Checks (§3.5)
    e_level_sorted = np.sort(e_level[np.isfinite(e_level)])

    def _earth_point_rank(pt_lat: float, pt_lon: float) -> tuple[float, float]:
        val = float(
            _sample_grid_nearest(
                earth_clim["grid_lat"],
                earth_clim["grid_lon"],
                earth_clim["dust_level"],
                np.array([pt_lat]),
                np.array([pt_lon]),
            )[0]
        )
        return val, _searchsorted_rank(e_level_sorted, val)

    def _mars_point_rank(pt_lat: float, pt_lon: float) -> tuple[float, float]:
        val = float(
            _sample_grid_nearest(
                mars_clim["grid_lat"],
                mars_clim["grid_lon"],
                mars_clim["dust_level"],
                np.array([pt_lat]),
                np.array([pt_lon]),
            )[0]
        )
        return val, _searchsorted_rank(m_level_sorted, val)

    per_year_means = mars_clim["per_year_global_mean"]
    top3_years = [
        y for y, _ in sorted(per_year_means.items(), key=lambda kv: -kv[1])[:3]
    ]

    gcurve = mars_clim["global_curve"]
    peak_bin = int(np.nanargmax(gcurve))
    peak_ls_center = 30.0 * peak_bin + 15.0

    bod_val, bod_rank = _earth_point_rank(17.0, 18.0)
    tak_val, tak_rank = _earth_point_rank(39.0, 83.0)
    ata_val, ata_rank = _earth_point_rank(-24.5, -69.3)
    hel_val, hel_rank = _mars_point_rank(-42.0, 70.0)
    tha_val, tha_rank = _mars_point_rank(0.0, -110.0)

    checks = [
        {
            "id": 1,
            "name": "mars_variables_identified",
            "kind": "hard",
            "passed": True,
            "observed": mars_clim["var_info"],
            "expected": "Unambiguous Montabone 610 Pa CDOD and Ls variable names printed",
        },
        {
            "id": 2,
            "name": "earth_sds_and_scaling",
            "kind": "hard",
            "passed": True,
            "observed": {
                **earth_clim["sds_meta"],
                "sahara_summer_aod": _safe_round(earth_clim["sahara_summer_aod"], 4),
            },
            "expected": "MOD08_M3 Deep_Blue 550 SDS found with printed scale/offset",
        },
        {
            "id": 3,
            "name": "mars_storm_years_top3",
            "kind": "soft",
            "passed": set(top3_years) == set(STORM_YEARS),
            "observed": {
                "top3_years": top3_years,
                "per_year_global_mean": {
                    f"MY{k}": _safe_round(v, 5) for k, v in sorted(per_year_means.items())
                },
            },
            "expected": "MY25, MY28, and MY34 are the 3 highest years",
        },
        {
            "id": 4,
            "name": "mars_global_curve_perihelion_peak",
            "kind": "hard",
            "passed": bool(180.0 <= peak_ls_center <= 330.0),
            "observed": {
                "peak_bin": peak_bin,
                "peak_ls_center_deg": peak_ls_center,
                "global_curve": [_safe_round(x, 5) for x in gcurve],
            },
            "expected": "Peak bin center within Ls 180-330 deg",
        },
        {
            "id": 5,
            "name": "earth_known_dust_sources",
            "kind": "hard",
            "passed": bool(
                np.isfinite(bod_rank)
                and np.isfinite(tak_rank)
                and bod_rank > 0.9
                and tak_rank > 0.9
            ),
            "observed": {
                "bodele_17_18": {"aod": _safe_round(bod_val, 4), "rank": _safe_round(bod_rank, 4)},
                "taklimakan_39_83": {"aod": _safe_round(tak_val, 4), "rank": _safe_round(tak_rank, 4)},
            },
            "expected": "rank > 0.9 at both Bodele and Taklimakan",
        },
        {
            "id": 6,
            "name": "earth_atacama_clean_air",
            "kind": "soft",
            "passed": bool(np.isfinite(ata_rank) and ata_rank < 0.5),
            "observed": {"aod": _safe_round(ata_val, 4), "rank": _safe_round(ata_rank, 4)},
            "expected": "rank < 0.5 in the Atacama",
        },
        {
            "id": 7,
            "name": "mars_hellas_gt_tharsis",
            "kind": "soft",
            "passed": bool(
                np.isfinite(hel_rank) and np.isfinite(tha_rank) and hel_rank > tha_rank
            ),
            "observed": {
                "hellas": {"cdod610": _safe_round(hel_val, 4), "rank": _safe_round(hel_rank, 4)},
                "tharsis": {"cdod610": _safe_round(tha_val, 4), "rank": _safe_round(tha_rank, 4)},
            },
            "expected": "Hellas (-42, 70) rank > Tharsis (0, -110) rank",
        },
        {
            "id": 8,
            "name": "dust_maps_written",
            "kind": "soft",
            "passed": len(map_files) == 4 and all((out_dir / f).exists() for f in map_files),
            "observed": map_files,
            "expected": "4 PNG maps written",
        },
    ]

    hard_checks = [c for c in checks if c["kind"] == "hard"]
    soft_checks = [c for c in checks if c["kind"] == "soft"]
    hard_passed = sum(1 for c in hard_checks if c["passed"])
    soft_passed = sum(1 for c in soft_checks if c["passed"])

    report = {
        "task": "T13",
        "slurm_job_id": os.environ.get("SLURM_JOB_ID"),
        "commit": _git_short_sha(Path(__file__).resolve().parents[1]),
        "runtime_s": round(time.perf_counter() - t0, 3),
        "hard_passed": hard_passed,
        "hard_total": len(hard_checks),
        "soft_passed": soft_passed,
        "soft_total": len(soft_checks),
        "checks": checks,
    }
    checks_path = out_dir / "t13_checks.json"
    with open(checks_path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, allow_nan=False)

    logger.info(
        "T13 checks: hard %d/%d, soft %d/%d -> %s",
        hard_passed,
        len(hard_checks),
        soft_passed,
        len(soft_checks),
        checks_path,
    )
    if hard_passed < len(hard_checks):
        failed_names = [c["name"] for c in hard_checks if not c["passed"]]
        raise RuntimeError(f"T13 hard checks failed: {failed_names}")
    return report


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build T13 dust and seasonal phase layers for Mars & Earth.")
    p.add_argument("--project-dir", type=Path, default=YUCA_PROJECT_DIR)
    p.add_argument("--t3-dir", type=Path, default=YUCA_PROJECT_DIR / "runs" / "2242278")
    p.add_argument("--t4-dir", type=Path, default=YUCA_PROJECT_DIR / "runs" / "2242423")
    p.add_argument("--t5-dir", type=Path, default=YUCA_PROJECT_DIR / "runs" / "2242438")
    p.add_argument("--out-dir", type=Path, required=True)
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="[%(levelname)s] %(name)s: %(message)s",
    )
    args = _parse_args(argv)
    run_dust(
        project_dir=args.project_dir,
        t3_dir=args.t3_dir,
        t4_dir=args.t4_dir,
        t5_dir=args.t5_dir,
        out_dir=args.out_dir,
    )


if __name__ == "__main__":
    main()
