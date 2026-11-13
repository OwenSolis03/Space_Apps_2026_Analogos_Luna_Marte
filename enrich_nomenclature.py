#!/usr/bin/env python3
import os, struct, json, math, glob

RADIUS_KM = {"Mars": 3396.19, "Moon": 1737.40}

def read_dbf(path):
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
                val = raw[pos:pos+flen].decode("utf-8", "replace").strip()
                pos += flen
                row[name] = val
            rows.append(row)
        return rows

def haversine(lat1, lon1, lat2, lon2, r):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(((lon2 - lon1 + 180.0) % 360.0) - 180.0)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2.0 * r * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))
def load_catalog(pattern):
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

base_path = "/lustre/proyectos/p089/output/planetary_baselines.json"
nom_dir = "/lustre/proyectos/p089/data/raw/nomenclature"
cats = {"Mars": load_catalog(f"{nom_dir}/MARS*.dbf"), "Moon": load_catalog(f"{nom_dir}/MOON*.dbf")}

with open(base_path, "r", encoding="utf-8") as f:
    data = json.load(f)

for body, bdata in data["targets"].items():
    feats = cats[body]
    r = RADIUS_KM[body]
    major = [x for x in feats if x["diam"] >= 30.0] or feats
    for a in bdata["archetypes"]:
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
            "display_label": f"{near['name']} ({near['type']})" if dn < 80 else f"Near {reg['name']} ({reg['type']})"
        }
    print(f"[OK] {body}: {len(bdata['archetypes'])} arquetipos nombrados con {len(feats)} rasgos IAU.")

with open(base_path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
