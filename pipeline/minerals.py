"""T18: mineralogy as display-only context.

Adds a ``mineralogy`` block to every target and, when the EMIT file is available, to every Earth
analog of ``analogs_universe.json``. Nothing here enters the score: the instruments see different
minerals on each body, so a like-for-like comparison would be misleading (see
``docs/plan_mineralogy_context.md``).

Sources (all verified on 2026-11-14):

* Moon, targets: Kaguya Multiband Imager mineral maps, 4 pixels per degree, 50N-50S, USGS bucket.
* Mars, targets: MGS TES mineral abundance maps (Bandfield 2002), 4 pixels per degree, ASU WMS (VICAR).
* Earth, analogs: EMIT L3 aggregated mineral abundance (EMITL3ASA v002), 0.5 degrees, 52N-52S.

The module only reads rasters and the universe JSON. It never touches the matching or the scores.

Usage::

    python -m pipeline.minerals --universe analogs_universe.json --out out/analogs_universe.json \\
        --kaguya-dir data/raw/moon/kaguya_mi --tes-dir data/raw/mars/tes --emit-file data/raw/earth/emit/EMIT_L3_ASA_002.nc

Every source is optional. A source that is not given leaves the ``mineralogy`` blocks that the input
file already has untouched, so the step can be run in two passes (Moon and Mars first, EMIT later).
"""

from __future__ import annotations

import argparse
import copy
import json
import logging
import math
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

BODY_RADIUS_KM = {"Moon": 1737.4, "Mars": 3396.19, "Earth": 6371.0}
PATCH_RADIUS_KM = 16.0  # half of the 32 km patch used everywhere else in the pipeline
DETECTION_PCT = 5.0  # TES detection level used in the Mars summary (Bandfield 2002: about 5 to 10%)
EMIT_MIN_PCT = 0.5  # EMIT minerals below this are not named in the summary
EMIT_FILL = -9999.0


# ---------------------------------------------------------------------------------------------
# Source registry
# ---------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Var:
    """One displayed variable. ``lo``/``hi`` are the valid range in the file's own units."""

    key: str
    label: str
    unit: str  # unit after ``scale`` is applied
    scale: float
    lo: float
    hi: float
    file_token: str  # Kaguya: file name part; TES: file stem; EMIT: normalised variable name


@dataclass(frozen=True)
class Source:
    id: str
    body: str
    name: str
    lat_min: float
    lat_max: float
    coverage_note: str
    no_data_note: str
    vars: tuple[Var, ...]


KAGUYA = Source(
    id="kaguya_mi",
    body="Moon",
    name="Kaguya Multiband Imager mineral maps (JAXA SELENE), USGS Astrogeology",
    lat_min=-50.0,
    lat_max=50.0,
    coverage_note="Kaguya mineral maps only cover 50N to 50S, so there is no mineral map at this latitude.",
    no_data_note="No valid Kaguya value around this site.",
    vars=(
        Var("feo", "FeO", "wt%", 1.0, 0.0, 30.0, "FeOWeightPercent"),
        Var("olivine", "Olivine", "%", 100.0, 0.0, 1.0, "OlivinePercent"),
        Var("orthopyroxene", "Orthopyroxene (low-Ca)", "%", 100.0, 0.0, 1.0, "OrthopyroxenePercent"),
        Var("clinopyroxene", "Clinopyroxene (high-Ca)", "%", 100.0, 0.0, 1.0, "ClinopyroxenePercent"),
        Var("plagioclase", "Plagioclase", "%", 100.0, 0.0, 1.0, "PlagioclasePercent"),
        Var("maturity", "Optical maturity", "index", 1.0, 0.0, 1.0, "OpticalMaturityIndex"),
    ),
)

