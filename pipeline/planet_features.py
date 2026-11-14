"""Barrido global de Marte y la Luna en parches AEQD de 32x32 km (T3)."""

from __future__ import annotations

import argparse
import atexit
import math
import multiprocessing as mp
import os
from pathlib import Path

os.environ.setdefault("GDAL_CACHEMAX", "256")
os.environ.setdefault("PROJ_IGNORE_CELESTIAL_BODY", "YES")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import rasterio
from pyproj import CRS, Transformer
from rasterio.enums import Resampling
from scipy.spatial import cKDTree

from .config import (
    BODY_RADII_M,
    DIVINER_PARQUET_REL,
    FEATURE_NAMES,
    MARS_RAW_FILES,
    MOON_RAW_FILES,
    PATCH_RES_M,
    PATCH_SIZE_KM,
    YUCA_PROJECT_DIR,
)
from .features import compute_features
from .geo import extract_patch, get_antimeridian_skipped_count, reset_antimeridian_skipped_count

MARS_COLUMNS: list[str] = [
    "body",
    "lat",
    "lon",
    *FEATURE_NAMES,
    "themis_day",
    "themis_night",
    "themis_delta",
    "valid_frac",
]

MOON_COLUMNS: list[str] = [
    "body",
    "lat",
    "lon",
    *FEATURE_NAMES,
    "wac_reflectance",
    "ice_favorability",
    "diviner_tmax_k",
    "diviner_tavg_k",
    "ice_depth_m",
    "valid_frac",
]

_DIVINER_COLS: list[str] = ["tri_clon", "tri_clat", "temp_avg", "temp_max", "ice_depth"]
_WORKER_STATE: dict[str, object] = {}


def generate_grid(
    body: str,
    size_km: float = PATCH_SIZE_KM,
    lat_min: float = -88.0,
    lat_max: float = 88.0,
) -> list[tuple[float, float]]:
    """Genera una grilla casi equiareal de centros (lat, lon) para un cuerpo."""
    body_norm = body.strip().capitalize()
    if body_norm not in BODY_RADII_M:
        raise ValueError(f"Cuerpo no soportado: {body!r}")

    radius_m = BODY_RADII_M[body_norm]
    dlat = math.degrees((size_km * 1000.0) / radius_m)
    lats = np.arange(lat_min, lat_max + 1e-9, dlat)

    points: list[tuple[float, float]] = []
    for lat in lats:
        lat_f = float(lat)
        cos_lat = math.cos(math.radians(lat_f))
        if cos_lat <= 1e-6:
            continue
        dlon = dlat / cos_lat
        lons = np.arange(-180.0 + dlon / 2.0, 180.0, dlon)
        for lon in lons:
            points.append((round(lat_f, 6), round(float(lon), 6)))
    return points


def select_stripe(
    points: list[tuple[float, float]],
    stripe_idx: int,
    num_stripes: int,
) -> list[tuple[float, float]]:
    """Devuelve la franja `stripe_idx` de `num_stripes` particiones contiguas."""
    if num_stripes <= 1:
        return points
    if stripe_idx < 0 or stripe_idx >= num_stripes:
        raise ValueError(
            f"stripe_idx={stripe_idx} fuera de rango [0, {num_stripes - 1}]."
        )
    if not points:
        return []
    n = len(points)
    base, rem = divmod(n, num_stripes)
    start = stripe_idx * base + min(stripe_idx, rem)
    end = start + base + (1 if stripe_idx < rem else 0)
    return points[start:end]


