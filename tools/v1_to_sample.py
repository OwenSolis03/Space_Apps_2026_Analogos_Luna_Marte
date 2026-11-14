"""Convierte output/analogs.json (v1) al esquema v2 de la app (docs/plan_implementacion.md, seccion 5).

Es un puente mientras T7/T8 no existan: los sub_scores se calculan aqui con un kernel RBF
provisional sobre las cuatro metricas que tiene la v1 (pendiente media, P90, sigma de elevacion
y TRI). Ambiente y termico quedan en null porque la v1 no los tiene.

Uso:  python tools/v1_to_sample.py [entrada] [salida]
"""
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "output" / "analogs.json"
DST = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "app" / "public" / "data" / "sample.json"

# v1 -> nombre v2 del rasgo, dimension a la que pertenece y sigma provisional
# (relativo al valor del blanco, con un minimo absoluto para terrenos planos).
FEATURES = {
    "mean_slope_deg": ("mean_slope_deg", "topography", 0.35, 1.5),
    "p90_slope_deg": ("p90_slope_deg", "topography", 0.35, 2.5),
    "roughness_std_m": ("detrended_std_m", "roughness", 0.35, 30.0),
    "tri": ("tri_m", "roughness", 0.35, 25.0),
}

PRESETS = {
    "mobility_and_traction": {
        "label": "Rover mobility and traction",
        "weights": {"topography": 0.45, "roughness": 0.40, "environment": 0.15, "thermal": 0},
    },
    "landing_site": {
        "label": "Landing and plains operations",
        "weights": {"topography": 0.70, "roughness": 0.30, "environment": 0, "thermal": 0},
    },
    "hazard_navigation": {
        "label": "Rough-terrain navigation",
        "weights": {"topography": 0.30, "roughness": 0.60, "environment": 0.10, "thermal": 0},
    },
}

# Texto provisional; T11 (pipeline/data/limits.json, P3) lo reemplaza con fuentes revisadas.
FACT_SHEET = {
    "Moon": "https://nssdc.gsfc.nasa.gov/planetary/factsheet/moonfact.html",
    "Mars": "https://nssdc.gsfc.nasa.gov/planetary/factsheet/marsfact.html",
}
LIMITS = {
    "Moon": [
        ("gravity", "1 g", "0.166 g", "Traction, wheel sinkage and regolith dynamics change completely."),
        ("atmosphere", "1013 hPa", "vacuum", "No wind erosion or convection; dust charges up and sticks electrostatically."),
        ("radiation", "magnetosphere", "no shield", "Direct exposure to solar wind and cosmic rays."),
        ("thermal_cycle", "~20 °C daily", "~120 °C to -170 °C", "Extreme thermal cycling; permanently shadowed craters drop below -230 °C."),
        ("polar_lighting", "high sun", "grazing sun", "Long shadows and extreme contrast that Earth terrain cannot reproduce."),
    ],
    "Mars": [
        ("gravity", "1 g", "0.38 g", "Wheel sinkage and the angle of repose of loose material change."),
        ("pressure", "1013 hPa", "~6 hPa", "Wind drag and the saltation threshold are not comparable."),
        ("radiation", "magnetosphere", "no global shield", "Cosmic rays and solar particles reach the surface."),
        ("thermal_cycle", "~20 °C daily", "~80-100 °C daily", "Thermal fatigue of materials and batteries."),
        ("elevation_datum", "sea level", "areoid", "Absolute height is not comparable, so it is left out of the index."),
    ],
}


def rbf(t, e, rel, floor):
    s = max(floor, abs(t) * rel)
    return math.exp(-((t - e) ** 2) / (2 * s * s))


