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
from pipeline.export import _olympus_mons_sanity_check, build_t7_report
from pipeline.match import EARTH_RADIUS_KM, PRESET_KEYS, match_all


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
                "glim_code": "ig" if i == 0 else ("vb" if i % 3 == 0 else "ss"),
                "geo_class": "ICE" if i == 0 else ("VOLCANIC_BASIC" if i % 3 == 0 else "SEDIMENTARY"),
                "ice_surface": bool(i == 0),
                "lava_tube_terrain": bool(i % 3 == 0 and i != 0),
                "dust_level_rank": (i + 1) / 40.0,
                "dust_seasonality_rank": ((i * 7) % 40 + 1) / 40.0,
                "dust_peak_phase_deg": float((i * 37) % 360),
                "cold_rank_E": 1.0 if i == 0 else (i + 1) / 80.0,
                "ice_E": 1.0 if i == 0 else 0.0,
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
                "geo_unit": "Nc",
                "geo_class": "IMPACT",
                "geo_class_share": 1.0,
                "dust_level_rank": np.nan,
                "dust_seasonality_rank": np.nan,
                "dust_peak_phase_deg": np.nan,
                "cold_rank_T": 0.97,
                "ice_T": 1.0,
                "ice_source": "diviner_prp",
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
                "geo_unit": "lHv",
                "geo_class": "VOLCANIC_BASIC",
                "geo_class_share": 0.75,
                "dust_level_rank": 0.6,
                "dust_seasonality_rank": 0.5,
                "dust_peak_phase_deg": 225.0,
                "cold_rank_T": np.nan,
                "ice_T": 0.0,
                "ice_source": "none",
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
            if tgt["body"] == "Moon":
                assert analog["sub_scores"]["dust"] is None
                assert analog["sub_scores"]["ice"] is not None
            else:
                assert analog["sub_scores"]["dust"] is not None
            assert set(analog["geology"]) == {"glim_code", "geo_class", "lava_tube_terrain", "ice_surface"}
            assert set(analog["dust"]) == {"level_rank", "seasonality_rank", "peak_phase_deg"}
            assert set(analog["ice"]) == {"cold_rank", "ice_E"}
            if analog["subsurface_note"] is not None:
                assert tgt["geology"]["geo_class"] == "VOLCANIC_BASIC"
                assert analog["geology"]["lava_tube_terrain"] is True
        assert tgt["geology"]["geo_class"] in {"IMPACT", "VOLCANIC_BASIC"}
        assert (tgt["dust"] is None) == (tgt["body"] == "Moon")
        assert tgt["ice"]["ice_source"] in {"diviner_prp", "none"}

    meta = parsed["metadata"]
    assert [d["key"] for d in meta["dimensions"]] == [
        "topography", "roughness", "environment", "thermal", "geology", "dust", "ice", "mineral",
    ]
    assert meta["geology_similarity"]["VOLCANIC_BASIC"]["PYROCLASTIC"] == 0.6
    assert meta["runs"]["T12"] == meta["runs"]["T13"] == meta["runs"]["T14"] == "unknown"
    assert {n["item"] for n in meta["not_modelled"]} == {"mineralogy (spectral)", "biology", "caves (mapped)"}
    assert parsed["mission_presets"]["dust_and_seasons"]["applies_to"] == ["Mars"]
    assert len(parsed["mission_presets"]) == 6
    assert "geology_and_materials_mineral_exp" in parsed["mission_presets"]

    olympus_stub = {"top10": [{"geo_class": "SEDIMENTARY"}, {"geo_class": "VOLCANIC_BASIC"}]}
    checks = run_t7_checks(matches, targets, universe, written, olympus=olympus_stub)
    assert checks["summary"]["hard_total"] == 10
    assert checks["summary"]["hard_passed"] == 10
    assert [c["id"] for c in checks["checks"]] == list(range(1, 18))

    no_olympus = run_t7_checks(matches, targets, universe, written, olympus=None)
    assert no_olympus["summary"]["hard_passed"] == 9
    assert not [c for c in no_olympus["checks"] if c["id"] == 7][0]["passed"]


def test_limits_fallback(tmp_path: Path, caplog) -> None:
    sample_path = _write_synthetic_sample(tmp_path / "sample.json")
    missing_limits = tmp_path / "does_not_exist.json"

    with caplog.at_level("WARNING"):
        limits, source = load_limits(limits_path=missing_limits, sample_json_path=sample_path)

    assert source == "provisional (sample.json)"
    assert limits["Moon"][0]["factor"] == "gravity"
    assert limits["Mars"][0]["target"] == "0.38 g"
    assert any("provisional" in rec.message.lower() for rec in caplog.records)


