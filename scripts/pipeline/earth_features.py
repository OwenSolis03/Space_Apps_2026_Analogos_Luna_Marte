"""Global Earth sweep over Copernicus GLO-90 DEM and environmental layers (T5).

This module manages the candidate grid preparation, vegetation pre-filtering,
Copernicus GLO-90 VRT creation, parallel morphometric feature extraction, and
integration with environmental/logistics layers for Earth planetary analog sites:
1. Copernicus GLO-90 Tile Index:
   - Evaluates coverage across 26,475 GeoTIFF tiles and constructs a unified global VRT.
2. Vegetation Pre-filtering (MODIS NDVI):
   - Discards heavily vegetated surfaces (NDVI max > 0.25) to isolate arid, barren,
     hyper-arid, volcanic, and polar terrain suitable as Moon/Mars analogs.
   - Preserves polar ice sheets and cold zones where NDVI is unmeasured (NaN) but valid
     LST land data exists.
3. Parallel AEQD Feature Extraction:
   - Extracts 32x32 km patches at 500 m/pixel via `pipeline.geo` and calculates the 7 canonical
     morphometric features via `pipeline.features`.
4. Multi-Layer Merge:
   - Merges elevation features with MODIS LST, aridity indices, logistics (roads, airports),
     and known analog station boundaries into `features_earth.parquet`.
"""

from __future__ import annotations

import argparse
import atexit
from datetime import datetime, timezone
import json
import math
import multiprocessing as mp
import os
from pathlib import Path
import re
import shutil
import subprocess
import time

os.environ.setdefault("GDAL_CACHEMAX", "256")
os.environ.setdefault("PROJ_IGNORE_CELESTIAL_BODY", "YES")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import rasterio
from rasterio.enums import Resampling

from .config import (
    EARTH_DERIVED_FILES,
    EARTH_RAW_FILES,
    FEATURE_NAMES,
    PATCH_RES_M,
    PATCH_SIZE_KM,
    YUCA_PROJECT_DIR,
)
from .earth_layers import (
    EARTH_ENV_COLUMNS,
    NUMERIC_ENV_COLUMNS,
    TEXT_ENV_COLUMNS,
    EarthLayers,
    KnownRegions,
    patch_window_stat,
)
from .features import compute_features
from .geo import extract_patch, get_antimeridian_skipped_count, reset_antimeridian_skipped_count
from .planet_features import apply_limit, generate_grid, plot_slope_map, select_stripe

TILE_RE = re.compile(
    r"(?:^|_)(?P<ns>[NS])(?P<lat>\d{2})_00_(?P<ew>[EW])(?P<lon>\d{3})(?:_00_DEM(?:\.tif)?|\.tif)?$"
)
VRT_NODATA: float = -9999.0
NDVI_PREFILTER_MAX: float = 0.25
HALF_PATCH_KM: float = PATCH_SIZE_KM / 2.0
EXPECTED_VRT_RES_DEG: float = 1.0 / 1200.0

CANDIDATE_COLUMNS: list[str] = ["lat", "lon", *EARTH_ENV_COLUMNS, "ndvi_missing"]
EARTH_FEATURE_COLUMNS: list[str] = ["lat", "lon", *FEATURE_NAMES, "valid_frac"]
EARTH_COLUMNS: list[str] = [
    "body",
    "lat",
    "lon",
    *FEATURE_NAMES,
    "valid_frac",
    *EARTH_ENV_COLUMNS,
    "ndvi_missing",
]

_EARTH_WORKER: dict[str, object] = {}


def parse_tile_cell(name: str) -> tuple[int, int]:
    """Extract integer cell bounds (lat_floor, lon_floor) from Copernicus tile filename."""
    base = Path(name).name
    m = TILE_RE.search(base)
    if m is None:
        raise ValueError(f"Invalid Copernicus tile name: {name!r}")
    lat_v = int(m.group("lat"))
    lon_v = int(m.group("lon"))
    if m.group("ns") == "S":
        lat_v = -lat_v
    if m.group("ew") == "W":
        lon_v = -lon_v
    if not (-90 <= lat_v <= 89 and -180 <= lon_v <= 179):
        raise ValueError(f"Tile cell out of valid geographic range ({lat_v}, {lon_v}) in {name!r}")
    return lat_v, lon_v


def load_tile_cells(copernicus_dir: Path) -> set[tuple[int, int]]:
    """Return set of available (lat_floor, lon_floor) 1x1 deg cells without opening GeoTIFF headers."""
    cells: set[tuple[int, int]] = set()
    with os.scandir(copernicus_dir) as it:
        for entry in it:
            if entry.is_file() and entry.name.lower().endswith(".tif"):
                cells.add(parse_tile_cell(entry.name))
    return cells