def apply_limit(
    points: list[tuple[float, float]],
    limit: int | None,
) -> list[tuple[float, float]]:
    """Submuestrea uniformemente hasta `limit` centros manteniendo cobertura latitudinal."""
    if limit is None or limit <= 0 or len(points) <= limit:
        return points
    step = max(1, len(points) // limit)
    return points[::step][:limit]


def _diviner_transformer() -> Transformer:
    r_moon = BODY_RADII_M["Moon"]
    geo_crs = CRS.from_proj4(f"+proj=longlat +R={r_moon} +no_defs")
    stere_crs = CRS.from_proj4(
        f"+proj=stere +lat_0=-90 +lon_0=0 +x_0=0 +y_0=0 +R={r_moon} +units=m +no_defs"
    )
    return Transformer.from_crs(geo_crs, stere_crs, always_xy=True)


def prepare_diviner_parquet(tab_path: Path, parquet_path: Path) -> Path | None:
    """Convierte dlre_prp_south.tab (CSV con encabezado) a parquet en data/derived/."""
    if parquet_path.exists():
        return parquet_path

    candidate = tab_path
    if not candidate.exists():
        alt = tab_path.with_name("DLRE_PRP_SOUTH.TAB")
        if alt.exists():
            candidate = alt
        else:
            return None

    df = pd.read_csv(
        candidate,
        usecols=_DIVINER_COLS,
        skipinitialspace=True,
        dtype={
            "tri_clon": "float64",
            "tri_clat": "float64",
            "temp_avg": "float32",
            "temp_max": "float32",
            "ice_depth": "float32",
        },
    )
    df = df.dropna(subset=["tri_clon", "tri_clat"]).copy()
    lons = ((df["tri_clon"].to_numpy(dtype=np.float64) + 180.0) % 360.0) - 180.0
    lats = df["tri_clat"].to_numpy(dtype=np.float64)

    transformer = _diviner_transformer()
    xs, ys = transformer.transform(lons, lats)
    df["x_m"] = np.asarray(xs, dtype=np.float64)
    df["y_m"] = np.asarray(ys, dtype=np.float64)
    # -999 indica ausencia de hielo estable -> NaN para la mediana.
    df.loc[df["ice_depth"] <= -900.0, "ice_depth"] = np.float32(np.nan)
    df = df[["x_m", "y_m", "temp_avg", "temp_max", "ice_depth"]]

    parquet_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = parquet_path.with_name(f".{parquet_path.name}.{os.getpid()}.tmp")
    df.to_parquet(tmp_path, index=False)
    os.replace(tmp_path, parquet_path)
    print(f"[INFO] Diviner PRP cacheado en {parquet_path} ({len(df):,} triángulos)")
    return parquet_path


def load_diviner_prp(
    tab_path: Path,
    parquet_path: Path | None = None,
) -> dict[str, object] | None:
    """Carga la tabla Diviner PRP desde parquet derivado (o desde .tab si aún no existe)."""
    target_parquet = parquet_path if parquet_path is not None else tab_path.with_suffix(".parquet")
    resolved = prepare_diviner_parquet(tab_path, target_parquet)
    if resolved is None or not resolved.exists():
        return None

    df = pd.read_parquet(resolved)
    if df.empty:
        return None

    xy = df[["x_m", "y_m"]].to_numpy(dtype=np.float64)
    valid = np.all(np.isfinite(xy), axis=1)
    if not np.any(valid):
        return None

    return {
        "tree": cKDTree(xy[valid]),
        "xy": xy[valid],
        "transformer": _diviner_transformer(),
        "tmax": df["temp_max"].to_numpy(dtype=np.float32)[valid],
        "tavg": df["temp_avg"].to_numpy(dtype=np.float32)[valid],
        "depth": df["ice_depth"].to_numpy(dtype=np.float32)[valid],
    }


def _close_worker() -> None:
    for key, obj in list(_WORKER_STATE.items()):
        if key == "aux_srcs" and isinstance(obj, dict):
            for src in obj.values():
                if src is not None:
                    src.close()
        elif hasattr(obj, "close"):
            obj.close()
    _WORKER_STATE.clear()


def _init_worker(
    body: str,
    dem_path: str,
    aux_paths: dict[str, str],
    diviner_tab_path: str | None,
    diviner_parquet_path: str | None,
    size_km: float,
    res_m: float,
) -> None:
    _close_worker()
    aux_srcs: dict[str, rasterio.DatasetReader] = {}
    for name, path_str in aux_paths.items():
        if path_str and Path(path_str).exists():
            aux_srcs[name] = rasterio.open(path_str)

    diviner = None
    if diviner_tab_path or diviner_parquet_path:
        tab_p = Path(diviner_tab_path) if diviner_tab_path else Path("")
        pq_p = Path(diviner_parquet_path) if diviner_parquet_path else None
        diviner = load_diviner_prp(tab_p, pq_p)

    _WORKER_STATE["body"] = body
    _WORKER_STATE["dem_src"] = rasterio.open(dem_path)
    _WORKER_STATE["aux_srcs"] = aux_srcs
    _WORKER_STATE["diviner"] = diviner
    _WORKER_STATE["size_km"] = size_km
    _WORKER_STATE["res_m"] = res_m
    atexit.register(_close_worker)


def _sample_aux_median(
    aux_src: rasterio.DatasetReader | None,
    lat: float,
    lon: float,
    body: str,
    size_km: float,
    res_m: float,
) -> np.float32:
    if aux_src is None:
        return np.float32(np.nan)
    patch = extract_patch(
        aux_src,
        lat=lat,
        lon=lon,
        body=body,
        size_km=size_km,
        res_m=res_m,
        resampling=Resampling.average,
    )
    if patch is None:
        return np.float32(np.nan)
    finite = patch[np.isfinite(patch)]
    if finite.size == 0:
        return np.float32(np.nan)
    return np.float32(np.median(finite))


def _query_diviner_patch(
    diviner: dict[str, object],
    lat: float,
    lon: float,
    size_km: float,
) -> tuple[np.float32, np.float32, np.float32]:
    """Calcula la mediana dentro del parche polar sobre triángulos Diviner PRP."""
    nan32 = np.float32(np.nan)
    half_m = size_km * 500.0
    x, y = diviner["transformer"].transform(lon, lat)  # type: ignore[union-attr]
    tree: cKDTree = diviner["tree"]  # type: ignore[assignment]
    idxs = tree.query_ball_point([x, y], r=half_m * math.sqrt(2.0))
    if not idxs:
        return nan32, nan32, nan32

    idx_arr = np.asarray(idxs, dtype=np.int64)
    xy = diviner["xy"][idx_arr]  # type: ignore[index]
    in_square = (np.abs(xy[:, 0] - x) <= half_m) & (np.abs(xy[:, 1] - y) <= half_m)
    if not np.any(in_square):
        return nan32, nan32, nan32
    sel = idx_arr[in_square]

    tmax_vals = diviner["tmax"][sel]  # type: ignore[index]
    tavg_vals = diviner["tavg"][sel]  # type: ignore[index]
    depth_vals = diviner["depth"][sel]  # type: ignore[index]

    tmax_med = np.float32(np.nanmedian(tmax_vals)) if np.any(np.isfinite(tmax_vals)) else nan32
    tavg_med = np.float32(np.nanmedian(tavg_vals)) if np.any(np.isfinite(tavg_vals)) else nan32
    depth_med = np.float32(np.nanmedian(depth_vals)) if np.any(np.isfinite(depth_vals)) else nan32
    return tmax_med, tavg_med, depth_med


def _process_point(point: tuple[float, float]) -> dict[str, object] | None:
    lat, lon = point
    body = str(_WORKER_STATE["body"])
    dem_src = _WORKER_STATE["dem_src"]
    aux_srcs: dict[str, rasterio.DatasetReader] = _WORKER_STATE["aux_srcs"]  # type: ignore[assignment]
    diviner = _WORKER_STATE["diviner"]
    size_km = float(_WORKER_STATE["size_km"])
    res_m = float(_WORKER_STATE["res_m"])

    dem_patch = extract_patch(
        dem_src,
        lat=lat,
        lon=lon,
        body=body,
        size_km=size_km,
        res_m=res_m,
        resampling=Resampling.average,
    )
    if dem_patch is None:
        return None

    valid_frac = np.float32(np.isfinite(dem_patch).mean())
    feats = compute_features(dem_patch, res_m=res_m)

    row: dict[str, object] = {
        "body": body,
        "lat": float(lat),
        "lon": float(lon),
        **feats,
    }

    if body == "Mars":
        # Nota: THEMIS Day/Night se guardan en valores crudos del mosaico (no son temperatura física).
        themis_day = _sample_aux_median(
            aux_srcs.get("themis_day"), lat, lon, body, size_km, res_m
        )
        # El mosaico THEMIS Night cubre aproximadamente 60°N–60°S.
        if abs(lat) <= 61.0:
            themis_night = _sample_aux_median(
                aux_srcs.get("themis_night"), lat, lon, body, size_km, res_m
            )
        else:
            themis_night = np.float32(np.nan)

        if np.isfinite(themis_day) and np.isfinite(themis_night):
            themis_delta = np.float32(themis_day - themis_night)
        else:
            themis_delta = np.float32(np.nan)

        row["themis_day"] = themis_day
        row["themis_night"] = themis_night
        row["themis_delta"] = themis_delta
    elif body == "Moon":
        row["wac_reflectance"] = _sample_aux_median(
            aux_srcs.get("wac_reflectance"), lat, lon, body, size_km, res_m
        )
        if lat <= -70.0:
            row["ice_favorability"] = _sample_aux_median(
                aux_srcs.get("ice_south"), lat, lon, body, size_km, res_m
            )
        elif lat >= 70.0:
            row["ice_favorability"] = _sample_aux_median(
                aux_srcs.get("ice_north"), lat, lon, body, size_km, res_m
            )
        else:
            row["ice_favorability"] = np.float32(np.nan)

        div_tmax = np.float32(np.nan)
        div_tavg = np.float32(np.nan)
        ice_depth = np.float32(np.nan)
        # La malla polar sur de Diviner PRP cubre desde ~75.9°S hasta 90°S.
        if isinstance(diviner, dict) and lat <= -75.0:
            div_tmax, div_tavg, ice_depth = _query_diviner_patch(
                diviner, lat=lat, lon=lon, size_km=size_km
            )

        row["diviner_tmax_k"] = div_tmax
        row["diviner_tavg_k"] = div_tavg
        row["ice_depth_m"] = ice_depth

    row["valid_frac"] = valid_frac
    return row


def _build_dataframe(rows: list[dict[str, object]], body: str) -> pd.DataFrame:
    cols = MARS_COLUMNS if body == "Mars" else MOON_COLUMNS
    if not rows:
        df = pd.DataFrame({c: pd.Series(dtype="float32") for c in cols})
        df["body"] = df["body"].astype("string")
        df["lat"] = df["lat"].astype("float64")
        df["lon"] = df["lon"].astype("float64")
        return df

    df = pd.DataFrame(rows, columns=cols)
    df["body"] = df["body"].astype("string")
    df["lat"] = df["lat"].astype("float64")
    df["lon"] = df["lon"].astype("float64")
    for col in cols:
        if col not in ("body", "lat", "lon"):
            df[col] = df[col].astype("float32")
    return df


def plot_slope_map(df: pd.DataFrame, body: str, png_path: Path) -> Path:
    """Genera un mapa scatter lat/lon de mean_slope_deg para validación visual rápida."""
    png_path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(12, 6))
    if len(df) > 0:
        slopes = df["mean_slope_deg"].to_numpy(dtype=np.float64)
        vmax = max(1.0, float(np.nanpercentile(slopes, 98)))
        marker_size = 6.0 if len(df) < 3000 else 1.2
        sc = ax.scatter(
            df["lon"],
            df["lat"],
            c=slopes,
            cmap="inferno",
            s=marker_size,
            vmin=0.0,
            vmax=vmax,
            linewidths=0,
        )
        cbar = fig.colorbar(sc, ax=ax, pad=0.02)
        cbar.set_label("mean_slope_deg (°)")
    ax.set_xlim(-180, 180)
    ax.set_ylim(-90, 90)
    ax.set_xlabel("Longitud (°)")
    ax.set_ylabel("Latitud (°)")
    ax.set_title(f"{body} — mean_slope_deg ({len(df):,} parches válidos)")
    ax.grid(True, linestyle="--", linewidth=0.4, alpha=0.4)
    fig.tight_layout()
    fig.savefig(png_path, dpi=180)
    plt.close(fig)
    return png_path


