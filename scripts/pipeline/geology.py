"""Geological mapping, lithological classification, and surface materials (T14).

This module manages lithological and stratigraphic datasets across all three celestial bodies:
- Earth: Global Lithological Map (GLiM) 0.5-degree gridded database, sampled at candidate
  coordinates with a robust 3x3 nearest-neighbor fallback for coastal and island pixels.
- Moon: USGS Unified Geologic Map of the Moon (Fortezzo et al., 2020), querying GIS shapefile
  polygons or falling back to nearest polygon centroid within 150 km.
- Mars: USGS Global Geologic Map of Mars (SIM 3292, Tanaka et al., 2014), performing point-in-polygon
  spatial intersections against regional geologic units.
- Expert overrides: Explicit manual overrides from `data/geology_overrides.json` for
  well-studied mission landing sites and field analog stations.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
import logging
import math
import os
from pathlib import Path
import re
import subprocess
import time

os.environ.setdefault("PROJ_IGNORE_CELESTIAL_BODY", "YES")

import geopandas as gpd
import numpy as np
import pandas as pd
import pyogrio

from .config import BODY_RADII_M, YUCA_PROJECT_DIR
from .geology_rules import (
    GEO_CLASSES,
    GEO_SIMILARITY,
    GLIM_CODES,
    GLIM_TO_CLASS,
    VALID_GLIM_INT_CODES,
    classify_unit,
)

logger = logging.getLogger(__name__)

GLIM_ASCII_REL: Path = Path("geology/earth_glim/glim_wgs84_0point5deg.txt.asc")
MOON_GEO_DIR_REL: Path = Path("geology/moon_unified")
MARS_GEO_DIR_REL: Path = Path("geology/mars_sim3292")
DEFAULT_OVERRIDES_PATH: Path = Path(__file__).resolve().parents[2] / "data" / "geology_overrides.json"

UNIT_SYMBOL_CANDIDATES: tuple[str, ...] = (
    "unit",
    "unitsymbol",
    "unit_symbol",
    "mapunit",
    "map_unit",
    "first_unit",
    "geounit",
    "geo_unit",
    "unitabbr",
    "unit_abbr",
    "unit_code",
    "symbol",
    "label",
)
UNIT_NAME_CANDIDATES: tuple[str, ...] = (
    "unitname",
    "unit_name",
    "fullname",
    "full_name",
    "name",
    "first_name",
    "unit_label",
)
UNIT_DESC_CANDIDATES: tuple[str, ...] = (
    "description",
    "desc",
    "unitdesc",
    "unit_desc",
    "first_desc",
    "description_of_unit",
    "lithology",
    "type",
    "period",
    "age",
    "notes",
)


def load_glim(path: Path | str) -> np.ndarray:
    """Load the GLiM 0.5 deg ESRI ASCII grid into an int16 array of shape (360, 720)."""
    arr = np.loadtxt(Path(path), skiprows=6, dtype=np.int16)
    if arr.ndim != 2:
        raise ValueError(f"Expected 2D GLiM grid, got shape {arr.shape}")
    return arr


def glim_at(
    grid: np.ndarray,
    lat: np.ndarray | float,
    lon: np.ndarray | float,
) -> np.ndarray:
    """Return vectorised GLiM string codes ('vb', 'sm', ..., or None) with 3x3 coast fallback."""
    grid_arr = np.asarray(grid, dtype=np.int32)
    if grid_arr.ndim != 2:
        raise ValueError(f"Expected 2D grid, got shape {grid_arr.shape}")
    nrows, ncols = grid_arr.shape
    dlat = 180.0 / float(nrows)
    dlon = 360.0 / float(ncols)

    lat_arr = np.atleast_1d(np.asarray(lat, dtype=np.float64))
    lon_arr = np.atleast_1d(np.asarray(lon, dtype=np.float64))
    lat_b, lon_b = np.broadcast_arrays(lat_arr, lon_arr)
    out_shape = lat_b.shape
    lat_f = lat_b.ravel()
    lon_f = lon_b.ravel()

    n = lat_f.size
    out = np.full(n, None, dtype=object)
    finite = np.isfinite(lat_f) & np.isfinite(lon_f)
    if not np.any(finite):
        return out.reshape(out_shape)

    rows = np.zeros(n, dtype=np.int64)
    cols = np.zeros(n, dtype=np.int64)
    rows[finite] = np.clip(
        np.floor((90.0 - lat_f[finite]) / dlat).astype(np.int64), 0, nrows - 1
    )
    cols[finite] = np.clip(
        np.floor((lon_f[finite] + 180.0) / dlon).astype(np.int64), 0, ncols - 1
    )

    center = np.full(n, -9999, dtype=np.int32)
    center[finite] = grid_arr[rows[finite], cols[finite]]

    valid_lut = np.zeros(32, dtype=bool)
    for code_int in VALID_GLIM_INT_CODES:
        valid_lut[code_int] = True

    in_range = (center >= 0) & (center < 32)
    is_valid = np.zeros(n, dtype=bool)
    is_valid[in_range] = valid_lut[center[in_range]]

    good_idx = np.flatnonzero(finite & is_valid)
    for idx in good_idx:
        out[idx] = GLIM_CODES[int(center[idx])]

    bad_idx = np.flatnonzero(finite & (~is_valid))
    for idx in bad_idx:
        r = int(rows[idx])
        c = int(cols[idx])
        patch = grid_arr[max(0, r - 1) : min(nrows, r + 2), max(0, c - 1) : min(ncols, c + 2)]
        vals = patch.ravel()
        valid_neighbors = [int(v) for v in vals if 0 <= int(v) < 32 and valid_lut[int(v)]]
        if not valid_neighbors:
            continue
        counts = Counter(valid_neighbors)
        best_code = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
        out[idx] = GLIM_CODES[best_code]

    return out.reshape(out_shape)


def sample_earth_geology(t5_df: pd.DataFrame, grid: np.ndarray) -> pd.DataFrame:
    """Assign Earth GLiM code, shared geo_class, and ice/lava labels to T5 patches."""
    lat = pd.to_numeric(t5_df["lat"], errors="coerce").to_numpy(dtype=np.float64)
    lon = pd.to_numeric(t5_df["lon"], errors="coerce").to_numpy(dtype=np.float64)
    codes = glim_at(grid, lat, lon)
    geo_classes = [GLIM_TO_CLASS.get(c) if c is not None else None for c in codes]
    ice_surface = np.asarray([c == "ig" for c in codes], dtype=bool)
    lava_tube = np.asarray([c == "vb" for c in codes], dtype=bool)

    return pd.DataFrame(
        {
            "lat": lat.astype(np.float64),
            "lon": lon.astype(np.float64),
            "glim_code": pd.Series(codes, dtype="string"),
            "geo_class": pd.Series(geo_classes, dtype="string"),
            "ice_surface": ice_surface,
            "lava_tube_terrain": lava_tube,
        }
    )


def _find_gis_sources(base_dir: Path) -> list[Path]:
    """Locate .gdb directories and .shp files under base_dir."""
    gdbs = sorted(p for p in base_dir.rglob("*.gdb") if p.is_dir())
    shps = sorted(p for p in base_dir.rglob("*.shp") if p.is_file())
    # Prefer .gdb containers if present alongside shapefiles, else return both
    return gdbs + shps


def _pick_col(columns: list[str], candidates: tuple[str, ...]) -> str | None:
    lower_map = {c.lower(): c for c in columns}
    for cand in candidates:
        if cand in lower_map:
            return lower_map[cand]
    for cand in candidates:
        if cand in ("type", "age"):
            continue
        for c in columns:
            clow = c.lower()
            if clow.startswith("shape_") or clow in ("objectid", "fid"):
                continue
            if cand in clow:
                return c
    return None


def _load_planetary_polygons(
    body: str,
    base_dir: Path,
) -> tuple[gpd.GeoDataFrame, str, str | None, str | None]:
    """Inspect GIS files in base_dir, load geologic unit polygons, and attach descriptions."""
    sources = _find_gis_sources(base_dir)
    if not sources:
        raise FileNotFoundError(f"No .gdb or .shp files found for {body} under {base_dir}")

    chosen_source: Path | None = None
    chosen_layer: str | None = None
    best_rank = (999, "")
    tables_to_check: list[tuple[Path, str]] = []

    skip_tokens = (
        "contact",
        "fault",
        "line",
        "point",
        "grid",
        "graticule",
        "neatline",
        "boundary",
        "clip",
        "mask",
        "extent",
        "anno",
        "label",
        "structure",
        "landing",
        "published",
    )

    for src in sources:
        try:
            layers = pyogrio.list_layers(src)
        except Exception as exc:
            logger.warning("Failed to list layers in %s: %s", src, exc)
            continue
        logger.info("%s GIS source %s layers: %s", body, src.name, layers.tolist())
        for layer_name, geom_type in layers:
            lname = str(layer_name)
            gtype = "" if geom_type is None else str(geom_type)
            lname_low = lname.lower()
            if "polygon" in gtype.lower():
                if not any(tok in lname_low for tok in skip_tokens):
                    if lname_low in ("geounits", "mapunitpolys", "sim3292_global_geology"):
                        prio = 0
                    elif "geounit" in lname_low or "global_geology" in lname_low:
                        prio = 1
                    elif "unit" in lname_low or "geo" in lname_low:
                        prio = 2
                    elif "poly" in lname_low:
                        prio = 3
                    else:
                        prio = 4
                    cand_rank = (prio, lname_low)
                    if cand_rank < best_rank:
                        best_rank = cand_rank
                        chosen_source = src
                        chosen_layer = lname
            if gtype == "" or gtype.lower() == "none" or "desc" in lname_low or "dmu" in lname_low:
                tables_to_check.append((src, lname))

    # Fallback: take first polygon layer in any source
    if chosen_source is None:
        for src in sources:
            layers = pyogrio.list_layers(src)
            for layer_name, geom_type in layers:
                gtype = "" if geom_type is None else str(geom_type)
                if "polygon" in gtype.lower():
                    chosen_source = src
                    chosen_layer = str(layer_name)
                    break
            if chosen_source is not None:
                break

    if chosen_source is None or chosen_layer is None:
        raise RuntimeError(f"Could not find a polygon geologic unit layer for {body} in {base_dir}")

    gdf = gpd.read_file(chosen_source, layer=chosen_layer, engine="pyogrio")
    logger.info(
        "%s polygons loaded from %s (layer=%s): %d features, CRS=%s, columns=%s, bounds=%s",
        body,
        chosen_source,
        chosen_layer,
        len(gdf),
        gdf.crs,
        [c for c in gdf.columns if c != gdf.geometry.name],
        tuple(round(float(v), 4) for v in gdf.total_bounds),
    )

    attr_cols = [c for c in gdf.columns if c != gdf.geometry.name]
    unit_col = _pick_col(attr_cols, UNIT_SYMBOL_CANDIDATES)
    if unit_col is None:
        raise RuntimeError(
            f"Could not identify unit symbol column for {body} in columns {attr_cols}"
        )

    name_col = _pick_col([c for c in attr_cols if c != unit_col], UNIT_NAME_CANDIDATES)
    desc_col = _pick_col(
        [c for c in attr_cols if c not in (unit_col, name_col)],
        UNIT_DESC_CANDIDATES,
    )

    # Check companion DescriptionOfMapUnits-style tables or CSVs for missing names/descriptions
    dmu_map: dict[str, str] = {}
    for tbl_src, tbl_layer in tables_to_check:
        if tbl_src == chosen_source and tbl_layer == chosen_layer:
            continue
        try:
            tbl = pyogrio.read_dataframe(tbl_src, layer=tbl_layer, read_geometry=False)
        except Exception:
            continue
        t_cols = list(tbl.columns)
        t_unit = _pick_col(t_cols, UNIT_SYMBOL_CANDIDATES)
        t_name = _pick_col([c for c in t_cols if c != t_unit], UNIT_NAME_CANDIDATES)
        t_desc = _pick_col(
            [c for c in t_cols if c not in (t_unit, t_name)],
            UNIT_DESC_CANDIDATES,
        )
        if t_unit is not None and (t_name is not None or t_desc is not None):
            logger.info(
                "%s companion unit description table found: %s / %s (unit=%s, name=%s, desc=%s)",
                body,
                tbl_src.name,
                tbl_layer,
                t_unit,
                t_name,
                t_desc,
            )
            for _, r in tbl.iterrows():
                uval = str(r[t_unit]).strip()
                parts = []
                if t_name and pd.notna(r[t_name]):
                    parts.append(str(r[t_name]).strip())
                if t_desc and pd.notna(r[t_desc]):
                    parts.append(str(r[t_desc]).strip())
                text = " — ".join(p for p in parts if p)
                if uval and text and uval not in dmu_map:
                    dmu_map[uval] = text

    # Also check CSV/TXT files (including sim3292_readme.txt) if descriptions are still sparse
    for csv_path in sorted(base_dir.rglob("*.csv")):
        try:
            tbl = pd.read_csv(csv_path)
            t_cols = list(tbl.columns)
            t_unit = _pick_col(t_cols, UNIT_SYMBOL_CANDIDATES)
            t_name = _pick_col([c for c in t_cols if c != t_unit], UNIT_NAME_CANDIDATES)
            t_desc = _pick_col(
                [c for c in t_cols if c not in (t_unit, t_name)],
                UNIT_DESC_CANDIDATES,
            )
            if t_unit is not None and (t_name is not None or t_desc is not None):
                for _, r in tbl.iterrows():
                    uval = str(r[t_unit]).strip()
                    parts = []
                    if t_name and pd.notna(r[t_name]):
                        parts.append(str(r[t_name]).strip())
                    if t_desc and pd.notna(r[t_desc]):
                        parts.append(str(r[t_desc]).strip())
                    text = " — ".join(p for p in parts if p)
                    if uval and text and uval not in dmu_map:
                        dmu_map[uval] = text
        except Exception:
            continue

    gdf = gdf.copy()
    gdf["_unit"] = gdf[unit_col].astype("string").str.strip()

    texts: list[str] = []
    for _, row in gdf.iterrows():
        uval = "" if pd.isna(row["_unit"]) else str(row["_unit"])
        parts: list[str] = []
        if name_col and pd.notna(row[name_col]):
            parts.append(str(row[name_col]).strip())
        if desc_col and pd.notna(row[desc_col]):
            parts.append(str(row[desc_col]).strip())
        if uval in dmu_map:
            parts.append(dmu_map[uval])
        combined = " — ".join(p for p in dict.fromkeys(p for p in parts if p))
        if not combined:
            combined = uval
        texts.append(combined)

    gdf["_desc_full"] = pd.Series(texts, index=gdf.index, dtype="string")
    return gdf, unit_col, name_col, desc_col


def _load_overrides(path: Path | None) -> dict[str, dict[str, str | None]]:
    """Load optional unit-to-class overrides committed after Claude review (§5.6)."""
    if path is None or not path.exists():
        return {"Moon": {}, "Mars": {}}
    with open(path, "r", encoding="utf-8") as fh:
        raw = json.load(fh)
    payload = raw.get("overrides", raw) if isinstance(raw, dict) else {}
    out: dict[str, dict[str, str | None]] = {"Moon": {}, "Mars": {}}
    for body in ("Moon", "Mars"):
        section = payload.get(body) or payload.get(body.lower()) or {}
        if isinstance(section, dict):
            for unit, val in section.items():
                if val is not None and val not in GEO_CLASSES:
                    raise ValueError(
                        f"Invalid override geo_class {val!r} for {body} unit {unit!r}"
                    )
                out[body][str(unit)] = val
    return out


def _compute_unit_areas(gdf: gpd.GeoDataFrame, radius_m: float) -> pd.Series:
    """Compute polygon areas in spherical/projected equal-area units per geometry."""
    if gdf.crs is not None:
        try:
            cea_crs = f"+proj=cea +R={radius_m} +units=m +no_defs"
            areas = gdf.geometry.to_crs(cea_crs).area
            if areas.notna().all() and float(areas.sum()) > 0.0:
                return areas
        except Exception as exc:
            logger.warning("Equal-area projection area fallback: %s", exc)
    if gdf.crs is not None and gdf.crs.is_projected:
        return gdf.geometry.area
    # Latitude-weighted planar degree area fallback
    centroids = gdf.geometry.centroid
    cos_lat = np.maximum(0.05, np.cos(np.radians(centroids.y.to_numpy(dtype=np.float64))))
    return gdf.geometry.area * cos_lat


def _summarize_and_classify_units(
    body: str,
    gdf: gpd.GeoDataFrame,
    overrides: dict[str, str | None],
) -> tuple[gpd.GeoDataFrame, pd.DataFrame]:
    """Classify unique map units, apply overrides, and compute per-unit area shares."""
    areas = _compute_unit_areas(gdf, BODY_RADII_M[body])
    work = gdf.copy()
    work["_area"] = areas.to_numpy(dtype=np.float64)

    summary = (
        work.groupby("_unit", dropna=False, sort=True)
        .agg(
            description=("_desc_full", "first"),
            polygon_count=("_area", "size"),
            total_area=("_area", "sum"),
        )
        .reset_index()
        .rename(columns={"_unit": "unit"})
    )
    total_area = float(summary["total_area"].sum())
    summary["area_share"] = (
        summary["total_area"] / total_area if total_area > 0.0 else 0.0
    )

    unit_to_class: dict[str, str | None] = {}
    unit_to_rule: dict[str, str] = {}
    classes: list[str | None] = []
    rules: list[str] = []
    for _, row in summary.iterrows():
        u = "" if pd.isna(row["unit"]) else str(row["unit"])
        desc = "" if pd.isna(row["description"]) else str(row["description"])
        gclass, rule = classify_unit(body, f"{u} — {desc}" if desc != u else u)
        if u in overrides:
            gclass = overrides[u]
            rule = "override"
        unit_to_class[u] = gclass
        unit_to_rule[u] = rule
        classes.append(gclass)
        rules.append(rule)

    summary["geo_class"] = pd.Series(classes, dtype="string")
    summary["rule_matched"] = pd.Series(rules, dtype="string")
    summary = summary.sort_values("area_share", ascending=False).reset_index(drop=True)

    work["_geo_class"] = work["_unit"].map(unit_to_class).astype("string")
    work["_rule_matched"] = work["_unit"].map(unit_to_rule).astype("string")
    return work, summary


def sample_polygons_at_points(
    gdf: gpd.GeoDataFrame,
    lat: np.ndarray | list[float],
    lon: np.ndarray | list[float],
    body: str,
) -> tuple[np.ndarray, np.ndarray]:
    """Sample polygon unit and geo_class at (lat, lon) coordinates via sjoin(within)."""
    lat_arr = np.asarray(lat, dtype=np.float64)
    lon_arr = np.asarray(lon, dtype=np.float64)
    n = lat_arr.size
    out_unit = np.full(n, None, dtype=object)
    out_class = np.full(n, None, dtype=object)
    if n == 0:
        return out_unit, out_class

    radius_m = BODY_RADII_M[body]
    lon_sample = lon_arr.copy()
    if gdf.crs is not None and gdf.crs.is_geographic:
        b = gdf.total_bounds
        if b[2] > 180.5 and b[0] >= -5.0:
            lon_sample = lon_sample % 360.0

    src_crs = (
        gdf.crs.geodetic_crs
        if (gdf.crs is not None and getattr(gdf.crs, "geodetic_crs", None) is not None)
        else f"+proj=longlat +R={radius_m} +no_defs"
    )
    pts = gpd.GeoDataFrame(
        {"_pt_idx": np.arange(n, dtype=np.int64)},
        geometry=gpd.points_from_xy(lon_sample, lat_arr),
        crs=src_crs,
    )
    if gdf.crs is not None:
        pts = pts.to_crs(gdf.crs)

    poly_sub = gdf[["_unit", "_geo_class", gdf.geometry.name]]
    joined = gpd.sjoin(pts, poly_sub, how="left", predicate="within")
    joined = joined.drop_duplicates(subset=["_pt_idx"], keep="first")

    matched = joined[joined["index_right"].notna()]
    for _, row in matched.iterrows():
        idx = int(row["_pt_idx"])
        out_unit[idx] = None if pd.isna(row["_unit"]) else str(row["_unit"])
        out_class[idx] = None if pd.isna(row["_geo_class"]) else str(row["_geo_class"])

    # Boundary fallback with intersects for any unmatched finite points
    missing_mask = pd.isna(joined.set_index("_pt_idx").reindex(range(n))["index_right"]).to_numpy()
    missing_idx = np.flatnonzero(missing_mask & np.isfinite(lat_arr) & np.isfinite(lon_arr))
    if missing_idx.size > 0:
        pts_miss = pts.iloc[missing_idx]
        joined2 = gpd.sjoin(pts_miss, poly_sub, how="left", predicate="intersects")
        joined2 = joined2.drop_duplicates(subset=["_pt_idx"], keep="first")
        for _, row in joined2[joined2["index_right"].notna()].iterrows():
            idx = int(row["_pt_idx"])
            out_unit[idx] = None if pd.isna(row["_unit"]) else str(row["_unit"])
            out_class[idx] = None if pd.isna(row["_geo_class"]) else str(row["_geo_class"])

    still_missing = int(np.sum(np.array([u is None for u in out_unit])))
    if still_missing > 0:
        logger.warning("%s: %d/%d sample points fell outside all unit polygons", body, still_missing, n)

    return out_unit, out_class


def _majority_vote_target(units: list[str | None], classes: list[str | None]) -> tuple[str | None, str | None, float]:
    """Return (majority_unit, majority_class, class_share) over sampled anchor points."""
    valid_pairs = [(u, c) for u, c in zip(units, classes) if c is not None]
    if not valid_pairs:
        # Check if units exist even when class is null
        valid_units = [u for u in units if u is not None]
        if valid_units:
            maj_u = Counter(valid_units).most_common(1)[0][0]
            return maj_u, None, float("nan")
        return None, None, float("nan")

    class_counts = Counter(c for _, c in valid_pairs)
    # Center anchor tie-breaker (index 0 if valid)
    first_valid_class = valid_pairs[0][1]
    maj_class = sorted(
        class_counts.items(),
        key=lambda kv: (-kv[1], 0 if kv[0] == first_valid_class else 1, kv[0]),
    )[0][0]

    matching_units = [u for u, c in valid_pairs if c == maj_class and u is not None]
    maj_unit = (
        Counter(matching_units).most_common(1)[0][0] if matching_units else None
    )
    share = float(class_counts[maj_class]) / float(len(valid_pairs))
    return maj_unit, maj_class, share


def build_mapping_review_md(
    units_by_body: dict[str, pd.DataFrame],
    out_path: Path,
) -> None:
    """Write geology_mapping_review.md with one row per unit for Moon and Mars (§2.3)."""
    lines: list[str] = [
        "# T14 Geology Unit Mapping Review (Moon and Mars)",
        "",
        "Generated by `pipeline/geology.py` for review at `plan_t12_t15.md` §5.6.",
        "Rows marked with **`[REVIEW]`** used the `default` rule or mapped to `null`.",
        "",
    ]

    for body in ("Moon", "Mars"):
        df = units_by_body[body]
        flagged = df[(df["rule_matched"] == "default") | df["geo_class"].isna()]
        flagged_area = float(flagged["area_share"].sum()) * 100.0
        lines.extend(
            [
                f"## {body} ({len(df)} units; default/null area share = {flagged_area:.2f}%)",
                "",
                "| Flag | Unit | Area % | Class | Rule | Description (<=120 chars) |",
                "| --- | --- | ---: | --- | --- | --- |",
            ]
        )
        for _, row in df.iterrows():
            unit_s = str(row["unit"]).replace("|", "/")
            gclass = "null" if pd.isna(row["geo_class"]) else str(row["geo_class"])
            rule = str(row["rule_matched"])
            is_flag = (rule == "default") or pd.isna(row["geo_class"])
            flag_s = "**`[REVIEW]`**" if is_flag else ""
            desc_raw = "" if pd.isna(row["description"]) else str(row["description"])
            desc_clean = re.sub(r"\s+", " ", desc_raw).strip().replace("|", "/")
            if len(desc_clean) > 120:
                desc_clean = desc_clean[:117] + "..."
            area_pct = float(row["area_share"]) * 100.0
            lines.append(
                f"| {flag_s} | `{unit_s}` | {area_pct:.2f}% | `{gclass}` | `{rule}` | {desc_clean} |"
            )
        lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")


def _git_short_sha(repo_dir: Path) -> str:
    try:
        res = subprocess.run(
            ["git", "-C", str(repo_dir), "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        return res.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def run_geology(
    project_dir: Path,
    t3_dir: Path,
    t4_dir: Path,
    t5_dir: Path,
    out_dir: Path,
    overrides_path: Path | None = DEFAULT_OVERRIDES_PATH,
) -> dict[str, object]:
    """Run T14 geology sampling across Earth, Moon, Mars, and T4 targets."""
    t0 = time.perf_counter()
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = project_dir / "data" / "raw"

    # 1. Earth GLiM
    glim_path = raw_dir / GLIM_ASCII_REL
    logger.info("Loading Earth GLiM raster from %s", glim_path)
    glim_grid = load_glim(glim_path)
    t5_earth = pd.read_parquet(t5_dir / "features_earth.parquet", columns=["lat", "lon"])
    geo_earth = sample_earth_geology(t5_earth, glim_grid)
    geo_earth.to_parquet(out_dir / "geology_earth.parquet", index=False)
    logger.info(
        "Wrote geology_earth.parquet (%d rows, ice_surface=%d, lava_tube_terrain=%d)",
        len(geo_earth),
        int(geo_earth["ice_surface"].sum()),
        int(geo_earth["lava_tube_terrain"].sum()),
    )

    # 2. Moon & Mars polygons + classification
    overrides = _load_overrides(overrides_path)
    gdfs: dict[str, gpd.GeoDataFrame] = {}
    units_summary: dict[str, pd.DataFrame] = {}

    for body, rel_dir, t3_file, out_pq, out_csv in (
        ("Moon", MOON_GEO_DIR_REL, "features_moon.parquet", "geology_moon.parquet", "geology_units_moon.csv"),
        ("Mars", MARS_GEO_DIR_REL, "features_mars.parquet", "geology_mars.parquet", "geology_units_mars.csv"),
    ):
        raw_gdf, unit_col, name_col, desc_col = _load_planetary_polygons(body, raw_dir / rel_dir)
        classified_gdf, summary_df = _summarize_and_classify_units(body, raw_gdf, overrides[body])
        gdfs[body] = classified_gdf
        units_summary[body] = summary_df
        summary_df.to_csv(out_dir / out_csv, index=False)
        logger.info(
            "%s: %d unique units (unit_col=%s, name_col=%s, desc_col=%s) -> %s",
            body,
            len(summary_df),
            unit_col,
            name_col,
            desc_col,
            out_dir / out_csv,
        )

        t3_df = pd.read_parquet(t3_dir / t3_file, columns=["lat", "lon"])
        t3_units, t3_classes = sample_polygons_at_points(
            classified_gdf, t3_df["lat"].to_numpy(), t3_df["lon"].to_numpy(), body
        )
        out_df = pd.DataFrame(
            {
                "lat": t3_df["lat"].to_numpy(dtype=np.float64),
                "lon": t3_df["lon"].to_numpy(dtype=np.float64),
                "unit": pd.Series(t3_units, dtype="string"),
                "geo_class": pd.Series(t3_classes, dtype="string"),
            }
        )
        out_df.to_parquet(out_dir / out_pq, index=False)
        logger.info("Wrote %s (%d rows)", out_dir / out_pq, len(out_df))

    review_path = out_dir / "geology_mapping_review.md"
    build_mapping_review_md(units_summary, review_path)
    logger.info("Wrote %s", review_path)

    # 3. Sample T4 targets (anchor patches for curated targets, center point for clusters)
    targets_df = pd.read_parquet(t4_dir / "targets.parquet", columns=["target_id", "type", "body", "lat", "lon"])
    patches_path = t4_dir / "targets_patches.parquet"
    patches_df = (
        pd.read_parquet(patches_path)
        if patches_path.exists()
        else pd.DataFrame(columns=["target_id", "body", "lat", "lon", "ok"])
    )

    target_records: list[dict[str, object]] = []
    for body in ("Moon", "Mars"):
        body_targets = targets_df[targets_df["body"].astype(str) == body]
        for _, trow in body_targets.iterrows():
            tid = str(trow["target_id"])
            ttype = str(trow["type"])
            if ttype == "CURATED" and not patches_df.empty:
                sub = patches_df[patches_df["target_id"].astype(str) == tid]
                if "ok" in sub.columns and bool(sub["ok"].any()):
                    sub = sub[sub["ok"]]
                if not sub.empty:
                    pts_lat = sub["lat"].to_numpy(dtype=np.float64)
                    pts_lon = sub["lon"].to_numpy(dtype=np.float64)
                else:
                    pts_lat = np.array([float(trow["lat"])])
                    pts_lon = np.array([float(trow["lon"])])
                u_list, c_list = sample_polygons_at_points(gdfs[body], pts_lat, pts_lon, body)
                maj_u, maj_c, share = _majority_vote_target(list(u_list), list(c_list))
            else:
                u_arr, c_arr = sample_polygons_at_points(
                    gdfs[body], [float(trow["lat"])], [float(trow["lon"])], body
                )
                maj_u = None if u_arr[0] is None else str(u_arr[0])
                maj_c = None if c_arr[0] is None else str(c_arr[0])
                share = 1.0 if maj_c is not None else float("nan")

            target_records.append(
                {
                    "target_id": tid,
                    "unit": maj_u,
                    "geo_class": maj_c,
                    "geo_class_share": np.float32(share),
                }
            )

    geo_targets_df = pd.DataFrame(target_records)
    geo_targets_df["target_id"] = geo_targets_df["target_id"].astype("string")
    geo_targets_df["unit"] = geo_targets_df["unit"].astype("string")
    geo_targets_df["geo_class"] = geo_targets_df["geo_class"].astype("string")
    geo_targets_df["geo_class_share"] = pd.to_numeric(
        geo_targets_df["geo_class_share"], errors="coerce"
    ).astype("float32")
    geo_targets_df.to_parquet(out_dir / "geology_targets.parquet", index=False)
    logger.info("Wrote geology_targets.parquet (%d targets)", len(geo_targets_df))

    # 4. Run T14 checks (§2.4)
    def _earth_class(pt_lat: float, pt_lon: float) -> tuple[str | None, str | None]:
        code = glim_at(glim_grid, [pt_lat], [pt_lon])[0]
        return code, (GLIM_TO_CLASS.get(code) if code is not None else None)

    def _planet_class(body: str, pt_lat: float, pt_lon: float) -> tuple[str | None, str | None]:
        u, c = sample_polygons_at_points(gdfs[body], [pt_lat], [pt_lon], body)
        return u[0], c[0]

    target_class_map = {
        str(r["target_id"]): (None if pd.isna(r["geo_class"]) else str(r["geo_class"]))
        for _, r in geo_targets_df.iterrows()
    }

    pin_code, pin_cls = _earth_class(31.8, -113.4)
    tib_code, tib_cls = _earth_class(21.0, 18.0)
    dv_code, dv_cls = _earth_class(-77.5, 162.0)
    grl_code, grl_cls = _earth_class(72.0, -40.0)
    ant_code, ant_cls = _earth_class(-80.0, 0.0)

    imb_u, imb_cls = _planet_class("Moon", 35.0, -15.0)
    tra_u, tra_cls = _planet_class("Moon", 8.0, 31.0)
    shack_cls = target_class_map.get("moon-shackleton-rim")

    oly_u, oly_cls = _planet_class("Mars", 18.65, -133.8)
    ars_u, ars_cls = _planet_class("Mars", -8.3, -120.1)
    npole_u, npole_cls = _planet_class("Mars", 87.0, 0.0)
    arc_cls = target_class_map.get("mars-arcadia-swim")
    uto_cls = target_class_map.get("mars-utopia-zhurong")

    default_or_null: dict[str, dict[str, object]] = {}
    for body in ("Moon", "Mars"):
        sdf = units_summary[body]
        flagged = sdf[(sdf["rule_matched"] == "default") | sdf["geo_class"].isna()]
        default_or_null[body] = {
            "area_frac": round(float(flagged["area_share"].sum()), 5),
            "units": [str(u) for u in flagged["unit"].tolist()],
        }

    checks = [
        {
            "id": 1,
            "name": "earth_pinacate_tibesti",
            "kind": "hard",
            "passed": bool(pin_cls == "VOLCANIC_BASIC" and tib_cls == "VOLCANIC_BASIC"),
            "observed": {
                "pinacate": {"glim_code": pin_code, "geo_class": pin_cls},
                "tibesti": {"glim_code": tib_code, "geo_class": tib_cls},
            },
            "expected": "VOLCANIC_BASIC for both",
        },
        {
            "id": 2,
            "name": "earth_dry_valleys",
            "kind": "hard",
            "passed": bool(dv_cls == "SEDIMENTARY"),
            "observed": {"glim_code": dv_code, "geo_class": dv_cls},
            "expected": "SEDIMENTARY (not ICE)",
        },
        {
            "id": 3,
            "name": "earth_ice_interiors",
            "kind": "hard",
            "passed": bool(grl_cls == "ICE" and ant_cls == "ICE"),
            "observed": {
                "greenland": {"glim_code": grl_code, "geo_class": grl_cls},
                "antarctica": {"glim_code": ant_code, "geo_class": ant_cls},
            },
            "expected": "ICE for both",
        },
        {
            "id": 4,
            "name": "moon_maria",
            "kind": "hard",
            "passed": bool(imb_cls == "VOLCANIC_BASIC" and tra_cls == "VOLCANIC_BASIC"),
            "observed": {
                "mare_imbrium": {"unit": imb_u, "geo_class": imb_cls},
                "mare_tranquillitatis": {"unit": tra_u, "geo_class": tra_cls},
            },
            "expected": "VOLCANIC_BASIC for both",
        },
        {
            "id": 5,
            "name": "moon_shackleton_rim",
            "kind": "soft",
            "passed": bool(shack_cls in ("IMPACT", "CRYSTALLINE")),
            "observed": shack_cls,
            "expected": "IMPACT or CRYSTALLINE",
        },
        {
            "id": 6,
            "name": "mars_tharsis_volcanoes",
            "kind": "hard",
            "passed": bool(oly_cls == "VOLCANIC_BASIC" and ars_cls == "VOLCANIC_BASIC"),
            "observed": {
                "olympus_mons": {"unit": oly_u, "geo_class": oly_cls},
                "arsia_mons": {"unit": ars_u, "geo_class": ars_cls},
            },
            "expected": "VOLCANIC_BASIC for both",
        },
        {
            "id": 7,
            "name": "mars_north_polar_cap",
            "kind": "hard",
            "passed": bool(npole_cls == "ICE"),
            "observed": {"unit": npole_u, "geo_class": npole_cls},
            "expected": "ICE",
        },
        {
            "id": 8,
            "name": "mars_arcadia_utopia",
            "kind": "soft",
            "passed": bool(arc_cls == "SEDIMENTARY" and uto_cls == "SEDIMENTARY"),
            "observed": {"arcadia_swim": arc_cls, "utopia_zhurong": uto_cls},
            "expected": "SEDIMENTARY for both",
        },
        {
            "id": 9,
            "name": "default_or_null_area_share",
            "kind": "soft",
            "passed": bool(
                default_or_null["Moon"]["area_frac"] < 0.10
                and default_or_null["Mars"]["area_frac"] < 0.10
            ),
            "observed": default_or_null,
            "expected": "< 0.10 area share for each body",
        },
    ]

    hard_checks = [c for c in checks if c["kind"] == "hard"]
    soft_checks = [c for c in checks if c["kind"] == "soft"]
    hard_passed = sum(1 for c in hard_checks if c["passed"])
    soft_passed = sum(1 for c in soft_checks if c["passed"])

    report = {
        "task": "T14",
        "slurm_job_id": os.environ.get("SLURM_JOB_ID"),
        "commit": _git_short_sha(Path(__file__).resolve().parents[2]),
        "runtime_s": round(time.perf_counter() - t0, 3),
        "earth_class_counts": {
            str(k): int(v)
            for k, v in geo_earth["geo_class"].value_counts(dropna=False).items()
        },
        "hard_passed": hard_passed,
        "hard_total": len(hard_checks),
        "soft_passed": soft_passed,
        "soft_total": len(soft_checks),
        "checks": checks,
    }
    checks_path = out_dir / "t14_checks.json"
    with open(checks_path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, allow_nan=False)

    logger.info(
        "T14 checks: hard %d/%d, soft %d/%d -> %s",
        hard_passed,
        len(hard_checks),
        soft_passed,
        len(soft_checks),
        checks_path,
    )
    if hard_passed < len(hard_checks):
        failed_names = [c["name"] for c in hard_checks if not c["passed"]]
        raise RuntimeError(f"T14 hard checks failed: {failed_names}")
    return report


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build T14 geology layers for Earth, Moon, Mars.")
    p.add_argument("--project-dir", type=Path, default=YUCA_PROJECT_DIR)
    p.add_argument("--t3-dir", type=Path, default=YUCA_PROJECT_DIR / "runs" / "2242278")
    p.add_argument("--t4-dir", type=Path, default=YUCA_PROJECT_DIR / "runs" / "2242423")
    p.add_argument("--t5-dir", type=Path, default=YUCA_PROJECT_DIR / "runs" / "2242438")
    p.add_argument("--out-dir", type=Path, required=True)
    p.add_argument("--overrides", type=Path, default=DEFAULT_OVERRIDES_PATH)
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="[%(levelname)s] %(name)s: %(message)s",
    )
    args = _parse_args(argv)
    run_geology(
        project_dir=args.project_dir,
        t3_dir=args.t3_dir,
        t4_dir=args.t4_dir,
        t5_dir=args.t5_dir,
        out_dir=args.out_dir,
        overrides_path=args.overrides,
    )


if __name__ == "__main__":
    main()