def test_olympus_check_and_report(tmp_path: Path) -> None:
    earth = _synthetic_earth_40()
    targets = _synthetic_targets()
    t13, t14 = tmp_path / "t13", tmp_path / "t14"
    t13.mkdir()
    t14.mkdir()
    km = math.radians(1.0) * EARTH_RADIUS_KM
    mars_rows = []
    for i, (lat, lon) in enumerate([(18.65, -133.8), (18.65 + 400.0 / km, -133.8), (-30.0, 20.0), (5.0, 80.0)]):
        mars_rows.append(
            {
                "lat": lat,
                "lon": lon,
                "mean_slope_deg": 3.0 + i,
                "p90_slope_deg": 6.0 + i,
                "relief_m": 400.0 + 50 * i,
                "hypsometric_integral": 0.5,
                "detrended_std_m": 90.0 + 10 * i,
                "tri_m": 50.0 + 5 * i,
                "mean_elev_m": 1000.0,
                "themis_delta": 20.0 + 10 * i,
            }
        )
    mars_t3 = pd.DataFrame(mars_rows)
    pd.DataFrame(
        {"lat": mars_t3["lat"], "lon": mars_t3["lon"], "unit": "Ave", "geo_class": "VOLCANIC_BASIC"}
    ).to_parquet(t14 / "geology_mars.parquet")
    pd.DataFrame(
        {
            "lat": mars_t3["lat"],
            "lon": mars_t3["lon"],
            "dust_level_rank": 0.5,
            "dust_seasonality_rank": 0.5,
            "dust_peak_phase_deg": 200.0,
        }
    ).to_parquet(t13 / "dust_mars.parquet")

    oly = _olympus_mons_sanity_check(earth, mars_t3, t13, t14)
    assert oly is not None
    assert oly["preset"] == "geology_and_materials"
    assert oly["target_geo_class"] == "VOLCANIC_BASIC"
    assert 1 <= len(oly["top10"]) <= 10
    assert any(r["geo_class"] == "VOLCANIC_BASIC" for r in oly["top10"])

    meta: dict[str, object] = {}
    matches = match_all(earth, targets, pd.DataFrame({"themis_delta": [20.0, 40.0, 60.0]}), meta_out=meta)
    sample = _write_synthetic_sample(tmp_path / "sample.json")
    universe = build_universe_dict(
        matches_df=matches,
        targets_df=targets,
        earth_df=earth,
        matches_meta=meta,
        limits_path=tmp_path / "none.json",
        sample_json_path=sample,
    )
    written = write_universe_json(universe, tmp_path / "out")
    checks = run_t7_checks(matches, targets, universe, written, olympus=oly)
    assert checks["summary"]["hard_passed"] == checks["summary"]["hard_total"] == 10
    report = build_t7_report(universe, checks, earth, mars_t3, olympus=oly)
    assert "Olympus Mons" in report and "geology_and_materials" in report
    assert "## 5. T15 Review Tables" in report
    assert "## 6. T16 Missing Data Policy Review" in report


def test_export_preset_status_and_missing_dims(tmp_path: Path) -> None:
    earth = _synthetic_earth_40()
    targets = _synthetic_targets()
    meta: dict[str, object] = {}
    matches = match_all(earth, targets, pd.DataFrame({"themis_delta": [20.0, 40.0, 60.0]}), meta_out=meta)
    sample_path = _write_synthetic_sample(tmp_path / "sample.json")
    universe = build_universe_dict(
        matches_df=matches,
        targets_df=targets,
        earth_df=earth,
        matches_meta=meta,
        limits_path=tmp_path / "missing.json",
        sample_json_path=sample_path,
    )
    written = write_universe_json(universe, tmp_path / "out")
    parsed = json.loads(written[0].read_text(encoding="utf-8"))

    for t in parsed["targets"]:
        ps = t["preset_status"]
        assert set(ps.keys()) == set(PRESET_KEYS)
        if t["body"] == "Moon":
            assert ps["dust_and_seasons"]["status"] == "not_applicable_body"
            assert ps["dust_and_seasons"]["coverage"] == 0.0
        for a in t["analogs"]:
            assert isinstance(a["earth_missing_dims"], list)
            for pkey, st_info in ps.items():
                if st_info["status"] != "ok":
                    assert a["msi_by_preset"][pkey] is None
                    assert pkey not in a["selected_by"]