TES = Source(
    id="tes_bandfield2002",
    body="Mars",
    name="MGS TES mineral abundance maps (Bandfield 2002), ASU Mars Global Data Sets",
    lat_min=-90.0,
    lat_max=90.0,
    coverage_note="",
    no_data_note="TES has no reliable retrieval here: the surface is dust covered or the fit is poor, so the map is masked.",
    vars=(
        Var("olivine", "Olivine", "%", 100.0, 0.0, 1.0, "olivine"),
        Var("orthopyroxene", "Orthopyroxene (low-Ca)", "%", 100.0, 0.0, 1.0, "orthopyroxene"),
        Var("clinopyroxene", "Clinopyroxene (high-Ca)", "%", 100.0, 0.0, 1.0, "clinopyroxene"),
        Var("plagioclase", "Plagioclase", "%", 100.0, 0.0, 1.0, "plagioclase"),
        Var("hematite", "Hematite", "%", 100.0, 0.0, 1.0, "hematite"),
    ),
)

EMIT = Source(
    id="emit_l3asa",
    body="Earth",
    name="EMIT L3 aggregated mineral abundance v002 (NASA JPL, LP DAAC)",
    lat_min=-52.0,
    lat_max=52.0,
    coverage_note="EMIT only observes between 52N and 52S, so there is no EMIT value at this latitude.",
    no_data_note="No EMIT value in this 0.5 degree cell (not observed, or masked for cloud, water, vegetation or urban areas).",
    vars=(
        Var("calcite", "Calcite", "%", 1.0, 0.0, 100.0, "calcite"),
        Var("chlorite", "Chlorite", "%", 1.0, 0.0, 100.0, "chlorite"),
        Var("dolomite", "Dolomite", "%", 1.0, 0.0, 100.0, "dolomite"),
        Var("goethite", "Goethite", "%", 1.0, 0.0, 100.0, "goethite"),
        Var("gypsum", "Gypsum", "%", 1.0, 0.0, 100.0, "gypsum"),
        Var("hematite", "Hematite", "%", 1.0, 0.0, 100.0, "hematite"),
        Var("illite_muscovite", "Illite + muscovite", "%", 1.0, 0.0, 100.0, "illitemuscovite"),
        Var("kaolinite", "Kaolinite", "%", 1.0, 0.0, 100.0, "kaolinite"),
        Var("montmorillonite", "Montmorillonite", "%", 1.0, 0.0, 100.0, "montmorillonite"),
        Var("vermiculite", "Vermiculite", "%", 1.0, 0.0, 100.0, "vermiculite"),
    ),
)

SOURCES = {s.id: s for s in (KAGUYA, TES, EMIT)}

DATASETS = {
    "kaguya_mi": {
        "name": "Kaguya Multiband Imager mineral maps (4 ppd)",
        "source": "JAXA SELENE, processed by USGS Astrogeology",
        "url": "https://astrogeology.usgs.gov/search/map/kaguya_lunar_multiband_imager_59mpp",
    },
    "tes_bandfield2002": {
        "name": "MGS TES mineral abundance maps (4 ppd)",
        "source": "NASA MGS TES, Bandfield (2002), ASU Mars Global Data Sets",
        "url": "https://www.mars.asu.edu/data/",
    },
    "emit_l3asa": {
        "name": "EMIT L3 Aggregated Mineral Spectral Abundance 0.5 deg V002",
        "source": "NASA JPL EMIT, LP DAAC",
        "url": "https://doi.org/10.5067/EMIT/EMITL3ASA.002",
    },
}

CITATIONS = {
    "kaguya_mi": (
        "Ohtake, M. (2016). Global map products from the Kaguya Multiband Imager at 512 ppd: Minerals, FeO and OMAT. "
        "47th Lunar and Planetary Science Conference, abstract 2994. Maps produced by M. Lemelin and colleagues; "
        "data: USGS Astrogeology, Kaguya Lunar Multiband Imager 59mpp."
    ),
    "tes_bandfield2002": "Bandfield, J.L. (2002). Global mineral distributions on Mars. J. Geophys. Res., 107(E6), 5042, doi:10.1029/2001JE001510.",
    "emit_l3asa": (
        "NASA JPL EMIT team (2024). EMIT L3 Aggregated Mineral Spectral Abundance and Uncertainty 0.5 Deg V002. "
        "NASA LP DAAC, doi:10.5067/EMIT/EMITL3ASA.002."
    ),
}

