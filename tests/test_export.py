"""Synthetic unit tests for T8 export and checks (pipeline/export.py)."""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from pipeline.export import (
    REQUIRED_ANALOG_KEYS,
    REQUIRED_TARGET_KEYS,
    build_universe_dict,
    load_limits,
    run_t7_checks,
    write_universe_json,
)
from pipeline.match import EARTH_RADIUS_KM, match_all


def _synthetic_earth_40() -> pd.DataFrame:
    """Create 40 spread-out Earth candidate patches so >= 20 satisfy 150 km separation."""
    km_per_deg = math.radians(1.0) * EARTH_RADIUS_KM
    rows = []
    for i in range(40):
        lat = -40.0 + (i % 10) * (200.0 / km_per_deg)
        lon = -60.0 + (i // 10) * 5.0
        rows.append(
            {
                "body": "Earth",
                "lat": round(lat, 6),
                "lon": round(lon, 6),
                "mean_slope_deg": 1.0 + i * 0.25,
                "p90_slope_deg": 2.0 + i * 0.5,
                "relief_m": 100.0 + i * 25.0,
                "hypsometric_integral": 0.40 + (i % 5) * 0.05,
                "detrended_std_m": 40.0 + i * 5.0,
                "tri_m": 25.0 + i * 3.0,
                "mean_elev_m": 500.0 + i * 10.0,
                "valid_frac": 0.98,
                "ndvi_max": np.nan if i == 0 else 0.08 + (i % 3) * 0.03,
                "lst_day_c": -25.0 if i == 0 else 20.0 + i * 0.2,
                "lst_night_c": -40.0 if i == 0 else 5.0 + i * 0.1,
                "lst_amplitude_c": 15.0 + i * 0.2,
                "dist_road_km": 10.0 + i,
                "dist_airport_km": 50.0 + i,
                "nearest_airport_iata": "HMO",
                "nearest_airport_name": "Hermosillo Airport",
                "country": "Antarctica" if i == 0 else "Mexico",
                "known_region": None if i % 2 else "atacama",
                "classification": "NEW_CANDIDATE" if i % 2 else "KNOWN_ANALOG",
                "ndvi_missing": bool(i == 0),
            }
        )
    return pd.DataFrame(rows)


def _synthetic_targets() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "target_id": "moon-a3-haworth",
                "type": "CURATED",
                "body": "Moon",
                "name": "Haworth rim",
                "category": "Artemis III candidate region",
                "why": "South pole rim.",
                "lat": -87.45,
                "lon": -5.17,
                "anchor_note": "Approximate rim",
                "source_url": "https://example.org/a3",
                "coord_source_url": "https://example.org/coord",
                "status": "ok",
                "mean_slope_deg": 5.0,
                "p90_slope_deg": 10.0,
                "relief_m": 500.0,
                "hypsometric_integral": 0.50,
                "detrended_std_m": 120.0,
                "tri_m": 70.0,
                "mean_elev_m": -700.0,
                "themis_day": np.nan,
                "themis_night": np.nan,
                "themis_delta": np.nan,
                "wac_reflectance": 40.0,
                "wac_percentile": 0.25,
                "ice_favorability": 0.1,
                "diviner_tmax_k": 220.0,
                "diviner_tavg_k": 65.0,
                "ice_depth_m": 0.05,
                "ice_stable_frac": 1.0,
                "iau_label": "Haworth (Crater, craters)",
                "cluster_rank": pd.NA,
            },
            {
                "target_id": "mars-perseverance-jezero",
                "type": "CURATED",
                "body": "Mars",
                "name": "Jezero Crater",
                "category": "Landing site",
                "why": "Ancient lake delta.",
                "lat": 18.44,
                "lon": 77.45,
                "anchor_note": "Published landing site",
                "source_url": "https://example.org/jezero",
                "coord_source_url": "https://example.org/jcoord",
                "status": "ok",
                "mean_slope_deg": 2.5,
                "p90_slope_deg": 5.0,
                "relief_m": 250.0,
                "hypsometric_integral": 0.48,
                "detrended_std_m": 80.0,
                "tri_m": 45.0,
                "mean_elev_m": -2500.0,
                "themis_day": 150.0,
                "themis_night": 90.0,
                "themis_delta": 60.0,
                "wac_reflectance": np.nan,
                "wac_percentile": np.nan,
                "ice_favorability": np.nan,
                "diviner_tmax_k": np.nan,
                "diviner_tavg_k": np.nan,
                "ice_depth_m": np.nan,
                "ice_stable_frac": np.nan,
                "iau_label": "Jezero (Crater, craters)",
                "cluster_rank": pd.NA,
            },
        ]
    )


