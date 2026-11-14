#!/usr/bin/env python3
"""Earth-to-Planetary analog matching pipeline (v1 script).

Extracts Copernicus GLO-90 terrain windows in parallel, standardizes 4 morphometric
features (roughness_std_m, mean_slope_deg, p90_slope_deg, tri) alongside planetary
archetypes from `output/planetary_baselines.json`, selects the top-k nearest Earth analogs
with spatial diversity (150 km minimum geodesic separation), and outputs `output/analogs.json`.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
import glob
import json
import math
import os

import numpy as np
import rasterio
from rasterio.windows import Window
from sklearn.preprocessing import StandardScaler

MORPH_KEYS = ["roughness_std_m", "mean_slope_deg", "p90_slope_deg", "tri"]


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate great-circle distance between two points in kilometers on spherical Earth."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 12742.0 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))


def analyze_earth_tile(tile_path: str) -> list[dict[str, object]]:
    """Scan a Copernicus GLO-90 GeoTIFF tile in 512x512 windows and compute morphometric metrics."""
    records = []
    try:
        with rasterio.open(tile_path) as src:
            nodata = src.nodata
            res_x, res_y = src.res
            for row in range(0, src.height, 512):
                for col in range(0, src.width, 512):
                    w, h = min(512, src.width - col), min(512, src.height - row)
                    if w < 256 or h < 256:
                        continue
                    data = src.read(1, window=Window(col, row, w, h)).astype(np.float32)
                    if nodata is not None:
                        data[np.isclose(data, nodata)] = np.nan
                    valid = np.isfinite(data)
                    if valid.mean() < 0.85 or (np.abs(data[valid]) < 0.5).mean() > 0.30:
                        continue
                    lon, lat = src.xy(row + h / 2.0, col + w / 2.0)
                    dx = abs(res_x) * 111320.0 * max(0.15, math.cos(math.radians(lat)))
                    dy = abs(res_y) * 111320.0
                    med = float(np.nanmedian(data))
                    clean = np.where(valid, data, med)
                    gy, gx = np.gradient(clean, dy, dx)
                    slope = np.degrees(np.arctan(np.hypot(gx, gy)))
                    std_e, m_slp = float(np.std(clean)), float(np.mean(slope))
                    if std_e < 5.0 and m_slp < 0.3:
                        continue
                    records.append({
                        "lat": round(float(lat), 4),
                        "lon": round(float(lon), 4),
                        "tile": os.path.basename(tile_path),
                        "mean_elev_m": round(float(np.mean(clean)), 1),
                        "vec": [std_e, m_slp, float(np.percentile(slope, 90)), float(np.mean(np.abs(clean - med)))],
                    })
    except Exception:
        return []
    return records


def main() -> None:
    p = argparse.ArgumentParser(
        description="Match Earth Copernicus GLO-90 terrain patches against Moon/Mars archetypes (v1)."
    )
    p.add_argument("--project-dir", required=True, help="Base path to project on HPC.")
    p.add_argument("--workers", type=int, default=32, help="Parallel worker processes.")
    p.add_argument("--top-k", type=int, default=5, help="Top analogs to select per archetype.")
    p.add_argument("--min-dist-km", type=float, default=150.0, help="Minimum separation in km between analogs.")
    args = p.parse_args()

    with open(os.path.join(args.project_dir, "output/planetary_baselines.json"), "r", encoding="utf-8") as f:
        baselines = json.load(f)

    tiles = sorted(glob.glob(os.path.join(args.project_dir, "data/raw/earth/copernicus_90m/*.tif")))
    print(f"[*] Earth tiles: {len(tiles)} | Workers: {args.workers}")

    all_earth = []
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        for i, batch in enumerate(ex.map(analyze_earth_tile, tiles, chunksize=16), 1):
            all_earth.extend(batch)
            if i % 1000 == 0 or i == len(tiles):
                print(f"    Progress: {i}/{len(tiles)} tiles -> {len(all_earth)} candidate sites")

    earth_vecs = np.array([r["vec"] for r in all_earth], dtype=np.float32)
    output = {"generated_on": "Yuca HPC Cluster", "earth_sites_evaluated": len(all_earth), "targets": {}}

    for body, bdata in baselines["targets"].items():
        archs = bdata["archetypes"]
        t_vecs = np.array([[a["metrics"][k] for k in MORPH_KEYS] for a in archs], dtype=np.float32)
        scaler = StandardScaler().fit(np.vstack([t_vecs, earth_vecs]))
        t_norm, e_norm = scaler.transform(t_vecs), scaler.transform(earth_vecs)

        enriched = []
        for idx, arch in enumerate(archs):
            dists = np.linalg.norm(e_norm - t_norm[idx], axis=1)
            matches = []
            for e_i in np.argsort(dists):
                rec = all_earth[e_i]
                if any(haversine_km(rec["lat"], rec["lon"], m["lat"], m["lon"]) < args.min_dist_km for m in matches):
                    continue
                d = float(dists[e_i])
                matches.append({
                    "rank": len(matches) + 1,
                    "similarity_score": round(100.0 / (1.0 + 0.35 * d), 2),
                    "distance": round(d, 4),
                    "lat": rec["lat"],
                    "lon": rec["lon"],
                    "tile": rec["tile"],
                    "metrics": {
                        "mean_elev_m": rec["mean_elev_m"],
                        "roughness_std_m": round(rec["vec"][0], 2),
                        "mean_slope_deg": round(rec["vec"][1], 2),
                        "p90_slope_deg": round(rec["vec"][2], 2),
                        "tri": round(rec["vec"][3], 2),
                    },
                })
                if len(matches) == args.top_k:
                    break
            enriched.append({
                "cluster_id": arch["cluster_id"],
                "iau_nomenclature": arch.get("iau_nomenclature"),
                "target_coords": {"lat": arch["lat"], "lon": arch["lon"]},
                "target_metrics": arch["metrics"],
                "top_earth_analogs": matches,
            })
        output["targets"][body] = enriched
        print(f"[OK] {body}: {len(enriched)} archetypes matched.")

    out_path = os.path.join(args.project_dir, "output/analogs.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"[DONE] Saved to: {out_path}")


if __name__ == "__main__":
    main()