CAVEATS = {
    "kaguya_mi": [
        "Estimates from a spectral fit to Kaguya MI images at about 7.6 km per pixel; the fit is calibrated within 50 degrees of the equator.",
        "Mineral values are modal fractions of the fitted mix (olivine, two pyroxenes, plagioclase), not a lab analysis.",
    ],
    "tes_bandfield2002": [
        "TES maps are about 16 km per pixel and the detection level is roughly 5 to 10%, so small values are close to noise.",
        "About a quarter of the planet is masked (dust covered or poor fit); masked sites are shown as no data.",
    ],
    "emit_l3asa": [
        "Values are mass fractions of the EMIT-10 minerals, averaged over 0.5 degree cells (about 55 km), at the median grain size.",
        "The file has no units attribute; its values never add up to more than 0.8 at any site, so they are read as fractions of 0 to 1 and shown as percent. Treat the absolute numbers with care.",
        "EMIT mostly sees arid surface minerals (clays, carbonates, sulfates, iron oxides), not the mafic minerals of the Moon and Mars.",
    ],
}


# ---------------------------------------------------------------------------------------------
# Grids
# ---------------------------------------------------------------------------------------------


class Grid:
    """A north-up lat/lon grid. ``data`` holds the file's own values, NaN where unknown."""

    def __init__(self, data: np.ndarray, west: float, east: float, north: float, south: float) -> None:
        self.data = np.asarray(data, dtype=np.float64)
        self.west, self.east, self.north, self.south = float(west), float(east), float(north), float(south)
        self.rows, self.cols = self.data.shape
        self.dlon = (self.east - self.west) / self.cols
        self.dlat = (self.north - self.south) / self.rows
        self.wraps = (self.east - self.west) >= 359.0

    def index(self, lat: float, lon: float) -> tuple[int, int] | None:
        if not (self.south - 1e-9 <= lat <= self.north + 1e-9):
            return None
        if self.wraps:
            x = ((lon - self.west) % 360.0) / self.dlon
        else:
            if not (self.west - 1e-9 <= lon <= self.east + 1e-9):
                return None
            x = (lon - self.west) / self.dlon
        row = min(self.rows - 1, max(0, int((self.north - lat) / self.dlat)))
        col = min(self.cols - 1, max(0, int(x)))
        return row, col

    def radius_px(self, body: str, radius_km: float = PATCH_RADIUS_KM) -> int:
        cell_km = self.dlat * math.pi / 180.0 * BODY_RADIUS_KM[body]
        return max(0, int(round(radius_km / cell_km)))

    def window_median(self, lat: float, lon: float, radius: int, lo: float, hi: float) -> float:
        """Median of the valid values (``lo`` <= v <= ``hi``) in a (2r+1) square window, NaN if none."""
        idx = self.index(lat, lon)
        if idx is None:
            return float("nan")
        r, c = idx
        r0, r1 = max(0, r - radius), min(self.rows, r + radius + 1)
        cols = np.arange(c - radius, c + radius + 1)
        cols = cols % self.cols if self.wraps else cols[(cols >= 0) & (cols < self.cols)]
        window = self.data[r0:r1][:, cols]
        ok = np.isfinite(window) & (window >= lo) & (window <= hi)
        return float(np.median(window[ok])) if ok.any() else float("nan")


def load_geotiff_grid(path: Path) -> Grid:
    import rasterio

    with rasterio.open(path) as src:
        data = src.read(1).astype(np.float64)
        if src.nodata is not None:
            data[data == src.nodata] = np.nan
        b = src.bounds
        return Grid(data, b.left, b.right, b.top, b.bottom)


def load_vicar_grid(path: Path, west: float = 0.0, east: float = 360.0) -> Grid:
    """Read the ASU JMARS VICAR export: a text label of LBLSIZE bytes, then 32-bit floats, north row first."""
    raw = Path(path).read_bytes()
    head = raw[:80].decode("latin1")
    m = re.search(r"LBLSIZE=(\d+)", head)
    if not m:
        raise ValueError(f"{path}: not a VICAR file (no LBLSIZE)")
    lblsize = int(m.group(1))
    label = raw[:lblsize].decode("latin1")

    def field(name: str) -> str:
        found = re.search(rf"\b{name}=('?)([^\s']+)\1", label)
        if not found:
            raise ValueError(f"{path}: VICAR label has no {name}")
        return found.group(2)

    rows, cols = int(field("NL")), int(field("NS"))
    fmt, intfmt = field("FORMAT"), field("REALFMT")
    if fmt != "REAL":
        raise ValueError(f"{path}: expected FORMAT='REAL', got {fmt!r}")
    dtype = "<f4" if intfmt in ("RIEEE", "IEEE") else ">f4"
    need = lblsize + rows * cols * 4
    if len(raw) < need:
        raise ValueError(f"{path}: truncated file ({len(raw)} of {need} bytes), download it again")
    data = np.frombuffer(raw, dtype=dtype, count=rows * cols, offset=lblsize).reshape(rows, cols)
    return Grid(data.astype(np.float64), west, east, 90.0, -90.0)