def merge_body_stripes(out_dir: Path, body: str) -> Path | None:
    """Concatena los parquet de franjas de `body` y genera el PNG global."""
    body_lower = body.lower()
    stripe_files = sorted(out_dir.glob(f"features_{body_lower}_*.parquet"))
    if not stripe_files:
        print(f"[WARN] No hay archivos features_{body_lower}_*.parquet en {out_dir}")
        return None

    dfs = [pd.read_parquet(p) for p in stripe_files]
    merged = pd.concat(dfs, ignore_index=True) if len(dfs) > 1 else dfs[0]
    merged_path = out_dir / f"features_{body_lower}.parquet"
    merged.to_parquet(merged_path, index=False)

    png_path = out_dir / f"map_{body_lower}_mean_slope_deg.png"
    plot_slope_map(merged, body=body, png_path=png_path)
    print(
        f"[MERGE] {body}: {len(stripe_files)} franjas -> {len(merged):,} parches válidos "
        f"en {merged_path} | mapa {png_path}"
    )
    return merged_path


def run_body_extraction(
    body: str,
    raw_dir: Path,
    out_dir: Path,
    derived_dir: Path | None = None,
    stripe_idx: int = 0,
    num_stripes: int = 1,
    workers: int = 8,
    limit: int | None = None,
    size_km: float = PATCH_SIZE_KM,
    res_m: float = PATCH_RES_M,
    file_overrides: dict[str, Path] | None = None,
) -> Path:
    """Ejecuta la extracción para una franja de `body` y escribe su parquet."""
    body_norm = body.strip().capitalize()
    raw_spec = MARS_RAW_FILES if body_norm == "Mars" else MOON_RAW_FILES

    resolved: dict[str, Path] = {
        k: raw_dir / rel for k, rel in raw_spec.items()
    }
    if file_overrides:
        resolved.update(file_overrides)

    dem_path = resolved["dem"]
    if not dem_path.exists():
        raise FileNotFoundError(f"No se encontró el DEM de {body_norm}: {dem_path}")

    aux_paths: dict[str, str] = {}
    for k, p in resolved.items():
        if k in ("dem", "diviner_prp"):
            continue
        if p.exists():
            aux_paths[k] = str(p)
        else:
            print(f"[WARN] Capa auxiliar opcional ausente para {body_norm} ({k}): {p}")

    full_grid = generate_grid(body_norm, size_km=size_km)
    if limit is not None and limit > 0:
        all_candidates = apply_limit(full_grid, limit)
    else:
        all_candidates = full_grid

    stripe_points = select_stripe(all_candidates, stripe_idx=stripe_idx, num_stripes=num_stripes)

    diviner_tab_path: str | None = None
    diviner_parquet_path: str | None = None
    if (
        body_norm == "Moon"
        and "diviner_prp" in resolved
        and any(pt[0] <= -75.0 for pt in stripe_points)
    ):
        target_derived = derived_dir if derived_dir is not None else (raw_dir.parent / "derived")
        diviner_pq = target_derived / DIVINER_PARQUET_REL
        prepared = prepare_diviner_parquet(resolved["diviner_prp"], diviner_pq)
        if prepared is not None:
            diviner_tab_path = str(resolved["diviner_prp"])
            diviner_parquet_path = str(prepared)
        else:
            print(f"[WARN] Tabla Diviner PRP no encontrada en {resolved['diviner_prp']}")

    reset_antimeridian_skipped_count()
    out_dir.mkdir(parents=True, exist_ok=True)

    n_workers = max(1, min(workers, len(stripe_points))) if stripe_points else 1
    rows: list[dict[str, object]] = []

    if not stripe_points:
        rows = []
    elif n_workers == 1:
        _init_worker(
            body_norm,
            str(dem_path),
            aux_paths,
            diviner_tab_path,
            diviner_parquet_path,
            size_km,
            res_m,
        )
        try:
            for pt in stripe_points:
                res = _process_point(pt)
                if res is not None:
                    rows.append(res)
        finally:
            _close_worker()
    else:
        chunksize = max(1, min(64, len(stripe_points) // (n_workers * 4) or 1))
        with mp.Pool(
            processes=n_workers,
            initializer=_init_worker,
            initargs=(
                body_norm,
                str(dem_path),
                aux_paths,
                diviner_tab_path,
                diviner_parquet_path,
                size_km,
                res_m,
            ),
        ) as pool:
            for res in pool.imap(_process_point, stripe_points, chunksize=chunksize):
                if res is not None:
                    rows.append(res)

    df = _build_dataframe(rows, body_norm)
    stripe_path = out_dir / f"features_{body_norm.lower()}_{stripe_idx}.parquet"
    df.to_parquet(stripe_path, index=False)

    skipped_antimeridian = get_antimeridian_skipped_count() if n_workers == 1 else "N/A (multiproceso)"
    print(
        f"[OK] {body_norm} franja {stripe_idx}/{num_stripes}: "
        f"{len(df):,}/{len(stripe_points):,} parches válidos "
        f"(grilla completa={len(full_grid):,}, antimeridiano={skipped_antimeridian}) -> {stripe_path}"
    )
    if len(df) > 0:
        print(
            f"     mean_slope_deg: min={df['mean_slope_deg'].min():.2f}°, "
            f"mediana={df['mean_slope_deg'].median():.2f}°, "
            f"p95={df['mean_slope_deg'].quantile(0.95):.2f}°, "
            f"max={df['mean_slope_deg'].max():.2f}°"
        )
        if body_norm == "Moon" and "diviner_tavg_k" in df.columns:
            div_cov = int(df["diviner_tavg_k"].notna().sum())
            if div_cov > 0:
                ice_stable = int(df["ice_depth_m"].notna().sum())
                no_ice = div_cov - ice_stable
                print(
                    f"     Diviner polar: {div_cov:,} parches con cobertura "
                    f"(con hielo estable={ice_stable:,}, sin hielo/-999={no_ice:,})"
                )

    if num_stripes <= 1:
        merge_body_stripes(out_dir, body_norm)

    return stripe_path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extrae rasgos geomorfométricos globales de Marte y la Luna (T3)."
    )
    parser.add_argument(
        "--project-dir",
        type=Path,
        default=YUCA_PROJECT_DIR,
        help="Directorio raíz del proyecto (contiene data/raw).",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        required=True,
        help="Directorio de salida para esta corrida (p.ej. runs/<SLURM_JOB_ID>).",
    )
    parser.add_argument(
        "--body",
        choices=["Mars", "Moon", "all"],
        default="all",
        help="Cuerpo a procesar.",
    )
    parser.add_argument("--stripe-idx", type=int, default=0, help="Índice de franja [0..num-stripes-1].")
    parser.add_argument("--num-stripes", type=int, default=1, help="Total de franjas en el job array.")
    parser.add_argument("--workers", type=int, default=8, help="Procesos paralelos por franja.")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limita el total de parches candidatos por cuerpo (corrida de prueba).",
    )
    parser.add_argument(
        "--merge",
        action="store_true",
        help="Solo combina las franjas existentes en --out-dir y genera los mapas PNG.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    bodies = ["Mars", "Moon"] if args.body == "all" else [args.body]
    raw_dir = args.project_dir / "data" / "raw"
    derived_dir = args.project_dir / "data" / "derived"

    if args.merge:
        for body in bodies:
            merge_body_stripes(args.out_dir, body)
        return

    for body in bodies:
        run_body_extraction(
            body=body,
            raw_dir=raw_dir,
            out_dir=args.out_dir,
            derived_dir=derived_dir,
            stripe_idx=args.stripe_idx,
            num_stripes=args.num_stripes,
            workers=args.workers,
            limit=args.limit,
        )


if __name__ == "__main__":
    main()