def _write_synthetic_sample(path: Path) -> Path:
    sample = {
        "limits": {
            "Moon": [
                {
                    "factor": "gravity",
                    "earth": "1 g",
                    "target": "0.166 g",
                    "consequence": "Lower gravity.",
                    "source": "https://nssdc.gsfc.nasa.gov/planetary/factsheet/moonfact.html",
                }
            ],
            "Mars": [
                {
                    "factor": "gravity",
                    "earth": "1 g",
                    "target": "0.38 g",
                    "consequence": "Lower gravity.",
                    "source": "https://nssdc.gsfc.nasa.gov/planetary/factsheet/marsfact.html",
                }
            ],
        }
    }
    path.write_text(json.dumps(sample), encoding="utf-8")
    return path


def test_json_no_nan_and_schema(tmp_path: Path) -> None:
    earth = _synthetic_earth_40()
    targets = _synthetic_targets()
    mars_t3 = pd.DataFrame({"themis_delta": [20.0, 40.0, 60.0, 80.0]})

    meta: dict[str, object] = {}
    matches = match_all(earth, targets, mars_t3, meta_out=meta)
    sample_path = _write_synthetic_sample(tmp_path / "sample.json")

    universe = build_universe_dict(
        matches_df=matches,
        targets_df=targets,
        earth_df=earth,
        matches_meta=meta,
        limits_path=tmp_path / "missing_limits.json",
        sample_json_path=sample_path,
        export_job_id="99999",
    )
    out_dir = tmp_path / "out"
    written = write_universe_json(universe, out_dir)
    assert len(written) == 1

    raw = written[0].read_text(encoding="utf-8")
    assert "NaN" not in raw
    assert "Infinity" not in raw
    parsed = json.loads(raw)

    assert len(parsed["targets"]) == 2
    moon_t, mars_t = parsed["targets"]
    assert moon_t["body"] == "Moon"
    assert mars_t["body"] == "Mars"

    for tgt in parsed["targets"]:
        assert REQUIRED_TARGET_KEYS.issubset(tgt.keys())
        for analog in tgt["analogs"]:
            assert REQUIRED_ANALOG_KEYS.issubset(analog.keys())
            if tgt["body"] == "Moon":
                assert analog["sub_scores"]["thermal"] is None
            else:
                assert analog["sub_scores"]["thermal"] is not None
            if analog["earth_env"]["ndvi_missing"]:
                assert analog["earth_env"]["ndvi_max"] is None

    checks = run_t7_checks(matches, targets, universe, written)
    assert checks["summary"]["hard_passed"] == 5
    assert checks["summary"]["hard_total"] == 5


def test_limits_fallback(tmp_path: Path, caplog) -> None:
    sample_path = _write_synthetic_sample(tmp_path / "sample.json")
    missing_limits = tmp_path / "does_not_exist.json"

    with caplog.at_level("WARNING"):
        limits, source = load_limits(limits_path=missing_limits, sample_json_path=sample_path)

    assert source == "provisional (sample.json)"
    assert limits["Moon"][0]["factor"] == "gravity"
    assert limits["Mars"][0]["target"] == "0.38 g"
    assert any("provisional" in rec.message.lower() for rec in caplog.records)