def _name_key(name: str) -> str:
    """Letters only, lower case: 'Illite+Muscovite' and a GDAL 'Illite+Muscovite3' both give 'illitemuscovite'."""
    return re.sub(r"[^a-z]", "", name.lower())


def _on_lattice(value: float, step: float) -> bool:
    q = value / step
    return abs(q - round(q)) < 1e-4


def emit_origin(left: float, top: float, dx: float, dy: float, corner: bool | None) -> tuple[float, float, bool]:
    """Fix the half-cell shift of the EMIT coordinates.

    The EMIT guide says latitude and longitude hold the upper-left corner of each cell, while GDAL treats
    coordinate values as cell centres. With ``corner=None`` we detect it: corner values fall on multiples of
    the cell size, centre values fall half a cell off.
    """
    first_lon, first_lat = left + dx / 2.0, top - dy / 2.0  # what GDAL read as the first coordinates
    if corner is None:
        corner = _on_lattice(first_lon, dx) and _on_lattice(first_lat, dy)
    if corner:
        return first_lon, first_lat, True  # true west edge = first lon value, true north edge = first lat value
    return left, top, False


def grids_from_coords(
    arrays: dict[str, np.ndarray], lat: np.ndarray, lon: np.ndarray, corner: bool | None = None, scale: float = 1.0
) -> dict[str, Grid]:
    """Grids from 2-D ``(lat, lon)`` arrays and their 1-D coordinate vectors (ascending or descending latitude).

    ``corner`` says whether the coordinate values are the upper-left corner of each cell (the EMIT guide) or
    the cell centre; ``None`` detects it from the lattice, as in :func:`emit_origin`.
    """
    lat_v, lon_v = np.asarray(lat, dtype=np.float64), np.asarray(lon, dtype=np.float64)
    dx, dy = float(np.median(np.diff(lon_v))), float(np.median(np.abs(np.diff(lat_v))))
    data = {k: np.asarray(v, dtype=np.float64) * scale for k, v in arrays.items()}
    if lat_v[0] < lat_v[-1]:  # south first: flip so that row 0 is the northmost
        lat_v = lat_v[::-1]
        data = {k: v[::-1] for k, v in data.items()}
    if corner is None:
        corner = _on_lattice(float(lon_v[0]), dx) and _on_lattice(float(lat_v[0]), dy)
    west = float(lon_v[0]) if corner else float(lon_v[0]) - dx / 2.0
    north = float(lat_v[0]) if corner else float(lat_v[0]) + dy / 2.0
    logger.info("EMIT coordinates treated as %s values", "corner" if corner else "centre")
    return {
        k: Grid(v, west, west + dx * v.shape[1], north, north - dy * v.shape[0]) for k, v in data.items()
    }


def _emit_via_gdal(path: Path, corner: bool | None, scale: float = 1.0) -> dict[str, Grid]:
    import rasterio

    wanted = {v.file_token: v.key for v in EMIT.vars}
    grids: dict[str, Grid] = {}
    with rasterio.open(path) as src:
        subs = list(src.subdatasets)
    if not subs:
        raise RuntimeError("GDAL found no variables (is the netCDF driver available?)")
    for sub in subs:
        var = sub.rsplit(":", 1)[-1]
        key = _name_key(var)
        if "uq" in key or key not in wanted:
            continue
        with rasterio.open(sub) as ds:
            data = ds.read(1).astype(np.float64)
            data[data == EMIT_FILL] = np.nan
            if ds.nodata is not None:
                data[data == ds.nodata] = np.nan
            data = data * scale
            b = ds.bounds
            dx, dy = (b.right - b.left) / ds.width, (b.top - b.bottom) / ds.height
            left, top, is_corner = emit_origin(b.left, b.top, dx, dy, corner)
            grids[wanted[key]] = Grid(data, left, left + dx * ds.width, top, top - dy * ds.height)
            logger.info("EMIT variable %r -> %s (corner convention: %s)", var, wanted[key], is_corner)
    if not grids:
        raise RuntimeError(f"no EMIT-10 mineral variable among {[s.rsplit(':', 1)[-1] for s in subs]}")
    return grids