def has_tile(
    lat: np.ndarray | float,
    lon: np.ndarray | float,
    cells: set[tuple[int, int]],
) -> np.ndarray:
    """Return boolean mask for coordinates whose containing 1x1 deg cell is present in `cells`."""
    lat_arr = np.atleast_1d(np.asarray(lat, dtype=np.float64))
    lon_arr = np.atleast_1d(np.asarray(lon, dtype=np.float64))
    if lat_arr.shape != lon_arr.shape:
        raise ValueError("lat and lon arrays must have identical shape")
    valid = np.isfinite(lat_arr) & np.isfinite(lon_arr)
    lat_floor = np.floor(lat_arr).astype(np.int64)
    lon_floor = np.floor(lon_arr).astype(np.int64)
    out = np.array(
        [
            bool(v and ((int(la), int(lo)) in cells))
            for v, la, lo in zip(valid.tolist(), lat_floor.tolist(), lon_floor.tolist())
        ],
        dtype=bool,
    )
    return out


def build_vrt(copernicus_dir: Path, vrt_path: Path) -> Path:
    """Construct global Copernicus VRT atomically (-srcnodata 0 -vrtnodata -9999) if absent."""
    vrt_out = Path(vrt_path)
    if vrt_out.exists():
        print(f"[T5] VRT already exists, reusing: {vrt_out}", flush=True)
        return vrt_out

    gdalbuildvrt = shutil.which("gdalbuildvrt")
    if gdalbuildvrt is None:
        raise RuntimeError("gdalbuildvrt not found in environment")

    cop_dir = Path(copernicus_dir)
    if not cop_dir.is_dir():
        raise FileNotFoundError(f"Copernicus directory not found: {cop_dir}")

    tiles = sorted(
        str(p) for p in cop_dir.iterdir() if p.is_file() and p.suffix.lower() == ".tif"
    )
    if not tiles:
        raise FileNotFoundError(f"No .tif tiles found in {cop_dir}")

    vrt_out.parent.mkdir(parents=True, exist_ok=True)
    list_path = vrt_out.with_suffix(".list.txt")
    list_path.write_text("\n".join(tiles) + "\n", encoding="utf-8")

    tmp_vrt = vrt_out.with_suffix(".tmp.vrt")
    if tmp_vrt.exists():
        tmp_vrt.unlink()

    cmd = [
        gdalbuildvrt,
        "-overwrite",
        "-resolution",
        "highest",
        "-srcnodata",
        "0",
        "-vrtnodata",
        str(int(VRT_NODATA)),
        "-input_file_list",
        str(list_path),
        str(tmp_vrt),
    ]
    try:
        subprocess.run(cmd, check=True)
        os.replace(tmp_vrt, vrt_out)
    except Exception:
        if tmp_vrt.exists():
            tmp_vrt.unlink()
        raise

    with rasterio.open(vrt_out) as src:
        if src.crs is None or src.crs.to_epsg() != 4326:
            raise ValueError(f"Unexpected CRS in VRT {vrt_out}: {src.crs}")
        if src.nodata is None or not math.isclose(float(src.nodata), VRT_NODATA, rel_tol=0.0, abs_tol=1e-6):
            raise ValueError(f"Unexpected nodata value in VRT {vrt_out}: {src.nodata} != {VRT_NODATA}")
        if not (
            math.isclose(src.res[0], EXPECTED_VRT_RES_DEG, rel_tol=0.0, abs_tol=1e-9)
            and math.isclose(src.res[1], EXPECTED_VRT_RES_DEG, rel_tol=0.0, abs_tol=1e-9)
        ):
            raise ValueError(f"Unexpected resolution in VRT {vrt_out}: {src.res}")
        print(
            f"[VRT] {vrt_out}: {src.width}x{src.height}, bounds={src.bounds}, "
            f"res={src.res}, tiles={len(tiles):,}",
            flush=True,
        )

    return vrt_out


