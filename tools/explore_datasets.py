#!/usr/bin/env python3
"""Explorador de los datasets descargados en Yuca.

Genera un reporte HTML autocontenido (miniaturas, metadatos, estadísticas, histogramas y valores en
sitios conocidos) más un resumen en Markdown y en JSON. Solo depende de numpy y rasterio; las
imágenes PNG y las gráficas se generan sin matplotlib. Para MODIS (HDF4) usa GDAL si lo soporta y,
si no, pyhdf.

Uso (dentro de un job, nunca en el login node):
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
# Catálogo: qué es cada dataset y para qué lo usamos
# ---------------------------------------------------------------------------

RASTERS = [
    {
        "key": "mars_mola", "body": "Marte", "path": "mars/Mars_MGS_MOLA_DEM_mosaic_global_463m.tif",
        "title": "Elevación MOLA (Mars Global Surveyor)", "kind": "dem", "units": "m",
        "what": "Modelo digital de elevación global de Marte a 463 m/px, medido con el altímetro láser MOLA. "
                "Las alturas son relativas al areoide (el 'nivel del mar' marciano).",
        "use": "Fuente de la topografía de Marte: pendientes, relieve y rugosidad de cada parche.",
        "samples": [("Cráter Jezero", 18.38, 77.58), ("Cráter Gale", -5.4, 137.8), ("Olympus Mons", 18.65, -133.8)],
    },
    {
        "key": "mars_themis_day", "body": "Marte", "path": "mars/Mars_ODY_THEMIS_IR_Day_Mosaic_100m.tif",
        "title": "THEMIS infrarrojo de día (Mars Odyssey)", "kind": "image", "units": "valor crudo del mosaico",
        "what": "Mosaico global de imágenes infrarrojas térmicas de día a 100 m/px. Lo brillante está más caliente. "
                "Los valores son niveles de gris del mosaico, no temperaturas en kelvin.",
        "use": "Contraste térmico día-noche (junto con THEMIS de noche) como proxy de tamaño de grano y roca.",
        "samples": [("Cráter Jezero", 18.38, 77.58), ("Cráter Gale", -5.4, 137.8)],
    },
    {
        "key": "mars_themis_night", "body": "Marte", "path": "mars/Mars_MO_THEMIS-IR-Night_mosaic_60N60S_100m_v14.tif",
        "title": "THEMIS infrarrojo de noche (Mars Odyssey)", "kind": "image", "units": "valor crudo del mosaico",
        "what": "Mosaico infrarrojo térmico de noche a 100 m/px, solo entre 60°N y 60°S. De noche, la roca expuesta "
                "conserva calor y se ve brillante; el polvo fino se enfría y se ve oscuro.",
        "use": "Con el de día da la amplitud térmica; de noche es el mejor indicador de roca contra polvo.",
        "samples": [("Cráter Jezero", 18.38, 77.58), ("Cráter Gale", -5.4, 137.8)],
    },
    {
        "key": "moon_lola", "body": "Luna", "path": "moon/Lunar_LRO_LOLA_Global_LDEM_118m.tif",
        "title": "Elevación LOLA (Lunar Reconnaissance Orbiter)", "kind": "dem", "units": "m",
        "what": "Modelo digital de elevación global de la Luna a 118 m/px, medido con el altímetro láser LOLA. "
                "Alturas relativas a una esfera de 1737.4 km.",
        "use": "Fuente de la topografía lunar para los parches y para los blancos del polo sur.",
        "samples": [("Apolo 11 (Mar de la Tranquilidad)", 0.674, 23.473), ("Cráter Tycho", -43.31, -11.36)],
    },
    {
        "key": "moon_wac", "body": "Luna", "path": "moon/Lunar_LRO_LROC-WAC_Mosaic_global_100m_June2013.tif",
        "title": "Reflectancia LROC WAC (Lunar Reconnaissance Orbiter)", "kind": "image", "units": "reflectancia normalizada",
        "what": "Mosaico global de la cámara gran angular de LRO a 100 m/px. Los mares (basalto) se ven oscuros y "
                "las tierras altas (anortosita) claras.",
        "use": "Reflectancia real de la superficie lunar (reemplaza al falso 'albedo' de la v1).",
        "samples": [("Apolo 11 (Mar de la Tranquilidad)", 0.674, 23.473), ("Cráter Tycho", -43.31, -11.36)],
    },
    {
        "key": "moon_ice_south", "body": "Luna", "path": "moon/Moon_IceFavorabilityIndex_90S000E_591mp.tif",
        "title": "Índice de favorabilidad de hielo, polo sur", "kind": "index", "units": "índice",
        "what": "Índice de USGS que combina temperatura, sombra e iluminación para estimar dónde es más probable "
                "encontrar hielo de agua cerca de la superficie. Proyección polar.",
        "use": "Contexto de recursos (ISRU) para los blancos del polo sur y las regiones de Artemis III.",
        "samples": [],
    },
    {
        "key": "moon_ice_north", "body": "Luna", "path": "moon/Moon_IceFavorabilityIndex_90N000E_591mp.tif",
        "title": "Índice de favorabilidad de hielo, polo norte", "kind": "index", "units": "índice",
        "what": "Mismo índice para el polo norte lunar.", "use": "Comparación y contexto.", "samples": [],
    },
    {
        "key": "moon_clrshade_obsolete", "body": "Luna", "path": "moon/Lunar_LRO_LOLA_Albedo_Global_128ppd.tif",
        "title": "OBSOLETO: LOLA ClrShade (mal nombrado como 'Albedo')", "kind": "image", "units": "RGB",
        "what": "Relieve sombreado a color. Se bajó por error con nombre de albedo en la v1.",
        "use": "Ninguno: mover a _to_delete/.", "samples": [], "optional": True,
    },
]

EARTH_SAMPLE_TILES = [
    ("Desierto de Sonora / El Pinacate", "N31", "W114"),
    ("Desierto de Atacama", "S24", "W070"),
    ("Himalaya", "N28", "E086"),
    ("Sahara (Argelia)", "N25", "E010"),
    ("Valles Secos de McMurdo (Antártida)", "S78", "E162"),
    ("Islandia", "N64", "W019"),
    ("Amazonía (control con vegetación)", "S03", "W060"),
]

TILE_RE = re.compile(r"_([NS])(\d{2})_00_([EW])(\d{3})_00_DEM")

# ---------------------------------------------------------------------------
# PNG, colores y SVG sin dependencias
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
        return '<p class="muted">Sin datos suficientes para histograma.</p>'
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
    return (f'<svg class="hist" viewBox="0 0 {w} {h}" role="img" aria-label="Histograma">{bars}'
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
# Rasters planetarios
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
    """Valor del raster (banda 1, mediana 3x3) en una coordenada lat/lon del propio cuerpo."""
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
# Copernicus
# ---------------------------------------------------------------------------

def tile_latlon(name: str):
    m = TILE_RE.search(name)
    if not m:
        return None
    lat = int(m.group(2)) * (1 if m.group(1) == "N" else -1)
    lon = int(m.group(4)) * (1 if m.group(3) == "E" else -1)
    return lat, lon


def check_tile(path: str):
    """Abre el tile y lee un bloque central de 64x64. Devuelve (nombre, ok, error, tamaño)."""
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
    res = {"key": "earth_copernicus", "body": "Tierra", "title": "Copernicus DEM GLO-90 (ESA)", "exists": os.path.isdir(d)}
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

    # Mapa de cobertura 1°: verde = tile OK, rojo = no abre, naranja = en la lista pero falta
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
    "ndvi": {"title": "MODIS NDVI mensual (MOD13C2, 0.05°)", "dir": "earth/modis/ndvi",
             "layers": {"NDVI": ("CMG 0.05 Deg Monthly NDVI", lambda a: np.where(a < -2000, np.nan, a / 10000.0))}},
    "lst": {"title": "MODIS temperatura superficial mensual (MOD11C3, 0.05°)", "dir": "earth/modis/lst",
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
    res = {"key": f"earth_modis_{key}", "body": "Tierra", "title": spec["title"], "exists": bool(files),
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
        res["error"] = (f"No se pudo leer HDF4 ({type(e).__name__}: {e}). Instalar soporte: "
                        "`pip install pyhdf` en el entorno, o GDAL con HDF4.")
        return res
    maps = []
    if key == "ndvi":
        nmax = agg["NDVI"]["max"]
        maps.append(("NDVI máximo anual", nmax[::4, ::4], "ndvi", (-0.1, 0.9), stats(nmax)))
    else:
        day = agg["LST_Day"]["sum"] / np.where(agg["LST_Day"]["n"] > 0, agg["LST_Day"]["n"], np.nan)
        night = agg["LST_Night"]["sum"] / np.where(agg["LST_Night"]["n"] > 0, agg["LST_Night"]["n"], np.nan)
        amp = day - night
        maps.append(("Temperatura media de día (°C)", day[::4, ::4], "heat", (-40, 50), stats(day)))
        maps.append(("Temperatura media de noche (°C)", night[::4, ::4], "heat", (-50, 35), stats(night)))
        maps.append(("Amplitud día − noche (°C)", amp[::4, ::4], "heat", (0, 30), stats(amp)))
    res.update({"monthly": monthly, "backend": backend,
                "maps": [(t, colorize(a, c, *rng), st, a) for t, a, c, rng, st in maps]})
    return res


# ---------------------------------------------------------------------------
# Vectores (Natural Earth) y nomenclatura IAU
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
    """Lee vértices de un .shp (Point, PolyLine, Polygon y sus variantes Z/M)."""
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
        ("ne_10m_roads", "Carreteras (Natural Earth 1:10m)", "Distancia a carretera: logística de campañas de campo."),
        ("ne_10m_airports", "Aeropuertos (Natural Earth 1:10m)", "Distancia a aeropuerto: logística."),
        ("ne_10m_admin_0_countries", "Países (Natural Earth 1:10m)", "Llenar el país de cada análogo."),
    ]:
        shp = glob.glob(os.path.join(base, layer, "*.shp"))
        res = {"key": f"earth_{layer}", "body": "Tierra", "title": label, "use": use, "exists": bool(shp)}
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
    for body, pat in [("Marte", "MARS*.dbf"), ("Luna", "MOON*.dbf")]:
        files = glob.glob(os.path.join(data_root, "nomenclature", pat))
        res = {"key": f"iau_{body}", "body": body, "title": f"Nomenclatura IAU de {body}", "exists": bool(files)}
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
    return {"key": "moon_diviner", "body": "Luna", "title": "Diviner Polar Resource Product", "exists": bool(files),
            "files": [(os.path.basename(f), os.path.getsize(f)) for f in files]}


# ---------------------------------------------------------------------------
# Reporte
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
        return '<span class="pill bad">no encontrado</span>'
    if r.get("error"):
        return '<span class="pill bad">error al leer</span>'
    m = r.get("meta", {})
    if m.get("incomplete_aria2") or r.get("n_incomplete"):
        return '<span class="pill warn">incompleto</span>'
    if r.get("n_bad"):
        return '<span class="pill warn">con tiles dañados</span>'
    return '<span class="pill ok">OK</span>'


def render_raster(r: dict, spec: dict) -> str:
    head = f'<h3>{html.escape(r["title"])} {status_pill(r)}</h3><p class="muted"><code>{html.escape(r.get("path", ""))}</code></p>'
    if not r.get("exists"):
        return f'<div class="card">{head}<p>No está en Yuca.</p></div>'
    if r.get("error"):
        return f'<div class="card">{head}<pre>{html.escape(r["error"])}\n{html.escape(r.get("trace", ""))}</pre></div>'
    m, st = r["meta"], r["stats"]
    res_txt = f'{fmt(m["res"][0])} × {fmt(m["res"][1])}'
    meta_rows = [
        ("Qué es", html.escape(spec["what"])), ("Para qué lo usamos", html.escape(spec["use"])),
        ("Tamaño en disco", human_bytes(m["size_bytes"]) + (" (con .aria2: incompleto)" if m["incomplete_aria2"] else "")),
        ("Dimensiones", f'{m["width"]:,} × {m["height"]:,} px, {m["bands"]} banda(s), {m["dtype"]}'),
        ("Resolución (unidades del CRS)", res_txt), ("Sistema de referencia", html.escape(str(m.get("crs_name")))),
        ("Radio del cuerpo en el CRS", fmt(m.get("radius_m")) + " m" if m.get("radius_m") else "—"),
        ("Límites (CRS)", ", ".join(fmt(b) for b in m["bounds"])), ("Nodata", fmt(m["nodata"]) if m["nodata"] is not None else "—"),
        ("Bloques / overviews / compresión", f'{m["block_shape"]} / {m["overviews"] or "ninguno"} / {m["compression"] or "—"}'),
        ("Unidades declaradas", html.escape(str(m.get("units") or spec["units"]))),
    ]
    stat_rows = [("Píxeles válidos", f'{st.get("valid_frac", 0) * 100:.1f} %')] + [
        (k, fmt(st.get(k))) for k in ["min", "p1", "p5", "median", "mean", "p95", "p99", "max", "std"] if k in st]
    samp = ""
    if r.get("samples"):
        samp = "<h3>Valores en sitios conocidos</h3>" + table(
            [(f"{n} ({la:.2f}, {lo:.2f})", fmt(v) if v is not None else "fuera de cobertura") for n, la, lo, v in r["samples"]])
    tags = ""
    if m.get("tags") or m.get("band_tags"):
        tags = "<details><summary class='muted'>Metadatos del archivo</summary><pre>" + html.escape(
            json.dumps({"dataset": m.get("tags"), "banda_1": m.get("band_tags")}, indent=1, ensure_ascii=False)) + "</pre></details>"
    return (f'<div class="card">{head}<div class="grid"><div>{img_tag(r["thumb"], r["title"])}'
            f'<p class="muted">Miniatura con estiramiento p2–p98. Leído en {r.get("seconds")} s.</p>'
            f'{hist_svg(r["values"], spec["units"])}</div><div>{table(meta_rows)}<h3>Estadísticas (miniatura)</h3>'
            f'{table(stat_rows)}{samp}{tags}</div></div></div>')


def render_copernicus(r: dict) -> str:
    head = f'<h3>{html.escape(r["title"])} {status_pill(r)}</h3>'
    if not r.get("exists"):
        return f'<div class="card">{head}<p>No está en Yuca.</p></div>'
    rows = [
        ("Qué es", "Modelo digital de superficie global de ESA a 3 segundos de arco (~90 m), en tiles de 1° × 1°."),
        ("Para qué lo usamos", "Topografía de la Tierra para buscar análogos."),
        ("Tiles descargados", f'{r["n_tif"]:,} de {r["n_expected"]:,} en la lista oficial'),
        ("Faltan de la lista", f'{r["n_missing"]:,}'),
        ("Incompletos (.aria2)", f'{r["n_incomplete"]:,}'),
        ("Fallidos en la última descarga", f'{r["failed_urls_last_job"]:,}' + (f' (<code>{html.escape(os.path.basename(r["failed_list"]))}</code>)' if r["failed_list"] else "")),
        ("Tiles que no abren", f'{r["n_bad"]:,}' + ("" if r["validated"] else " (no se validó)")),
        ("Tamaño total", human_bytes(r["total_bytes"])),
    ]
    bad = ""
    if r["bad"]:
        bad = "<details><summary>Tiles que no abren</summary><pre>" + html.escape(
            "\n".join(f"{n}: {e}" for n, e in r["bad"])) + "</pre></details>"
    legend = ('<p class="legend"><span><i class="sw" style="background:#46c86e"></i>tile OK</span>'
              '<span><i class="sw" style="background:#dc3232"></i>no abre</span>'
              '<span><i class="sw" style="background:#f09628"></i>en la lista pero falta</span>'
              '<span><i class="sw" style="background:#1e283c;border:1px solid #888"></i>sin tile (océano)</span></p>')
    tiles = []
    for s in r["samples"]:
        if not s.get("exists"):
            tiles.append(f'<div class="card"><h3>{html.escape(s["label"])}</h3><p class="muted">No descargado: <code>{html.escape(s["file"])}</code></p></div>')
        elif s.get("error"):
            tiles.append(f'<div class="card"><h3>{html.escape(s["label"])}</h3><pre>{html.escape(s["error"])}</pre></div>')
        else:
            st = s["stats"]
            tiles.append(f'<div class="card"><h3>{html.escape(s["label"])}</h3>{img_tag(s["thumb"], s["label"])}' + table([
                ("Elevación (m)", f'{fmt(st.get("min"))} a {fmt(st.get("max"))}, mediana {fmt(st.get("median"))}'),
                ("Pendiente media / p90", f'{s["slope_mean"]:.1f}° / {s["slope_p90"]:.1f}°'),
                ("Píxeles", f'{s["shape"][1]} × {s["shape"][0]}'),
                ("Válidos", f'{st.get("valid_frac", 0) * 100:.1f} %')]) + "</div>")
    return (f'<div class="card">{head}<div class="grid"><div>{img_tag(r["coverage"], "Cobertura de Copernicus")}{legend}</div>'
            f'<div>{table(rows)}{bad}</div></div></div><h3>Tiles de muestra</h3><div class="tiles">{"".join(tiles)}</div>')


def render_modis(r: dict) -> str:
    head = f'<h3>{html.escape(r["title"])} {status_pill(r)}</h3>'
    if not r.get("exists"):
        return f'<div class="card">{head}<p>No está en Yuca.</p></div>'
    if r.get("error"):
        return f'<div class="card">{head}<p>{r["n_files"]} archivos, {human_bytes(r["total_bytes"])}.</p><pre>{html.escape(r["error"])}</pre></div>'
    maps = "".join(f'<div><h3>{html.escape(t)}</h3>{img_tag(img, t)}{table([(k, fmt(st.get(k))) for k in ["min", "median", "mean", "max"]])}</div>'
                   for t, img, st, _a in r["maps"])
    layers = [k for k in r["monthly"][0] if k not in ("month", "file")]
    mrows = "".join("<tr><td>" + m["month"] + "</td>" + "".join(
        f'<td>{fmt(m[l]["mean"])}</td>' for l in layers) + "</tr>" for m in r["monthly"])
    mtable = ("<table><tr><th>Mes</th>" + "".join(f"<th>{l} (media global)</th>" for l in layers) + "</tr>" + mrows + "</table>")
    what = ("NDVI: índice de vegetación (−0.2 a 1). Menos de 0.1 es suelo desnudo, roca o arena; más de 0.5 es vegetación densa. "
            "Lo usamos como máscara: los análogos deben estar en zonas sin vegetación." if "ndvi" in r["key"] else
            "Temperatura de la superficie de día y de noche (°C), media mensual. La amplitud día − noche es el equivalente "
            "terrestre del contraste térmico de THEMIS en Marte.")
    return (f'<div class="card">{head}<p>{html.escape(what)}</p><p class="muted">{r["n_files"]} archivos, '
            f'{human_bytes(r["total_bytes"])}, leídos con {r["backend"]}.</p><div class="tiles">{maps}</div>'
            f'<details><summary>Valores por mes</summary>{mtable}</details></div>')


def render_vector(r: dict) -> str:
    head = f'<h3>{html.escape(r["title"])} {status_pill(r)}</h3>'
    if not r.get("exists"):
        return f'<div class="card">{head}<p>No está en Yuca.</p></div>'
    if r.get("error"):
        return f'<div class="card">{head}<pre>{html.escape(r["error"])}</pre></div>'
    sample = "<pre>" + html.escape(json.dumps(r["sample_rows"][:3], indent=1, ensure_ascii=False)[:2500]) + "</pre>"
    return (f'<div class="card">{head}<div class="grid"><div>{img_tag(r["map"], r["title"])}</div><div>'
            + table([("Para qué lo usamos", html.escape(r["use"])), ("Elementos", f'{r["n_features"]:,}'),
                     ("Geometría", r["shape_type"]), ("Columnas", html.escape(", ".join(r["fields"][:40])))])
            + f'<details><summary>Primeras filas</summary>{sample}</details></div></div></div>')


def render_nomenclature(r: dict) -> str:
    head = f'<h3>{html.escape(r["title"])} {status_pill(r)}</h3>'
    if not r.get("exists"):
        return f'<div class="card">{head}<p>No está en Yuca.</p></div>'
    return (f'<div class="card">{head}<p>Catálogo oficial de nombres de la Unión Astronómica Internacional (<code>{html.escape(r["file"])}</code>). '
            f'Lo usamos para ponerle nombre a cada sitio de la Luna o Marte.</p><div class="grid"><div>'
            + table([("Rasgos con nombre", f'{r["n_features"]:,}'), ("Columnas", html.escape(", ".join(r["fields"])))])
            + "</div><div><h3>Por tipo</h3>" + table([(html.escape(t), f"{n:,}") for t, n in r["by_type"]]) + "</div></div></div>")


def render_diviner(r: dict) -> str:
    head = f'<h3>{html.escape(r["title"])} {status_pill(r)}</h3>'
    if not r.get("exists"):
        return (f'<div class="card">{head}<p>Pendiente de descarga manual (PDS <code>LRO-L-DLRE-5-PRP-V2.0</code>, '
                f'<code>DLRE_PRP_SOUTH.TAB</code>) a <code>data/raw/moon/diviner/</code>.</p></div>')
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
    lines = [f"# Exploración de datasets ({results['generated_at']})", "", "| Cuerpo | Dataset | Estado | Detalle |", "| --- | --- | --- | --- |"]

    def state(r):
        return "no encontrado" if not r.get("exists") else ("error" if r.get("error") else (
            "incompleto" if (r.get("meta", {}).get("incomplete_aria2") or r.get("n_incomplete")) else (
                "con tiles dañados" if r.get("n_bad") else "OK")))

    for r in results["rasters"]:
        if not r.get("exists") and r.get("optional"):
            continue
        det = ""
        if r.get("meta"):
            m, st = r["meta"], r["stats"]
            det = (f'{m["width"]}×{m["height"]} px, {m["dtype"]}, {human_bytes(m["size_bytes"])}, '
                   f'válidos {st.get("valid_frac", 0) * 100:.0f} %, rango {fmt(st.get("p1"))} a {fmt(st.get("p99"))}')
        lines.append(f'| {r["body"]} | {r["title"]} | {state(r)} | {det or r.get("error", "")} |')
    c = results["copernicus"]
    if c.get("exists"):
        lines.append(f'| Tierra | {c["title"]} | {state(c)} | {c["n_tif"]:,} tiles de {c["n_expected"]:,}; faltan {c["n_missing"]:,}; '
                     f'no abren {c["n_bad"]:,}; fallidos última descarga {c["failed_urls_last_job"]:,}; {human_bytes(c["total_bytes"])} |')
    for r in results["modis"]:
        det = f'{r.get("n_files", 0)} archivos' + (f'; {r["error"]}' if r.get("error") else "")
        lines.append(f'| Tierra | {r["title"]} | {state(r)} | {det} |')
    for r in results["vectors"]:
        lines.append(f'| Tierra | {r["title"]} | {state(r)} | {r.get("n_features", "")} elementos |')
    for r in results["nomenclature"]:
        lines.append(f'| {r["body"]} | {r["title"]} | {state(r)} | {r.get("n_features", "")} rasgos |')
    d = results["diviner"]
    lines.append(f'| Luna | {d["title"]} | {state(d)} | {len(d["files"])} archivos |')
    return "\n".join(lines) + "\n"


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--data-root", default="/lustre/proyectos/p089/data/raw")
    p.add_argument("--out-dir", required=True)
    p.add_argument("--workers", type=int, default=int(os.environ.get("SLURM_CPUS_PER_TASK", "4")))
    p.add_argument("--max-px", type=int, default=900, help="Ancho máximo de las miniaturas")
    p.add_argument("--no-validate-tiles", action="store_true", help="No abrir cada tile de Copernicus")
    p.add_argument("--only", choices=["planets", "copernicus", "modis", "vectors"], help="Explorar solo una parte")
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
            print(f"    -> {'OK' if r.get('meta') else r.get('error', 'no existe')}", flush=True)
        results["nomenclature"] = explore_nomenclature(args.data_root)
        results["diviner"] = explore_diviner(args.data_root)
    if args.only in (None, "copernicus"):
        print("[*] Copernicus", flush=True)
        results["copernicus"] = explore_copernicus(args.data_root, args.workers, args.max_px, not args.no_validate_tiles)
        c = results["copernicus"]
        print(f"    -> {c.get('n_tif', 0)} tiles, {c.get('n_bad', 0)} no abren", flush=True)
    if args.only in (None, "modis"):
        for key in MODIS_SPECS:
            print(f"[*] MODIS {key}", flush=True)
            results["modis"].append(explore_modis(args.data_root, key))
    if args.only in (None, "vectors"):
        print("[*] Natural Earth", flush=True)
        results["vectors"] = explore_vectors(args.data_root)

    # HTML
    by_body = {"Marte": [], "Luna": []}
    for r in results["rasters"]:
        if r.get("optional") and not r.get("exists"):
            continue
        by_body[r["body"]].append(render_raster(r, specs[r["key"]]))
    nom = {r["body"]: render_nomenclature(r) for r in results["nomenclature"]}
    sections = []
    if by_body["Marte"] or "Marte" in nom:
        sections.append('<h2 id="marte">Marte</h2>' + "".join(by_body["Marte"]) + nom.get("Marte", ""))
    if by_body["Luna"] or "Luna" in nom:
        sections.append('<h2 id="luna">Luna</h2>' + "".join(by_body["Luna"]) + nom.get("Luna", "")
                        + (render_diviner(results["diviner"]) if args.only in (None, "planets") else ""))
    earth = ""
    if results["copernicus"].get("exists") or args.only in (None, "copernicus"):
        earth += render_copernicus(results["copernicus"])
    earth += "".join(render_modis(r) for r in results["modis"]) + "".join(render_vector(r) for r in results["vectors"])
    if earth:
        sections.append('<h2 id="tierra">Tierra</h2>' + earth)
    doc = (f'<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
           f'<title>Exploración de datasets</title><style>{CSS}</style></head><body><main>'
           f'<h1>Exploración de datasets</h1><p class="muted">Planetary Analog Finder · generado {results["generated_at"]} '
           f'en {html.escape(os.uname().nodename if hasattr(os, "uname") else "")} · {round(time.time() - t0)} s · '
           f'<code>{html.escape(args.data_root)}</code></p><nav><a href="#marte">Marte</a><a href="#luna">Luna</a><a href="#tierra">Tierra</a></nav>'
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