def _emit_via_xarray(path: Path, corner: bool | None, scale: float = 1.0) -> dict[str, Grid]:
    import xarray as xr

    wanted = {v.file_token: v.key for v in EMIT.vars}
    with xr.open_dataset(path) as ds:
        lat_name = next((n for n in ("latitude", "lat") if n in ds.variables), None)
        lon_name = next((n for n in ("longitude", "lon") if n in ds.variables), None)
        if lat_name is None or lon_name is None:
            raise RuntimeError(f"no latitude/longitude variable; variables are {list(ds.variables)}")
        arrays: dict[str, np.ndarray] = {}
        for name in ds.data_vars:
            key = _name_key(str(name))
            if "uq" in key or key not in wanted or ds[name].ndim != 2:
                continue
            arr = np.asarray(ds[name].values, dtype=np.float64)
            arr[arr == EMIT_FILL] = np.nan
            arrays[wanted[key]] = arr
        if not arrays:
            raise RuntimeError(f"no EMIT-10 mineral variable among {list(ds.data_vars)}")
        return grids_from_coords(arrays, np.asarray(ds[lat_name].values), np.asarray(ds[lon_name].values), corner, scale)


def load_emit_grids(path: Path, corner: bool | None = None, scale: float = 1.0) -> dict[str, Grid]:
    """Read the EMIT-10 mineral variables (mass fraction, %), skipping the ``_UQ_`` uncertainty variables.

    GDAL (through rasterio) is tried first because it is what the tests exercise; xarray is the fallback
    for environments whose GDAL has no netCDF driver (the Yuca environment has xarray).

    ``scale`` multiplies every value: use 100 if the file stores fractions (0 to 1) although the guide says percent
    (the Kaguya maps do the same); see :func:`check_emit_units`.
    """
    errors: list[str] = []
    for name, reader in (("GDAL", _emit_via_gdal), ("xarray", _emit_via_xarray)):
        try:
            grids = reader(Path(path), corner, scale)
            logger.info("EMIT read with %s: %s", name, sorted(grids))
            return grids
        except Exception as exc:  # noqa: BLE001 - report every backend before giving up
            errors.append(f"{name}: {type(exc).__name__}: {exc}")
            logger.warning("EMIT reader %s failed: %s", name, exc)
    raise RuntimeError(f"Could not read {path}. " + " | ".join(errors))


def load_kaguya_grids(directory: Path) -> dict[str, Grid]:
    grids: dict[str, Grid] = {}
    for v in KAGUYA.vars:
        p = Path(directory) / f"Lunar_Kaguya_MIMap_MineralDeconv_{v.file_token}_50N50S.tif"
        if p.exists():
            grids[v.key] = load_geotiff_grid(p)
        else:
            logger.warning("Kaguya file missing: %s", p)
    return grids


def load_tes_grids(directory: Path) -> dict[str, Grid]:
    grids: dict[str, Grid] = {}
    for v in TES.vars:
        p = Path(directory) / f"tes_{v.file_token}.vic"
        if p.exists():
            grids[v.key] = load_vicar_grid(p)
        else:
            logger.warning("TES file missing: %s", p)
    return grids


# ---------------------------------------------------------------------------------------------
# Sampling and plain-language summaries
# ---------------------------------------------------------------------------------------------


def _label(source: Source, key: str) -> str:
    return next(v.label for v in source.vars if v.key == key)


