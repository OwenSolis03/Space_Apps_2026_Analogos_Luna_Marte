#!/usr/bin/env python3
"""Dataset explorer for raw planetary and Earth datasets on Yuca HPC.

Generates a self-contained HTML report (thumbnails, metadata, summary statistics,
histograms, and values at known ground-truth landmarks) plus Markdown and JSON summaries.
Relies solely on numpy and rasterio; PNG previews and histogram plots are synthesized
without matplotlib. For MODIS (HDF4), uses GDAL subdatasets if supported or falls back to pyhdf.

Usage (inside an HPC batch job, never on login nodes):
    python tools/explore_datasets.py --data-root /lustre/proyectos/p089/data/raw \
        --out-dir /lustre/proyectos/p089/runs/$SLURM_JOB_ID/exploracion --workers 32
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import glob
import html
import json
import math
import os
import re
import struct
import sys
import time
import traceback
import zlib
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.windows import Window

# ---------------------------------------------------------------------------
# Dataset Catalogue: Metadata, specifications, and pipeline use cases
# ---------------------------------------------------------------------------

RASTERS = [
    {
        "key": "mars_mola", "body": "Mars", "path": "mars/Mars_MGS_MOLA_DEM_mosaic_global_463m.tif",
        "title": "MOLA Elevation (Mars Global Surveyor)", "kind": "dem", "units": "m",
        "what": "Global digital elevation model of Mars at 463 m/px, measured by the MOLA laser altimeter. "
                "Elevations are relative to the martian areoid reference datum.",
        "use": "Primary topography source for Mars: derives slope, relief, and roughness for each patch.",
        "samples": [("Jezero Crater", 18.38, 77.58), ("Gale Crater", -5.4, 137.8), ("Olympus Mons", 18.65, -133.8)],
    },
    {
        "key": "mars_themis_day", "body": "Mars", "path": "mars/Mars_ODY_THEMIS_IR_Day_Mosaic_100m.tif",
        "title": "THEMIS Daytime Infrared (Mars Odyssey)", "kind": "image", "units": "raw mosaic counts",
        "what": "Global daytime thermal infrared mosaic at 100 m/px. Brighter pixels indicate higher temperatures. "
                "Values are raw mosaic brightness levels, not calibrated Kelvin temperatures.",
        "use": "Day-night thermal contrast (combined with nighttime THEMIS) as a proxy for grain size and bedrock exposure.",
        "samples": [("Jezero Crater", 18.38, 77.58), ("Gale Crater", -5.4, 137.8)],
    },
    {
        "key": "mars_themis_night", "body": "Mars", "path": "mars/Mars_MO_THEMIS-IR-Night_mosaic_60N60S_100m_v14.tif",
        "title": "THEMIS Nighttime Infrared (Mars Odyssey)", "kind": "image", "units": "raw mosaic counts",
        "what": "Nighttime thermal infrared mosaic at 100 m/px spanning 60°N to 60°S. At night, exposed bedrock "
                "retains heat and appears bright, whereas fine-grained dust cools rapidly and appears dark.",
        "use": "Provides thermal inertia proxy: best indicator for discriminating exposed bedrock from mantled dust.",
        "samples": [("Jezero Crater", 18.38, 77.58), ("Gale Crater", -5.4, 137.8)],
    },
    {
        "key": "moon_lola", "body": "Moon", "path": "moon/Lunar_LRO_LOLA_Global_LDEM_118m.tif",
        "title": "LOLA Elevation (Lunar Reconnaissance Orbiter)", "kind": "dem", "units": "m",
        "what": "Global digital elevation model of the Moon at 118 m/px, measured by the LOLA laser altimeter. "
                "Elevations are relative to a reference sphere of radius 1,737.4 km.",
        "use": "Lunar topography source for surface patches and south polar Artemis landing candidates.",
        "samples": [("Apollo 11 (Mare Tranquillitatis)", 0.674, 23.473), ("Tycho Crater", -43.31, -11.36)],
    },
    {
        "key": "moon_wac", "body": "Moon", "path": "moon/Lunar_LRO_LROC-WAC_Mosaic_global_100m_June2013.tif",
        "title": "LROC WAC Reflectance (Lunar Reconnaissance Orbiter)", "kind": "image", "units": "normalized reflectance",
        "what": "Global monochrome mosaic from the LRO Wide Angle Camera at 100 m/px. Basaltic maria appear dark "
                "while anorthositic highlands appear bright.",
        "use": "True lunar surface reflectance (replaces the uncalibrated v1 'albedo' proxy).",
        "samples": [("Apollo 11 (Mare Tranquillitatis)", 0.674, 23.473), ("Tycho Crater", -43.31, -11.36)],
    },
    {
        "key": "moon_ice_south", "body": "Moon", "path": "moon/Moon_IceFavorabilityIndex_90S000E_591mp.tif",
        "title": "Lunar South Polar Ice Favorability Index", "kind": "index", "units": "index",
        "what": "USGS index combining surface temperature, persistent shadow, and illumination models to predict "
                "near-surface water ice stability. Polar stereographic projection.",
        "use": "In-situ resource utilization (ISRU) context for south polar targets and Artemis III exploration zones.",
        "samples": [],
    },
    {
        "key": "moon_ice_north", "body": "Moon", "path": "moon/Moon_IceFavorabilityIndex_90N000E_591mp.tif",
        "title": "Lunar North Polar Ice Favorability Index", "kind": "index", "units": "index",
        "what": "USGS ice favorability model for the lunar north polar region.", "use": "Comparative analysis and ISRU context.", "samples": [],
    },
    {
        "key": "moon_clrshade_obsolete", "body": "Moon", "path": "moon/Lunar_LRO_LOLA_Albedo_Global_128ppd.tif",
        "title": "DEPRECATED: LOLA ClrShade (misnamed as 'Albedo')", "kind": "image", "units": "RGB",
        "what": "Color shaded-relief rendering downloaded erroneously as albedo in v1.",
        "use": "None: scheduled for deletion in _to_delete/.", "samples": [], "optional": True,
    },
]

EARTH_SAMPLE_TILES = [
    ("Sonoran Desert / El Pinacate", "N31", "W114"),
    ("Atacama Desert", "S24", "W070"),
    ("Himalayas", "N28", "E086"),
    ("Sahara (Algeria)", "N25", "E010"),
    ("McMurdo Dry Valleys (Antarctica)", "S78", "E162"),
    ("Iceland", "N64", "W019"),
    ("Amazon Rainforest (Vegetated Control)", "S03", "W060"),
]

TILE_RE = re.compile(r"_([NS])(\d{2})_00_([EW])(\d{3})_00_DEM")

# ---------------------------------------------------------------------------
# PNG encoding, color palettes, and SVG generation without dependencies
# ---------------------------------------------------------------------------

CMAPS = {
    "dem": [(0.0, (40, 60, 140)), (0.25, (70, 150, 170)), (0.45, (120, 180, 110)),
            (0.65, (215, 200, 120)), (0.85, (160, 110, 70)), (1.0, (250, 250, 250))],
    "gray": [(0.0, (10, 10, 10)), (1.0, (245, 245, 245))],
    "index": [(0.0, (20, 20, 60)), (0.5, (60, 120, 200)), (1.0, (230, 250, 255))],
    "ndvi": [(0.0, (120, 80, 40)), (0.3, (220, 200, 140)), (0.6, (110, 180, 80)), (1.0, (20, 90, 30))],
    "heat": [(0.0, (10, 10, 40)), (0.35, (120, 30, 110)), (0.7, (230, 100, 40)), (1.0, (250, 240, 160))],
}


def png_bytes(rgba: np.ndarray) -> bytes:
    h, w, _ = rgba.shape
    raw = b"".join(b"\x00" + rgba[i].tobytes() for i in range(h))

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b""))


def colorize(arr: np.ndarray, cmap: str, lo: float | None = None, hi: float | None = None) -> np.ndarray:
    a = arr.astype(np.float64)
    valid = np.isfinite(a)
    if lo is None or hi is None:
        if valid.any():
            lo, hi = np.percentile(a[valid], [2, 98])
        else:
            lo, hi = 0.0, 1.0
    t = np.clip((a - lo) / (hi - lo if hi > lo else 1.0), 0, 1)
    stops = CMAPS[cmap]
    xs = [s[0] for s in stops]
    out = np.zeros(a.shape + (4,), dtype=np.uint8)
    for c in range(3):
        out[..., c] = np.interp(t, xs, [s[1][c] for s in stops]).astype(np.uint8)
    out[..., 3] = np.where(valid, 255, 0)
    return out


def rgb_to_rgba(stack: np.ndarray) -> np.ndarray:
    rgb = np.moveaxis(stack[:3], 0, -1).astype(np.uint8)
    alpha = np.full(rgb.shape[:2] + (1,), 255, dtype=np.uint8)
    return np.concatenate([rgb, alpha], axis=-1)


def img_tag(rgba: np.ndarray, alt: str) -> str:
    b64 = base64.b64encode(png_bytes(rgba)).decode("ascii")
    return f'<img class="thumb" alt="{html.escape(alt)}" src="data:image/png;base64,{b64}">'


def hist_svg(values: np.ndarray, units: str) -> str:
    v = values[np.isfinite(values)]
    if v.size < 10:
        return '<p class="muted">Insufficient valid data for histogram.</p>'
    lo, hi = np.percentile(v, [0.5, 99.5])
    if hi <= lo:
        hi = lo + 1
    counts, edges = np.histogram(np.clip(v, lo, hi), bins=40, range=(lo, hi))
    w, h, pad = 420, 120, 18
    bw = (w - 2 * pad) / len(counts)
    top = counts.max() or 1
    bars = "".join(
        f'<rect x="{pad + i * bw:.1f}" y="{h - pad - (c / top) * (h - 2 * pad):.1f}" width="{max(bw - 1, 1):.1f}" '
        f'height="{(c / top) * (h - 2 * pad):.1f}" class="bar"/>' for i, c in enumerate(counts))
    return (f'<svg class="hist" viewBox="0 0 {w} {h}" role="img" aria-label="Histogram">{bars}'
            f'<text x="{pad}" y="{h - 3}" class="axis">{fmt(lo)}</text>'
            f'<text x="{w - pad}" y="{h - 3}" class="axis" text-anchor="end">{fmt(hi)} {html.escape(units)}</text></svg>')


def fmt(x) -> str:
    if x is None or (isinstance(x, float) and not math.isfinite(x)):
        return "—"
    if isinstance(x, (int, np.integer)):
        return f"{int(x):,}"
    ax = abs(float(x))
    if ax != 0 and (ax >= 1e6 or ax < 1e-3):
        return f"{float(x):.3e}"
    return f"{float(x):,.3f}".rstrip("0").rstrip(".")


def human_bytes(n: int) -> str:
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if n < 1024 or unit == "TB":
            return f"{n:.1f} {unit}" if unit != "B" else f"{n} B"
        n /= 1024
    return f"{n} B"


def stats(arr: np.ndarray) -> dict:
    v = arr[np.isfinite(arr)]
    total = arr.size
    if v.size == 0:
        return {"valid_frac": 0.0}
    p = np.percentile(v, [1, 5, 50, 95, 99])
    return {"valid_frac": round(v.size / total, 4), "min": float(v.min()), "p1": float(p[0]), "p5": float(p[1]),
            "median": float(p[2]), "p95": float(p[3]), "p99": float(p[4]), "max": float(v.max()),
            "mean": float(v.mean()), "std": float(v.std())}


def table(rows: list[tuple[str, str]]) -> str:
    return "<table>" + "".join(f"<tr><th>{html.escape(k)}</th><td>{v}</td></tr>" for k, v in rows) + "</table>"


# ---------------------------------------------------------------------------
# Planetary Rasters
# ---------------------------------------------------------------------------

def masked_read(src, out_shape, band=1) -> np.ndarray:
    arr = src.read(band, out_shape=out_shape, resampling=Resampling.average if src.count == 1 else Resampling.nearest)
    arr = arr.astype(np.float64)
    if src.nodata is not None:
        arr[np.isclose(arr, src.nodata)] = np.nan
    arr[np.abs(arr) > 1e30] = np.nan
    scale, offset = src.scales[band - 1], src.offsets[band - 1]
    if (scale not in (None, 1.0)) or (offset not in (None, 0.0)):
        arr = arr * (scale or 1.0) + (offset or 0.0)
    return arr


def sample_point(src, lat: float, lon: float):
    """Sample 3x3 median raster value (band 1) at body geodetic lat/lon coordinates."""
    try:
        from pyproj import CRS, Transformer
        crs = CRS.from_wkt(src.crs.to_wkt())
        tr = Transformer.from_crs(crs.geodetic_crs, crs, always_xy=True)
        for lon_try in (lon, lon + 360.0, lon - 360.0):
            x, y = tr.transform(lon_try, lat)
            row, col = src.index(x, y)
            if 0 <= row < src.height and 0 <= col < src.width:
                r0, c0 = max(0, row - 1), max(0, col - 1)
                win = Window(c0, r0, min(3, src.width - c0), min(3, src.height - r0))
                a = src.read(1, window=win).astype(np.float64)
                if src.nodata is not None:
                    a[np.isclose(a, src.nodata)] = np.nan
                v = float(np.nanmedian(a)) if np.isfinite(a).any() else float("nan")
                return v
        return None
    except Exception:
        return None


def explore_raster(spec: dict, data_root: str, max_px: int) -> dict:
    path = os.path.join(data_root, spec["path"])
    res = {"key": spec["key"], "body": spec["body"], "title": spec["title"], "path": path, "exists": os.path.exists(path)}
    if not res["exists"]:
        return res
    aria = os.path.exists(path + ".aria2")
    t0 = time.time()
    try:
        with rasterio.open(path) as src:
            scale = min(1.0, max_px / max(src.width, src.height))
            out_shape = (max(1, int(src.height * scale)), max(1, int(src.width * scale)))
            meta = {
                "size_bytes": os.path.getsize(path), "incomplete_aria2": aria,
                "width": src.width, "height": src.height, "bands": src.count, "dtype": src.dtypes[0],
                "nodata": src.nodata, "crs": src.crs.to_wkt()[:400] if src.crs else None,
                "crs_name": (src.crs.to_dict().get("proj") if src.crs else None),
                "res": [abs(src.res[0]), abs(src.res[1])], "bounds": list(src.bounds),
                "block_shape": list(src.block_shapes[0]), "overviews": src.overviews(1),
                "compression": src.compression.value if src.compression else None,
                "tags": {k: v for k, v in list(src.tags().items())[:12]},
                "band_tags": {k: v for k, v in list(src.tags(1).items())[:12]},
                "units": src.units[0] if src.units and src.units[0] else None,
            }
            try:
                from pyproj import CRS
                c = CRS.from_wkt(src.crs.to_wkt())
                meta["crs_name"] = c.name
                meta["radius_m"] = c.ellipsoid.semi_major_metre if c.ellipsoid else None
            except Exception:
                pass
            if src.count >= 3 and src.dtypes[0] == "uint8":
                stack = src.read([1, 2, 3], out_shape=(3,) + out_shape, resampling=Resampling.nearest)
                rgba = rgb_to_rgba(stack)
                arr = stack[0].astype(np.float64)
            else:
                arr = masked_read(src, out_shape)
                rgba = colorize(arr, {"dem": "dem", "image": "gray", "index": "index"}[spec["kind"]])
            st = stats(arr)
            samples = [(name, lat, lon, sample_point(src, lat, lon)) for name, lat, lon in spec.get("samples", [])]
        res.update({"meta": meta, "stats": st, "samples": samples, "thumb": rgba, "values": arr,
                    "seconds": round(time.time() - t0, 1)})
    except Exception as e:  # noqa: BLE001
        res["error"] = f"{type(e).__name__}: {e}"
        res["trace"] = traceback.format_exc(limit=3)
    return res


# ---------------------------------------------------------------------------
# Copernicus DEM
# ---------------------------------------------------------------------------

def tile_latlon(name: str):
    m = TILE_RE.search(name)
    if not m:
        return None
    lat = int(m.group(2)) * (1 if m.group(1) == "N" else -1)
    lon = int(m.group(4)) * (1 if m.group(3) == "E" else -1)
    return lat, lon


def check_tile(path: str):
    """Open raster tile and read a central 64x64 block. Returns (name, ok, error, file_size)."""
    name = os.path.basename(path)
    try:
        size = os.path.getsize(path)
        with rasterio.open(path) as src:
            w = Window(max(0, src.width // 2 - 32), max(0, src.height // 2 - 32), min(64, src.width), min(64, src.height))
            src.read(1, window=w)
        return name, True, None, size
    except Exception as e:  # noqa: BLE001
        return name, False, f"{type(e).__name__}: {str(e)[:150]}", None


def explore_copernicus(data_root: str, workers: int, max_px: int, validate: bool) -> dict:
    base = os.path.join(data_root, "earth")
    d = os.path.join(base, "copernicus_90m")
    res = {"key": "earth_copernicus", "body": "Earth", "title": "Copernicus DEM GLO-90 (ESA)", "exists": os.path.isdir(d)}
    if not res["exists"]:
        return res
    names = sorted(os.listdir(d))
    tifs = [n for n in names if n.endswith(".tif")]
    aria = [n for n in names if n.endswith(".aria2")]
    expected = []
    tl = os.path.join(base, "copernicus_90m_tileList.txt")
    if os.path.exists(tl):
        with open(tl, encoding="utf-8", errors="replace") as f:
            expected = [ln.strip().replace("\r", "") for ln in f if ln.strip()]
            expected = [e if e.endswith(".tif") else e + ".tif" for e in expected]
    failed_lists = sorted(glob.glob(os.path.join(base, "copernicus_90m_fallidos_*.txt")))
    failed_urls = 0
    if failed_lists:
        with open(failed_lists[-1], encoding="utf-8", errors="replace") as f:
            failed_urls = sum(1 for ln in f if ln.startswith("http"))

    bad, sizes = [], []
    if validate and tifs:
        with ProcessPoolExecutor(max_workers=workers) as ex:
            for name, ok, err, size in ex.map(check_tile, [os.path.join(d, n) for n in tifs], chunksize=64):
                if ok:
                    sizes.append(size)
                else:
                    bad.append((name, err))
    else:
        sizes = [os.path.getsize(os.path.join(d, n)) for n in tifs]

    # 1-degree coverage map: green = tile valid, red = failed to open, orange = in catalogue but missing
    cov = np.zeros((180, 360, 4), dtype=np.uint8)
    cov[..., :3] = (30, 40, 60)
    cov[..., 3] = 255
    have, bad_names = set(tifs), {b[0] for b in bad}

    def paint(name, color):
        ll = tile_latlon(name)
        if ll:
            r, c = 89 - ll[0], ll[1] + 180
            if 0 <= r < 180 and 0 <= c < 360:
                cov[r, c, :3] = color

    for n in expected:
        if n not in have:
            paint(n, (240, 150, 40))
    for n in tifs:
        paint(n, (220, 50, 50) if n in bad_names else (70, 200, 110))
    cov = np.repeat(np.repeat(cov, 3, axis=0), 3, axis=1)

    samples = []
    for label, la, lo in EARTH_SAMPLE_TILES:
        fname = f"Copernicus_DSM_COG_30_{la}_00_{lo}_00_DEM.tif"
        p = os.path.join(d, fname)
        if not os.path.exists(p):
            samples.append({"label": label, "file": fname, "exists": False})
            continue
        try:
            with rasterio.open(p) as src:
                sc = min(1.0, 300 / max(src.width, src.height))
                arr = masked_read(src, (max(1, int(src.height * sc)), max(1, int(src.width * sc))))
                full = src.read(1).astype(np.float64)
                if src.nodata is not None:
                    full[np.isclose(full, src.nodata)] = np.nan
                lat0 = src.bounds.bottom + 0.5
                dx = abs(src.res[0]) * 111320.0 * math.cos(math.radians(lat0))
                dy = abs(src.res[1]) * 111320.0
                filled = np.where(np.isfinite(full), full, np.nanmedian(full) if np.isfinite(full).any() else 0)
                gy, gx = np.gradient(filled, dy, dx)
                slope = np.degrees(np.arctan(np.hypot(gx, gy)))
                samples.append({"label": label, "file": fname, "exists": True, "shape": [src.height, src.width],
                                "res_deg": [abs(src.res[0]), abs(src.res[1])], "stats": stats(full),
                                "slope_mean": float(np.nanmean(slope)), "slope_p90": float(np.nanpercentile(slope, 90)),
                                "thumb": colorize(arr, "dem"), "values": full})
        except Exception as e:  # noqa: BLE001
            samples.append({"label": label, "file": fname, "exists": True, "error": str(e)})

    res.update({
        "n_tif": len(tifs), "n_incomplete": len(aria), "n_expected": len(expected),
        "n_missing": len([n for n in expected if n not in have]), "n_bad": len(bad), "bad": bad[:200],
        "failed_urls_last_job": failed_urls, "failed_list": failed_lists[-1] if failed_lists else None,
        "total_bytes": int(sum(sizes)), "validated": validate, "coverage": cov, "samples": samples,
    })
    return res


# ---------------------------------------------------------------------------
# MODIS (HDF4)
# ---------------------------------------------------------------------------

MODIS_SPECS = {
    "ndvi": {"title": "Monthly MODIS NDVI (MOD13C2, 0.05°)", "dir": "earth/modis/ndvi",
             "layers": {"NDVI": ("CMG 0.05 Deg Monthly NDVI", lambda a: np.where(a < -2000, np.nan, a / 10000.0))}},
    "lst": {"title": "Monthly MODIS Land Surface Temperature (MOD11C3, 0.05°)", "dir": "earth/modis/lst",
            "layers": {"LST_Day": ("LST_Day_CMG", lambda a: np.where(a == 0, np.nan, a * 0.02 - 273.15)),
                       "LST_Night": ("LST_Night_CMG", lambda a: np.where(a == 0, np.nan, a * 0.02 - 273.15))}},
}


def read_hdf4_layer(path: str, layer: str) -> tuple[np.ndarray, str]:
    try:
        with rasterio.open(path) as src:
            subs = [s for s in src.subdatasets if s.endswith(f':"{layer}"') or s.endswith(f":{layer}")]
        if subs:
            with rasterio.open(subs[0]) as sub:
                return sub.read(1).astype(np.float64), "gdal"
    except Exception:
        pass
    from pyhdf.SD import SD, SDC  # type: ignore
    f = SD(path, SDC.READ)
    try:
        return np.asarray(f.select(layer).get(), dtype=np.float64), "pyhdf"
    finally:
        f.end()


def month_of(fname: str) -> str:
    m = re.search(r"\.A(\d{4})(\d{3})\.", fname)
    if not m:
        return fname
    d = dt.date(int(m.group(1)), 1, 1) + dt.timedelta(days=int(m.group(2)) - 1)
    return d.strftime("%Y-%m")


def explore_modis(data_root: str, key: str) -> dict:
    spec = MODIS_SPECS[key]
    d = os.path.join(data_root, spec["dir"])
    files = sorted(glob.glob(os.path.join(d, "*.hdf")))
    res = {"key": f"earth_modis_{key}", "body": "Earth", "title": spec["title"], "exists": bool(files),
           "n_files": len(files), "total_bytes": int(sum(os.path.getsize(f) for f in files))}
    if not files:
        return res
    monthly, agg, backend = [], {}, None
    try:
        for f in files:
            row = {"month": month_of(os.path.basename(f)), "file": os.path.basename(f)}
            for lname, (layer, conv) in spec["layers"].items():
                raw, backend = read_hdf4_layer(f, layer)
                a = conv(raw)
                row[lname] = {"mean": float(np.nanmean(a)), "min": float(np.nanmin(a)), "max": float(np.nanmax(a))}
                if lname not in agg:
                    agg[lname] = {"max": a.copy(), "sum": np.nan_to_num(a), "n": np.isfinite(a).astype(np.int16)}
                else:
                    agg[lname]["max"] = np.fmax(agg[lname]["max"], a)
                    agg[lname]["sum"] += np.nan_to_num(a)
                    agg[lname]["n"] += np.isfinite(a)
            monthly.append(row)
    except Exception as e:  # noqa: BLE001
        res["error"] = (f"Failed to read HDF4 ({type(e).__name__}: {e}). Install HDF4 support: "
                        "`pip install pyhdf` or configure GDAL with HDF4.")
        return res
    maps = []
    if key == "ndvi":
        nmax = agg["NDVI"]["max"]
        maps.append(("Annual Maximum NDVI", nmax[::4, ::4], "ndvi", (-0.1, 0.9), stats(nmax)))
    else:
        day = agg["LST_Day"]["sum"] / np.where(agg["LST_Day"]["n"] > 0, agg["LST_Day"]["n"], np.nan)
        night = agg["LST_Night"]["sum"] / np.where(agg["LST_Night"]["n"] > 0, agg["LST_Night"]["n"], np.nan)
        amp = day - night
        maps.append(("Mean Daytime Temperature (°C)", day[::4, ::4], "heat", (-40, 50), stats(day)))
        maps.append(("Mean Nighttime Temperature (°C)", night[::4, ::4], "heat", (-50, 35), stats(night)))
        maps.append(("Day − Night Amplitude (°C)", amp[::4, ::4], "heat", (0, 30), stats(amp)))
    res.update({"monthly": monthly, "backend": backend,
                "maps": [(t, colorize(a, c, *rng), st, a) for t, a, c, rng, st in maps]})
    return res


# ---------------------------------------------------------------------------
# Vector Datasets (Natural Earth) and IAU Planetary Nomenclature
# ---------------------------------------------------------------------------

def read_dbf(path: str, max_rows: int | None = None):
    with open(path, "rb") as f:
        numrec, hdrlen, reclen = struct.unpack("<4xIHH20x", f.read(32))
        fields = []
        while True:
            b = f.read(1)
            if not b or b == b"\r":
                break
            rec = b + f.read(31)
            fields.append((rec[:11].split(b"\x00")[0].decode("ascii", "ignore"), chr(rec[11]), rec[16]))
        f.seek(hdrlen)
        rows = []
        for _ in range(numrec if max_rows is None else min(numrec, max_rows)):
            raw = f.read(reclen)
            if not raw:
                break
            pos, row = 1, {}
            for name, _t, flen in fields:
                row[name] = raw[pos:pos + flen].decode("utf-8", "replace").strip()
                pos += flen
            rows.append(row)
    return numrec, fields, rows


def shp_points(path: str, max_points: int = 400_000) -> tuple[int, str, np.ndarray]:
    """Read vertices from a .shp (Point, PolyLine, Polygon and their Z/M variants)."""
    types = {1: "Point", 3: "PolyLine", 5: "Polygon", 8: "MultiPoint", 11: "PointZ", 13: "PolyLineZ", 15: "PolygonZ"}
    pts, n = [], 0
    with open(path, "rb") as f:
        header = f.read(100)
        shape_type = struct.unpack("<i", header[32:36])[0]
        while True:
            rh = f.read(8)
            if len(rh) < 8:
                break
            _, clen = struct.unpack(">ii", rh)
            content = f.read(clen * 2)
            n += 1
            st = struct.unpack("<i", content[:4])[0]
            if st in (1, 11, 21):
                pts.append(struct.unpack("<2d", content[4:20]))
            elif st in (3, 5, 13, 15, 23, 25):
                nparts, npts = struct.unpack("<2i", content[36:44])
                off = 44 + 4 * nparts
                xy = np.frombuffer(content[off:off + 16 * npts], dtype="<f8").reshape(-1, 2)
                pts.extend(map(tuple, xy[:: max(1, npts // 200)]))
            elif st in (8, 18, 28):
                npts = struct.unpack("<i", content[36:40])[0]
                xy = np.frombuffer(content[40:40 + 16 * npts], dtype="<f8").reshape(-1, 2)
                pts.extend(map(tuple, xy))
    arr = np.array(pts, dtype=np.float64) if pts else np.zeros((0, 2))
    if len(arr) > max_points:
        arr = arr[:: len(arr) // max_points + 1]
    return n, types.get(shape_type, str(shape_type)), arr


def points_map(arr: np.ndarray, color=(250, 200, 60)) -> np.ndarray:
    img = np.zeros((360, 720, 4), dtype=np.uint8)
    img[..., :3] = (30, 40, 60)
    img[..., 3] = 255
    if len(arr):
        c = np.clip(((arr[:, 0] + 180) * 2).astype(int), 0, 719)
        r = np.clip(((90 - arr[:, 1]) * 2).astype(int), 0, 359)
        img[r, c, :3] = color
    return img


def explore_vectors(data_root: str) -> list[dict]:
    out = []
    base = os.path.join(data_root, "earth", "naturalearth")
    for layer, label, use in [
        ("ne_10m_roads", "Roads (Natural Earth 1:10m)", "Distance to nearest road: logistics for field campaigns."),
        ("ne_10m_airports", "Airports (Natural Earth 1:10m)", "Distance to nearest airport: logistics and accessibility."),
        ("ne_10m_admin_0_countries", "Admin 0 Countries (Natural Earth 1:10m)", "Assign country name to each candidate analog."),
    ]:
        shp = glob.glob(os.path.join(base, layer, "*.shp"))
        res = {"key": f"earth_{layer}", "body": "Earth", "title": label, "use": use, "exists": bool(shp)}
        if shp:
            try:
                n, stype, pts = shp_points(shp[0])
                nrec, fields, rows = read_dbf(shp[0][:-4] + ".dbf", max_rows=5)
                res.update({"n_features": n, "shape_type": stype, "fields": [f[0] for f in fields],
                            "sample_rows": rows, "map": points_map(pts)})
            except Exception as e:  # noqa: BLE001
                res["error"] = str(e)
        out.append(res)
    return out


def explore_nomenclature(data_root: str) -> list[dict]:
    out = []
    for body, pat in [("Mars", "MARS*.dbf"), ("Moon", "MOON*.dbf")]:
        files = glob.glob(os.path.join(data_root, "nomenclature", pat))
        res = {"key": f"iau_{body.lower()}", "body": body, "title": f"IAU Nomenclature for {body}", "exists": bool(files)}
        if files:
            nrec, fields, rows = read_dbf(files[0])
            tcol = next((f[0] for f in fields if f[0].lower() == "type"), None)
            counts = {}
            for r in rows:
                t = r.get(tcol, "?") if tcol else "?"
                counts[t] = counts.get(t, 0) + 1
            res.update({"file": os.path.basename(files[0]), "n_features": nrec, "fields": [f[0] for f in fields],
                        "by_type": sorted(counts.items(), key=lambda x: -x[1])[:15], "sample_rows": rows[:5]})
        out.append(res)
    return out


def explore_diviner(data_root: str) -> dict:
    d = os.path.join(data_root, "moon", "diviner")
    files = sorted(glob.glob(os.path.join(d, "*")))
    return {"key": "moon_diviner", "body": "Moon", "title": "Diviner Polar Resource Product", "exists": bool(files),
            "files": [(os.path.basename(f), os.path.getsize(f)) for f in files]}


# ---------------------------------------------------------------------------
# HTML, Markdown, and JSON Reporting
# ---------------------------------------------------------------------------

CSS = """
:root{--bg:#f7f7f5;--card:#fff;--ink:#1d1d1f;--muted:#6b6b70;--line:#e3e3e0;--accent:#2f6fde;--ok:#1f8a4c;--warn:#b26a00;--bad:#c62828;--bar:#2f6fde}
@media (prefers-color-scheme:dark){:root{--bg:#141416;--card:#1d1d20;--ink:#ececee;--muted:#9a9aa2;--line:#2e2e33;--accent:#7aa7ff;--ok:#4cc27e;--warn:#f0a43a;--bad:#ff6b6b;--bar:#7aa7ff}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,-apple-system,Segoe UI,sans-serif}
main{max-width:1180px;margin:0 auto;padding:24px 16px 64px}h1{font-size:26px;margin:0 0 4px}h2{margin:40px 0 12px;font-size:20px;border-bottom:1px solid var(--line);padding-bottom:6px}
h3{margin:0 0 6px;font-size:17px}.muted{color:var(--muted)}nav a{color:var(--accent);margin-right:14px;text-decoration:none}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px;margin:14px 0}
.grid{display:grid;grid-template-columns:minmax(0,1.1fr) minmax(0,1fr);gap:18px}@media(max-width:820px){.grid{grid-template-columns:1fr}}
.thumb{width:100%;height:auto;border-radius:6px;background:#000;image-rendering:auto}
table{border-collapse:collapse;width:100%;font-size:13px;margin:6px 0}th,td{text-align:left;padding:4px 8px;border-bottom:1px solid var(--line);vertical-align:top}
th{color:var(--muted);font-weight:500;width:38%}td code,p code{font-size:12px}.pill{display:inline-block;padding:1px 8px;border-radius:999px;font-size:12px;font-weight:600}
.ok{background:color-mix(in srgb,var(--ok) 18%,transparent);color:var(--ok)}.warn{background:color-mix(in srgb,var(--warn) 18%,transparent);color:var(--warn)}
.bad{background:color-mix(in srgb,var(--bad) 18%,transparent);color:var(--bad)}.hist{width:100%;max-width:440px}.hist .bar{fill:var(--bar)}.hist .axis{fill:var(--muted);font-size:10px}
.tiles{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:12px}.legend span{margin-right:14px;font-size:13px}
.sw{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:4px;vertical-align:middle}
pre{white-space:pre-wrap;font-size:12px;background:var(--bg);padding:8px;border-radius:6px}
"""


def status_pill(r: dict) -> str:
    if not r.get("exists"):
        return '<span class="pill bad">not found</span>'
    if r.get("error"):
        return '<span class="pill bad">read error</span>'
    m = r.get("meta", {})
    if m.get("incomplete_aria2") or r.get("n_incomplete"):
        return '<span class="pill warn">incomplete</span>'
    if r.get("n_bad"):
        return '<span class="pill warn">corrupt tiles</span>'
    return '<span class="pill ok">OK</span>'


def render_raster(r: dict, spec: dict) -> str:
    head = f'<h3>{html.escape(r["title"])} {status_pill(r)}</h3><p class="muted"><code>{html.escape(r.get("path", ""))}</code></p>'
    if not r.get("exists"):
        return f'<div class="card">{head}<p>Not found on Yuca.</p></div>'
    if r.get("error"):
        return f'<div class="card">{head}<pre>{html.escape(r["error"])}\n{html.escape(r.get("trace", ""))}</pre></div>'
    m, st = r["meta"], r["stats"]
    res_txt = f'{fmt(m["res"][0])} × {fmt(m["res"][1])}'
    meta_rows = [
        ("Description", html.escape(spec["what"])), ("Pipeline use", html.escape(spec["use"])),
        ("Disk size", human_bytes(m["size_bytes"]) + (" (with .aria2: incomplete)" if m["incomplete_aria2"] else "")),
        ("Dimensions", f'{m["width"]:,} × {m["height"]:,} px, {m["bands"]} band(s), {m["dtype"]}'),
        ("Resolution (CRS units)", res_txt), ("Coordinate reference system", html.escape(str(m.get("crs_name")))),
        ("Body radius in CRS", fmt(m.get("radius_m")) + " m" if m.get("radius_m") else "—"),
        ("Bounds (CRS)", ", ".join(fmt(b) for b in m["bounds"])), ("Nodata", fmt(m["nodata"]) if m["nodata"] is not None else "—"),
        ("Blocks / overviews / compression", f'{m["block_shape"]} / {m["overviews"] or "none"} / {m["compression"] or "—"}'),
        ("Declared units", html.escape(str(m.get("units") or spec["units"]))),
    ]
    stat_rows = [("Valid pixels", f'{st.get("valid_frac", 0) * 100:.1f} %')] + [
        (k, fmt(st.get(k))) for k in ["min", "p1", "p5", "median", "mean", "p95", "p99", "max", "std"] if k in st]
    samp = ""
    if r.get("samples"):
        samp = "<h3>Values at known landmarks</h3>" + table(
            [(f"{n} ({la:.2f}, {lo:.2f})", fmt(v) if v is not None else "outside coverage") for n, la, lo, v in r["samples"]])
    tags = ""
    if m.get("tags") or m.get("band_tags"):
        tags = "<details><summary class='muted'>File metadata</summary><pre>" + html.escape(
            json.dumps({"dataset": m.get("tags"), "band_1": m.get("band_tags")}, indent=1, ensure_ascii=False)) + "</pre></details>"
    return (f'<div class="card">{head}<div class="grid"><div>{img_tag(r["thumb"], r["title"])}'
            f'<p class="muted">Thumbnail with p2–p98 stretch. Read in {r.get("seconds")} s.</p>'
            f'{hist_svg(r["values"], spec["units"])}</div><div>{table(meta_rows)}<h3>Statistics (thumbnail)</h3>'
            f'{table(stat_rows)}{samp}{tags}</div></div></div>')


def render_copernicus(r: dict) -> str:
    head = f'<h3>{html.escape(r["title"])} {status_pill(r)}</h3>'
    if not r.get("exists"):
        return f'<div class="card">{head}<p>Not found on Yuca.</p></div>'
    rows = [
        ("Description", "ESA global digital surface model at 3 arc-seconds (~90 m), packaged in 1° × 1° tiles."),
        ("Pipeline use", "Earth topography source for planetary analog matching."),
        ("Downloaded tiles", f'{r["n_tif"]:,} of {r["n_expected"]:,} in official catalogue'),
        ("Missing from catalogue", f'{r["n_missing"]:,}'),
        ("Incomplete (.aria2)", f'{r["n_incomplete"]:,}'),
        ("Failed in latest download", f'{r["failed_urls_last_job"]:,}' + (f' (<code>{html.escape(os.path.basename(r["failed_list"]))}</code>)' if r["failed_list"] else "")),
        ("Unreadable tiles", f'{r["n_bad"]:,}' + ("" if r["validated"] else " (not validated)")),
        ("Total disk size", human_bytes(r["total_bytes"])),
    ]
    bad = ""
    if r["bad"]:
        bad = "<details><summary>Unreadable tiles</summary><pre>" + html.escape(
            "\n".join(f"{n}: {e}" for n, e in r["bad"])) + "</pre></details>"
    legend = ('<p class="legend"><span><i class="sw" style="background:#46c86e"></i>tile OK</span>'
              '<span><i class="sw" style="background:#dc3232"></i>unreadable</span>'
              '<span><i class="sw" style="background:#f09628"></i>in catalogue but missing</span>'
              '<span><i class="sw" style="background:#1e283c;border:1px solid #888"></i>no tile (ocean)</span></p>')
    tiles = []
    for s in r["samples"]:
        if not s.get("exists"):
            tiles.append(f'<div class="card"><h3>{html.escape(s["label"])}</h3><p class="muted">Not downloaded: <code>{html.escape(s["file"])}</code></p></div>')
        elif s.get("error"):
            tiles.append(f'<div class="card"><h3>{html.escape(s["label"])}</h3><pre>{html.escape(s["error"])}</pre></div>')
        else:
            st = s["stats"]
            tiles.append(f'<div class="card"><h3>{html.escape(s["label"])}</h3>{img_tag(s["thumb"], s["label"])}' + table([
                ("Elevation (m)", f'{fmt(st.get("min"))} to {fmt(st.get("max"))}, median {fmt(st.get("median"))}'),
                ("Mean / P90 slope", f'{s["slope_mean"]:.1f}° / {s["slope_p90"]:.1f}°'),
                ("Pixels", f'{s["shape"][1]} × {s["shape"][0]}'),
                ("Valid", f'{st.get("valid_frac", 0) * 100:.1f} %')]) + "</div>")
    return (f'<div class="card">{head}<div class="grid"><div>{img_tag(r["coverage"], "Copernicus Coverage")}{legend}</div>'
            f'<div>{table(rows)}{bad}</div></div></div><h3>Sample tiles</h3><div class="tiles">{"".join(tiles)}</div>')


def render_modis(r: dict) -> str:
    head = f'<h3>{html.escape(r["title"])} {status_pill(r)}</h3>'
    if not r.get("exists"):
        return f'<div class="card">{head}<p>Not found on Yuca.</p></div>'
    if r.get("error"):
        return f'<div class="card">{head}<p>{r["n_files"]} files, {human_bytes(r["total_bytes"])}.</p><pre>{html.escape(r["error"])}</pre></div>'
    maps = "".join(f'<div><h3>{html.escape(t)}</h3>{img_tag(img, t)}{table([(k, fmt(st.get(k))) for k in ["min", "median", "mean", "max"]])}</div>'
                   for t, img, st, _a in r["maps"])
    layers = [k for k in r["monthly"][0] if k not in ("month", "file")]
    mrows = "".join("<tr><td>" + m["month"] + "</td>" + "".join(
        f'<td>{fmt(m[l]["mean"])}</td>' for l in layers) + "</tr>" for m in r["monthly"])
    mtable = ("<table><tr><th>Month</th>" + "".join(f"<th>{l} (global mean)</th>" for l in layers) + "</tr>" + mrows + "</table>")
    what = ("NDVI: vegetation index (−0.2 to 1). Values < 0.1 indicate bare soil, rock, or sand; values > 0.5 indicate dense vegetation. "
            "Used as a filter mask: analog sites must be barren." if "ndvi" in r["key"] else
            "Daytime and nighttime surface temperatures (°C), monthly mean. Day-night temperature amplitude serves as "
            "the terrestrial analog of martian THEMIS thermal contrast.")
    return (f'<div class="card">{head}<p>{html.escape(what)}</p><p class="muted">{r["n_files"]} files, '
            f'{human_bytes(r["total_bytes"])}, read via {r["backend"]}.</p><div class="tiles">{maps}</div>'
            f'<details><summary>Values by month</summary>{mtable}</details></div>')


def render_vector(r: dict) -> str:
    head = f'<h3>{html.escape(r["title"])} {status_pill(r)}</h3>'
    if not r.get("exists"):
        return f'<div class="card">{head}<p>Not found on Yuca.</p></div>'
    if r.get("error"):
        return f'<div class="card">{head}<pre>{html.escape(r["error"])}</pre></div>'
    sample = "<pre>" + html.escape(json.dumps(r["sample_rows"][:3], indent=1, ensure_ascii=False)[:2500]) + "</pre>"
    return (f'<div class="card">{head}<div class="grid"><div>{img_tag(r["map"], r["title"])}</div><div>'
            + table([("Pipeline use", html.escape(r["use"])), ("Features", f'{r["n_features"]:,}'),
                     ("Geometry", r["shape_type"]), ("Columns", html.escape(", ".join(r["fields"][:40])))])
            + f'<details><summary>First rows</summary>{sample}</details></div></div></div>')


def render_nomenclature(r: dict) -> str:
    head = f'<h3>{html.escape(r["title"])} {status_pill(r)}</h3>'
    if not r.get("exists"):
        return f'<div class="card">{head}<p>Not found on Yuca.</p></div>'
    return (f'<div class="card">{head}<p>Official International Astronomical Union (IAU) feature gazetteer (<code>{html.escape(r["file"])}</code>). '
            f'Used for labeling and geodetic reference of Moon and Mars targets.</p><div class="grid"><div>'
            + table([("Named features", f'{r["n_features"]:,}'), ("Columns", html.escape(", ".join(r["fields"])))])
            + "</div><div><h3>By feature type</h3>" + table([(html.escape(t), f"{n:,}") for t, n in r["by_type"]]) + "</div></div></div>")


def render_diviner(r: dict) -> str:
    head = f'<h3>{html.escape(r["title"])} {status_pill(r)}</h3>'
    if not r.get("exists"):
        return (f'<div class="card">{head}<p>Pending download (PDS <code>LRO-L-DLRE-5-PRP-V2.0</code>, '
                f'<code>DLRE_PRP_SOUTH.TAB</code>) to <code>data/raw/moon/diviner/</code>.</p></div>')
    return f'<div class="card">{head}' + table([(html.escape(n), human_bytes(s)) for n, s in r["files"]]) + "</div>"


def strip_arrays(obj):
    if isinstance(obj, dict):
        return {k: strip_arrays(v) for k, v in obj.items() if not isinstance(v, np.ndarray)}
    if isinstance(obj, (list, tuple)):
        return [strip_arrays(v) for v in obj if not isinstance(v, np.ndarray)]
    if isinstance(obj, (np.floating, np.integer)):
        return obj.item()
    return obj


def markdown_summary(results: dict) -> str:
    lines = [f"# Dataset Exploration Summary ({results['generated_at']})", "", "| Body | Dataset | Status | Details |", "| --- | --- | --- | --- |"]

    def state(r):
        return "not found" if not r.get("exists") else ("error" if r.get("error") else (
            "incomplete" if (r.get("meta", {}).get("incomplete_aria2") or r.get("n_incomplete")) else (
                "corrupt tiles" if r.get("n_bad") else "OK")))

    for r in results["rasters"]:
        if not r.get("exists") and r.get("optional"):
            continue
        det = ""
        if r.get("meta"):
            m, st = r["meta"], r["stats"]
            det = (f'{m["width"]}×{m["height"]} px, {m["dtype"]}, {human_bytes(m["size_bytes"])}, '
                   f'valid {st.get("valid_frac", 0) * 100:.0f} %, range {fmt(st.get("p1"))} to {fmt(st.get("p99"))}')
        lines.append(f'| {r["body"]} | {r["title"]} | {state(r)} | {det or r.get("error", "")} |')
    c = results["copernicus"]
    if c.get("exists"):
        lines.append(f'| Earth | {c["title"]} | {state(c)} | {c["n_tif"]:,} tiles of {c["n_expected"]:,}; missing {c["n_missing"]:,}; '
                     f'unreadable {c["n_bad"]:,}; failed in latest run {c["failed_urls_last_job"]:,}; {human_bytes(c["total_bytes"])} |')
    for r in results["modis"]:
        det = f'{r.get("n_files", 0)} files' + (f'; {r["error"]}' if r.get("error") else "")
        lines.append(f'| Earth | {r["title"]} | {state(r)} | {det} |')
    for r in results["vectors"]:
        lines.append(f'| Earth | {r["title"]} | {state(r)} | {r.get("n_features", "")} features |')
    for r in results["nomenclature"]:
        lines.append(f'| {r["body"]} | {r["title"]} | {state(r)} | {r.get("n_features", "")} named features |')
    d = results["diviner"]
    lines.append(f'| Moon | {d["title"]} | {state(d)} | {len(d["files"])} files |')
    return "\n".join(lines) + "\n"


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--data-root", default="/lustre/proyectos/p089/data/raw")
    p.add_argument("--out-dir", required=True)
    p.add_argument("--workers", type=int, default=int(os.environ.get("SLURM_CPUS_PER_TASK", "4")))
    p.add_argument("--max-px", type=int, default=900, help="Maximum preview thumbnail width in pixels")
    p.add_argument("--no-validate-tiles", action="store_true", help="Skip opening every individual Copernicus DEM tile")
    p.add_argument("--only", choices=["planets", "copernicus", "modis", "vectors"], help="Explore only a specific subsystem")
    args = p.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    t0 = time.time()
    results = {"generated_at": dt.datetime.now().isoformat(timespec="seconds"), "data_root": args.data_root,
               "rasters": [], "copernicus": {"exists": False}, "modis": [], "vectors": [], "nomenclature": [],
               "diviner": {"exists": False, "files": [], "title": "Diviner"}}
    specs = {s["key"]: s for s in RASTERS}

    if args.only in (None, "planets"):
        for spec in RASTERS:
            print(f"[*] {spec['title']}", flush=True)
            r = explore_raster(spec, args.data_root, args.max_px)
            r["optional"] = spec.get("optional", False)
            results["rasters"].append(r)
            print(f"    -> {'OK' if r.get('meta') else r.get('error', 'not found')}", flush=True)
        results["nomenclature"] = explore_nomenclature(args.data_root)
        results["diviner"] = explore_diviner(args.data_root)
    if args.only in (None, "copernicus"):
        print("[*] Copernicus", flush=True)
        results["copernicus"] = explore_copernicus(args.data_root, args.workers, args.max_px, not args.no_validate_tiles)
        c = results["copernicus"]
        print(f"    -> {c.get('n_tif', 0)} tiles, {c.get('n_bad', 0)} unreadable", flush=True)
    if args.only in (None, "modis"):
        for key in MODIS_SPECS:
            print(f"[*] MODIS {key}", flush=True)
            results["modis"].append(explore_modis(args.data_root, key))
    if args.only in (None, "vectors"):
        print("[*] Natural Earth", flush=True)
        results["vectors"] = explore_vectors(args.data_root)

    # HTML
    by_body = {"Mars": [], "Moon": []}
    for r in results["rasters"]:
        if r.get("optional") and not r.get("exists"):
            continue
        by_body[r["body"]].append(render_raster(r, specs[r["key"]]))
    nom = {r["body"]: render_nomenclature(r) for r in results["nomenclature"]}
    sections = []
    if by_body["Mars"] or "Mars" in nom:
        sections.append('<h2 id="mars">Mars</h2>' + "".join(by_body["Mars"]) + nom.get("Mars", ""))
    if by_body["Moon"] or "Moon" in nom:
        sections.append('<h2 id="moon">Moon</h2>' + "".join(by_body["Moon"]) + nom.get("Moon", "")
                        + (render_diviner(results["diviner"]) if args.only in (None, "planets") else ""))
    earth = ""
    if results["copernicus"].get("exists") or args.only in (None, "copernicus"):
        earth += render_copernicus(results["copernicus"])
    earth += "".join(render_modis(r) for r in results["modis"]) + "".join(render_vector(r) for r in results["vectors"])
    if earth:
        sections.append('<h2 id="earth">Earth</h2>' + earth)
    doc = (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
           f'<title>Dataset Exploration</title><style>{CSS}</style></head><body><main>'
           f'<h1>Dataset Exploration</h1><p class="muted">PROTOTERRA · generated {results["generated_at"]} '
           f'on {html.escape(os.uname().nodename if hasattr(os, "uname") else "")} · {round(time.time() - t0)} s · '
           f'<code>{html.escape(args.data_root)}</code></p><nav><a href="#mars">Mars</a><a href="#moon">Moon</a><a href="#earth">Earth</a></nav>'
           + "".join(sections) + "</main></body></html>")
    with open(os.path.join(args.out_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(doc)
    with open(os.path.join(args.out_dir, "resumen.md"), "w", encoding="utf-8") as f:
        f.write(markdown_summary(results))
    with open(os.path.join(args.out_dir, "resumen.json"), "w", encoding="utf-8") as f:
        json.dump(strip_arrays(results), f, indent=1, ensure_ascii=False, default=str)
    print(f"[DONE] {args.out_dir}/index.html ({os.path.getsize(os.path.join(args.out_dir, 'index.html')) / 1e6:.1f} MB)")
    print(open(os.path.join(args.out_dir, "resumen.md"), encoding="utf-8").read())


if __name__ == "__main__":
    sys.exit(main())