def _compute_prefilter_masks(
    lat: np.ndarray,
    lon: np.ndarray,
    cells: set[tuple[int, int]],
    layers: EarthLayers,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[str, int]]:
    """Apply vegetation pre-filter rules and compute diagnostic count statistics."""
    lat_arr = np.atleast_1d(np.asarray(lat, dtype=np.float64))
    lon_arr = np.atleast_1d(np.asarray(lon, dtype=np.float64))
    n = lat_arr.shape[0]

    tile_mask = has_tile(lat_arr, lon_arr, cells)
    no_tile_count = int(np.sum(~tile_mask))

    keep_mask = np.zeros(n, dtype=bool)
    ndvi_missing_mask = np.zeros(n, dtype=bool)
    no_land_mask = np.zeros(n, dtype=bool)
    vegetated_count = 0

    tile_idx = np.flatnonzero(tile_mask)
    if tile_idx.size > 0:
        ndvi_vals = layers.ndvi_prefilter(
            lat_arr[tile_idx], lon_arr[tile_idx], half_km=HALF_PATCH_KM
        )
        finite_ndvi = np.isfinite(ndvi_vals)
        keep_finite = finite_ndvi & (ndvi_vals <= NDVI_PREFILTER_MAX)
        veg_mask = finite_ndvi & (ndvi_vals > NDVI_PREFILTER_MAX)
        vegetated_count = int(np.sum(veg_mask))
        keep_mask[tile_idx[keep_finite]] = True

        nan_idx = tile_idx[~finite_ndvi]
        if nan_idx.size > 0:
            if layers.lst_day_c is None:
                raise RuntimeError("lst_day_c is required to evaluate coordinates with NaN NDVI")
            lst_vals = patch_window_stat(
                layers.lst_day_c,
                lat_arr[nan_idx],
                lon_arr[nan_idx],
                half_km=HALF_PATCH_KM,
                stat="mean",
                res=layers.res,
            )
            has_lst = np.isfinite(lst_vals)
            keep_mask[nan_idx[has_lst]] = True
            ndvi_missing_mask[nan_idx[has_lst]] = True
            no_land_mask[nan_idx[~has_lst]] = True

    counts = {
        "grid": int(n),
        "no_tile": no_tile_count,
        "vegetated": int(vegetated_count),
        "no_land_data": int(np.sum(no_land_mask)),
        "ndvi_missing": int(np.sum(ndvi_missing_mask)),
        "kept": int(np.sum(keep_mask)),
    }
    return keep_mask, ndvi_missing_mask, no_land_mask, counts


def prefilter(
    lat: np.ndarray,
    lon: np.ndarray,
    cells: set[tuple[int, int]],
    layers: EarthLayers,
) -> tuple[np.ndarray, dict[str, int]]:
    """Return boolean candidate mask and pre-filter summary statistics."""
    keep_mask, _, _, counts = _compute_prefilter_masks(lat, lon, cells, layers)
    return keep_mask, counts


def _lat_band_breakdown(lat: np.ndarray, mask: np.ndarray) -> dict[str, int]:
    sub = lat[mask]
    return {
        "south_lt_minus60": int(np.sum(sub < -60.0)),
        "mid_minus60_to_60": int(np.sum((sub >= -60.0) & (sub <= 60.0))),
        "north_gt_60": int(np.sum(sub > 60.0)),
    }