def _ranked(values: dict[str, float | None], keys: list[str]) -> list[tuple[str, float]]:
    present = [(k, values[k]) for k in keys if values.get(k) is not None]
    return sorted(present, key=lambda kv: -kv[1])  # type: ignore[operator]


def summarize_moon(values: dict[str, float | None]) -> str:
    parts: list[str] = []
    feo = values.get("feo")
    if feo is not None:
        if feo >= 14.0:
            kind = "iron-rich, mare-like basalt"
        elif feo <= 8.0:
            kind = "iron-poor, highland-like rock"
        else:
            kind = "intermediate iron content"
        parts.append(f"FeO {feo:.0f} wt%, {kind}")
    top = _ranked(values, ["olivine", "orthopyroxene", "clinopyroxene", "plagioclase"])
    if top:
        parts.append(f"most abundant mineral: {_label(KAGUYA, top[0][0]).lower()} ({top[0][1]:.0f}%)")
    text = "; ".join(parts)
    return text[:1].upper() + text[1:]


def summarize_mars(values: dict[str, float | None]) -> str:
    top = _ranked(values, ["olivine", "orthopyroxene", "clinopyroxene", "plagioclase"])
    parts: list[str] = []
    if top and top[0][1] >= DETECTION_PCT:
        parts.append(f"Most abundant of the four silicates: {_label(TES, top[0][0]).lower()} ({top[0][1]:.0f}%)")
    elif top:
        parts.append(f"No silicate above the TES detection level (about {DETECTION_PCT:g}%)")
    hem = values.get("hematite")
    if hem is not None and hem >= DETECTION_PCT:
        parts.append(f"hematite present ({hem:.0f}%)")
    return "; ".join(parts)


def summarize_earth(values: dict[str, float | None]) -> str:
    top = [(k, v) for k, v in _ranked(values, [x.key for x in EMIT.vars]) if v >= EMIT_MIN_PCT][:3]
    if not top:
        return f"No EMIT-10 mineral above {EMIT_MIN_PCT:g}%"
    named = ", ".join(f"{_label(EMIT, k).lower()} ({v:.1f}%)" for k, v in top)
    return f"Mostly {named}"


SUMMARIZERS = {"Moon": summarize_moon, "Mars": summarize_mars, "Earth": summarize_earth}


def sample_source(source: Source, grids: dict[str, Grid], lat: float, lon: float) -> dict[str, object]:
    """Mineral values of one site. Status: ok, outside_coverage or no_data."""
    base: dict[str, object] = {"source": source.id}
    if not (source.lat_min <= lat <= source.lat_max):
        return {**base, "status": "outside_coverage", "note": source.coverage_note}
    values: dict[str, float | None] = {}
    for v in source.vars:
        grid = grids.get(v.key)
        if grid is None:
            continue
        raw = grid.window_median(lat, lon, grid.radius_px(source.body), v.lo, v.hi)
        values[v.key] = None if math.isnan(raw) else round(raw * v.scale, 3 if v.unit == "index" else 2)
    if not any(x is not None for x in values.values()):
        return {**base, "status": "no_data", "note": source.no_data_note}
    return {**base, "status": "ok", "values": values, "summary": SUMMARIZERS[source.body](values)}


# ---------------------------------------------------------------------------------------------
# Universe enrichment
# ---------------------------------------------------------------------------------------------

MINERALOGY_NOTE = (
    "Mineral maps are shown on the site sheet as context and do not enter the score: each instrument sees "
    "different minerals on each body, so comparing them row by row would be misleading."
)


def _variables_registry(used: list[Source]) -> dict[str, dict[str, object]]:
    out: dict[str, dict[str, object]] = {}
    for s in used:
        out[s.id] = {"body": s.body, "variables": [{"key": v.key, "label": v.label, "unit": v.unit} for v in s.vars]}
    return out


