"""Export v2 matching results into analogs_universe.json, run T7/T8 hard checks,
and generate t7_report.md (T8).
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
from .match import (
    MATCH_FEATURES,
    MAX_POLAR_PER_PRESET,
    MIN_SEP_KM,
    POLAR_COLD_LST_C,
    PRESET_KEYS,
    PRESETS,
    Normalizer,
    _knn_embedding,
    dimension_scores,
    format_earth_id,
    haversine_km,
    mismatches,
    msi,
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
    "mismatches",
}


def default_datasets() -> list[dict[str, object]]:
    """Return the 10 pipeline dataset provenance entries using verified doc URLs only."""
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

    for _, t_row in ordered_targets.iterrows():
        tid = str(t_row["target_id"])
        body = str(t_row["body"])
        m_rows = matches_by_target.get(tid, [])

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
            }
            msi_by_preset = {
                pkey: _round_val(m_row.get(f"msi_{pkey}"), 3)
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
                    "mismatches": mm_list,
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
    t7_lbl = str(job_id) if job_id else "manual"
    sigma_scale = float(meta_in.get("sigma_scale", 1.0))

    metadata = {
        "version": "2.0.0",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": f"pipeline v2 (T3 {t3_lbl}, T4 {t4_lbl}, T5 {t5_lbl}, T7 {t7_lbl})",
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
            "max_polar_cold_per_preset": MAX_POLAR_PER_PRESET,
        },
        "datasets": default_datasets(),
    }

    mission_presets = {
        pkey: {
            "label": PRESETS[pkey]["label"],
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


def run_t7_checks(
    matches_df: pd.DataFrame,
    targets_df: pd.DataFrame,
    universe: dict[str, object],
    written_files: list[Path],
) -> dict[str, object]:
    """Evaluate the 5 hard checks in plan_t7_t8.md §5 and return structured JSON report."""
    ok_targets = targets_df[targets_df["status"] == "ok"] if "status" in targets_df.columns else targets_df
    ok_ids = [str(tid) for tid in ok_targets["target_id"].tolist()]

    # 1. Coverage (>= 20 per preset per ok target, or 8000-pool retry used and logged)
    low_no_retry: list[dict[str, object]] = []
    low_with_retry: list[dict[str, object]] = []
    if matches_df.empty:
        low_no_retry = [{"target_id": tid, "preset": "all", "count": 0} for tid in ok_ids]
    else:
        by_tid = {str(tid): grp for tid, grp in matches_df.groupby("target_id", sort=False)}
        for tid in ok_ids:
            grp = by_tid.get(tid)
            if grp is None or grp.empty:
                low_no_retry.append({"target_id": tid, "preset": "all", "count": 0})
                continue
            retry_used = bool(grp["retry_used"].any()) if "retry_used" in grp.columns else False
            for pkey in PRESET_KEYS:
                col = f"rank_{pkey}"
                cnt = int(grp[col].notna().sum()) if col in grp.columns else 0
                if cnt < MIN_COVERAGE_PER_PRESET:
                    rec = {"target_id": tid, "preset": pkey, "count": cnt, "retry_used": retry_used}
                    if retry_used:
                        low_with_retry.append(rec)
                    else:
                        low_no_retry.append(rec)
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

    # 3. Polar cap (<= 3 polar_cold per target/preset)
    max_polar_seen = 0
    polar_violations: list[dict[str, object]] = []
    if not matches_df.empty:
        for tid, grp in matches_df.groupby("target_id", sort=False):
            for pkey in PRESET_KEYS:
                col = f"rank_{pkey}"
                sub = grp[grp[col].notna()] if col in grp.columns else grp.iloc[0:0]
                p_cnt = int(sub["polar_cold"].sum()) if "polar_cold" in sub.columns else 0
                if p_cnt > max_polar_seen:
                    max_polar_seen = p_cnt
                if p_cnt > MAX_POLAR_PER_PRESET:
                    polar_violations.append(
                        {"target_id": str(tid), "preset": pkey, "polar_cold": p_cnt}
                    )
    check3_pass = len(polar_violations) == 0

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

    checks = [
        {
            "id": 1,
            "name": "coverage",
            "kind": "hard",
            "passed": check1_pass,
            "observed": {
                "targets_checked": len(ok_ids),
                "below_20_no_retry": low_no_retry[:10],
                "below_20_no_retry_count": len(low_no_retry),
                "below_20_with_retry_count": len(low_with_retry),
            },
            "expected": ">= 20 analogs per (ok target, preset), or 8000-pool retry used",
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
            "name": "polar_cap",
            "kind": "hard",
            "passed": check3_pass,
            "observed": {
                "max_polar_per_preset": max_polar_seen,
                "violations": polar_violations[:10],
            },
            "expected": "<= 3 polar_cold per (target, preset)",
        },
        {
            "id": 4,
            "name": "scores",
            "kind": "hard",
            "passed": check4_pass,
            "observed": {
                "error_count": len(score_errors),
                "sample_errors": score_errors,
            },
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
            "expected": "valid JSON (no NaN/Infinity), < 20 MB (or split), types.ts keys present",
        },
    ]

    hard_passed = sum(1 for c in checks if c["passed"])
    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "summary": {
            "hard_passed": hard_passed,
            "hard_total": len(checks),
        },
        "checks": checks,
    }


def _olympus_mons_sanity_check(
    earth_df: pd.DataFrame,
    mars_t3: pd.DataFrame | None,
    sigma_scale: float = 1.0,
) -> dict[str, object] | None:
    """Evaluate top 10 diverse Earth analogs for the T3 Mars patch closest to Olympus Mons."""
    if mars_t3 is None or mars_t3.empty or earth_df.empty:
        return None
    if not {"lat", "lon", *MATCH_FEATURES}.issubset(mars_t3.columns):
        return None

    m_lats = pd.to_numeric(mars_t3["lat"], errors="coerce").to_numpy(dtype=np.float64)
    m_lons = pd.to_numeric(mars_t3["lon"], errors="coerce").to_numpy(dtype=np.float64)
    valid_m = np.isfinite(m_lats) & np.isfinite(m_lons)
    for feat in MATCH_FEATURES:
        valid_m &= np.isfinite(pd.to_numeric(mars_t3[feat], errors="coerce").to_numpy(dtype=np.float64))
    if not np.any(valid_m):
        return None

    mars_valid = mars_t3.loc[valid_m].reset_index(drop=True)
    d_ang = haversine_km(
        OLYMPUS_LAT,
        OLYMPUS_LON,
        mars_valid["lat"].to_numpy(dtype=np.float64),
        mars_valid["lon"].to_numpy(dtype=np.float64),
    )
    nearest_i = int(np.argmin(d_ang))
    patch = mars_valid.iloc[nearest_i]
    mars_dist_km = float(d_ang[nearest_i]) * (BODY_RADII_M["Mars"] / BODY_RADII_M["Earth"])

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

    patch_df = pd.DataFrame([{**patch.to_dict(), "body": "Mars"}])
    z_t = norm.transform(patch_df)[0]
    zt_e, zt_t_arr = thermal_ranks(earth_clean, mars_valid, patch_df)
    zt_t = float(zt_t_arr[0])

    ndvi_e = pd.to_numeric(earth_clean["ndvi_max"], errors="coerce").to_numpy(dtype=np.float64)
    lst_day = pd.to_numeric(earth_clean["lst_day_c"], errors="coerce").to_numpy(dtype=np.float64)
    polar_e = lst_day < POLAR_COLD_LST_C
    lat_e = pd.to_numeric(earth_clean["lat"], errors="coerce").to_numpy(dtype=np.float64)
    lon_e = pd.to_numeric(earth_clean["lon"], errors="coerce").to_numpy(dtype=np.float64)

    # Full Earth candidate matrix is ~40k rows, so exact vectorized evaluation stays sub-second.
    _ = _knn_embedding(z_e)
    scores = dimension_scores(z_e, z_t, ndvi_e, zt_e, zt_t, sigma_scale=sigma_scale)
    msi_mob = np.asarray(
        msi(scores, PRESETS["mobility_and_traction"]["weights"]),
        dtype=np.float64,
    )
    order = np.argsort(-np.where(np.isfinite(msi_mob), msi_mob, -np.inf), kind="mergesort")
    chosen = select_diverse(
        order,
        lat_e,
        lon_e,
        polar_e,
        n=10,
        min_sep_km=MIN_SEP_KM,
        max_polar=MAX_POLAR_PER_PRESET,
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
            zt_t,
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
                "msi_mobility": _round_val(msi_mob[g_idx], 3),
                "S_topography": _round_val(scores["topography"][g_idx], 3),
                "S_roughness": _round_val(scores["roughness"][g_idx], 3),
                "S_environment": _round_val(scores["environment"][g_idx], 3),
                "S_thermal": _round_val(scores["thermal"][g_idx], 3),
                "mismatch_count": len(mm),
            }
        )

    return {
        "target_lat": round(float(patch["lat"]), 4),
        "target_lon": round(float(patch["lon"]), 4),
        "offset_mars_km": round(mars_dist_km, 2),
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


def build_t7_report(
    universe: dict[str, object],
    checks_report: dict[str, object],
    earth_df: pd.DataFrame,
    mars_t3: pd.DataFrame | None = None,
    match_runtime_s: float | None = None,
    export_runtime_s: float | None = None,
    sigma_scale: float = 1.0,
) -> str:
    """Build the human-readable t7_report.md report specified in plan_t7_t8.md §5."""
    meta = universe["metadata"]
    lines: list[str] = [
        "# T7/T8 Matching & Export Report",
        "",
        f"- **Source:** `{meta.get('source')}`",
        f"- **Commit:** `{meta.get('commit')}`",
        f"- **Limits source:** `{meta.get('limits_source')}`",
        f"- **Earth patches evaluated:** `{meta.get('earth_patches_evaluated')}`",
        f"- **Sigma:** `{meta.get('sigma')}`",
        "",
        "## Hard Checks Summary",
        "",
        f"**Passed:** `{checks_report['summary']['hard_passed']}/{checks_report['summary']['hard_total']}`",
        "",
        "| # | Check | Status | Details |",
        "| --- | --- | --- | --- |",
    ]
    for chk in checks_report["checks"]:
        status = "PASS" if chk["passed"] else "FAIL"
        lines.append(
            f"| {chk['id']} | `{chk['name']}` | {status} | `{json.dumps(chk['observed'], separators=(',', ':'))}` |"
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
        lines.append("| Rank | Earth ID | Country | Known region | MSI | S_topo | S_rough | S_env | S_therm | Mismatches |")
        lines.append("| ---: | --- | --- | --- | ---: | ---: | ---: | ---: | --- | ---: |")
        for rank_i, a in enumerate(t.get("analogs", [])[:5], start=1):
            ss = a["sub_scores"]
            st_str = f"{ss['thermal']:.3f}" if ss["thermal"] is not None else "null"
            lines.append(
                f"| {rank_i} | `{a['id']}` | {a['country'] or '-'} | {a['known_region'] or '-'} | "
                f"{a['msi_by_preset']['mobility_and_traction']:.3f} | {ss['topography']:.3f} | "
                f"{ss['roughness']:.3f} | {ss['environment']:.3f} | {st_str} | {len(a['mismatches'])} |"
            )
        lines.append("")

    # 3. Olympus Mons sanity check
    lines.extend(["## 3. Olympus Mons Sanity Check (`18.65°N, -133.80°E`)", ""])
    olympus = _olympus_mons_sanity_check(earth_df=earth_df, mars_t3=mars_t3, sigma_scale=sigma_scale)
    if olympus is None:
        lines.append("Skipped (no Mars T3 feature table available).")
    else:
        lines.append(
            f"- **Nearest T3 Mars patch:** `({olympus['target_lat']}, {olympus['target_lon']})` "
            f"({olympus['offset_mars_km']} km from reference coordinates)"
        )
        lines.append(f"- **Mars features:** `{json.dumps(olympus['features'], separators=(',', ':'))}`")
        lines.append("")
        lines.append("| Rank | Earth ID | Country | Known region | Classification | MSI | S_topo | S_rough | S_env | S_therm | Mismatches |")
        lines.append("| ---: | --- | --- | --- | --- | ---: | ---: | ---: | ---: | --- | ---: |")
        for row in olympus["top10"]:
            st_str = f"{row['S_thermal']:.3f}" if row["S_thermal"] is not None else "null"
            lines.append(
                f"| {row['rank']} | `{row['earth_id']}` | {row['country'] or '-'} | {row['known_region'] or '-'} | "
                f"{row['classification'] or '-'} | {row['msi_mobility']:.3f} | {row['S_topography']:.3f} | "
                f"{row['S_roughness']:.3f} | {row['S_environment']:.3f} | {st_str} | {row['mismatch_count']} |"
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
    lines.append(f"- **`polar_cold` analogs:** `{polar_cold_total}`")
    lines.append(f"- **`ndvi_missing` analogs:** `{ndvi_missing_total}`")
    lines.append("")
    lines.append("### Top 15 Countries among Exported Analogs")
    lines.append("")
    lines.append("| Rank | Country | Pairs |")
    lines.append("| ---: | --- | ---: |")
    top_countries = sorted(country_counts.items(), key=lambda kv: (-kv[1], kv[0]))[:15]
    for rank_i, (c_name, cnt) in enumerate(top_countries, start=1):
        lines.append(f"| {rank_i} | {c_name} | {cnt} |")

    # 5. Runtime
    lines.extend(["", "## 5. Runtime", ""])
    lines.append(f"- **Match (`pipeline.match`):** `{match_runtime_s if match_runtime_s is not None else 'n/a'} s`")
    lines.append(f"- **Export (`pipeline.export`):** `{round(export_runtime_s, 3) if export_runtime_s is not None else 'n/a'} s`")
    lines.append("")
    return "\n".join(lines)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Export analogs_universe.json and run T7/T8 checks (T8).")
    p.add_argument("--t3-dir", type=Path, default=YUCA_PROJECT_DIR / "runs" / "2242278")
    p.add_argument("--t4-dir", type=Path, default=YUCA_PROJECT_DIR / "runs" / "2242423")
    p.add_argument("--t5-dir", type=Path, required=True)
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

    targets_df = pd.read_parquet(targets_path)
    earth_df = pd.read_parquet(earth_path)
    mars_t3 = pd.read_parquet(mars_path) if mars_path.exists() else None

    universe = build_universe_dict(
        matches_df=matches_df,
        targets_df=targets_df,
        earth_df=earth_df,
        matches_meta=matches_meta,
        limits_path=args.limits,
        sample_json_path=args.sample_json,
    )
    written_files = write_universe_json(universe, args.out_dir)

    checks_report = run_t7_checks(
        matches_df=matches_df,
        targets_df=targets_df,
        universe=universe,
        written_files=written_files,
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
