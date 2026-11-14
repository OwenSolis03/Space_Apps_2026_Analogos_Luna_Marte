"""Export v2 matching results into analogs_universe.json, run T7/T8 hard checks,
and generate t7_report.md (T8).

Universe schema (v2.0.0 with T16 missing-data policy):
- metadata: version, generated_at, runs, scoring_policy, preset_status_summary, ...
- mission_presets: presets with label, applies_to, weights
- limits: physical limits for Moon and Mars
- targets: list of target entries, each with:
  - id, type, body, name, lat, lon, category, why, ...
  - available_dims: list of dimension names available for this target
  - preset_status: dict mapping preset_key to {status, coverage, missing_dims}
  - analogs: list of analog entries, each with:
    - id, lat, lon, country, classification, ...
    - sub_scores: raw S_* scores (null where missing)
    - msi_by_preset: MSI per preset (null if target's preset status is not "ok")
    - selected_by: list of presets that selected this analog
    - earth_missing_dims: list of target available dimensions missing on Earth
    - ...
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import logging
import math
import os
from pathlib import Path
import subprocess
import time

import numpy as np
import pandas as pd

from .config import BODY_RADII_M, YUCA_PROJECT_DIR
from .geology_rules import GEO_CLASSES, GEO_SIMILARITY
from .match import (
    DIMENSIONS,
    EARTH_MISSING_SCORE,
    ICE_CAP_EXEMPT_PRESETS,
    MATCH_FEATURES,
    MAX_ICE_SURFACE_PER_PRESET,
    MIN_PRESET_COVERAGE,
    MIN_SEP_KM,
    PRESET_KEYS,
    PRESETS,
    Normalizer,
    TargetVec,
    available_dims,
    build_earth_arrays,
    format_earth_id,
    haversine_km,
    load_layers,
    mismatches,
    msi,
    preset_status,
    score_target,
    select_diverse,
    thermal_ranks,
)
from .targets import ALL_AUX_AND_DERIVED_COLS, AUX_COLS, TARGETS_JSON

logger = logging.getLogger(__name__)

DEFAULT_LIMITS_JSON: Path = Path(__file__).parent / "data" / "limits.json"
DEFAULT_SAMPLE_JSON: Path = (
    Path(__file__).resolve().parents[1] / "app" / "public" / "data" / "sample.json"
)

MAX_UNIVERSE_BYTES: int = 20 * 1024 * 1024
MIN_COVERAGE_PER_PRESET: int = 20
TOP_N_REPORT: int = 30
OLYMPUS_LAT: float = 18.65
OLYMPUS_LON: float = -133.80
FRACTION_AUX_KEYS: set[str] = {"wac_percentile", "ice_stable_frac"}

REQUIRED_LIMIT_KEYS: set[str] = {"factor", "earth", "target", "consequence", "source"}
REQUIRED_TARGET_KEYS: set[str] = {
    "id",
    "type",
    "body",
    "name",
    "lat",
    "lon",
    "category",
    "why",
    "source_url",
    "iau_label",
    "features",
    "aux",
    "available_dims",
    "preset_status",
    "geology",
    "dust",
    "ice",
    "analogs",
}
REQUIRED_ANALOG_KEYS: set[str] = {
    "id",
    "lat",
    "lon",
    "country",
    "classification",
    "known_region",
    "sub_scores",
    "msi_by_preset",
    "selected_by",
    "features",
    "earth_env",
    "logistics",
    "polar_cold",
    "geology",
    "dust",
    "ice",
    "subsurface_note",
    "mismatches",
    "earth_missing_dims",
}


def default_datasets() -> list[dict[str, object]]:
    """Return the pipeline dataset provenance entries using verified doc URLs only."""
    return [
        {
            "name": "MGS MOLA DEM 463 m",
            "source": "NASA PDS / USGS Astrogeology",
            # TODO(verify): add canonical USGS Astrogeology catalog URL for MOLA 463 m
            "url": None,
        },
        {
            "name": "Mars ODY THEMIS IR Day/Night 100 m",
            "source": "NASA PDS / USGS Astrogeology",
            # TODO(verify): add canonical USGS Astrogeology catalog URLs for THEMIS Day/Night 100 m
            "url": None,
        },
        {
            "name": "LRO LOLA LDEM 118 m",
            "source": "NASA / USGS Astrogeology",
            "url": "https://astrogeology.usgs.gov/search/map/moon_lro_lola_dem_118m",
        },
        {
            "name": "LRO LROC WAC Mosaic 100 m",
            "source": "NASA / USGS Astrogeology",
            # TODO(verify): add canonical USGS Astrogeology catalog URL for LROC WAC 100 m
            "url": None,
        },
        {
            "name": "LRO Diviner Polar Resource Product (south)",
            "source": "NASA PDS Geosciences",
            "url": "https://pds-geosciences.wustl.edu/lro/urn-nasa-pds-lro_diviner_derived1/data_derived_prp/",
        },
        {
            "name": "USGS Lunar Ice Favorability Index",
            "source": "USGS Astrogeology",
            # TODO(verify): add canonical USGS catalog URL for Moon_IceFavorabilityIndex
            "url": None,
        },
        {
            "name": "Copernicus DEM GLO-90",
            "source": "ESA",
            "url": "https://dataspace.copernicus.eu/explore-data/data-collections/copernicus-contributing-missions/collections-description/COP-DEM",
        },
        {
            "name": "MODIS MOD13C2 & MOD11C3 (2023)",
            "source": "NASA Earthdata / LP DAAC",
            # TODO(verify): add LP DAAC landing URLs for MOD13C2 v061 and MOD11C3 v061
            "url": None,
        },
        {
            "name": "Natural Earth 10m (roads, airports, countries)",
            "source": "Natural Earth",
            # TODO(verify): add canonical Natural Earth 10m cultural vectors page URL
            "url": None,
        },
        {
            "name": "GLiM Global Lithological Map 0.5 deg (Hartmann and Moosdorf 2012)",
            "source": "PANGAEA",
            "url": "https://doi.pangaea.de/10.1594/PANGAEA.788537",
        },
        {
            "name": "USGS SIM 3292 Global Geologic Map of Mars (Tanaka et al. 2014)",
            "source": "USGS",
            "url": "https://pubs.usgs.gov/sim/3292/",
        },
        {
            "name": "USGS Unified Geologic Map of the Moon, 1:5M (Fortezzo, Spudis and Harrel 2020)",
            "source": "USGS Astrogeology",
            "url": "https://asc-astropedia.s3.us-west-2.amazonaws.com/Moon/Geology/Unified_Geologic_Map_of_the_Moon_GIS_v2.zip",
        },
        {
            "name": "Mars dust climatology, kriged CDOD v2 (Montabone et al. 2015, 2020)",
            "source": "LMD / Mars Climate Database",
            "url": "https://www-mars.lmd.jussieu.fr/mars/dust_climatology/",
        },
        {
            "name": "MODIS Terra MOD08_M3 collection 6.1 (Deep Blue AOD 550 nm, 2019-2023)",
            "source": "NASA Earthdata / LAADS DAAC",
            # TODO(verify): add LAADS landing URL for MOD08_M3 v6.1
            "url": None,
        },
        {
            "name": "Gazetteer of Planetary Nomenclature",
            "source": "USGS / IAU",
            "url": "https://planetarynames.wr.usgs.gov/",
        },
    ]


def _finite_float(val: object) -> float | None:
    if val is None or pd.isna(val):
        return None
    f = float(val)
    if not math.isfinite(f):
        return None
    return f


def _round_val(val: object, decimals: int) -> float | None:
    f = _finite_float(val)
    if f is None:
        return None
    rounded = round(f, decimals)
    return 0.0 if rounded == 0.0 else rounded


def _clean_str(val: object) -> str | None:
    if val is None or pd.isna(val):
        return None
    s = str(val).strip()
    if not s or s.lower() == "nan":
        return None
    return s


def load_limits(
    limits_path: Path | None = None,
    sample_json_path: Path | None = None,
) -> tuple[dict[str, list[dict[str, object]]], str]:
    """Load T11 physical body limits from limits.json, or fall back to sample.json."""
    l_path = DEFAULT_LIMITS_JSON if limits_path is None else Path(limits_path)
    s_path = DEFAULT_SAMPLE_JSON if sample_json_path is None else Path(sample_json_path)

    if l_path.exists():
        with open(l_path, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
        out: dict[str, list[dict[str, object]]] = {}
        for body in ("Moon", "Mars"):
            if body not in raw or not isinstance(raw[body], list):
                raise ValueError(f"limits.json missing list for body {body!r}")
            cleaned: list[dict[str, object]] = []
            for idx, entry in enumerate(raw[body]):
                if not isinstance(entry, dict):
                    raise ValueError(f"limits.json {body}[{idx}] must be an object")
                missing = REQUIRED_LIMIT_KEYS - set(entry.keys())
                if missing:
                    raise ValueError(f"limits.json {body}[{idx}] missing keys: {sorted(missing)}")
                if not _clean_str(entry.get("source")):
                    raise ValueError(f"limits.json {body}[{idx}] has empty source")
                cleaned.append({k: entry[k] for k in ("factor", "earth", "target", "consequence", "source")})
            out[body] = cleaned
        return out, "pipeline/data/limits.json"

    logger.warning(
        "Physical limits file %s not found; using provisional limits from %s",
        l_path,
        s_path,
    )
    if not s_path.exists():
        raise FileNotFoundError(
            f"Neither limits.json ({l_path}) nor fallback sample.json ({s_path}) exists."
        )
    with open(s_path, "r", encoding="utf-8") as fh:
        sample = json.load(fh)
    limits_raw = sample.get("limits")
    if not isinstance(limits_raw, dict) or "Moon" not in limits_raw or "Mars" not in limits_raw:
        raise ValueError(f"Fallback sample JSON {s_path} missing valid 'limits' section")
    return {
        "Moon": list(limits_raw["Moon"]),
        "Mars": list(limits_raw["Mars"]),
    }, "provisional (sample.json)"


def _curated_order_map(targets_json_path: Path | None) -> dict[str, int]:
    path = TARGETS_JSON if targets_json_path is None else Path(targets_json_path)
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    return {str(t["id"]): idx for idx, t in enumerate(data.get("targets", []))}


def order_targets(
    targets_df: pd.DataFrame,
    targets_json_path: Path | None = None,
) -> pd.DataFrame:
    """Order targets curated first (Moon, then Mars in targets.json order), then clusters by body & rank."""
    order_map = _curated_order_map(targets_json_path)
    sort_keys: list[tuple[int, int, int, str]] = []
    for orig_idx, row in targets_df.iterrows():
        tid = str(row["target_id"])
        ttype = str(row.get("type", "")).upper()
        body = str(row.get("body", ""))
        type_ord = 0 if ttype == "CURATED" else 1
        body_ord = 0 if body == "Moon" else (1 if body == "Mars" else 2)
        if ttype == "CURATED":
            item_ord = order_map.get(tid, 100_000 + int(orig_idx))
        else:
            rank_val = _finite_float(row.get("cluster_rank"))
            item_ord = int(rank_val) if rank_val is not None else 100_000 + int(orig_idx)
        sort_keys.append((type_ord, body_ord, item_ord, tid))
    ordered_positions = sorted(range(len(targets_df)), key=lambda i: sort_keys[i])
    return targets_df.iloc[ordered_positions].reset_index(drop=True)


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


def _run_label(path_str: str | None) -> str:
    if not path_str:
        return "unknown"
    return Path(path_str).name or str(path_str)


def _target_aux_dict(t_row: pd.Series, body: str) -> dict[str, float | None]:
    if body in AUX_COLS:
        keys = list(AUX_COLS[body])
        if body == "Moon":
            keys.append("ice_stable_frac")
    else:
        keys = [c for c in ALL_AUX_AND_DERIVED_COLS if c in t_row.index]

    aux: dict[str, float | None] = {}
    for key in keys:
        if key not in t_row.index:
            aux[key] = None
            continue
        decimals = 4 if key in FRACTION_AUX_KEYS else 2
        aux[key] = _round_val(t_row[key], decimals)
    return aux


def _opt_round(val: object, decimals: int) -> float | None:
    return _round_val(val, decimals)


def _bool_or_none(val: object) -> bool | None:
    if val is None:
        return None
    try:
        if pd.isna(val):
            return None
    except (TypeError, ValueError):
        pass
    return bool(val)


def _analog_geology(e_row: dict[str, object]) -> dict[str, object]:
    return {
        "glim_code": _clean_str(e_row.get("glim_code")),
        "geo_class": _clean_str(e_row.get("geo_class")),
        "lava_tube_terrain": bool(_bool_or_none(e_row.get("lava_tube_terrain")) or False),
        "ice_surface": bool(_bool_or_none(e_row.get("ice_surface")) or False),
    }


def _analog_dust(e_row: dict[str, object]) -> dict[str, object]:
    return {
        "level_rank": _opt_round(e_row.get("dust_level_rank"), 3),
        "seasonality_rank": _opt_round(e_row.get("dust_seasonality_rank"), 3),
        "peak_phase_deg": _opt_round(e_row.get("dust_peak_phase_deg"), 1),
    }


def _analog_ice(e_row: dict[str, object]) -> dict[str, object]:
    return {
        "cold_rank": _opt_round(e_row.get("cold_rank_E"), 3),
        "ice_E": _opt_round(e_row.get("ice_E"), 2),
    }


SUBSURFACE_NOTE: str = "Basaltic volcanic terrain: lava tubes are possible here (not mapped)"

CITATIONS: list[str] = [
    "Hartmann, J. and Moosdorf, N. (2012). The new global lithological map database GLiM. Geochem. Geophys. Geosyst., doi:10.1029/2012GC004370 (data: PANGAEA 10.1594/PANGAEA.788537).",
    "Tanaka, K.L. et al. (2014). Geologic map of Mars. USGS Scientific Investigations Map 3292.",
    "Fortezzo, C.M., Spudis, P.D. and Harrel, S.L. (2020). Release of the digital Unified Global Geologic Map of the Moon at 1:5,000,000-scale. USGS.",
    "Montabone, L. et al. (2015). Eight-year climatology of dust optical depth on Mars. Icarus 251, 65-95, doi:10.1016/j.icarus.2014.12.034.",
    "Montabone, L. et al. (2020). Martian year 34 column dust climatology from Mars Climate Sounder observations. J. Geophys. Res. Planets, doi:10.1029/2019JE006111.",
    "MODIS Terra Atmosphere Monthly Global Product MOD08_M3, collection 6.1 (NASA LAADS DAAC).",
]

NOT_MODELLED: list[dict[str, str]] = [
    {
        "item": "mineralogy (spectral)",
        "note": "Geology is regional lithology and mapped units, not spectra: two sites with the same class can differ in mineral composition.",
    },
    {
        "item": "biology",
        "note": "Earth analogs are selected as bare ground only; microbial life, soil biology and habitability are not modelled.",
    },
    {
        "item": "caves (mapped)",
        "note": "Lava tubes are only suggested by basaltic terrain; no cave inventory is used and nothing is scored on it.",
    },
]


def _geology_similarity_dict() -> dict[str, dict[str, float]]:
    return {a: {b: float(v) for b, v in row.items()} for a, row in GEO_SIMILARITY.items()}


def build_universe_dict(
    matches_df: pd.DataFrame,
    targets_df: pd.DataFrame,
    earth_df: pd.DataFrame,
    matches_meta: dict[str, object] | None = None,
    limits_path: Path | None = None,
    sample_json_path: Path | None = None,
    targets_json_path: Path | None = None,
    export_job_id: str | None = None,
) -> dict[str, object]:
    """Assemble the complete analogs_universe v2 structure from T4, T5, and T7 outputs."""
    meta_in = dict(matches_meta or {})
    limits_dict, limits_source = load_limits(limits_path=limits_path, sample_json_path=sample_json_path)

    earth_idx_df = earth_df.reset_index(drop=True).copy()
    if "earth_id" not in earth_idx_df.columns:
        earth_idx_df["earth_id"] = [
            format_earth_id(la, lo)
            for la, lo in zip(earth_idx_df["lat"].to_numpy(), earth_idx_df["lon"].to_numpy())
        ]
    earth_lookup = {
        str(rec["earth_id"]): rec
        for rec in earth_idx_df.to_dict(orient="records")
    }

    matches_by_target: dict[str, list[dict[str, object]]] = {}
    if not matches_df.empty:
        for tid, grp in matches_df.groupby("target_id", sort=False):
            matches_by_target[str(tid)] = grp.to_dict(orient="records")

    active_targets = targets_df
    if "status" in active_targets.columns:
        active_targets = active_targets[active_targets["status"] == "ok"]
    if not matches_df.empty:
        matched_ids = set(matches_df["target_id"].astype(str).unique())
        active_targets = active_targets[active_targets["target_id"].astype(str).isin(matched_ids)]
    ordered_targets = order_targets(active_targets, targets_json_path=targets_json_path)

    target_entries: list[dict[str, object]] = []
    missing_earth_ids: list[str] = []

    meta_status_records = meta_in.get("preset_status", [])
    meta_status_map: dict[tuple[str, str], dict[str, object]] = {}
    if isinstance(meta_status_records, list):
        for rec in meta_status_records:
            if isinstance(rec, dict) and "target_id" in rec and "preset" in rec:
                meta_status_map[(str(rec["target_id"]), str(rec["preset"]))] = rec

    for _, t_row in ordered_targets.iterrows():
        tid = str(t_row["target_id"])
        body = str(t_row["body"])
        m_rows = matches_by_target.get(tid, [])

        target_preset_status: dict[str, dict[str, object]] = {}
        avail_dims_set: set[str] = set()
        has_meta_status = all((tid, pkey) in meta_status_map for pkey in PRESET_KEYS)

        if has_meta_status:
            for pkey in PRESET_KEYS:
                rec = meta_status_map[(tid, pkey)]
                miss = rec.get("missing_dims", "")
                miss_list = (
                    [d.strip() for d in miss.split(",") if d.strip()]
                    if isinstance(miss, str)
                    else list(miss)
                )
                av = rec.get("available_dims", "")
                av_list = (
                    [d.strip() for d in av.split(",") if d.strip()]
                    if isinstance(av, str)
                    else list(av)
                )
                avail_dims_set.update(av_list)
                target_preset_status[pkey] = {
                    "status": str(rec.get("status", "ok")),
                    "coverage": round(float(rec.get("coverage", 1.0)), 3),
                    "missing_dims": miss_list,
                }
            available_dims_list = sorted(avail_dims_set)
        else:
            zt_val = _finite_float(t_row.get("themis_delta"))
            if zt_val is None:
                d = _finite_float(t_row.get("themis_day"))
                n = _finite_float(t_row.get("themis_night"))
                if d is not None and n is not None:
                    zt_val = d - n
            tv = TargetVec(
                body=str(body),
                z_t=np.zeros(6, dtype=np.float64),
                zt_t=float(zt_val) if zt_val is not None else float("nan"),
                lat=float(_finite_float(t_row.get("lat")) or 0.0),
                geo_class=_clean_str(t_row.get("geo_class")),
                dust_level_rank=float(_finite_float(t_row.get("dust_level_rank")) if _finite_float(t_row.get("dust_level_rank")) is not None else float("nan")),
                dust_season_rank=float(_finite_float(t_row.get("dust_seasonality_rank")) if _finite_float(t_row.get("dust_seasonality_rank")) is not None else float("nan")),
                dust_phase=float(_finite_float(t_row.get("dust_peak_phase_deg")) if _finite_float(t_row.get("dust_peak_phase_deg")) is not None else float("nan")),
                cold_rank=float(_finite_float(t_row.get("cold_rank_T")) if _finite_float(t_row.get("cold_rank_T")) is not None else float("nan")),
                ice_t=float(_finite_float(t_row.get("ice_T")) if _finite_float(t_row.get("ice_T")) is not None else float("nan")),
            )
            tdims = available_dims(tv)
            available_dims_list = sorted(tdims)
            for pkey in PRESET_KEYS:
                status, cov, miss = preset_status(
                    PRESETS[pkey]["weights"],
                    body,
                    PRESETS[pkey].get("applies_to"),
                    tdims,
                )
                target_preset_status[pkey] = {
                    "status": status,
                    "coverage": round(float(cov), 3),
                    "missing_dims": miss,
                }

        analogs_list: list[dict[str, object]] = []
        for m_row in m_rows:
            eid = str(m_row["earth_id"])
            e_row = earth_lookup.get(eid)
            if e_row is None:
                missing_earth_ids.append(eid)
                continue

            sub_scores = {
                "topography": _round_val(m_row.get("S_topography"), 3),
                "roughness": _round_val(m_row.get("S_roughness"), 3),
                "environment": _round_val(m_row.get("S_environment"), 3),
                "thermal": None if body == "Moon" else _round_val(m_row.get("S_thermal"), 3),
                "geology": _round_val(m_row.get("S_geology"), 3),
                "dust": None if body == "Moon" else _round_val(m_row.get("S_dust"), 3),
                "ice": _round_val(m_row.get("S_ice"), 3),
            }
            msi_by_preset = {
                pkey: (
                    None
                    if target_preset_status[pkey]["status"] != "ok"
                    else _round_val(m_row.get(f"msi_{pkey}"), 3)
                )
                for pkey in PRESET_KEYS
            }
            selected_by = [tok for tok in str(m_row.get("selected_by", "")).split(",") if tok]
            features_dict = {
                feat: _round_val(e_row.get(feat), 2)
                for feat in [*MATCH_FEATURES, "mean_elev_m"]
            }
            earth_env = {
                "ndvi_max": _round_val(e_row.get("ndvi_max"), 2),
                "lst_day_c": _round_val(e_row.get("lst_day_c"), 2),
                "lst_night_c": _round_val(e_row.get("lst_night_c"), 2),
                "lst_amplitude_c": _round_val(e_row.get("lst_amplitude_c"), 2),
                "ndvi_missing": bool(e_row.get("ndvi_missing", False)),
            }
            logistics = {
                "dist_road_km": _round_val(e_row.get("dist_road_km"), 2),
                "dist_airport_km": _round_val(e_row.get("dist_airport_km"), 2),
                "nearest_airport_iata": _clean_str(e_row.get("nearest_airport_iata")),
                "nearest_airport_name": _clean_str(e_row.get("nearest_airport_name")),
            }
            mm_raw = m_row.get("mismatches_json")
            mm_list = json.loads(mm_raw) if isinstance(mm_raw, str) and mm_raw else []

            raw_emd = m_row.get("earth_missing_dims")
            if isinstance(raw_emd, str):
                earth_missing_dims = [d.strip() for d in raw_emd.split(",") if d.strip()]
            elif isinstance(raw_emd, (list, tuple, set)):
                earth_missing_dims = list(raw_emd)
            else:
                earth_missing_dims = []

            analogs_list.append(
                {
                    "id": eid,
                    "lat": _round_val(m_row["lat"], 4),
                    "lon": _round_val(m_row["lon"], 4),
                    "country": _clean_str(e_row.get("country")),
                    "classification": _clean_str(e_row.get("classification")) or "NEW_CANDIDATE",
                    "known_region": _clean_str(e_row.get("known_region")),
                    "sub_scores": sub_scores,
                    "msi_by_preset": msi_by_preset,
                    "selected_by": selected_by,
                    "features": features_dict,
                    "earth_env": earth_env,
                    "logistics": logistics,
                    "polar_cold": bool(m_row.get("polar_cold", False)),
                    "geology": _analog_geology(e_row),
                    "dust": _analog_dust(e_row),
                    "ice": _analog_ice(e_row),
                    "subsurface_note": (
                        SUBSURFACE_NOTE
                        if (
                            bool(_bool_or_none(e_row.get("lava_tube_terrain")) or False)
                            and _clean_str(t_row.get("geo_class")) == "VOLCANIC_BASIC"
                        )
                        else None
                    ),
                    "mismatches": mm_list,
                    "earth_missing_dims": earth_missing_dims,
                }
            )

        analogs_list.sort(
            key=lambda a: (
                -(
                    a["msi_by_preset"]["mobility_and_traction"]
                    if a["msi_by_preset"]["mobility_and_traction"] is not None
                    else -1.0
                ),
                a["id"],
            )
        )

        t_features = {
            feat: _round_val(t_row.get(feat), 2)
            for feat in [*MATCH_FEATURES, "mean_elev_m"]
        }
        target_entries.append(
            {
                "id": tid,
                "type": str(t_row["type"]),
                "body": body,
                "name": str(t_row["name"]),
                "lat": _round_val(t_row["lat"], 4),
                "lon": _round_val(t_row["lon"], 4),
                "category": _clean_str(t_row.get("category")),
                "why": _clean_str(t_row.get("why")),
                "source_url": _clean_str(t_row.get("source_url")),
                "coord_source_url": _clean_str(t_row.get("coord_source_url")),
                "anchor_note": _clean_str(t_row.get("anchor_note")),
                "iau_label": _clean_str(t_row.get("iau_label")),
                "features": t_features,
                "aux": _target_aux_dict(t_row, body),
                "available_dims": available_dims_list,
                "preset_status": target_preset_status,
                "geology": {
                    "unit": _clean_str(t_row.get("geo_unit")),
                    "geo_class": _clean_str(t_row.get("geo_class")),
                    "geo_class_share": _round_val(t_row.get("geo_class_share"), 3),
                },
                "dust": (
                    None
                    if body == "Moon"
                    else {
                        "level_rank": _round_val(t_row.get("dust_level_rank"), 3),
                        "seasonality_rank": _round_val(t_row.get("dust_seasonality_rank"), 3),
                        "peak_phase_deg": _round_val(t_row.get("dust_peak_phase_deg"), 1),
                    }
                ),
                "ice": {
                    "cold_rank": _round_val(t_row.get("cold_rank_T"), 3),
                    "ice_T": _round_val(t_row.get("ice_T"), 2),
                    "ice_source": _clean_str(t_row.get("ice_source")),
                },
                "analogs": analogs_list,
            }
        )

    if missing_earth_ids:
        raise KeyError(
            f"{len(missing_earth_ids)} match rows reference unknown earth_id(s), e.g. {missing_earth_ids[:3]}"
        )

    job_id = export_job_id or meta_in.get("slurm_job_id") or os.environ.get("SLURM_JOB_ID")
    t3_lbl = _run_label(meta_in.get("t3_dir"))
    t4_lbl = _run_label(meta_in.get("t4_dir"))
    t5_lbl = _run_label(meta_in.get("t5_dir"))
    t12_lbl = _run_label(meta_in.get("t12_dir"))
    t13_lbl = _run_label(meta_in.get("t13_dir"))
    t14_lbl = _run_label(meta_in.get("t14_dir"))
    t7_lbl = str(job_id) if job_id else "manual"
    sigma_scale = float(meta_in.get("sigma_scale", 1.0))

    metadata = {
        "version": "2.0.0",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": (
            f"pipeline v2 (T3 {t3_lbl}, T4 {t4_lbl}, T5 {t5_lbl}, T12 {t12_lbl}, "
            f"T13 {t13_lbl}, T14 {t14_lbl}, T15 {t7_lbl})"
        ),
        "runs": {
            "T3": t3_lbl,
            "T4": t4_lbl,
            "T5": t5_lbl,
            "T12": t12_lbl,
            "T13": t13_lbl,
            "T14": t14_lbl,
            "match_export": t7_lbl,
        },
        "slurm_job_id": str(job_id) if job_id is not None else None,
        "commit": meta_in.get("commit") or _git_short_sha(Path(__file__).resolve().parents[1]),
        "limits_source": limits_source,
        "patch": {
            "size_km": 32,
            "res_m": 500,
            "projection": "local azimuthal equidistant",
        },
        "earth_patches_evaluated": int(meta_in.get("earth_patches_evaluated", len(earth_idx_df))),
        "sigma": {
            "topography": round(sigma_scale, 4),
            "roughness": round(sigma_scale, 4),
        },
        "normalization": meta_in.get("normalization", {}),
        "selection": {
            "top_n": 30,
            "min_sep_km": int(MIN_SEP_KM),
            "candidate_pool": "none: every Earth patch is scored for every target",
            "max_ice_surface_per_preset": MAX_ICE_SURFACE_PER_PRESET,
            "ice_cap_exempt_presets": list(ICE_CAP_EXEMPT_PRESETS),
            "dust_tropical_rule": "dust phase term dropped when |lat| < 15 deg for the Earth patch or the target",
        },
        "dimensions": DIMENSIONS,
        "geology_classes": list(GEO_CLASSES),
        "geology_similarity": _geology_similarity_dict(),
        "citations": CITATIONS,
        "not_modelled": NOT_MODELLED,
        "datasets": default_datasets(),
        "scoring_policy": {
            "earth_missing_score": EARTH_MISSING_SCORE,
            "min_preset_coverage": MIN_PRESET_COVERAGE,
            "rules": [
                "A dimension that does not apply to the target's body is ignored, and presets are only computed for the bodies in applies_to.",
                "A dimension the target has no data for is ignored, but if the preset weight left is below 60% the target is not ranked for that preset.",
                "If the target has a dimension and the Earth patch does not, that dimension scores 0 (no evidence, no credit).",
                "Missing NDVI (permanent snow and ice) still counts as bare ground for the aridity dimension.",
            ],
        },
        "preset_status_summary": {
            b: {
                pkey: {
                    st: sum(
                        1
                        for t in target_entries
                        if t["body"] == b and t["preset_status"][pkey]["status"] == st
                    )
                    for st in sorted(
                        set(
                            t["preset_status"][pkey]["status"]
                            for t in target_entries
                            if t["body"] == b
                        )
                    )
                }
                for pkey in PRESET_KEYS
            }
            for b in sorted(set(t["body"] for t in target_entries))
        },
    }

    mission_presets = {
        pkey: {
            "label": PRESETS[pkey]["label"],
            "applies_to": list(PRESETS[pkey]["applies_to"]),
            "weights": dict(PRESETS[pkey]["weights"]),
        }
        for pkey in PRESET_KEYS
    }

    return {
        "metadata": metadata,
        "mission_presets": mission_presets,
        "limits": limits_dict,
        "targets": target_entries,
    }


def write_universe_json(universe: dict[str, object], out_dir: Path) -> list[Path]:
    """Write analogs_universe.json (splitting by body if > 20 MB), disallowing NaN/Infinity."""
    out_dir.mkdir(parents=True, exist_ok=True)
    main_path = out_dir / "analogs_universe.json"
    serialized = json.dumps(universe, allow_nan=False, separators=(",", ":"))
    size_bytes = len(serialized.encode("utf-8"))

    if size_bytes <= MAX_UNIVERSE_BYTES:
        main_path.write_text(serialized, encoding="utf-8")
        logger.info("Wrote %s (%.2f MB)", main_path, size_bytes / (1024.0 * 1024.0))
        return [main_path]

    logger.warning(
        "analogs_universe.json size (%.2f MB) exceeds 20 MB limit; splitting by body",
        size_bytes / (1024.0 * 1024.0),
    )
    written: list[Path] = []
    splits: dict[str, str] = {}
    targets_all = list(universe["targets"])
    for body in ("Moon", "Mars"):
        fname = f"analogs_{body.lower()}.json"
        fpath = out_dir / fname
        body_payload = {
            "metadata": universe["metadata"],
            "mission_presets": universe["mission_presets"],
            "limits": universe["limits"],
            "targets": [t for t in targets_all if t["body"] == body],
        }
        body_text = json.dumps(body_payload, allow_nan=False, separators=(",", ":"))
        fpath.write_text(body_text, encoding="utf-8")
        splits[body] = fname
        written.append(fpath)

    index_payload = {
        "metadata": universe["metadata"],
        "mission_presets": universe["mission_presets"],
        "limits": universe["limits"],
        "splits": splits,
    }
    main_path.write_text(json.dumps(index_payload, allow_nan=False, separators=(",", ":")), encoding="utf-8")
    written.insert(0, main_path)
    return written


def _reject_nonfinite(token: str) -> object:
    raise ValueError(f"Non-finite JSON constant encountered: {token!r}")


def _validate_target_and_analog_keys(targets: list[dict[str, object]]) -> list[str]:
    errors: list[str] = []
    for t in targets:
        missing_t = REQUIRED_TARGET_KEYS - set(t.keys())
        if missing_t:
            errors.append(f"Target {t.get('id')} missing keys: {sorted(missing_t)}")
            break
        for a in t.get("analogs", []):
            missing_a = REQUIRED_ANALOG_KEYS - set(a.keys())
            if missing_a:
                errors.append(f"Analog {a.get('id')} under {t.get('id')} missing keys: {sorted(missing_a)}")
                return errors
    return errors


MARS_PLAINS_IDS: tuple[str, ...] = (
    "mars-elysium-insight",
    "mars-arcadia-swim",
    "mars-utopia-zhurong",
    "mars-gusev-spirit",
    "mars-meridiani-opportunity",
)
PLAINS_SPREAD_MIN: float = 0.012


def _preset_top(target: dict[str, object], preset: str, n: int) -> list[dict[str, object]]:
    """Analogs selected by a preset, best MSI first."""
    sel = [
        a
        for a in target.get("analogs", [])
        if preset in a.get("selected_by", []) and a["msi_by_preset"].get(preset) is not None
    ]
    sel.sort(key=lambda a: (-float(a["msi_by_preset"][preset]), a["id"]))
    return sel[:n]


def run_t7_checks(
    matches_df: pd.DataFrame,
    targets_df: pd.DataFrame,
    universe: dict[str, object],
    written_files: list[Path],
    olympus: dict[str, object] | None = None,
) -> dict[str, object]:
    """Evaluate the T7 hard checks 1-5 and the T15 checks 6-11 (plan_t12_t15.md 5.7)."""
    ok_targets = targets_df[targets_df["status"] == "ok"] if "status" in targets_df.columns else targets_df
    ok_ids = [str(tid) for tid in ok_targets["target_id"].tolist()]

    # 1. Coverage (>= 20 per preset per ok target for presets with status ok)
    low_no_retry: list[dict[str, object]] = []
    target_status_map = {
        str(t["id"]): t.get("preset_status", {}) for t in universe.get("targets", [])
    }
    if matches_df.empty:
        low_no_retry = [{"target_id": tid, "preset": "all", "count": 0} for tid in ok_ids]
    else:
        by_tid = {str(tid): grp for tid, grp in matches_df.groupby("target_id", sort=False)}
        for tid in ok_ids:
            grp = by_tid.get(tid)
            if grp is None or grp.empty:
                low_no_retry.append({"target_id": tid, "preset": "all", "count": 0})
                continue
            t_status = target_status_map.get(tid, {})
            for pkey in PRESET_KEYS:
                if t_status and t_status.get(pkey, {}).get("status") != "ok":
                    continue
                col = f"rank_{pkey}"
                cnt = int(grp[col].notna().sum()) if col in grp.columns else 0
                if cnt < MIN_COVERAGE_PER_PRESET:
                    low_no_retry.append({"target_id": tid, "preset": pkey, "count": cnt})
    check1_pass = len(low_no_retry) == 0

    # 2. Diversity (>= 150 km separation within every target/preset)
    min_pair_km = float("inf")
    diversity_violations: list[dict[str, object]] = []
    if not matches_df.empty:
        for tid, grp in matches_df.groupby("target_id", sort=False):
            for pkey in PRESET_KEYS:
                col = f"rank_{pkey}"
                sub = grp[grp[col].notna()] if col in grp.columns else grp.iloc[0:0]
                if len(sub) < 2:
                    continue
                lats = sub["lat"].to_numpy(dtype=np.float64)
                lons = sub["lon"].to_numpy(dtype=np.float64)
                dmat = np.asarray(
                    haversine_km(lats[:, None], lons[:, None], lats[None, :], lons[None, :]),
                    dtype=np.float64,
                )
                iu = np.triu_indices(len(sub), k=1)
                pair_min = float(np.min(dmat[iu]))
                if pair_min < min_pair_km:
                    min_pair_km = pair_min
                if pair_min < MIN_SEP_KM - 1e-6:
                    diversity_violations.append(
                        {"target_id": str(tid), "preset": pkey, "min_km": round(pair_min, 3)}
                    )
    check2_pass = len(diversity_violations) == 0

    # 3. Ice cap (<= 3 ice_surface analogs per target/preset, except isru_and_ice)
    max_ice_seen = 0
    ice_violations: list[dict[str, object]] = []
    if not matches_df.empty and "ice_surface" in matches_df.columns:
        for tid, grp in matches_df.groupby("target_id", sort=False):
            for pkey in PRESET_KEYS:
                if pkey in ICE_CAP_EXEMPT_PRESETS:
                    continue
                col = f"rank_{pkey}"
                sub = grp[grp[col].notna()] if col in grp.columns else grp.iloc[0:0]
                i_cnt = int(sub["ice_surface"].sum())
                max_ice_seen = max(max_ice_seen, i_cnt)
                if i_cnt > MAX_ICE_SURFACE_PER_PRESET:
                    ice_violations.append({"target_id": str(tid), "preset": pkey, "ice_surface": i_cnt})
    check3_pass = len(ice_violations) == 0

    # 4. Scores (all non-null S_k and MSI in [0, 1], S_thermal null for Moon)
    score_errors: list[str] = []
    for t in universe.get("targets", []):
        body = t.get("body")
        for a in t.get("analogs", []):
            sub_s = a.get("sub_scores", {})
            if body == "Moon" and sub_s.get("thermal") is not None:
                score_errors.append(f"Moon target {t.get('id')} analog {a.get('id')} has non-null thermal")
            for k, v in sub_s.items():
                if v is not None and not (0.0 <= float(v) <= 1.0):
                    score_errors.append(f"{t.get('id')}/{a.get('id')} sub_scores[{k}]={v}")
            for k, v in a.get("msi_by_preset", {}).items():
                if v is not None and not (0.0 <= float(v) <= 1.0):
                    score_errors.append(f"{t.get('id')}/{a.get('id')} msi[{k}]={v}")
            if len(score_errors) >= 10:
                break
        if len(score_errors) >= 10:
            break
    check4_pass = len(score_errors) == 0

    # 5. JSON contract
    json_errors: list[str] = []
    parsed_targets: list[dict[str, object]] = []
    total_bytes = 0
    for fpath in written_files:
        try:
            raw_text = fpath.read_text(encoding="utf-8")
            size_b = len(raw_text.encode("utf-8"))
            total_bytes = max(total_bytes, size_b)
            if size_b > MAX_UNIVERSE_BYTES:
                json_errors.append(f"{fpath.name} size {size_b} > {MAX_UNIVERSE_BYTES}")
            parsed = json.loads(raw_text, parse_constant=_reject_nonfinite)
            if "targets" in parsed:
                parsed_targets.extend(parsed["targets"])
        except Exception as exc:
            json_errors.append(f"{fpath.name}: {exc}")
    json_errors.extend(_validate_target_and_analog_keys(parsed_targets))
    check5_pass = len(json_errors) == 0 and len(parsed_targets) == len(universe.get("targets", []))

    # 6. Layer scores in [0, 1]; S_dust and dust null for every Moon target
    layer_errors: list[str] = []
    n_geo = n_dust = n_ice = 0
    for t in universe.get("targets", []):
        body = t.get("body")
        for a in t.get("analogs", []):
            ss = a.get("sub_scores", {})
            for dim in ("geology", "dust", "ice"):
                v = ss.get(dim)
                if v is None:
                    continue
                if dim == "geology":
                    n_geo += 1
                elif dim == "dust":
                    n_dust += 1
                else:
                    n_ice += 1
                if not (0.0 <= float(v) <= 1.0):
                    layer_errors.append(f"{t.get('id')}/{a.get('id')} {dim}={v}")
            if body == "Moon" and ss.get("dust") is not None:
                layer_errors.append(f"Moon target {t.get('id')} analog {a.get('id')} has non-null S_dust")
            if len(layer_errors) >= 10:
                break
        if len(layer_errors) >= 10:
            break
    check6_pass = len(layer_errors) == 0

    # 7. Olympus Mons with geology_and_materials: >= 1 VOLCANIC_BASIC Earth patch in the top 10
    if olympus is None:
        check7_pass = False
        olympus_obs: object = "Mars T3 feature table unavailable; check could not be evaluated"
    else:
        top10 = olympus.get("top10", [])
        n_vb = sum(1 for r in top10 if r.get("geo_class") == "VOLCANIC_BASIC")
        check7_pass = n_vb >= 1
        olympus_obs = {
            "n_volcanic_basic_top10": n_vb,
            "top10_geo_classes": [r.get("geo_class") for r in top10],
        }

    # 8. Mars plains: spread top 1 -> top 30 (mobility_and_traction)
    spreads: list[dict[str, object]] = []
    for t in universe.get("targets", []):
        if t.get("id") not in MARS_PLAINS_IDS:
            continue
        top = _preset_top(t, "mobility_and_traction", TOP_N_REPORT)
        if len(top) >= 2:
            s1 = float(top[0]["msi_by_preset"]["mobility_and_traction"])
            sn = float(top[-1]["msi_by_preset"]["mobility_and_traction"])
            spreads.append({"id": t["id"], "n": len(top), "msi_1st": round(s1, 4), "msi_nth": round(sn, 4), "spread": round(s1 - sn, 4)})
    spread_vals = [float(r["spread"]) for r in spreads]
    check8_pass = bool(spread_vals) and float(np.median(spread_vals)) > PLAINS_SPREAD_MIN

    # 9. dust_and_seasons for Mars curated targets: top 5 with country and dust ranks
    dust_top: list[dict[str, object]] = []
    for t in universe.get("targets", []):
        if t.get("body") != "Mars" or t.get("type") != "CURATED":
            continue
        dust_top.append(
            {
                "id": t["id"],
                "target_dust": t.get("dust"),
                "top5": [
                    {
                        "id": a["id"],
                        "country": a.get("country"),
                        "msi": a["msi_by_preset"]["dust_and_seasons"],
                        "S_dust": a["sub_scores"].get("dust"),
                        "dust": a.get("dust"),
                    }
                    for a in _preset_top(t, "dust_and_seasons", 5)
                ],
            }
        )

    # 10. isru_and_ice for lunar curated targets: top 5
    isru_top: list[dict[str, object]] = []
    for t in universe.get("targets", []):
        if t.get("body") != "Moon" or t.get("type") != "CURATED":
            continue
        isru_top.append(
            {
                "id": t["id"],
                "target_ice": t.get("ice"),
                "top5": [
                    {
                        "id": a["id"],
                        "country": a.get("country"),
                        "msi": a["msi_by_preset"]["isru_and_ice"],
                        "S_ice": a["sub_scores"].get("ice"),
                        "ice": a.get("ice"),
                        "geo_class": a.get("geology", {}).get("geo_class"),
                    }
                    for a in _preset_top(t, "isru_and_ice", 5)
                ],
            }
        )

    # 11. Share per geo_class and lava-tube terrain count
    cls_counts: dict[str, int] = {}
    total_analogs = 0
    lava_tube = 0
    for t in universe.get("targets", []):
        for a in t.get("analogs", []):
            total_analogs += 1
            g = a.get("geology", {})
            key = str(g.get("geo_class") or "NULL")
            cls_counts[key] = cls_counts.get(key, 0) + 1
            if g.get("lava_tube_terrain"):
                lava_tube += 1
    cls_share = {k: round(v / total_analogs, 4) for k, v in sorted(cls_counts.items())} if total_analogs else {}

    checks = [
        {
            "id": 1,
            "name": "coverage",
            "kind": "hard",
            "passed": check1_pass,
            "observed": {
                "targets_checked": len(ok_ids),
                "below_20": low_no_retry[:10],
                "below_20_count": len(low_no_retry),
            },
            "expected": ">= 20 analogs per (ok target, preset) over the whole Earth table",
        },
        {
            "id": 2,
            "name": "diversity",
            "kind": "hard",
            "passed": check2_pass,
            "observed": {
                "min_pair_km": None if not math.isfinite(min_pair_km) else round(min_pair_km, 3),
                "violations": diversity_violations[:10],
            },
            "expected": ">= 150.0 km within each (target, preset)",
        },
        {
            "id": 3,
            "name": "ice_cap",
            "kind": "hard",
            "passed": check3_pass,
            "observed": {
                "max_ice_surface_per_preset": max_ice_seen,
                "exempt_presets": list(ICE_CAP_EXEMPT_PRESETS),
                "violations": ice_violations[:10],
            },
            "expected": "<= 3 ice_surface (GLiM ig) analogs per (target, preset), except isru_and_ice",
        },
        {
            "id": 4,
            "name": "scores",
            "kind": "hard",
            "passed": check4_pass,
            "observed": {"error_count": len(score_errors), "sample_errors": score_errors},
            "expected": "all S_k & MSI in [0, 1]; S_thermal null for Moon",
        },
        {
            "id": 5,
            "name": "json_contract",
            "kind": "hard",
            "passed": check5_pass,
            "observed": {
                "files": [f.name for f in written_files],
                "max_file_mb": round(total_bytes / (1024.0 * 1024.0), 3),
                "targets_parsed": len(parsed_targets),
                "errors": json_errors[:10],
            },
            "expected": "valid JSON (no NaN/Infinity), < 20 MB (or split), required target/analog keys present",
        },
        {
            "id": 6,
            "name": "layer_scores",
            "kind": "hard",
            "passed": check6_pass,
            "observed": {
                "non_null_geology": n_geo,
                "non_null_dust": n_dust,
                "non_null_ice": n_ice,
                "errors": layer_errors[:10],
            },
            "expected": "non-null S_geology, S_dust, S_ice in [0, 1]; S_dust null for all Moon targets",
        },
        {
            "id": 7,
            "name": "olympus_mons_geology",
            "kind": "hard",
            "passed": check7_pass,
            "observed": olympus_obs,
            "expected": "geology_and_materials: at least one VOLCANIC_BASIC Earth patch in the top 10",
        },
        {
            "id": 8,
            "name": "mars_plains_spread",
            "kind": "soft",
            "passed": check8_pass,
            "observed": {
                "median_spread": round(float(np.median(spread_vals)), 4) if spread_vals else None,
                "per_target": spreads,
            },
            "expected": f"mobility_and_traction spread top 1 -> top {TOP_N_REPORT} > {PLAINS_SPREAD_MIN} (the T7 value)",
        },
        {
            "id": 9,
            "name": "dust_and_seasons_mars_top5",
            "kind": "soft",
            "passed": True,
            "observed": dust_top,
            "expected": "review: top 5 per Mars curated target with country and dust ranks",
        },
        {
            "id": 10,
            "name": "isru_and_ice_moon_top5",
            "kind": "soft",
            "passed": True,
            "observed": isru_top,
            "expected": "review: Antarctica / Greenland / high cold deserts expected",
        },
        {
            "id": 11,
            "name": "geo_class_shares",
            "kind": "soft",
            "passed": True,
            "observed": {
                "total_pairs": total_analogs,
                "share_by_geo_class": cls_share,
                "count_by_geo_class": dict(sorted(cls_counts.items())),
                "lava_tube_terrain_pairs": lava_tube,
            },
            "expected": "print: share of exported analogs per geo_class and number with lava_tube_terrain",
        },
    ]

    hard = [c for c in checks if c["kind"] == "hard"]
    soft = [c for c in checks if c["kind"] == "soft"]
    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "summary": {
            "hard_passed": sum(1 for c in hard if c["passed"]),
            "hard_total": len(hard),
            "soft_passed": sum(1 for c in soft if c["passed"]),
            "soft_total": len(soft),
        },
        "checks": checks,
    }


OLYMPUS_PRESET: str = "geology_and_materials"


def _olympus_mons_sanity_check(
    earth_df: pd.DataFrame,
    mars_t3: pd.DataFrame | None,
    t13_dir: Path | None,
    t14_dir: Path | None,
    sigma_scale: float = 1.0,
) -> dict[str, object] | None:
    """Top 10 diverse Earth analogs (geology_and_materials) for the T3 Mars patch nearest Olympus Mons.

    Needs the row-aligned T14 ``geology_mars.parquet`` and T13 ``dust_mars.parquet`` tables.
    """
    if mars_t3 is None or mars_t3.empty or earth_df.empty:
        return None
    if not {"lat", "lon", *MATCH_FEATURES}.issubset(mars_t3.columns):
        return None
    if t14_dir is None or not (Path(t14_dir) / "geology_mars.parquet").exists():
        return None

    mars_all = mars_t3.reset_index(drop=True).copy()
    mars_all["_row"] = np.arange(len(mars_all))
    m_lats = pd.to_numeric(mars_all["lat"], errors="coerce").to_numpy(dtype=np.float64)
    m_lons = pd.to_numeric(mars_all["lon"], errors="coerce").to_numpy(dtype=np.float64)
    valid_m = np.isfinite(m_lats) & np.isfinite(m_lons)
    for feat in MATCH_FEATURES:
        valid_m &= np.isfinite(pd.to_numeric(mars_all[feat], errors="coerce").to_numpy(dtype=np.float64))
    if not np.any(valid_m):
        return None

    mars_valid = mars_all.loc[valid_m].reset_index(drop=True)
    d_ang = haversine_km(
        OLYMPUS_LAT,
        OLYMPUS_LON,
        mars_valid["lat"].to_numpy(dtype=np.float64),
        mars_valid["lon"].to_numpy(dtype=np.float64),
    )
    nearest_i = int(np.argmin(d_ang))
    patch = mars_valid.iloc[nearest_i]
    row = int(patch["_row"])
    mars_dist_km = float(d_ang[nearest_i]) * (BODY_RADII_M["Mars"] / BODY_RADII_M["Earth"])

    geo_mars = pd.read_parquet(Path(t14_dir) / "geology_mars.parquet")
    if len(geo_mars) != len(mars_all) or abs(float(geo_mars["lat"].iloc[row]) - float(patch["lat"])) > 1e-6:
        raise ValueError("geology_mars.parquet is not row-aligned with the T3 Mars feature table")
    patch_geo_unit = _clean_str(geo_mars["unit"].iloc[row])
    patch_geo_class = _clean_str(geo_mars["geo_class"].iloc[row])

    dust_level = dust_season = dust_phase = float("nan")
    if t13_dir is not None and (Path(t13_dir) / "dust_mars.parquet").exists():
        dust_mars = pd.read_parquet(Path(t13_dir) / "dust_mars.parquet")
        if len(dust_mars) == len(mars_all):
            dust_level = float(dust_mars["dust_level_rank"].iloc[row])
            dust_season = float(dust_mars["dust_seasonality_rank"].iloc[row])
            dust_phase = float(dust_mars["dust_peak_phase_deg"].iloc[row])

    earth_clean = earth_df.reset_index(drop=True).copy()
    if "earth_id" not in earth_clean.columns:
        earth_clean["earth_id"] = [
            format_earth_id(la, lo)
            for la, lo in zip(earth_clean["lat"].to_numpy(), earth_clean["lon"].to_numpy())
        ]

    norm = Normalizer.fit_earth(earth_clean)
    z_e = norm.transform(earth_clean)
    finite_e = np.all(np.isfinite(z_e), axis=1)
    earth_clean = earth_clean.loc[finite_e].reset_index(drop=True)
    z_e = z_e[finite_e]

    patch_df = pd.DataFrame([{**patch.drop(labels=["_row"]).to_dict(), "body": "Mars"}])
    z_t = norm.transform(patch_df)[0]
    zt_e, zt_t_arr = thermal_ranks(earth_clean, mars_valid, patch_df)
    ea = build_earth_arrays(earth_clean, z_e, zt_e)
    tv = TargetVec(
        body="Mars",
        z_t=z_t,
        zt_t=float(zt_t_arr[0]),
        lat=float(patch["lat"]),
        geo_class=patch_geo_class,
        dust_level_rank=dust_level,
        dust_season_rank=dust_season,
        dust_phase=dust_phase,
        cold_rank=float("nan"),
        ice_t=float("nan"),
    )
    scores = score_target(ea, tv, sigma_scale=sigma_scale)
    msi_vals = np.asarray(msi(scores, PRESETS[OLYMPUS_PRESET]["weights"]), dtype=np.float64)
    order = np.argsort(-np.where(np.isfinite(msi_vals), msi_vals, -np.inf), kind="mergesort")
    order = order[np.isfinite(msi_vals[order])]
    chosen = select_diverse(
        order,
        ea.lat,
        ea.lon,
        ea.ice_surface,
        n=10,
        min_sep_km=MIN_SEP_KM,
        max_polar=MAX_ICE_SURFACE_PER_PRESET,
    )

    t_phys = {feat: patch[feat] for feat in MATCH_FEATURES}
    top10: list[dict[str, object]] = []
    for rank_i, g_idx in enumerate(chosen, start=1):
        e_row = earth_clean.iloc[g_idx]
        mm = mismatches(
            {feat: e_row[feat] for feat in MATCH_FEATURES},
            t_phys,
            z_e[g_idx],
            z_t,
            float(zt_e[g_idx]),
            tv.zt_t,
        )
        top10.append(
            {
                "rank": rank_i,
                "earth_id": str(e_row["earth_id"]),
                "lat": _round_val(e_row["lat"], 4),
                "lon": _round_val(e_row["lon"], 4),
                "country": _clean_str(e_row.get("country")),
                "known_region": _clean_str(e_row.get("known_region")),
                "classification": _clean_str(e_row.get("classification")),
                "glim_code": _clean_str(e_row.get("glim_code")),
                "geo_class": _clean_str(e_row.get("geo_class")),
                "ice_surface": bool(ea.ice_surface[g_idx]),
                "msi_geology_preset": _round_val(msi_vals[g_idx], 3),
                "S_topography": _round_val(scores["topography"][g_idx], 3),
                "S_roughness": _round_val(scores["roughness"][g_idx], 3),
                "S_environment": _round_val(scores["environment"][g_idx], 3),
                "S_geology": _round_val(scores["geology"][g_idx], 3),
                "mismatch_count": len(mm),
            }
        )

    return {
        "preset": OLYMPUS_PRESET,
        "target_lat": round(float(patch["lat"]), 4),
        "target_lon": round(float(patch["lon"]), 4),
        "offset_mars_km": round(mars_dist_km, 2),
        "target_geo_unit": patch_geo_unit,
        "target_geo_class": patch_geo_class,
        "features": {feat: round(float(patch[feat]), 2) for feat in [*MATCH_FEATURES, "mean_elev_m"] if feat in patch},
        "top10": top10,
    }


def _curated_score_distributions(universe: dict[str, object]) -> dict[str, dict[str, object]]:
    """Summarize 1st and 30th mobility_and_traction MSI across curated targets per body."""
    stats: dict[str, dict[str, object]] = {}
    for body in ("Moon", "Mars"):
        best_scores: list[float] = []
        rank30_scores: list[float] = []
        per_target: list[dict[str, object]] = []
        for t in universe.get("targets", []):
            if t["body"] != body or t["type"] != "CURATED":
                continue
            mob_selected = sorted(
                (
                    float(a["msi_by_preset"]["mobility_and_traction"])
                    for a in t["analogs"]
                    if "mobility_and_traction" in a.get("selected_by", [])
                    and a["msi_by_preset"]["mobility_and_traction"] is not None
                ),
                reverse=True,
            )
            if not mob_selected:
                mob_selected = sorted(
                    (
                        float(a["msi_by_preset"]["mobility_and_traction"])
                        for a in t["analogs"]
                        if a["msi_by_preset"]["mobility_and_traction"] is not None
                    ),
                    reverse=True,
                )
            if not mob_selected:
                continue
            s1 = mob_selected[0]
            s30 = mob_selected[min(29, len(mob_selected) - 1)]
            best_scores.append(s1)
            rank30_scores.append(s30)
            per_target.append(
                {
                    "id": t["id"],
                    "name": t["name"],
                    "n_mob": len(mob_selected),
                    "msi_1st": round(s1, 3),
                    "msi_nth": round(s30, 3),
                }
            )
        if best_scores:
            stats[body] = {
                "n_curated": len(best_scores),
                "best_median": round(float(np.median(best_scores)), 3),
                "best_p90": round(float(np.percentile(best_scores, 90)), 3),
                "rank30_median": round(float(np.median(rank30_scores)), 3),
                "rank30_p90": round(float(np.percentile(rank30_scores, 90)), 3),
                "per_target": per_target,
            }
    return stats


def _short_json(obj: object, limit: int = 400) -> str:
    text = json.dumps(obj, separators=(",", ":"), default=str)
    return text if len(text) <= limit else text[: limit - 3] + "..."


def build_t7_report(
    universe: dict[str, object],
    checks_report: dict[str, object],
    earth_df: pd.DataFrame,
    mars_t3: pd.DataFrame | None = None,
    match_runtime_s: float | None = None,
    export_runtime_s: float | None = None,
    sigma_scale: float = 1.0,
    olympus: dict[str, object] | None = None,
) -> str:
    """Build the human-readable t7_report.md (plan_t7_t8.md 5, extended by plan_t12_t15.md 5.7)."""
    meta = universe["metadata"]
    lines: list[str] = [
        "# T15 Matching & Export Report (7 dimensions, 5 presets)",
        "",
        f"- **Source:** `{meta.get('source')}`",
        f"- **Commit:** `{meta.get('commit')}`",
        f"- **Limits source:** `{meta.get('limits_source')}`",
        f"- **Earth patches evaluated:** `{meta.get('earth_patches_evaluated')}`",
        f"- **Sigma:** `{meta.get('sigma')}`",
        "",
        "## Hard Checks Summary",
        "",
        f"**Hard passed:** `{checks_report['summary']['hard_passed']}/{checks_report['summary']['hard_total']}`; "
        f"**soft passed:** `{checks_report['summary']['soft_passed']}/{checks_report['summary']['soft_total']}`",
        "",
        "| # | Check | Kind | Status | Details |",
        "| --- | --- | --- | --- | --- |",
    ]
    for chk in checks_report["checks"]:
        status = "PASS" if chk["passed"] else "FAIL"
        lines.append(
            f"| {chk['id']} | `{chk['name']}` | {chk['kind']} | {status} | "
            f"`{_short_json(chk['observed'])}` |"
        )

    # 1. Score distribution per body (curated targets)
    lines.extend(["", "## 1. Curated Score Distribution (`mobility_and_traction`)", ""])
    dist = _curated_score_distributions(universe)
    lines.append("| Body | Curated targets | 1st MSI median | 1st MSI p90 | 30th MSI median | 30th MSI p90 |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: |")
    for body in ("Moon", "Mars"):
        if body not in dist:
            continue
        d = dist[body]
        lines.append(
            f"| {body} | {d['n_curated']} | {d['best_median']:.3f} | {d['best_p90']:.3f} | "
            f"{d['rank30_median']:.3f} | {d['rank30_p90']:.3f} |"
        )

    # 2. Top 5 per curated target
    lines.extend(["", "## 2. Top 5 Analogs per Curated Target (`mobility_and_traction`)", ""])
    for t in universe.get("targets", []):
        if t.get("type") != "CURATED":
            continue
        lines.append(f"### {t['id']} — {t['name']} ({t['body']})")
        lines.append("")
        lines.append(
            "| Rank | Earth ID | Country | Known region | Geo class | MSI | S_topo | S_rough | S_env | S_therm | S_geo | Mismatches |"
        )
        lines.append("| ---: | --- | --- | --- | --- | ---: | ---: | ---: | ---: | --- | --- | ---: |")
        for rank_i, a in enumerate(_preset_top(t, "mobility_and_traction", 5), start=1):
            ss = a["sub_scores"]
            st_str = f"{ss['thermal']:.3f}" if ss["thermal"] is not None else "null"
            sg_str = f"{ss['geology']:.3f}" if ss.get("geology") is not None else "null"
            lines.append(
                f"| {rank_i} | `{a['id']}` | {a['country'] or '-'} | {a['known_region'] or '-'} | "
                f"{a.get('geology', {}).get('geo_class') or '-'} | "
                f"{a['msi_by_preset']['mobility_and_traction']:.3f} | {ss['topography']:.3f} | "
                f"{ss['roughness']:.3f} | {ss['environment']:.3f} | {st_str} | {sg_str} | {len(a['mismatches'])} |"
            )
        lines.append("")

    # 3. Olympus Mons sanity check (geology_and_materials)
    lines.extend(["## 3. Olympus Mons Sanity Check (`18.65°N, -133.80°E`, preset `geology_and_materials`)", ""])
    if olympus is None:
        lines.append("Skipped (no Mars T3 feature table or T14 geology table available).")
    else:
        lines.append(
            f"- **Nearest T3 Mars patch:** `({olympus['target_lat']}, {olympus['target_lon']})` "
            f"({olympus['offset_mars_km']} km from reference coordinates), "
            f"unit `{olympus.get('target_geo_unit')}`, class `{olympus.get('target_geo_class')}`"
        )
        lines.append(f"- **Mars features:** `{json.dumps(olympus['features'], separators=(',', ':'))}`")
        lines.append("")
        lines.append(
            "| Rank | Earth ID | Country | Known region | GLiM | Geo class | Ice sheet | MSI | S_topo | S_rough | S_env | S_geo | Mismatches |"
        )
        lines.append("| ---: | --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |")
        for row in olympus["top10"]:
            lines.append(
                f"| {row['rank']} | `{row['earth_id']}` | {row['country'] or '-'} | {row['known_region'] or '-'} | "
                f"{row['glim_code'] or '-'} | {row['geo_class'] or '-'} | {'yes' if row['ice_surface'] else 'no'} | "
                f"{row['msi_geology_preset']:.3f} | {row['S_topography']:.3f} | {row['S_roughness']:.3f} | "
                f"{row['S_environment']:.3f} | {row['S_geology']:.3f} | {row['mismatch_count']} |"
            )

    # 4. Exported analog counts
    lines.extend(["", "## 4. Exported Analog Counts", ""])
    cls_counts: dict[str, int] = {}
    country_counts: dict[str, int] = {}
    polar_cold_total = 0
    ndvi_missing_total = 0
    total_analogs = 0
    for t in universe.get("targets", []):
        for a in t.get("analogs", []):
            total_analogs += 1
            cls_k = str(a.get("classification") or "UNKNOWN")
            cls_counts[cls_k] = cls_counts.get(cls_k, 0) + 1
            c_name = a.get("country") or "(none)"
            country_counts[c_name] = country_counts.get(c_name, 0) + 1
            if a.get("polar_cold"):
                polar_cold_total += 1
            if a.get("earth_env", {}).get("ndvi_missing"):
                ndvi_missing_total += 1

    lines.append(f"- **Total exported (target, analog) pairs:** `{total_analogs}`")
    lines.append(f"- **Classification counts:** `{json.dumps(cls_counts, sort_keys=True)}`")
    lines.append(f"- **`polar_cold` analogs (lst_day < -10 C, informational):** `{polar_cold_total}`")
    lines.append(f"- **`ndvi_missing` analogs:** `{ndvi_missing_total}`")
    lines.append("")
    lines.append("### Top 15 Countries among Exported Analogs")
    lines.append("")
    lines.append("| Rank | Country | Pairs |")
    lines.append("| ---: | --- | ---: |")
    top_countries = sorted(country_counts.items(), key=lambda kv: (-kv[1], kv[0]))[:15]
    for rank_i, (c_name, cnt) in enumerate(top_countries, start=1):
        lines.append(f"| {rank_i} | {c_name} | {cnt} |")

    # 5. T15 review tables (checks 8-11)
    by_name = {c["name"]: c for c in checks_report["checks"]}
    lines.extend(["", "## 5. T15 Review Tables (checks 8-11)", ""])

    spread = by_name.get("mars_plains_spread")
    if spread:
        lines.extend(["### 5.1 Mars plains: spread top 1 → top 30 (`mobility_and_traction`)", ""])
        obs = spread["observed"]
        lines.append(
            f"Median spread: `{obs['median_spread']}` (expected > `{PLAINS_SPREAD_MIN}`, the T7 value) — "
            f"**{'PASS' if spread['passed'] else 'FAIL'}**"
        )
        lines.append("")
        lines.append("| Target | Analogs | MSI 1st | MSI last | Spread |")
        lines.append("| --- | ---: | ---: | ---: | ---: |")
        for r in obs["per_target"]:
            lines.append(f"| `{r['id']}` | {r['n']} | {r['msi_1st']:.4f} | {r['msi_nth']:.4f} | {r['spread']:.4f} |")

    dust_chk = by_name.get("dust_and_seasons_mars_top5")
    if dust_chk:
        lines.extend(["", "### 5.2 `dust_and_seasons`: top 5 per Mars curated target", ""])
        for rec in dust_chk["observed"]:
            td = rec.get("target_dust") or {}
            lines.append(
                f"**`{rec['id']}`** — target dust ranks: level `{td.get('level_rank')}`, "
                f"seasonality `{td.get('seasonality_rank')}`, peak phase `{td.get('peak_phase_deg')}`°"
            )
            lines.append("")
            lines.append("| Rank | Earth ID | Country | MSI | S_dust | Level rank | Season rank | Peak phase |")
            lines.append("| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |")
            for i, a in enumerate(rec["top5"], start=1):
                d = a.get("dust") or {}
                sd = f"{a['S_dust']:.3f}" if a.get("S_dust") is not None else "null"
                lines.append(
                    f"| {i} | `{a['id']}` | {a['country'] or '-'} | {a['msi']:.3f} | {sd} | "
                    f"{d.get('level_rank')} | {d.get('seasonality_rank')} | {d.get('peak_phase_deg')} |"
                )
            lines.append("")

    isru_chk = by_name.get("isru_and_ice_moon_top5")
    if isru_chk:
        lines.extend(["### 5.3 `isru_and_ice`: top 5 per lunar curated target", ""])
        for rec in isru_chk["observed"]:
            ti = rec.get("target_ice") or {}
            lines.append(
                f"**`{rec['id']}`** — target cold rank `{ti.get('cold_rank')}`, ice_T `{ti.get('ice_T')}` "
                f"(`{ti.get('ice_source')}`)"
            )
            lines.append("")
            lines.append("| Rank | Earth ID | Country | Geo class | MSI | S_ice | Cold rank | ice_E |")
            lines.append("| ---: | --- | --- | --- | ---: | ---: | ---: | ---: |")
            for i, a in enumerate(rec["top5"], start=1):
                ic = a.get("ice") or {}
                si = f"{a['S_ice']:.3f}" if a.get("S_ice") is not None else "null"
                lines.append(
                    f"| {i} | `{a['id']}` | {a['country'] or '-'} | {a.get('geo_class') or '-'} | "
                    f"{a['msi']:.3f} | {si} | {ic.get('cold_rank')} | {ic.get('ice_E')} |"
                )
            lines.append("")

    shares = by_name.get("geo_class_shares")
    if shares:
        lines.extend(["### 5.4 Exported analogs per `geo_class`", ""])
        so = shares["observed"]
        lines.append(f"- **Total pairs:** `{so['total_pairs']}`; **with `lava_tube_terrain`:** `{so['lava_tube_terrain_pairs']}`")
        lines.append("")
        lines.append("| geo_class | Pairs | Share |")
        lines.append("| --- | ---: | ---: |")
        for k, v in so["count_by_geo_class"].items():
            lines.append(f"| {k} | {v} | {so['share_by_geo_class'][k]:.4f} |")

    # 6. Runtime
    lines.extend(["", "## 6. Runtime", ""])
    lines.append(f"- **Match (`pipeline.match`):** `{match_runtime_s if match_runtime_s is not None else 'n/a'} s`")
    lines.append(f"- **Export (`pipeline.export`):** `{round(export_runtime_s, 3) if export_runtime_s is not None else 'n/a'} s`")
    lines.append("")
    return "\n".join(lines)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Export analogs_universe.json and run T7/T8 checks (T8).")
    p.add_argument("--t3-dir", type=Path, default=YUCA_PROJECT_DIR / "runs" / "2242278")
    p.add_argument("--t4-dir", type=Path, default=YUCA_PROJECT_DIR / "runs" / "2242423")
    p.add_argument("--t5-dir", type=Path, required=True)
    p.add_argument("--t12-dir", type=Path, required=True, help="T12 ice run directory")
    p.add_argument("--t13-dir", type=Path, required=True, help="T13 dust run directory")
    p.add_argument("--t14-dir", type=Path, required=True, help="T14 geology run directory")
    p.add_argument("--out-dir", type=Path, required=True)
    p.add_argument("--limits", type=Path, default=DEFAULT_LIMITS_JSON)
    p.add_argument("--sample-json", type=Path, default=DEFAULT_SAMPLE_JSON)
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="[%(levelname)s] %(name)s: %(message)s",
    )
    t0 = time.perf_counter()
    args = _parse_args(argv)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    matches_path = args.out_dir / "matches.parquet"
    meta_path = args.out_dir / "matches_meta.json"
    targets_path = args.t4_dir / "targets.parquet"
    earth_path = args.t5_dir / "features_earth.parquet"
    mars_path = args.t3_dir / "features_mars.parquet"

    logger.info("Loading matches from %s", matches_path)
    matches_df = pd.read_parquet(matches_path)
    matches_meta: dict[str, object] = {}
    if meta_path.exists():
        with open(meta_path, "r", encoding="utf-8") as fh:
            matches_meta = json.load(fh)
    matches_meta.setdefault("t3_dir", str(args.t3_dir))
    matches_meta.setdefault("t4_dir", str(args.t4_dir))
    matches_meta.setdefault("t5_dir", str(args.t5_dir))
    matches_meta.setdefault("t12_dir", str(args.t12_dir))
    matches_meta.setdefault("t13_dir", str(args.t13_dir))
    matches_meta.setdefault("t14_dir", str(args.t14_dir))

    targets_df = pd.read_parquet(targets_path)
    earth_df = pd.read_parquet(earth_path)
    mars_t3 = pd.read_parquet(mars_path) if mars_path.exists() else None
    earth_df, targets_df = load_layers(earth_df, targets_df, args.t12_dir, args.t13_dir, args.t14_dir)

    universe = build_universe_dict(
        matches_df=matches_df,
        targets_df=targets_df,
        earth_df=earth_df,
        matches_meta=matches_meta,
        limits_path=args.limits,
        sample_json_path=args.sample_json,
    )
    written_files = write_universe_json(universe, args.out_dir)

    olympus = _olympus_mons_sanity_check(
        earth_df=earth_df,
        mars_t3=mars_t3,
        t13_dir=args.t13_dir,
        t14_dir=args.t14_dir,
        sigma_scale=float(matches_meta.get("sigma_scale", 1.0)),
    )
    checks_report = run_t7_checks(
        matches_df=matches_df,
        targets_df=targets_df,
        universe=universe,
        written_files=written_files,
        olympus=olympus,
    )
    export_elapsed_s = time.perf_counter() - t0
    report_md = build_t7_report(
        universe=universe,
        checks_report=checks_report,
        earth_df=earth_df,
        mars_t3=mars_t3,
        match_runtime_s=matches_meta.get("match_runtime_s"),
        export_runtime_s=export_elapsed_s,
        sigma_scale=float(matches_meta.get("sigma_scale", 1.0)),
        olympus=olympus,
    )

    checks_out = args.out_dir / "t7_checks.json"
    report_out = args.out_dir / "t7_report.md"
    with open(checks_out, "w", encoding="utf-8") as fh:
        json.dump(checks_report, fh, indent=2, allow_nan=False)
    report_out.write_text(report_md, encoding="utf-8")

    print(report_md)
    logger.info(
        "Hard checks: %d/%d passed (checks=%s, report=%s)",
        checks_report["summary"]["hard_passed"],
        checks_report["summary"]["hard_total"],
        checks_out,
        report_out,
    )
    if checks_report["summary"]["hard_passed"] < checks_report["summary"]["hard_total"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