def _update_metadata(universe: dict, used: list[Source]) -> None:
    meta = universe.setdefault("metadata", {})
    block = meta.setdefault("mineralogy", {})
    block["scored"] = False
    block["note"] = MINERALOGY_NOTE
    sources = block.setdefault("sources", {})
    for s in used:
        sources[s.id] = {
            "body": s.body,
            "name": s.name,
            "lat_range": [s.lat_min, s.lat_max],
            "caveats": CAVEATS[s.id],
            "variables": [{"key": v.key, "label": v.label, "unit": v.unit} for v in s.vars],
        }
        names = {d.get("name") for d in meta.get("datasets", [])}
        if DATASETS[s.id]["name"] not in names:
            meta.setdefault("datasets", []).append(dict(DATASETS[s.id]))
        if CITATIONS[s.id] not in meta.get("citations", []):
            meta.setdefault("citations", []).append(CITATIONS[s.id])
    for item in meta.get("not_modelled", []):
        if str(item.get("item", "")).startswith("mineralogy"):
            item["note"] = (
                "Geology is regional lithology and mapped units. Mineral maps (Moon: Kaguya, Mars: TES, Earth: EMIT) are "
                "shown as context on the site sheet but are not scored: the instruments see different minerals on each body."
            )


def enrich_universe(
    universe: dict,
    kaguya: dict[str, Grid] | None = None,
    tes: dict[str, Grid] | None = None,
    emit: dict[str, Grid] | None = None,
) -> tuple[dict, dict[str, dict[str, int]]]:
    """Return a copy of the universe with ``mineralogy`` blocks and the count of statuses per source.

    A source that is not given leaves the blocks already present in the input untouched.
    """
    out = copy.deepcopy(universe)
    counts: dict[str, dict[str, int]] = {}
    used: list[Source] = []

    def tally(src: Source, block: dict) -> None:
        counts.setdefault(src.id, {}).setdefault(str(block["status"]), 0)
        counts[src.id][str(block["status"])] += 1

    for source, grids, body in ((KAGUYA, kaguya, "Moon"), (TES, tes, "Mars")):
        if not grids:
            continue
        used.append(source)
        for t in out["targets"]:
            if t["body"] == body:
                block = sample_source(source, grids, float(t["lat"]), float(t["lon"]))
                t["mineralogy"] = block
                tally(source, block)

    if emit:
        used.append(EMIT)
        cache: dict[tuple[float, float], dict] = {}
        for t in out["targets"]:
            for a in t["analogs"]:
                key = (float(a["lat"]), float(a["lon"]))
                if key not in cache:
                    cache[key] = sample_source(EMIT, emit, *key)
                a["mineralogy"] = cache[key]
        for block in cache.values():
            tally(EMIT, block)

    if used:
        _update_metadata(out, used)
    return out, counts


# ---------------------------------------------------------------------------------------------
# Sanity checks and report
# ---------------------------------------------------------------------------------------------

# Known places used only as a soft check that the maps are read in the right place and orientation.
CHECKS = [
    ("Apollo 11 (Mare Tranquillitatis), FeO >= 14 wt%", KAGUYA, "feo", 0.67, 23.47, ">=", 14.0),
    ("Lunar far-side highlands, FeO <= 8 wt%", KAGUYA, "feo", -10.0, 150.0, "<=", 8.0),
    ("Lunar far-side highlands, plagioclase >= 60%", KAGUYA, "plagioclase", -10.0, 150.0, ">=", 60.0),
    ("Meridiani Planum, TES hematite >= 5%", TES, "hematite", -2.0, 354.0, ">=", 5.0),
    ("Syrtis Major, TES clinopyroxene >= 5%", TES, "clinopyroxene", 9.0, 69.0, ">=", 5.0),
]


def run_checks(kaguya: dict[str, Grid] | None, tes: dict[str, Grid] | None) -> list[tuple[str, bool | None, float | None]]:
    results = []
    for label, source, key, lat, lon, op, limit in CHECKS:
        grids = kaguya if source is KAGUYA else tes
        if not grids or key not in grids:
            results.append((label, None, None))
            continue
        block = sample_source(source, grids, lat, lon)
        val = (block.get("values") or {}).get(key) if block["status"] == "ok" else None  # type: ignore[union-attr]
        passed = None if val is None else (val >= limit if op == ">=" else val <= limit)
        results.append((label, passed, val))
    return results


