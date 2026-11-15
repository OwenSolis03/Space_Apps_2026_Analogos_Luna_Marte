#!/usr/bin/env python3
"""Planetary terrain archetype extraction and clustering pipeline (v1 script).

Performs windowed morphometric feature calculation over global MOLA (Mars) and LOLA (Moon)
DEM mosaics, samples auxiliary thermal/reflectance rasters (THEMIS IR day/night, LROC WAC),
standardizes features using StandardScaler, clusters terrain with MiniBatchKMeans into 40
archetypes per body, and records the medoid closest to each centroid in `output/planetary_baselines.json`.
"""

from __future__ import annotations

import argparse
import json
import math
import os

import numpy as np
import rasterio
from rasterio.windows import Window
from pyproj import Transformer
from scipy.spatial.distance import cdist
from sklearn.cluster import MiniBatchKMeans
from sklearn.preprocessing import StandardScaler

# Volumetric mean radii in meters
PLANET_RADIUS_M = {
    "Earth": 6371000.0,
    "Mars": 3396190.0,
    "Moon": 1737400.0,
}


def to_lat_lon(src, x_c: float, y_c: float, body: str) -> tuple[float, float]:
    """Convert projected dataset coordinates (x_c, y_c) to geographic (lat, lon) degrees."""
    if src.crs and not src.crs.is_geographic:
        try:
            transformer = Transformer.from_crs(src.crs, src.crs.geodetic_crs, always_xy=True)
            lon, lat = transformer.transform(x_c, y_c)
            if math.isfinite(lat) and math.isfinite(lon) and -90.0 <= lat <= 90.0:
                return float(lat), float(((lon + 180.0) % 360.0) - 180.0)
        except Exception:
            pass
        # Fallback to standard planetary equirectangular sphere projection
        r = PLANET_RADIUS_M[body]
        lat = math.degrees(y_c / r)
        lon = math.degrees(x_c / r)
        return max(-90.0, min(90.0, lat)), ((lon + 180.0) % 360.0) - 180.0
    return float(y_c), float(((x_c + 180.0) % 360.0) - 180.0)


def sample_aux_raster(aux_src, x_c: float, y_c: float) -> float:
    """Sample median value from auxiliary raster around coordinate (x_c, y_c)."""
    if aux_src is None:
        return np.nan
    try:
        row, col = aux_src.index(x_c, y_c)
        r0 = max(0, row - 16)
        c0 = max(0, col - 16)
        h = min(32, aux_src.height - r0)
        w = min(32, aux_src.width - c0)
        if h <= 0 or w <= 0:
            return np.nan
        patch = aux_src.read(1, window=Window(c0, r0, w, h)).astype(np.float32)
        if aux_src.nodata is not None:
            patch[np.isclose(patch, aux_src.nodata)] = np.nan
        patch[np.abs(patch) > 1e8] = np.nan
        val = float(np.nanmedian(patch))
        return val if math.isfinite(val) else np.nan
    except Exception:
        return np.nan


