#!/usr/bin/env python3
"""Enrich planetary baselines with official IAU / USGS nomenclature (v1 script).

Reads the official IAU DBF shapefile attribute tables for Mars and the Moon, calculates
geodesic Haversine distances to nearest named features and regional landmarks (>= 30 km diameter),
and updates `output/planetary_baselines.json` with standardized geographic display labels.
"""

from __future__ import annotations

import glob
import json
import math
import os
import struct

# Celestial body volumetric mean radii in kilometers
RADIUS_KM = {"Mars": 3396.19, "Moon": 1737.40}


def read_dbf(path: str) -> list[dict[str, str]]:
    """Parse dBASE III/IV table file (.dbf) into a list of row dictionaries."""
    with open(path, "rb") as f:
        numrec, hdrlen, reclen = struct.unpack("<4xIHH20x", f.read(32))
        fields = []
        while True:
            b = f.read(1)
            if not b or b == b"\r":
                break
            rec = b + f.read(31)
            name = rec[:11].split(b"\x00")[0].decode("ascii", "ignore").lower()
            ftype = chr(rec[11])
            flen = rec[16]
            fields.append((name, ftype, flen))
        f.seek(hdrlen)
        rows = []
        for _ in range(numrec):
            raw = f.read(reclen)
            if not raw or raw[0:1] == b"*":
                continue
            pos, row = 1, {}
            for name, ftype, flen in fields:
                val = raw[pos : pos + flen].decode("utf-8", "replace").strip()
                pos += flen
                row[name] = val
            rows.append(row)
        return rows


def haversine(lat1: float, lon1: float, lat2: float, lon2: float, r: float) -> float:
    """Compute spherical Haversine distance in kilometers on a sphere of radius r."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(((lon2 - lon1 + 180.0) % 360.0) - 180.0)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2.0 * r * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))


def load_catalog(pattern: str) -> list[dict[str, object]]:
    """Load and parse IAU nomenclature features matching the specified file glob pattern."""
    files = glob.glob(pattern)
    if not files:
        return []
    feats = []
    for r in read_dbf(files[0]):
        try:
            name = r.get("name") or r.get("clean_name", "")
            lat = float(r.get("center_lat") or r.get("lat"))
            lon = float(r.get("center_lon") or r.get("lon"))
            if lon > 180.0:
                lon -= 360.0
            ftype = r.get("type", "Feature")
            diam = float(r.get("diameter") or 0.0)
            if name and math.isfinite(lat) and math.isfinite(lon):
                feats.append({"name": name, "lat": lat, "lon": lon, "type": ftype, "diam": diam})
        except (ValueError, TypeError):
            continue
    return feats


def main() -> None:
    base_path = "/lustre/proyectos/p089/output/planetary_baselines.json"
    nom_dir = "/lustre/proyectos/p089/data/raw/nomenclature"
    cats = {"Mars": load_catalog(f"{nom_dir}/MARS*.dbf"), "Moon": load_catalog(f"{nom_dir}/MOON*.dbf")}

    if not os.path.exists(base_path):
        print(f"[WARN] Baseline file not found: {base_path}")
        return

    with open(base_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    for body, bdata in data.get("targets", {}).items():
        feats = cats.get(body, [])
        if not feats:
            continue
        r = RADIUS_KM[body]
        major = [x for x in feats if x["diam"] >= 30.0] or feats
        for a in bdata.get("archetypes", []):
            near = min(feats, key=lambda x: haversine(a["lat"], a["lon"], x["lat"], x["lon"], r))
            reg = min(major, key=lambda x: haversine(a["lat"], a["lon"], x["lat"], x["lon"], r))
            dn = haversine(a["lat"], a["lon"], near["lat"], near["lon"], r)
            dr = haversine(a["lat"], a["lon"], reg["lat"], reg["lon"], r)
            a["iau_nomenclature"] = {
                "nearest_feature": near["name"],
                "feature_type": near["type"],
                "distance_km": round(dn, 1),
                "regional_landmark": reg["name"],
                "regional_type": reg["type"],
                "regional_distance_km": round(dr, 1),
                "display_label": f"{near['name']} ({near['type']})" if dn < 80 else f"Near {reg['name']} ({reg['type']})",
            }
        print(f"[OK] {body}: {len(bdata['archetypes'])} archetypes labeled with {len(feats)} IAU features.")

    with open(base_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