def check_emit_units(universe: dict) -> float | None:
    """Largest sum of the ten EMIT minerals over all analogs with a value, or None if there is none.

    The values are meant to be percent. If no location ever sums to 1 or more, the file very likely stores
    fractions (0 to 1) and the numbers are 100 times too small; rerun with ``--emit-scale 100``.
    """
    sums = [
        sum(v for v in a["mineralogy"]["values"].values() if v is not None)
        for t in universe["targets"]
        for a in t["analogs"]
        if a.get("mineralogy", {}).get("source") == EMIT.id and a["mineralogy"].get("status") == "ok"
    ]
    return max(sums) if sums else None


def write_report(path: Path, universe: dict, counts: dict[str, dict[str, int]], checks: list) -> None:
    lines = ["# Mineralogy context report (T18)", ""]
    lines += ["## Sites by status", "", "| Source | ok | outside coverage | no data |", "| --- | --- | --- | --- |"]
    for sid, c in counts.items():
        lines.append(f"| {sid} | {c.get('ok', 0)} | {c.get('outside_coverage', 0)} | {c.get('no_data', 0)} |")
    top = check_emit_units(universe)
    if top is not None:
        lines += ["", f"EMIT units check: largest sum of the ten minerals at one location is {top:.2f}" + (" (below 1: the values may be fractions, see --emit-scale)" if top < 1.0 else "")]
    lines += ["", "## Sanity checks (soft)", ""]
    for label, passed, val in checks:
        mark = "n/a (source not loaded)" if passed is None and val is None else ("pass" if passed else "FAIL")
        lines.append(f"- {label}: {mark}" + (f" (value {val})" if val is not None else ""))
    lines += ["", "## Curated mission sites", "", "| Target | Status | Summary |", "| --- | --- | --- |"]
    for t in universe["targets"]:
        if t.get("type") == "CURATED" and t.get("mineralogy"):
            m = t["mineralogy"]
            lines.append(f"| {t['name']} | {m['status']} | {m.get('summary') or m.get('note', '')} |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--universe", type=Path, required=True, help="analogs_universe.json to enrich")
    p.add_argument("--out", type=Path, required=True, help="enriched analogs_universe.json")
    p.add_argument("--kaguya-dir", type=Path, help="folder with the Kaguya MI GeoTIFFs")
    p.add_argument("--tes-dir", type=Path, help="folder with the tes_*.vic files")
    p.add_argument("--emit-file", type=Path, help="EMIT_L3_ASA_002.nc")
    p.add_argument("--emit-corner", choices=["auto", "yes", "no"], default="auto")
    p.add_argument(
        "--emit-scale", type=float, default=100.0,
        help="multiply the EMIT values by this. The file has no units attribute and its values are fractions "
        "(0 to 1, see check_emit_units), so the default is 100 to show percent; use 1 to keep the raw values",
    )
    p.add_argument("--report", type=Path, help="write a Markdown report here")
    args = p.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    universe = json.loads(args.universe.read_text(encoding="utf-8"))
    kaguya = load_kaguya_grids(args.kaguya_dir) if args.kaguya_dir else None
    tes = load_tes_grids(args.tes_dir) if args.tes_dir else None
    emit = None
    if args.emit_file:
        emit = load_emit_grids(args.emit_file, {"auto": None, "yes": True, "no": False}[args.emit_corner], args.emit_scale)

    out, counts = enrich_universe(universe, kaguya, tes, emit)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    if emit:
        top = check_emit_units(out)
        if top is not None:
            logger.info("EMIT units check: the largest sum of the ten minerals at one location is %.2f (scale %g)", top, args.emit_scale)
            if top < 1.0:
                logger.warning(
                    "EMIT values never add up to 1 or more at any location, so they look like fractions, not percent. "
                    "Rerun with --emit-scale 100 if they are fractions."
                )
            elif top > 100.5:
                logger.warning("The ten EMIT minerals add up to more than 100%% at one location (%.1f): the scale is too large.", top)
    checks = run_checks(kaguya, tes)
    for sid, c in counts.items():
        logger.info("%s: %s", sid, c)
    for label, passed, val in checks:
        logger.info("check %s: %s (%s)", label, "n/a" if passed is None else ("pass" if passed else "FAIL"), val)
    if args.report:
        write_report(args.report, out, counts, checks)
    logger.info("wrote %s", args.out)


if __name__ == "__main__":
    main()