def prepare_candidates(
    project_dir: Path,
    out_dir: Path,
    limit: int | None = None,
) -> Path:
    """Build VRT if missing, pre-filter Earth grid, and write candidates.parquet."""
    proj = Path(project_dir)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    raw_dir = proj / "data" / "raw"
    derived_dir = proj / "data" / "derived"

    cop_dir = raw_dir / EARTH_RAW_FILES["copernicus_dir"]
    vrt_path = derived_dir / EARTH_DERIVED_FILES["copernicus_vrt"]
    build_vrt(cop_dir, vrt_path)

    full_grid = generate_grid("Earth", size_km=PATCH_SIZE_KM)
    lats_all = np.array([p[0] for p in full_grid], dtype=np.float64)
    lons_all = np.array([p[1] for p in full_grid], dtype=np.float64)

    cells = load_tile_cells(cop_dir)
    layers = EarthLayers.from_project(proj)

    keep_mask, ndvi_missing_mask, no_land_mask, counts = _compute_prefilter_masks(
        lats_all, lons_all, cells, layers
    )
    lat_breakdown = {
        "ndvi_missing": _lat_band_breakdown(lats_all, ndvi_missing_mask),
        "no_land_data": _lat_band_breakdown(lats_all, no_land_mask),
    }

    print(
        f"[PREPARE] grid={counts['grid']:,} no_tile={counts['no_tile']:,} "
        f"(with_tile={counts['grid'] - counts['no_tile']:,}) "
        f"vegetated={counts['vegetated']:,} no_land_data={counts['no_land_data']:,} "
        f"ndvi_missing={counts['ndvi_missing']:,} kept={counts['kept']:,}",
        flush=True,
    )
    print(f"[PREPARE] latitudinal breakdown: {lat_breakdown}", flush=True)

    kept_points = [pt for pt, k in zip(full_grid, keep_mask.tolist()) if k]
    if limit is not None and limit > 0:
        kept_points = apply_limit(kept_points, limit)
    kept_points = sorted(kept_points)

    cand_lats = np.array([p[0] for p in kept_points], dtype=np.float64)
    cand_lons = np.array([p[1] for p in kept_points], dtype=np.float64)

    env_df = layers.sample(cand_lats, cand_lons, half_km=HALF_PATCH_KM)
    cand_df = pd.DataFrame(
        {
            "lat": pd.Series(cand_lats, dtype="float64"),
            "lon": pd.Series(cand_lons, dtype="float64"),
        }
    )
    for col in EARTH_ENV_COLUMNS:
        cand_df[col] = env_df[col]
    cand_df["ndvi_missing"] = cand_df["ndvi_max"].isna().astype(bool)
    cand_df = cand_df[CANDIDATE_COLUMNS]

    cand_path = out / "candidates.parquet"
    cand_df.to_parquet(cand_path, index=False)

    cls_counts = {
        str(k): int(v) for k, v in cand_df["classification"].value_counts(dropna=False).items()
    }
    try:
        commit = subprocess.check_output(
            ["git", "-C", str(Path(__file__).resolve().parents[2]), "rev-parse", "--short", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        commit = "unknown"

    stats_payload = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "commit": commit,
        "vrt_path": str(vrt_path),
        "limit": int(limit) if limit is not None else None,
        "counts": counts,
        "with_tile": int(counts["grid"] - counts["no_tile"]),
        "lat_breakdown": lat_breakdown,
        "candidates_written": int(len(cand_df)),
        "classification_counts": cls_counts,
        "ndvi_missing_written": int(cand_df["ndvi_missing"].sum()),
    }
    stats_path = out / "prefilter_stats.json"
    stats_path.write_text(
        json.dumps(stats_payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        f"[PREPARE] written {len(cand_df):,} candidates to {cand_path} | "
        f"classification={cls_counts}",
        flush=True,
    )
    return cand_path


def _close_earth_worker() -> None:
    src = _EARTH_WORKER.pop("src", None)
    if src is not None:
        src.close()
    _EARTH_WORKER.clear()


atexit.register(_close_earth_worker)


def _init_earth_worker(vrt_path: str, size_km: float, res_m: float) -> None:
    """Open global Copernicus VRT once per worker process."""
    _close_earth_worker()
    _EARTH_WORKER["src"] = rasterio.open(vrt_path)
    _EARTH_WORKER["size_km"] = float(size_km)
    _EARTH_WORKER["res_m"] = float(res_m)


def _process_earth_point(point: tuple[float, float]) -> dict[str, object] | None:
    """Extract AEQD patch and compute 7 terrain morphometric features for an Earth candidate."""
    lat, lon = point
    src = _EARTH_WORKER["src"]
    size_km = float(_EARTH_WORKER["size_km"])
    res_m = float(_EARTH_WORKER["res_m"])

    patch = extract_patch(
        src,
        lat=lat,
        lon=lon,
        body="Earth",
        size_km=size_km,
        res_m=res_m,
        resampling=Resampling.average,
    )
    if patch is None:
        return None

    valid_frac = np.float32(np.isfinite(patch).mean())
    feats = compute_features(patch, res_m=res_m)
    return {
        "lat": float(lat),
        "lon": float(lon),
        **feats,
        "valid_frac": valid_frac,
    }


def _build_earth_feature_df(rows: list[dict[str, object]]) -> pd.DataFrame:
    if not rows:
        df = pd.DataFrame({c: pd.Series(dtype="float32") for c in EARTH_FEATURE_COLUMNS})
        df["lat"] = df["lat"].astype("float64")
        df["lon"] = df["lon"].astype("float64")
        return df

    df = pd.DataFrame(rows, columns=EARTH_FEATURE_COLUMNS)
    df["lat"] = df["lat"].astype("float64")
    df["lon"] = df["lon"].astype("float64")
    for col in EARTH_FEATURE_COLUMNS:
        if col not in ("lat", "lon"):
            df[col] = df[col].astype("float32")
    return df


def extract_stripe(
    run_dir: Path,
    stripe_idx: int,
    num_stripes: int,
    workers: int,
    vrt_path: Path,
    size_km: float = PATCH_SIZE_KM,
    res_m: float = PATCH_RES_M,
) -> Path:
    """Extract morphometric features for stripe partition `stripe_idx` of candidates.parquet."""
    t0 = time.perf_counter()
    run = Path(run_dir)
    cand_df = pd.read_parquet(run / "candidates.parquet", columns=["lat", "lon"])
    all_points = list(
        zip(cand_df["lat"].astype(float).tolist(), cand_df["lon"].astype(float).tolist())
    )
    stripe_points = select_stripe(all_points, stripe_idx=stripe_idx, num_stripes=num_stripes)

    reset_antimeridian_skipped_count()
    n_workers = max(1, min(workers, len(stripe_points))) if stripe_points else 1
    rows: list[dict[str, object]] = []

    if not stripe_points:
        rows = []
    elif n_workers == 1:
        _init_earth_worker(str(vrt_path), size_km, res_m)
        try:
            for pt in stripe_points:
                res = _process_earth_point(pt)
                if res is not None:
                    rows.append(res)
        finally:
            _close_earth_worker()
    else:
        chunksize = max(1, min(64, len(stripe_points) // (n_workers * 4) or 1))
        with mp.Pool(
            processes=n_workers,
            initializer=_init_earth_worker,
            initargs=(str(vrt_path), size_km, res_m),
        ) as pool:
            for res in pool.imap(_process_earth_point, stripe_points, chunksize=chunksize):
                if res is not None:
                    rows.append(res)

    df = _build_earth_feature_df(rows)
    out_path = run / f"features_earth_{stripe_idx}.parquet"
    df.to_parquet(out_path, index=False)

    elapsed = time.perf_counter() - t0
    skipped_antimeridian = (
        get_antimeridian_skipped_count() if n_workers == 1 else "N/A (multiprocessing)"
    )
    print(
        f"[OK] Earth stripe {stripe_idx}/{num_stripes}: "
        f"{len(df):,}/{len(stripe_points):,} valid patches in {elapsed:.1f}s "
        f"(antimeridian={skipped_antimeridian}) -> {out_path}",
        flush=True,
    )
    if len(df) > 0:
        for col, unit in (
            ("mean_slope_deg", "°"),
            ("relief_m", " m"),
            ("mean_elev_m", " m"),
        ):
            print(
                f"     {col}: min={df[col].min():.2f}{unit}, "
                f"median={df[col].median():.2f}{unit}, "
                f"p95={df[col].quantile(0.95):.2f}{unit}, "
                f"max={df[col].max():.2f}{unit}",
                flush=True,
            )
    return out_path


def merge_earth(
    run_dir: Path,
    num_stripes: int,
    allow_missing: bool = False,
) -> Path:
    """Concatenate stripe parquets `features_earth_<i>.parquet` and perform inner join with candidates.parquet."""
    run = Path(run_dir)
    expected = [(i, run / f"features_earth_{i}.parquet") for i in range(num_stripes)]
    existing = [p for _, p in expected if p.exists()]
    missing = [i for i, p in expected if not p.exists()]

    if missing:
        if not allow_missing:
            raise FileNotFoundError(
                f"Missing {len(missing)}/{num_stripes} stripes in {run}: {missing}"
            )
        covered_frac = 100.0 * len(existing) / max(num_stripes, 1)
        print(
            f"[WARN] Missing {len(missing)}/{num_stripes} stripes: {missing} "
            f"(partial stripe coverage: {covered_frac:.1f}%)",
            flush=True,
        )
    if not existing:
        raise FileNotFoundError(f"No features_earth_*.parquet stripes exist in {run}")

    feat_dfs = [pd.read_parquet(p) for p in existing]
    features_df = pd.concat(feat_dfs, ignore_index=True) if len(feat_dfs) > 1 else feat_dfs[0]
    cand_df = pd.read_parquet(run / "candidates.parquet")

    if len(features_df) == 0:
        raise RuntimeError("No valid rows across stripes to merge")

    merged = features_df.merge(cand_df, on=["lat", "lon"], how="inner", validate="one_to_one")
    if len(merged) != len(features_df):
        orphan = len(features_df) - len(merged)
        raise RuntimeError(
            f"Inner join with candidates.parquet left {orphan} orphan rows "
            f"({len(merged)} != {len(features_df)})"
        )

    merged["body"] = pd.Series(["Earth"] * len(merged), index=merged.index, dtype="string")
    merged = merged.sort_values(["lat", "lon"]).reset_index(drop=True)
    merged = merged[EARTH_COLUMNS]

    merged["body"] = merged["body"].astype("string")
    merged["lat"] = merged["lat"].astype("float64")
    merged["lon"] = merged["lon"].astype("float64")
    for col in (*FEATURE_NAMES, "valid_frac", *NUMERIC_ENV_COLUMNS):
        merged[col] = merged[col].astype("float32")
    for col in TEXT_ENV_COLUMNS:
        merged[col] = merged[col].astype("string")
    merged["ndvi_missing"] = merged["ndvi_missing"].astype(bool)

    if allow_missing and missing:
        pct_cands = 100.0 * (num_stripes - len(missing)) / num_stripes
        print(
            f"[MERGE] Partial coverage: {len(merged):,} valid "
            f"(~{pct_cands:.1f}% stripes compared to {len(cand_df):,} candidates)",
            flush=True,
        )

    out_path = run / "features_earth.parquet"
    merged.to_parquet(out_path, index=False)
    print(
        f"[MERGE] Earth: {len(existing)}/{num_stripes} stripes -> {len(merged):,} patches "
        f"in {out_path}",
        flush=True,
    )
    return out_path


def plot_earth_maps(df: pd.DataFrame, run_dir: Path) -> list[Path]:
    """Generate map_earth_mean_slope_deg.png and map_earth_classification.png."""
    run = Path(run_dir)
    run.mkdir(parents=True, exist_ok=True)
    p1 = plot_slope_map(df, body="Earth", png_path=run / "map_earth_mean_slope_deg.png")

    fig, ax = plt.subplots(figsize=(14, 7), dpi=180)
    is_known = df["classification"] == "KNOWN_ANALOG"
    is_missing = df["ndvi_missing"].astype(bool) & ~is_known
    is_new_cand = ~(is_known | is_missing)

    s_size = 6.0 if len(df) < 3000 else 1.2
    if is_new_cand.any():
        sub = df[is_new_cand]
        ax.scatter(
            sub["lon"],
            sub["lat"],
            c="#7f8c8d",
            s=s_size,
            linewidths=0,
            alpha=0.75,
            label=f"NEW_CANDIDATE ({int(is_new_cand.sum()):,})",
        )
    if is_missing.any():
        sub = df[is_missing]
        ax.scatter(
            sub["lon"],
            sub["lat"],
            c="#2980b9",
            s=s_size,
            linewidths=0,
            alpha=0.85,
            label=f"ndvi_missing / ice ({int(is_missing.sum()):,})",
        )
    if is_known.any():
        sub = df[is_known]
        ax.scatter(
            sub["lon"],
            sub["lat"],
            c="#e67e22",
            s=s_size * 1.4,
            linewidths=0,
            alpha=0.95,
            label=f"KNOWN_ANALOG ({int(is_known.sum()):,})",
        )

    ax.set_xlim(-180.0, 180.0)
    ax.set_ylim(-90.0, 90.0)
    ax.set_xlabel("Longitude (°)")
    ax.set_ylabel("Latitude (°)")
    ax.set_title(f"Earth — Candidate Classification ({len(df):,} valid patches)")
    ax.grid(True, linestyle="--", linewidth=0.4, alpha=0.4)
    ax.legend(loc="lower left", markerscale=4.0 if len(df) >= 3000 else 1.5, frameon=True)
    p2 = run / "map_earth_classification.png"
    fig.tight_layout()
    fig.savefig(p2)
    plt.close(fig)
    return [p1, p2]


def run_checks(df: pd.DataFrame, run_dir: Path) -> bool:
    """Evaluate pipeline acceptance criteria and write t5_checks.json."""
    run = Path(run_dir)
    stats_path = run / "prefilter_stats.json"
    stats = json.loads(stats_path.read_text(encoding="utf-8")) if stats_path.exists() else {}
    limit = stats.get("limit")
    is_smoke = limit is not None

    cand_path = run / "candidates.parquet"
    cand_df = pd.read_parquet(cand_path, columns=["lat", "lon"]) if cand_path.exists() else None
    if cand_df is not None:
        orphan_rows = int(len(df) - len(df.merge(cand_df, on=["lat", "lon"], how="inner")))
        cand_total = int(len(cand_df))
    else:
        orphan_rows = 0
        cand_total = int(len(df))

    all_nan_env_cols = [col for col in EARTH_ENV_COLUMNS if bool(df[col].isna().all())]

    def _subset_coords(sub_df: pd.DataFrame) -> list[dict[str, float]]:
        return [
            {"lat": round(float(r.lat), 4), "lon": round(float(r.lon), 4)}
            for r in sub_df[["lat", "lon"]].itertuples(index=False)
        ]

    amazon = df[df["lat"].between(-10.0, 2.0) & df["lon"].between(-75.0, -50.0)]
    congo = df[df["lat"].between(-5.0, 5.0) & df["lon"].between(12.0, 30.0)]
    indonesia = df[df["lat"].between(-5.0, 5.0) & df["lon"].between(95.0, 120.0)]

    presence = {
        "atacama": int((df["known_region"] == "atacama").sum()),
        "sahara": int((df["lat"].between(15.0, 30.0) & df["lon"].between(-10.0, 30.0)).sum()),
        "sonora": int((df["lat"].between(28.0, 33.0) & df["lon"].between(-115.0, -110.0)).sum()),
        "central_australia": int(
            (df["lat"].between(-28.0, -20.0) & df["lon"].between(125.0, 138.0)).sum()
        ),
        "mcmurdo-dry-valleys": int((df["known_region"] == "mcmurdo-dry-valleys").sum()),
    }

    kr_ids = [r["id"] for r in KnownRegions().regions]
    kr_counts = {rid: int((df["known_region"] == rid).sum()) for rid in kr_ids}
    cls_counts = {
        str(k): int(v) for k, v in df["classification"].value_counts(dropna=False).items()
    }
    new_cand_frac = (
        float(cls_counts.get("NEW_CANDIDATE", 0) / len(df)) if len(df) > 0 else 0.0
    )
    top_countries = {
        str(k): int(v) for k, v in df["country"].value_counts(dropna=True).head(15).items()
    }
    ndvi_missing_valid = int(df["ndvi_missing"].sum())

    valid_ratio = float(len(df) / cand_total) if cand_total > 0 else 0.0
    elev_min = float(df["mean_elev_m"].min()) if len(df) > 0 else float("nan")
    elev_max = float(df["mean_elev_m"].max()) if len(df) > 0 else float("nan")
    slope_med = float(df["mean_slope_deg"].median()) if len(df) > 0 else float("nan")

    slope_png = run / "map_earth_mean_slope_deg.png"
    cls_png = run / "map_earth_classification.png"

    checks: list[dict] = []
    if is_smoke:
        smoke_counts = stats.get("counts", {})
        kept_total = smoke_counts.get("kept")
        checks.extend(
            [
                {
                    "id": 1,
                    "name": "smoke_valid_fraction",
                    "kind": "hard",
                    "passed": bool(valid_ratio >= 0.70),
                    "observed": {"valid": int(len(df)), "candidates": cand_total, "frac": round(valid_ratio, 4)},
                    "expected": ">= 0.70 of candidates",
                },
                {
                    "id": 2,
                    "name": "smoke_elevation_range",
                    "kind": "hard",
                    "passed": bool(-500.0 <= elev_min and elev_max <= 7000.0),
                    "observed": {"min": round(elev_min, 2), "max": round(elev_max, 2)},
                    "expected": "[-500, 7000] m",
                },
                {
                    "id": 3,
                    "name": "smoke_slope_median",
                    "kind": "hard",
                    "passed": bool(0.5 <= slope_med <= 6.0),
                    "observed": round(slope_med, 3),
                    "expected": "[0.5, 6.0] deg",
                },
                {
                    "id": 4,
                    "name": "prefilter_grid_and_kept",
                    "kind": "hard",
                    "passed": bool(
                        smoke_counts.get("grid") == 497818
                        and stats.get("with_tile") == 179663
                        and kept_total is not None
                        and 35000 <= kept_total <= 80000
                    ),
                    "observed": {
                        "grid": smoke_counts.get("grid"),
                        "with_tile": stats.get("with_tile"),
                        "kept_total": kept_total,
                    },
                    "expected": "grid=497818, with_tile=179663, kept in [35000, 80000]",
                },
                {
                    "id": 5,
                    "name": "join_integrity",
                    "kind": "hard",
                    "passed": bool(orphan_rows == 0),
                    "observed": {"orphan_rows": orphan_rows, "all_nan_t6_cols": all_nan_env_cols},
                    "expected": "orphan_rows=0",
                },
            ]
        )
    else:
        checks.extend(
            [
                {
                    "id": 1,
                    "name": "valid_patch_count",
                    "kind": "hard",
                    "passed": bool(30000 <= len(df) <= 80000),
                    "observed": int(len(df)),
                    "expected": "[30000, 80000]",
                },
                {
                    "id": 2,
                    "name": "amazon_le_5",
                    "kind": "hard",
                    "passed": bool(len(amazon) <= 5),
                    "observed": {"count": int(len(amazon)), "points": _subset_coords(amazon)},
                    "expected": "<= 5",
                },
                {
                    "id": 3,
                    "name": "congo_le_5",
                    "kind": "hard",
                    "passed": bool(len(congo) <= 5),
                    "observed": {"count": int(len(congo)), "points": _subset_coords(congo)},
                    "expected": "<= 5",
                },
                {
                    "id": 4,
                    "name": "indonesia_le_5",
                    "kind": "hard",
                    "passed": bool(len(indonesia) <= 5),
                    "observed": {"count": int(len(indonesia)), "points": _subset_coords(indonesia)},
                    "expected": "<= 5",
                },
                {
                    "id": 5,
                    "name": "arid_regions_present",
                    "kind": "hard",
                    "passed": bool(all(v >= 1 for v in presence.values())),
                    "observed": presence,
                    "expected": ">= 1 in all benchmark regions",
                },
                {
                    "id": 6,
                    "name": "join_and_t6_columns",
                    "kind": "hard",
                    "passed": bool(orphan_rows == 0 and len(all_nan_env_cols) == 0),
                    "observed": {"orphan_rows": orphan_rows, "all_nan_t6_cols": all_nan_env_cols},
                    "expected": "orphan_rows=0 and no T6 environmental column entirely NaN",
                },
            ]
        )

    # Soft checks (§6.3 #7-#11)
    checks.extend(
        [
            {
                "id": 7,
                "name": "known_region_counts",
                "kind": "soft",
                "passed": True,
                "observed": kr_counts,
                "expected": "informative counts across 12 known regions",
            },
            {
                "id": 8,
                "name": "new_candidate_ratio",
                "kind": "soft",
                "passed": bool(new_cand_frac > 0.95),
                "observed": {
                    "new_candidate_frac": round(new_cand_frac, 4),
                    "classification_counts": cls_counts,
                },
                "expected": "> 0.95 NEW_CANDIDATE",
            },
            {
                "id": 9,
                "name": "top15_countries",
                "kind": "soft",
                "passed": bool("Mexico" in top_countries),
                "observed": top_countries,
                "expected": "Mexico in top 15",
            },
            {
                "id": 10,
                "name": "ndvi_missing_valid_count",
                "kind": "soft",
                "passed": bool(ndvi_missing_valid > 0 or is_smoke),
                "observed": ndvi_missing_valid,
                "expected": "count of valid patches with ndvi_missing flag",
            },
            {
                "id": 11,
                "name": "control_maps_written",
                "kind": "soft",
                "passed": bool(slope_png.exists() and cls_png.exists()),
                "observed": {
                    "mean_slope_deg": str(slope_png),
                    "classification": str(cls_png),
                },
                "expected": "ambos PNG generados",
            },
        ]
    )

    hard_checks = [c for c in checks if c["kind"] == "hard"]
    soft_checks = [c for c in checks if c["kind"] == "soft"]
    hard_passed = sum(1 for c in hard_checks if c["passed"])
    soft_passed = sum(1 for c in soft_checks if c["passed"])

    try:
        commit = subprocess.check_output(
            ["git", "-C", str(Path(__file__).resolve().parents[2]), "rev-parse", "--short", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        commit = "unknown"

    report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "commit": commit,
        "mode": "smoke" if is_smoke else "full",
        "limit": limit,
        "summary": {
            "hard_passed": hard_passed,
            "hard_total": len(hard_checks),
            "soft_passed": soft_passed,
            "soft_total": len(soft_checks),
        },
        "metrics": {
            "rows": int(len(df)),
            "candidates": cand_total,
            "valid_ratio": round(valid_ratio, 4),
            "elev_min_m": None if math.isnan(elev_min) else round(elev_min, 2),
            "elev_max_m": None if math.isnan(elev_max) else round(elev_max, 2),
            "slope_median_deg": None if math.isnan(slope_med) else round(slope_med, 3),
        },
        "checks": checks,
    }
    checks_path = run / "t5_checks.json"
    checks_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print("\n=== T5 Verification Checks ===", flush=True)
    for c in checks:
        status = "PASS" if c["passed"] else "FAIL"
        print(
            f"[{status}] #{c['id']:2d} ({c['kind']:4s}) {c['name']:<26s} "
            f"obs={c['observed']} | exp={c['expected']}",
            flush=True,
        )
    print(
        f"Summary ({report['mode']}): hard {hard_passed}/{len(hard_checks)}, "
        f"soft {soft_passed}/{len(soft_checks)} -> {checks_path}",
        flush=True,
    )
    return hard_passed == len(hard_checks)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Pipeline T5: Global Earth candidate extraction.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_prep = sub.add_parser("prepare", help="Build VRT, prefilter global grid, and sample environmental layers.")
    p_prep.add_argument("--project-dir", type=Path, default=YUCA_PROJECT_DIR)
    p_prep.add_argument("--run-dir", type=Path, required=True)
    p_prep.add_argument("--limit", type=int, default=None)

    p_ext = sub.add_parser("extract", help="Extract candidate stripe from Copernicus VRT.")
    p_ext.add_argument("--project-dir", type=Path, default=YUCA_PROJECT_DIR)
    p_ext.add_argument("--run-dir", type=Path, required=True)
    p_ext.add_argument("--stripe-idx", type=int, required=True)
    p_ext.add_argument("--num-stripes", type=int, default=32)
    p_ext.add_argument("--workers", type=int, default=16)

    p_mrg = sub.add_parser("merge", help="Merge stripes, generate maps, and run T5 verification checks.")
    p_mrg.add_argument("--run-dir", type=Path, required=True)
    p_mrg.add_argument("--num-stripes", type=int, default=32)
    p_mrg.add_argument("--allow-missing", action="store_true")

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.command == "prepare":
        prepare_candidates(args.project_dir, args.run_dir, limit=args.limit)
        return 0
    if args.command == "extract":
        vrt_path = Path(args.project_dir) / "data" / "derived" / EARTH_DERIVED_FILES["copernicus_vrt"]
        extract_stripe(
            run_dir=args.run_dir,
            stripe_idx=args.stripe_idx,
            num_stripes=args.num_stripes,
            workers=args.workers,
            vrt_path=vrt_path,
        )
        return 0
    if args.command == "merge":
        merged_path = merge_earth(
            run_dir=args.run_dir,
            num_stripes=args.num_stripes,
            allow_missing=args.allow_missing,
        )
        df = pd.read_parquet(merged_path)
        plot_earth_maps(df, args.run_dir)
        ok = run_checks(df, args.run_dir)
        return 0 if ok else 1
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
