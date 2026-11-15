"""Cryospheric and cold-trap analog dimension (T12).

This module computes thermal cold-trap percentiles, ground/surface ice indicators, and
Gaussian RBF ice similarity scores across Earth, Moon, and Mars:
- Earth: Cold rank derived from MODIS Land Surface Temperature (LST day/night mean)
  and ice indicators from GLiM ice sheets and permafrost/freezing conditions.
- Moon: Polar cold-trap ranks derived from LRO Diviner Polar Resource Product (dlre_prp)
  temperatures and USGS Lunar Ice Favorability Index.
- Mars: Subsurface/surface ice indicators derived from curated literature hints
  (SHARAD, neutron spectrometer, and Phoenix/Viking ground truth).
- Matching: Multi-component Gaussian RBF kernels comparing cold-trap ranks and ice levels.
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import os
from pathlib import Path
import subprocess
import time

import numpy as np
import pandas as pd
from scipy.stats import rankdata

from .config import YUCA_PROJECT_DIR

logger = logging.getLogger(__name__)

ICE_HINTS_JSON: Path = Path(__file__).resolve().parents[2] / "data" / "ice_hints.json"
COLD_RANK_SIGMA: float = 0.15
ICE_LEVEL_SIGMA: float = 0.50


def compute_ice_e(
    ice_surface: np.ndarray | pd.Series | bool,
    lst_day_c: np.ndarray | pd.Series | float,
) -> np.ndarray | float:
    """Compute Earth surface/subsurface ice indicator: 1.0 ice sheet, 0.5 frozen ground, 0.0 else."""
    scalar = np.ndim(ice_surface) == 0 and np.ndim(lst_day_c) == 0
    ice_arr = np.asarray(ice_surface, dtype=bool)
    lst_arr = np.asarray(lst_day_c, dtype=np.float64)
    ice_b, lst_b = np.broadcast_arrays(ice_arr, lst_arr)

    out = np.zeros(ice_b.shape, dtype=np.float32)
    frozen = (~ice_b) & np.isfinite(lst_b) & (lst_b < 0.0)
    out[frozen] = np.float32(0.5)
    out[ice_b] = np.float32(1.0)
    if scalar:
        return float(out)
    return out


def _rank_pct_cold(temp_vals: np.ndarray) -> np.ndarray:
    """Compute percentile rank of -temp (1.0 = coldest finite temperature)."""
    arr = np.asarray(temp_vals, dtype=np.float64)
    out = np.full(arr.shape, np.nan, dtype=np.float64)
    finite = np.isfinite(arr)
    n = int(np.sum(finite))
    if n > 0:
        out[finite] = rankdata(-arr[finite], method="average") / float(n)
    return out


def _searchsorted_cold_rank(sorted_neg_ref: np.ndarray, temp_val: float) -> float:
    """Percentile rank of -temp_val within a sorted reference of -temp values."""
    n = sorted_neg_ref.size
    if n == 0 or not np.isfinite(temp_val):
        return float("nan")
    key = -float(temp_val)
    left = int(np.searchsorted(sorted_neg_ref, key, side="left"))
    right = int(np.searchsorted(sorted_neg_ref, key, side="right"))
    eq = right - left
    if eq > 0:
        return float((left + 0.5 * (eq + 1)) / float(n))
    return float((left + 1) / float(n + 1))


def S_ice(
    body: str,
    cold_rank_e: float | np.ndarray,
    ice_e: float | np.ndarray,
    cold_rank_t: float | None,
    ice_t: float | None,
) -> float | np.ndarray:
    """RBF cold-trap and ice similarity for Moon (cold rank + ice) and Mars (ice_T > 0 only)."""
    body_norm = body.strip().capitalize()
    cre = np.asarray(cold_rank_e, dtype=np.float64)
    ie = np.asarray(ice_e, dtype=np.float64)
    scalar = cre.ndim == 0 and ie.ndim == 0
    shape = np.broadcast_shapes(cre.shape, ie.shape)
    out = np.full(shape, np.nan, dtype=np.float64)

    if ice_t is None or not np.isfinite(float(ice_t)):
        return float("nan") if scalar else out
    ice_t_f = float(ice_t)

    cre_b, ie_b = np.broadcast_arrays(cre, ie)

    if body_norm == "Moon":
        if cold_rank_t is None or not np.isfinite(float(cold_rank_t)):
            return float("nan") if scalar else out
        crt_f = float(cold_rank_t)
        valid = np.isfinite(cre_b) & np.isfinite(ie_b)
        if np.any(valid):
            d_cold = (cre_b[valid] - crt_f) / COLD_RANK_SIGMA
            d_ice = (ie_b[valid] - ice_t_f) / ICE_LEVEL_SIGMA
            d = np.sqrt(d_cold ** 2 + d_ice ** 2) / math.sqrt(2.0)
            out[valid] = np.exp(-0.5 * (d ** 2))
        return float(out) if scalar else out

    if body_norm == "Mars":
        if ice_t_f <= 0.0:
            return float("nan") if scalar else out
        valid = np.isfinite(ie_b)
        if np.any(valid):
            d_ice = (ie_b[valid] - ice_t_f) / ICE_LEVEL_SIGMA
            out[valid] = np.exp(-0.5 * (d_ice ** 2))
        return float(out) if scalar else out

    raise ValueError(f"Unsupported body for S_ice: {body!r}")


score_ice = S_ice


def load_ice_hints(path: Path = ICE_HINTS_JSON) -> dict[str, dict[str, object]]:
    """Load data/ice_hints.json keyed by target_id."""
    if not path.exists():
        logger.warning("ice_hints.json not found at %s; using empty hints", path)
        return {}
    with open(path, "r", encoding="utf-8") as fh:
        payload = json.load(fh)
    hints = payload.get("hints", [])
    out: dict[str, dict[str, object]] = {}
    for item in hints:
        tid = str(item["target_id"]).strip()
        out[tid] = dict(item)
    return out


def _safe_float(v: object) -> float | None:
    try:
        fv = float(v)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return fv if math.isfinite(fv) else None


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


def run_ice(
    t3_dir: Path,
    t4_dir: Path,
    t5_dir: Path,
    t14_dir: Path,
    out_dir: Path,
    hints_path: Path = ICE_HINTS_JSON,
) -> dict[str, object]:
    """Build ice_earth.parquet, ice_targets.parquet, and t12_checks.json."""
    t0 = time.perf_counter()
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. Earth cold_rank_E and ice_E
    earth_t5 = pd.read_parquet(t5_dir / "features_earth.parquet")
    geo_earth = pd.read_parquet(
        t14_dir / "geology_earth.parquet", columns=["lat", "lon", "ice_surface"]
    )
    if len(earth_t5) != len(geo_earth) or not (
        np.allclose(earth_t5["lat"].to_numpy(), geo_earth["lat"].to_numpy(), atol=1e-5)
        and np.allclose(earth_t5["lon"].to_numpy(), geo_earth["lon"].to_numpy(), atol=1e-5)
    ):
        raise ValueError(
            "features_earth.parquet and geology_earth.parquet rows do not align!"
        )

    tmean_earth = 0.5 * (
        pd.to_numeric(earth_t5["lst_day_c"], errors="coerce").to_numpy(dtype=np.float64)
        + pd.to_numeric(earth_t5["lst_night_c"], errors="coerce").to_numpy(dtype=np.float64)
    )
    cold_rank_e = _rank_pct_cold(tmean_earth).astype(np.float32)
    ice_e = compute_ice_e(
        geo_earth["ice_surface"].to_numpy(dtype=bool),
        earth_t5["lst_day_c"].to_numpy(dtype=np.float64),
    ).astype(np.float32)

    ice_earth_df = pd.DataFrame(
        {
            "lat": earth_t5["lat"].to_numpy(dtype=np.float64),
            "lon": earth_t5["lon"].to_numpy(dtype=np.float64),
            "cold_rank_E": cold_rank_e,
            "ice_E": ice_e,
        }
    )
    ice_earth_df.to_parquet(out_dir / "ice_earth.parquet", index=False)
    logger.info(
        "Wrote ice_earth.parquet (%d rows: ice_E==1.0 -> %d, ==0.5 -> %d, ==0.0 -> %d)",
        len(ice_earth_df),
        int(np.sum(ice_e == 1.0)),
        int(np.sum(ice_e == 0.5)),
        int(np.sum(ice_e == 0.0)),
    )

    # 2. Moon Diviner cold reference + Mars geology ICE + hints
    moon_t3 = pd.read_parquet(t3_dir / "features_moon.parquet", columns=["diviner_tavg_k"])
    div_vals = pd.to_numeric(moon_t3["diviner_tavg_k"], errors="coerce").to_numpy(dtype=np.float64)
    div_sorted_neg = np.sort(-div_vals[np.isfinite(div_vals)])
    logger.info("Moon T3 patches with finite diviner_tavg_k: %d", div_sorted_neg.size)

    targets_df = pd.read_parquet(
        t4_dir / "targets.parquet",
        columns=["target_id", "body", "name", "type", "lat", "lon", "diviner_tavg_k", "ice_stable_frac"],
    )
    geo_targets = pd.read_parquet(
        t14_dir / "geology_targets.parquet", columns=["target_id", "geo_class"]
    )
    geo_class_map = {
        str(r["target_id"]): (None if pd.isna(r["geo_class"]) else str(r["geo_class"]))
        for _, r in geo_targets.iterrows()
    }
    hints = load_ice_hints(hints_path)

    target_rows: list[dict[str, object]] = []
    for _, row in targets_df.iterrows():
        tid = str(row["target_id"])
        body = str(row["body"]).strip().capitalize()
        gcls = geo_class_map.get(tid)

        if body == "Moon":
            tavg = float(row["diviner_tavg_k"]) if pd.notna(row["diviner_tavg_k"]) else float("nan")
            isf = float(row["ice_stable_frac"]) if pd.notna(row["ice_stable_frac"]) else float("nan")
            if np.isfinite(tavg) and np.isfinite(isf):
                cold_rank_t = _searchsorted_cold_rank(div_sorted_neg, tavg)
                ice_t = isf
                ice_source = "diviner_prp"
            else:
                cold_rank_t = float("nan")
                ice_t = float("nan")
                ice_source = None
        elif body == "Mars":
            cold_rank_t = float("nan")
            hint = hints.get(tid)
            if hint is not None and gcls == "ICE":
                ice_t = float(hint["ice_T"])
                ice_source = "geology_ICE+ice_hint"
            elif hint is not None:
                ice_t = float(hint["ice_T"])
                ice_source = "ice_hint"
            elif gcls == "ICE":
                ice_t = 1.0
                ice_source = "geology_ICE"
            else:
                ice_t = 0.0
                ice_source = "none"
        else:
            raise ValueError(f"Unsupported body in targets.parquet: {body!r}")

        target_rows.append(
            {
                "target_id": tid,
                "cold_rank_T": np.float32(cold_rank_t),
                "ice_T": np.float32(ice_t),
                "ice_source": ice_source,
            }
        )

    ice_targets_df = pd.DataFrame(target_rows)
    ice_targets_df["target_id"] = ice_targets_df["target_id"].astype("string")
    ice_targets_df["ice_source"] = ice_targets_df["ice_source"].astype("string")
    ice_targets_df.to_parquet(out_dir / "ice_targets.parquet", index=False)
    logger.info("Wrote ice_targets.parquet (%d targets)", len(ice_targets_df))

    # 3. Checks (§4.3)
    # Check 1: Coldest 1% of Earth patches are in Antarctica or Greenland
    cold_mask = np.isfinite(cold_rank_e) & (cold_rank_e >= 0.99)
    cold_sub = earth_t5.loc[cold_mask].copy()
    countries = cold_sub["country"].fillna("None").astype(str).tolist()
    country_counts: dict[str, int] = {}
    for c in countries:
        country_counts[c] = country_counts.get(c, 0) + 1
    in_polar_sheet = (
        cold_sub["country"].isin(["Antarctica", "Greenland"])
        | (cold_sub["lat"] < -60.0)
        | ((cold_sub["lat"] > 59.0) & (cold_sub["lon"] >= -75.0) & (cold_sub["lon"] <= -10.0))
    )
    all_ant_grl = bool(len(cold_sub) > 0 and bool(in_polar_sheet.all()))

    # Check 2: Haworth & Slater cold_rank_T > 0.9
    it_map = ice_targets_df.set_index("target_id")
    haworth_cr = _safe_float(it_map.loc["moon-a3-haworth", "cold_rank_T"]) if "moon-a3-haworth" in it_map.index else None
    slater_cr = _safe_float(it_map.loc["moon-a3-slater-plain", "cold_rank_T"]) if "moon-a3-slater-plain" in it_map.index else None

    # Check 3: Dry Valleys patches have ice_E == 0.5
    if "known_region" in earth_t5.columns and bool((earth_t5["known_region"] == "antarctica-dry-valleys").any()):
        dv_mask = (earth_t5["known_region"] == "antarctica-dry-valleys").to_numpy()
    else:
        dv_mask = (
            (earth_t5["lat"].to_numpy() >= -78.2)
            & (earth_t5["lat"].to_numpy() <= -76.8)
            & (earth_t5["lon"].to_numpy() >= 160.0)
            & (earth_t5["lon"].to_numpy() <= 164.0)
        )
    dv_ice_vals = ice_e[dv_mask]
    dv_frac_05 = float(np.mean(dv_ice_vals == 0.5)) if dv_ice_vals.size > 0 else 0.0

    # Check 4: Mars targets with ice_T > 0
    mars_merged = targets_df[targets_df["body"] == "Mars"].merge(ice_targets_df, on="target_id", how="left")
    mars_ice = mars_merged[mars_merged["ice_T"].fillna(0.0) > 0.0]
    mars_ice_list = [
        {
            "target_id": str(r["target_id"]),
            "name": str(r["name"]),
            "ice_T": _safe_float(r["ice_T"]),
            "ice_source": None if pd.isna(r["ice_source"]) else str(r["ice_source"]),
        }
        for _, r in mars_ice.iterrows()
    ]
    mars_ice_ids = {item["target_id"] for item in mars_ice_list}

    checks = [
        {
            "id": 1,
            "name": "coldest_1pct_earth_polar",
            "kind": "soft",
            "passed": all_ant_grl,
            "observed": {
                "n_coldest_1pct": int(len(cold_sub)),
                "country_counts": country_counts,
                "outside_ant_grl_count": int((~in_polar_sheet).sum()),
            },
            "expected": "All coldest 1% patches in Antarctica or Greenland",
        },
        {
            "id": 2,
            "name": "moon_haworth_slater_cold_rank",
            "kind": "hard",
            "passed": bool(
                haworth_cr is not None
                and slater_cr is not None
                and haworth_cr > 0.9
                and slater_cr > 0.9
            ),
            "observed": {
                "moon-a3-haworth": None if haworth_cr is None else round(haworth_cr, 4),
                "moon-a3-slater-plain": None if slater_cr is None else round(slater_cr, 4),
            },
            "expected": "cold_rank_T > 0.9 for both",
        },
        {
            "id": 3,
            "name": "dry_valleys_ice_e_05",
            "kind": "soft",
            "passed": bool(dv_ice_vals.size > 0 and bool(np.all(dv_ice_vals == 0.5))),
            "observed": {
                "n_patches": int(dv_ice_vals.size),
                "frac_eq_0_5": round(dv_frac_05, 4),
                "unique_values": [float(v) for v in np.unique(dv_ice_vals)],
            },
            "expected": "ice_E == 0.5 on Dry Valleys patches",
        },
        {
            "id": 4,
            "name": "mars_ice_targets_list",
            "kind": "soft",
            "passed": bool("mars-arcadia-swim" in mars_ice_ids and len(mars_ice_list) >= 1),
            "observed": mars_ice_list,
            "expected": "Includes mars-arcadia-swim plus any polar clusters",
        },
    ]

    hard_checks = [c for c in checks if c["kind"] == "hard"]
    soft_checks = [c for c in checks if c["kind"] == "soft"]
    hard_passed = sum(1 for c in hard_checks if c["passed"])
    soft_passed = sum(1 for c in soft_checks if c["passed"])

    report = {
        "task": "T12",
        "t14_dir": str(t14_dir),
        "slurm_job_id": os.environ.get("SLURM_JOB_ID"),
        "commit": _git_short_sha(Path(__file__).resolve().parents[2]),
        "runtime_s": round(time.perf_counter() - t0, 3),
        "hard_passed": hard_passed,
        "hard_total": len(hard_checks),
        "soft_passed": soft_passed,
        "soft_total": len(soft_checks),
        "checks": checks,
    }
    checks_path = out_dir / "t12_checks.json"
    with open(checks_path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, allow_nan=False)

    logger.info(
        "T12 checks: hard %d/%d, soft %d/%d -> %s",
        hard_passed,
        len(hard_checks),
        soft_passed,
        len(soft_checks),
        checks_path,
    )
    if hard_passed < len(hard_checks):
        failed_names = [c["name"] for c in hard_checks if not c["passed"]]
        raise RuntimeError(f"T12 hard checks failed: {failed_names}")
    return report


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build T12 cold-trap and water-ice layers.")
    p.add_argument("--t3-dir", type=Path, default=YUCA_PROJECT_DIR / "runs" / "2242278")
    p.add_argument("--t4-dir", type=Path, default=YUCA_PROJECT_DIR / "runs" / "2242423")
    p.add_argument("--t5-dir", type=Path, default=YUCA_PROJECT_DIR / "runs" / "2242438")
    p.add_argument("--t14-dir", type=Path, required=True)
    p.add_argument("--out-dir", type=Path, required=True)
    p.add_argument("--hints", type=Path, default=ICE_HINTS_JSON)
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="[%(levelname)s] %(name)s: %(message)s",
    )
    args = _parse_args(argv)
    run_ice(
        t3_dir=args.t3_dir,
        t4_dir=args.t4_dir,
        t5_dir=args.t5_dir,
        t14_dir=args.t14_dir,
        out_dir=args.out_dir,
        hints_path=args.hints,
    )


if __name__ == "__main__":
    main()