def main():
    v1 = json.loads(SRC.read_text(encoding="utf-8"))
    targets = []
    for body, clusters in v1["targets"].items():
        # desviaciones por rasgo (blancos y analogos juntos) para marcar "donde se rompe"
        pool = {k: [] for k in FEATURES}
        for c in clusters:
            for k in FEATURES:
                pool[k].append(c["target_metrics"][k])
                pool[k] += [a["metrics"][k] for a in c["top_earth_analogs"]]
        sd = {}
        for k, vals in pool.items():
            m = sum(vals) / len(vals)
            sd[k] = math.sqrt(sum((v - m) ** 2 for v in vals) / len(vals)) or 1.0

        for c in clusters:
            tm = c["target_metrics"]
            analogs = []
            for a in c["top_earth_analogs"]:
                am = a["metrics"]
                dims = {"topography": [], "roughness": []}
                mismatches = []
                for k, (name, dim, rel, floor) in FEATURES.items():
                    dims[dim].append(rbf(tm[k], am[k], rel, floor))
                    z = (am[k] - tm[k]) / sd[k]
                    if abs(z) > 1.5:
                        mismatches.append({"feature": name, "earth": am[k], "target": tm[k], "z_diff": round(z, 2)})
                sub = {d: round(sum(v) / len(v), 3) for d, v in dims.items()}
                sub.update({"environment": None, "thermal": None})
                msi = {}
                for pid, p in PRESETS.items():
                    w = {d: x for d, x in p["weights"].items() if sub.get(d) is not None}
                    tot = sum(w.values()) or 1
                    msi[pid] = round(sum(sub[d] * x for d, x in w.items()) / tot, 3)
                analogs.append({
                    "id": f"earth-{a['lat']:.4f}-{a['lon']:.4f}",
                    "lat": round(a["lat"], 4),
                    "lon": round(a["lon"], 4),
                    "country": None,
                    "classification": "NEW_CANDIDATE",
                    "known_region": None,
                    "v1_similarity": a["similarity_score"],
                    "sub_scores": sub,
                    "msi_by_preset": msi,
                    "features": {FEATURES[k][0]: am[k] for k in FEATURES} | {"mean_elev_m": am["mean_elev_m"]},
                    "earth_env": None,
                    "logistics": None,
                    "mismatches": mismatches,
                    "source_tile": a.get("tile"),
                })
            nom = c["iau_nomenclature"]
            targets.append({
                "id": c["cluster_id"],
                "type": "CLUSTER",
                "body": body,
                "name": nom["display_label"].replace(" (", " · ").rstrip(")"),
                "lat": round(c["target_coords"]["lat"], 4),
                "lon": round(c["target_coords"]["lon"], 4),
                "category": nom.get("regional_type") or nom.get("feature_type"),
                "why": None,
                "source_url": None,
                "iau_label": nom["display_label"],
                "features": {FEATURES[k][0]: tm[k] for k in FEATURES} | {"mean_elev_m": tm["mean_elev_m"]},
                "aux": {k: v for k, v in tm.items() if k not in FEATURES and k != "mean_elev_m"},
                "analogs": analogs,
            })

    out = {
        "metadata": {
            "version": "2.0.0-sample",
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "source": "output/analogs.json (v1) converted with tools/v1_to_sample.py",
            "slurm_job_id": None,
            "earth_patches_evaluated": v1.get("earth_sites_evaluated"),
            "datasets": [
                {"name": "Copernicus DEM GLO-30", "source": "ESA", "url": "https://dataspace.copernicus.eu/explore-data/data-collections/copernicus-contributing-missions/collections-description/COP-DEM"},
                {"name": "MOLA-HRSC Blended DEM", "source": "NASA / ESA", "url": "https://astrogeology.usgs.gov/search/map/mars_mgs_mola_mex_hrsc_blended_dem_global_200m"},
                {"name": "LRO LOLA LDEM 118 m", "source": "NASA", "url": "https://astrogeology.usgs.gov/search/map/moon_lro_lola_dem_118m"},
                {"name": "IAU planetary nomenclature", "source": "USGS", "url": "https://planetarynames.wr.usgs.gov/"},
            ],
        },
        "mission_presets": PRESETS,
        "limits": {
            body: [{"factor": f, "earth": e, "target": t, "consequence": c, "source": FACT_SHEET[body]} for f, e, t, c in rows]
            for body, rows in LIMITS.items()
        },
        "targets": targets,
    }
    DST.parent.mkdir(parents=True, exist_ok=True)
    DST.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{DST}: {len(targets)} blancos, {DST.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