def compute_planetary_features(
    dem_path: str,
    body: str,
    aux_paths: dict[str, str],
    win_size: int = 256,
    max_windows: int = 4500,
) -> tuple[np.ndarray, list[dict[str, object]]]:
    """Extract terrain features and sample auxiliary values across sliding DEM raster windows."""
    features = []
    meta = []

    aux_srcs = {k: rasterio.open(p) for k, p in aux_paths.items() if p and os.path.exists(p)}

    with rasterio.open(dem_path) as src:
        nodata = src.nodata
        res_x, res_y = src.res
        is_geo = bool(src.crs and src.crs.is_geographic)
        scale_m = math.radians(1.0) * PLANET_RADIUS_M[body] if is_geo else 1.0
        dx = abs(res_x) * scale_m
        dy = abs(res_y) * scale_m

        all_windows = [
            Window(col, row, min(win_size, src.width - col), min(win_size, src.height - row))
            for row in range(0, src.height, win_size)
            for col in range(0, src.width, win_size)
        ]

        if max_windows and len(all_windows) > max_windows:
            step = max(1, len(all_windows) // max_windows)
            all_windows = all_windows[::step][:max_windows]

        for win in all_windows:
            if win.width < 32 or win.height < 32:
                continue

            data = src.read(1, window=win).astype(np.float32)
            if nodata is not None:
                data[np.isclose(data, nodata)] = np.nan
            data[np.abs(data) > 1e8] = np.nan

            if np.isfinite(data).mean() < 0.8:
                continue

            med = float(np.nanmedian(data))
            data_clean = np.where(np.isfinite(data), data, med)

            gy, gx = np.gradient(data_clean, dy, dx)
            slope_deg = np.degrees(np.arctan(np.hypot(gx, gy)))

            mean_elev = float(np.mean(data_clean))
            std_elev = float(np.std(data_clean))
            mean_slope = float(np.mean(slope_deg))
            p90_slope = float(np.percentile(slope_deg, 90))
            tri = float(np.mean(np.abs(data_clean - med)))

            row_c = win.row_off + win.height / 2.0
            col_c = win.col_off + win.width / 2.0
            x_c, y_c = src.xy(row_c, col_c)
            lat, lon = to_lat_lon(src, x_c, y_c, body)

            aux_vals = {k: sample_aux_raster(a_src, x_c, y_c) for k, a_src in aux_srcs.items()}

            # Morphometric clustering vector: elevation, roughness, mean slope, p90 slope, TRI
            features.append([mean_elev, std_elev, mean_slope, p90_slope, tri])
            meta.append({"lat": lat, "lon": lon, "aux": aux_vals})

    for a_src in aux_srcs.values():
        a_src.close()

    return np.array(features, dtype=np.float32), meta


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract planetary archetypes from global DEMs via MiniBatchKMeans (v1)."
    )
    parser.add_argument("--project-dir", required=True, help="Base path to project on HPC.")
    parser.add_argument("--n-clusters", type=int, default=40, help="Number of clusters per body.")
    args = parser.parse_args()

    mars_dem = os.path.join(args.project_dir, "data/raw/mars/Mars_MGS_MOLA_DEM_mosaic_global_463m.tif")
    mars_day = os.path.join(args.project_dir, "data/raw/mars/Mars_ODY_THEMIS_IR_Day_Mosaic_100m.tif")
    # THEMIS Night coverage spans 60N-60S; outside this latitude band, values sample as NaN.
    mars_night = os.path.join(args.project_dir, "data/raw/mars/Mars_MO_THEMIS-IR-Night_mosaic_60N60S_100m_v14.tif")

    moon_dem = os.path.join(args.project_dir, "data/raw/moon/Lunar_LRO_LOLA_Global_LDEM_118m.tif")
    moon_wac = os.path.join(args.project_dir, "data/raw/moon/Lunar_LRO_LROC-WAC_Mosaic_global_100m_June2013.tif")

    out_json = os.path.join(args.project_dir, "output/planetary_baselines.json")
    results: dict[str, object] = {"generated_on": "Yuca HPC Cluster", "targets": {}}

    configs = [
        ("Mars", mars_dem, {"themis_ir_day": mars_day, "themis_ir_night": mars_night}),
        ("Moon", moon_dem, {"wac_reflectance": moon_wac}),
    ]

    for body, dem_path, aux_paths in configs:
        if not os.path.exists(dem_path):
            print(f"[WARN] File not found: {dem_path}, skipping {body}.")
            continue

        print(f"[*] Processing global morphometric and auxiliary metrics for {body}...")
        feats, meta = compute_planetary_features(dem_path, body=body, aux_paths=aux_paths)
        if len(feats) == 0:
            continue

        scaler = StandardScaler()
        feats_norm = scaler.fit_transform(feats)

        kmeans = MiniBatchKMeans(n_clusters=min(args.n_clusters, len(feats)), random_state=42, batch_size=1024)
        kmeans.fit(feats_norm)

        dists = cdist(kmeans.cluster_centers_, feats_norm)
        rep_indices = np.argmin(dists, axis=1)

        clusters_out = []
        for cid, idx in enumerate(rep_indices):
            m = meta[idx]
            f = feats[idx]
            metrics: dict[str, float] = {
                "mean_elev_m": round(float(f[0]), 2),
                "roughness_std_m": round(float(f[1]), 2),
                "mean_slope_deg": round(float(f[2]), 2),
                "p90_slope_deg": round(float(f[3]), 2),
                "tri": round(float(f[4]), 2),
            }
            for k, v in m["aux"].items():
                if math.isfinite(v):
                    metrics[k] = round(float(v), 2)

            if "themis_ir_day" in metrics and "themis_ir_night" in metrics:
                metrics["diurnal_thermal_delta"] = round(metrics["themis_ir_day"] - metrics["themis_ir_night"], 2)

            clusters_out.append({
                "cluster_id": f"{body.lower()}-c{cid:02d}",
                "lat": round(m["lat"], 4),
                "lon": round(m["lon"], 4),
                "metrics": metrics,
            })

        results["targets"][body] = {
            "total_windows_analyzed": len(feats),
            "archetypes": clusters_out,
        }
        print(f"[OK] {body}: {len(feats)} windows -> {len(clusters_out)} archetypes with coordinates and auxiliary layers.")

    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"[DONE] Saved to {out_json}")


if __name__ == "__main__":
    main()
