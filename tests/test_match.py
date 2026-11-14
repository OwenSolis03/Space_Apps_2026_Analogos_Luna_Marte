"""Synthetic unit tests for T7 matching logic (pipeline/match.py)."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from pipeline.match import (
    DIMENSION_KEYS,
    EARTH_RADIUS_KM,
    ICE_CAP_EXEMPT_PRESETS,
    MATCH_FEATURES,
    MAX_ICE_SURFACE_PER_PRESET,
    PRESET_KEYS,
    PRESETS,
    Normalizer,
    TargetVec,
    build_earth_arrays,
    dimension_scores,
    dust_scores,
    format_earth_id,
    geology_scores,
    ice_scores,
    layer_mismatches,
    load_layers,
    match_all,
    mismatches,
    msi,
    preprocess_feature,
    score_target,
    select_by_preset,
    select_diverse,
    thermal_ranks,
)


def _sample_earth_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "lat": 20.0,
                "lon": -100.0,
                "mean_slope_deg": 2.0,
                "p90_slope_deg": 4.0,
                "relief_m": 200.0,
                "hypsometric_integral": 0.45,
                "detrended_std_m": 50.0,
                "tri_m": 30.0,
                "mean_elev_m": 500.0,
                "ndvi_max": 0.08,
                "lst_amplitude_c": 22.0,
            },
            {
                "lat": 25.0,
                "lon": -105.0,
                "mean_slope_deg": 4.0,
                "p90_slope_deg": 8.0,
                "relief_m": 400.0,
                "hypsometric_integral": 0.50,
                "detrended_std_m": 100.0,
                "tri_m": 60.0,
                "mean_elev_m": 800.0,
                "ndvi_max": 0.12,
                "lst_amplitude_c": 26.0,
            },
            {
                "lat": 30.0,
                "lon": -110.0,
                "mean_slope_deg": 6.0,
                "p90_slope_deg": 12.0,
                "relief_m": 800.0,
                "hypsometric_integral": 0.55,
                "detrended_std_m": 200.0,
                "tri_m": 120.0,
                "mean_elev_m": 1200.0,
                "ndvi_max": 0.20,
                "lst_amplitude_c": 30.0,
            },
        ]
    )


def test_identical_target_scores_one() -> None:
    earth = _sample_earth_df()
    norm = Normalizer.fit_earth(earth)
    z_e = norm.transform(earth)
    target = earth.iloc[[0]].copy()
    z_t = norm.transform(target)[0]

    scores = dimension_scores(
        z_e=z_e,
        z_t=z_t,
        ndvi=earth["ndvi_max"].to_numpy(),
        zt_e=np.array([0.2, 0.5, 0.8]),
        zt_t=0.2,
    )
    assert scores["topography"][0] == pytest.approx(1.0)
    assert scores["roughness"][0] == pytest.approx(1.0)
    assert scores["environment"][0] == pytest.approx(1.0)
    assert scores["thermal"][0] == pytest.approx(1.0)


def test_normalizer_uses_earth_only() -> None:
    earth = _sample_earth_df()
    norm_only = Normalizer.fit_earth(earth)

    extreme_targets = pd.DataFrame(
        [
            {
                "mean_slope_deg": 80.0,
                "p90_slope_deg": 85.0,
                "relief_m": 20000.0,
                "hypsometric_integral": 0.99,
                "detrended_std_m": 9000.0,
                "tri_m": 5000.0,
            }
        ]
    )
    norm_again = Normalizer.fit_earth(earth)
    z_t = norm_only.transform(extreme_targets)
    assert z_t.shape == (1, len(MATCH_FEATURES))
    assert norm_only.median == norm_again.median
    assert norm_only.scale == norm_again.scale


def test_log1p_applied() -> None:
    val = preprocess_feature(np.array([math.e - 1.0]), "relief_m")
    assert val[0] == pytest.approx(1.0)

    df = pd.DataFrame(
        {
            "mean_slope_deg": [1.0, 2.0, 3.0],
            "p90_slope_deg": [2.0, 4.0, 6.0],
            "relief_m": [math.e - 1.0, math.e**2 - 1.0, math.e**3 - 1.0],
            "hypsometric_integral": [0.4, 0.5, 0.6],
            "detrended_std_m": [10.0, 20.0, 30.0],
            "tri_m": [5.0, 10.0, 15.0],
        }
    )
    norm = Normalizer.fit_earth(df)
    assert norm.median["relief_m"] == pytest.approx(2.0)
    z = norm.transform(df)
    assert z[0, 2] < 0.0
    assert z[1, 2] == pytest.approx(0.0)


def test_env_score() -> None:
    z = np.zeros((3, len(MATCH_FEATURES)), dtype=np.float64)
    scores = dimension_scores(
        z_e=z,
        z_t=z[0],
        ndvi=np.array([0.10, 0.20, np.nan]),
        zt_e=np.array([0.5, 0.5, 0.5]),
        zt_t=np.nan,
    )
    assert scores["environment"][0] == pytest.approx(1.0)
    assert scores["environment"][1] == pytest.approx(math.exp(-0.5))
    assert scores["environment"][2] == pytest.approx(1.0)


def test_thermal_null_for_moon() -> None:
    earth = _sample_earth_df()
    mars_t3 = pd.DataFrame({"themis_delta": [10.0, 20.0, 30.0]})
    targets = pd.DataFrame(
        [
            {"body": "Moon", "themis_delta": np.nan},
            {"body": "Mars", "themis_delta": 20.0},
        ]
    )
    zt_e, zt_t = thermal_ranks(earth, mars_t3, targets)
    assert np.isnan(zt_t[0])
    assert zt_t[1] == pytest.approx(2.0 / 3.0)

    z = np.zeros((3, len(MATCH_FEATURES)), dtype=np.float64)
    scores = dimension_scores(
        z_e=z,
        z_t=z[0],
        ndvi=np.array([0.05, 0.05, 0.05]),
        zt_e=zt_e,
        zt_t=zt_t[0],
    )
    assert np.all(np.isnan(scores["thermal"]))


def test_msi_skips_null() -> None:
    val = msi(
        {"topography": 1.0, "thermal": np.nan},
        {"topography": 0.5, "thermal": 0.5},
    )
    assert val == pytest.approx(1.0)

    vec = msi(
        {
            "topography": np.array([1.0, 0.6]),
            "thermal": np.array([np.nan, 0.4]),
        },
        {"topography": 0.5, "thermal": 0.5},
    )
    np.testing.assert_allclose(vec, [1.0, 0.5])


def test_select_diverse_150km() -> None:
    km_per_deg = math.radians(1.0) * EARTH_RADIUS_KM
    lat_100 = np.array([i * (100.0 / km_per_deg) for i in range(6)], dtype=np.float64)
    lon = np.zeros(6, dtype=np.float64)
    polar = np.zeros(6, dtype=bool)
    picked_100 = select_diverse(np.arange(6), lat_100, lon, polar, n=30)
    assert picked_100 == [0, 2, 4]

    lat_200 = np.array([i * (200.0 / km_per_deg) for i in range(6)], dtype=np.float64)
    picked_200 = select_diverse(np.arange(6), lat_200, lon, polar, n=30)
    assert picked_200 == [0, 1, 2, 3, 4, 5]


def test_select_diverse_polar_cap() -> None:
    km_per_deg = math.radians(1.0) * EARTH_RADIUS_KM
    lats = np.array([(-80.0 + i * (250.0 / km_per_deg)) for i in range(20)], dtype=np.float64)
    lons = np.zeros(20, dtype=np.float64)
    polar = np.array([i < 10 for i in range(20)], dtype=bool)

    chosen = select_diverse(np.arange(20), lats, lons, polar, n=30)
    polar_chosen = [idx for idx in chosen if polar[idx]]
    assert len(polar_chosen) == 3
    assert len(chosen) == 13


def test_mismatches_threshold() -> None:
    e_row = {feat: 10.0 for feat in MATCH_FEATURES}
    t_row = {feat: 5.0 for feat in MATCH_FEATURES}

    z_t = np.zeros(len(MATCH_FEATURES), dtype=np.float64)
    z_e_below = np.zeros(len(MATCH_FEATURES), dtype=np.float64)
    z_e_below[0] = 1.4
    assert mismatches(e_row, t_row, z_e_below, z_t, zt_e=np.nan, zt_t=np.nan) == []

    z_e_above = np.zeros(len(MATCH_FEATURES), dtype=np.float64)
    z_e_above[0] = 1.6
    mm = mismatches(e_row, t_row, z_e_above, z_t, zt_e=np.nan, zt_t=np.nan)
    assert len(mm) == 1
    assert mm[0] == {
        "feature": "mean_slope_deg",
        "earth": 10.0,
        "target": 5.0,
        "z_diff": 1.6,
    }


def test_earth_id_format() -> None:
    assert format_earth_id(31.848, -113.39) == "earth+31.8480-113.3900"
    assert format_earth_id(-0.0, 0.0) == "earth+00.0000+000.0000"


# --------------------------------------------------------------------------- T15 (7 dimensions)


def _spread_earth(n: int = 40, ice_first: int = 0) -> pd.DataFrame:
    """Synthetic Earth table of n patches spaced ~200 km apart with layer columns."""
    km_per_deg = math.radians(1.0) * EARTH_RADIUS_KM
    classes = ["VOLCANIC_BASIC", "SEDIMENTARY", "IMPACT", "CRYSTALLINE", "ICE"]
    rows = []
    for i in range(n):
        is_ice = i < ice_first
        rows.append(
            {
                "lat": round(-40.0 + (i % 10) * (200.0 / km_per_deg), 6),
                "lon": -60.0 + (i // 10) * 5.0,
                "mean_slope_deg": 1.0 + i * 0.1,
                "p90_slope_deg": 2.0 + i * 0.2,
                "relief_m": 100.0 + i * 10.0,
                "hypsometric_integral": 0.4 + (i % 5) * 0.02,
                "detrended_std_m": 40.0 + i * 2.0,
                "tri_m": 25.0 + i * 1.5,
                "mean_elev_m": 500.0,
                "ndvi_max": 0.05,
                "lst_day_c": -20.0 if is_ice else 25.0,
                "lst_amplitude_c": 10.0 + i * 0.3,
                "geo_class": "ICE" if is_ice else classes[i % 4],
                "glim_code": "ig" if is_ice else "vb",
                "ice_surface": bool(is_ice),
                "lava_tube_terrain": bool(i % 7 == 0 and not is_ice),
                "dust_level_rank": (i + 1) / n,
                "dust_seasonality_rank": ((i * 7) % n + 1) / n,
                "dust_peak_phase_deg": float((i * 37) % 360),
                "cold_rank_E": 1.0 if is_ice else (i + 1) / (2.0 * n),
                "ice_E": 1.0 if is_ice else 0.0,
            }
        )
    return pd.DataFrame(rows)


def _target_vec(body: str = "Mars", lat: float = 30.0, geo: str | None = "VOLCANIC_BASIC", **kw) -> TargetVec:
    base = dict(
        body=body,
        z_t=np.zeros(len(MATCH_FEATURES)),
        zt_t=0.5 if body == "Mars" else float("nan"),
        lat=lat,
        geo_class=geo,
        dust_level_rank=0.6 if body == "Mars" else float("nan"),
        dust_season_rank=0.5 if body == "Mars" else float("nan"),
        dust_phase=225.0 if body == "Mars" else float("nan"),
        cold_rank=float("nan"),
        ice_t=0.0 if body == "Mars" else float("nan"),
    )
    base.update(kw)
    return TargetVec(**base)


def test_presets_have_seven_dimensions_and_five_presets() -> None:
    assert PRESET_KEYS == (
        "mobility_and_traction",
        "construction_and_base",
        "geology_and_materials",
        "dust_and_seasons",
        "isru_and_ice",
    )
    assert DIMENSION_KEYS == ("topography", "roughness", "environment", "thermal", "geology", "dust", "ice")
    for pkey in PRESET_KEYS:
        w = PRESETS[pkey]["weights"]
        assert set(w) == set(DIMENSION_KEYS)
        assert sum(w.values()) == pytest.approx(1.0)
    assert PRESETS["dust_and_seasons"]["applies_to"] == ["Mars"]


def test_geology_scores_use_similarity_matrix() -> None:
    cls = np.array(["VOLCANIC_BASIC", "PYROCLASTIC", "ICE", None, "EVAPORITE"], dtype=object)
    sc = geology_scores(cls, "VOLCANIC_BASIC")
    assert sc[0] == pytest.approx(1.0)
    assert sc[1] == pytest.approx(0.6)
    assert sc[2] == pytest.approx(0.0)
    assert np.isnan(sc[3])
    assert np.all(np.isnan(geology_scores(cls, None)))


def test_msi_seven_dimensions_with_nulls() -> None:
    scores = {
        "topography": np.array([1.0, 0.5]),
        "roughness": np.array([1.0, 0.5]),
        "environment": np.array([1.0, 0.5]),
        "thermal": np.array([np.nan, np.nan]),
        "geology": np.array([0.0, 1.0]),
        "dust": np.array([np.nan, np.nan]),
        "ice": np.array([np.nan, 1.0]),
    }
    w = PRESETS["isru_and_ice"]["weights"]
    vec = msi(scores, w)
    # patch 0: (0.2 + 0.1 + 0.05 + 0.0) / 0.5 = 0.7 ; patch 1: (0.1 + 0.05 + 0.025 + 0.15 + 0.5) / 1.0
    np.testing.assert_allclose(vec, [0.7, 0.825])


def test_tropical_target_ignores_phase_difference() -> None:
    n = 3
    lvl = np.full(n, 0.6)
    sea = np.full(n, 0.5)
    lat = np.full(n, 40.0)
    same = dust_scores("Mars", lvl, sea, np.full(n, 225.0), lat, 0.6, 0.5, 225.0, 40.0)
    opposite = dust_scores("Mars", lvl, sea, np.full(n, 45.0), lat, 0.6, 0.5, 225.0, 40.0)
    assert same[0] == pytest.approx(1.0)
    assert opposite[0] < 0.5

    tropical_t = dust_scores("Mars", lvl, sea, np.full(n, 45.0), lat, 0.6, 0.5, 225.0, 5.0)
    assert tropical_t[0] == pytest.approx(1.0)

    tropical_e = dust_scores("Mars", lvl, sea, np.full(n, 45.0), np.full(n, -10.0), 0.6, 0.5, 225.0, 40.0)
    assert tropical_e[0] == pytest.approx(1.0)

    # Without the phase term the level/season distance uses exp(-(dl^2 + ds^2) / 4).
    off = dust_scores("Mars", np.array([0.75]), np.array([0.5]), np.array([45.0]), np.array([5.0]), 0.6, 0.5, 225.0, 5.0)
    assert off[0] == pytest.approx(math.exp(-((0.15 / 0.15) ** 2) / 4.0))
    # A tropical Earth patch with a missing phase is still scored.
    nan_phase = dust_scores("Mars", lvl, sea, np.full(n, np.nan), np.full(n, 0.0), 0.6, 0.5, 225.0, 40.0)
    assert nan_phase[0] == pytest.approx(1.0)


def test_dust_is_null_for_moon_and_ice_nulls() -> None:
    n = 2
    assert np.all(np.isnan(dust_scores("Moon", np.ones(n), np.ones(n), np.ones(n), np.zeros(n), 0.5, 0.5, 90.0, 10.0)))
    assert np.all(np.isnan(ice_scores("Mars", np.ones(n), np.ones(n), float("nan"), 0.0)))
    assert np.all(np.isnan(ice_scores("Moon", np.ones(n), np.ones(n), float("nan"), float("nan"))))
    assert ice_scores("Mars", np.array([0.2]), np.array([1.0]), float("nan"), 1.0)[0] == pytest.approx(1.0)


def test_layer_mismatches() -> None:
    mm = layer_mismatches(
        "Mars", "SEDIMENTARY", "IMPACT", 0.9, 0.5, 0.5, 0.45, 10.0, 200.0, 40.0, 30.0, float("nan"), float("nan")
    )
    feats = [m["feature"] for m in mm]
    assert feats == ["geo_class", "dust_level_rank", "dust_peak_phase_deg"]
    assert mm[0]["z_diff"] is None
    # tropical target: no phase mismatch
    mm_t = layer_mismatches(
        "Mars", "IMPACT", "IMPACT", 0.5, 0.5, 0.5, 0.5, 10.0, 200.0, 40.0, 5.0, float("nan"), float("nan")
    )
    assert mm_t == []
    cold = layer_mismatches("Moon", None, None, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, 10.0, -87.0, 0.2, 0.97)
    assert [m["feature"] for m in cold] == ["cold_rank"]


def test_ice_cap_not_applied_to_isru_preset() -> None:
    earth = _spread_earth(40, ice_first=20)
    norm = Normalizer.fit_earth(earth)
    ea = build_earth_arrays(earth, norm.transform(earth), np.full(len(earth), 0.5))
    tv = _target_vec("Moon", lat=-87.0, geo="ICE", cold_rank=0.97, ice_t=1.0)
    scores = score_target(ea, tv)
    _, selected, _ = select_by_preset(scores, ea)
    for pkey in PRESET_KEYS:
        n_ice = int(sum(ea.ice_surface[i] for i in selected[pkey]))
        if pkey in ICE_CAP_EXEMPT_PRESETS:
            assert n_ice > MAX_ICE_SURFACE_PER_PRESET
        else:
            assert n_ice <= MAX_ICE_SURFACE_PER_PRESET


def test_scoring_without_pool_matches_bruteforce_top1() -> None:
    earth = _spread_earth(40)
    norm = Normalizer.fit_earth(earth)
    ea = build_earth_arrays(earth, norm.transform(earth), np.linspace(0.1, 0.9, len(earth)))
    tv = _target_vec("Mars", lat=30.0, geo="SEDIMENTARY")
    scores = score_target(ea, tv)
    msi_by_preset, selected, _ = select_by_preset(scores, ea)
    for pkey in PRESET_KEYS:
        brute = int(np.nanargmax(msi_by_preset[pkey]))
        assert selected[pkey][0] == brute
        assert msi_by_preset[pkey][selected[pkey][0]] == pytest.approx(np.nanmax(msi_by_preset[pkey]))


def test_match_all_seven_dimensions_and_moon_nulls() -> None:
    earth = _spread_earth(40, ice_first=4)
    targets = pd.DataFrame(
        [
            {
                "target_id": "moon-t",
                "type": "CURATED",
                "body": "Moon",
                "lat": -87.0,
                "lon": 0.0,
                "status": "ok",
                "mean_slope_deg": 3.0,
                "p90_slope_deg": 6.0,
                "relief_m": 300.0,
                "hypsometric_integral": 0.45,
                "detrended_std_m": 70.0,
                "tri_m": 40.0,
                "themis_delta": np.nan,
                "geo_class": "IMPACT",
                "dust_level_rank": np.nan,
                "dust_seasonality_rank": np.nan,
                "dust_peak_phase_deg": np.nan,
                "cold_rank_T": 0.97,
                "ice_T": 1.0,
            },
            {
                "target_id": "mars-t",
                "type": "CURATED",
                "body": "Mars",
                "lat": 5.0,
                "lon": 0.0,
                "status": "ok",
                "mean_slope_deg": 2.0,
                "p90_slope_deg": 4.0,
                "relief_m": 200.0,
                "hypsometric_integral": 0.45,
                "detrended_std_m": 60.0,
                "tri_m": 35.0,
                "themis_delta": 30.0,
                "geo_class": "VOLCANIC_BASIC",
                "dust_level_rank": 0.6,
                "dust_seasonality_rank": 0.5,
                "dust_peak_phase_deg": 225.0,
                "cold_rank_T": np.nan,
                "ice_T": 0.0,
            },
        ]
    )
    meta: dict[str, object] = {}
    out = match_all(earth, targets, pd.DataFrame({"themis_delta": [10.0, 30.0, 50.0]}), meta_out=meta)
    moon = out[out["target_id"] == "moon-t"]
    mars = out[out["target_id"] == "mars-t"]
    assert moon["S_dust"].isna().all() and moon["S_thermal"].isna().all()
    assert moon["S_ice"].notna().all()
    assert mars["S_dust"].notna().any() and mars["S_ice"].isna().all()
    for col in ("S_geology", "S_dust", "S_ice"):
        vals = out[col].dropna()
        assert ((vals >= 0.0) & (vals <= 1.0)).all()
    for pkey in PRESET_KEYS:
        assert f"rank_{pkey}" in out.columns and f"msi_{pkey}" in out.columns
        assert out[f"rank_{pkey}"].notna().sum() >= 20
    assert meta["candidate_pool"].startswith("none")


def test_load_layers_aligned_and_misaligned(tmp_path) -> None:
    earth = _spread_earth(5)[["lat", "lon"]].copy()
    targets = pd.DataFrame({"target_id": ["a", "b"], "body": ["Moon", "Mars"], "lat": [0.0, 1.0]})
    t12, t13, t14 = tmp_path / "t12", tmp_path / "t13", tmp_path / "t14"
    for d in (t12, t13, t14):
        d.mkdir()
    base = earth.copy()
    geo = base.assign(
        glim_code="vb", geo_class="VOLCANIC_BASIC", ice_surface=False, lava_tube_terrain=True
    )
    geo.to_parquet(t14 / "geology_earth.parquet")
    base.assign(dust_level_rank=0.5, dust_seasonality_rank=0.5, dust_peak_phase_deg=90.0).to_parquet(
        t13 / "dust_earth.parquet"
    )
    base.assign(cold_rank_E=0.1, ice_E=0.0).to_parquet(t12 / "ice_earth.parquet")
    pd.DataFrame(
        {"target_id": ["a", "b"], "unit": ["x", "y"], "geo_class": ["IMPACT", None], "geo_class_share": [1.0, 0.5]}
    ).to_parquet(t14 / "geology_targets.parquet")
    pd.DataFrame(
        {
            "target_id": ["a", "b"],
            "dust_level_rank": [np.nan, 0.4],
            "dust_seasonality_rank": [np.nan, 0.4],
            "dust_peak_phase_deg": [np.nan, 10.0],
        }
    ).to_parquet(t13 / "dust_targets.parquet")
    pd.DataFrame(
        {"target_id": ["a", "b"], "cold_rank_T": [0.9, np.nan], "ice_T": [1.0, 0.0], "ice_source": ["diviner_prp", "none"]}
    ).to_parquet(t12 / "ice_targets.parquet")

    e_out, t_out = load_layers(earth, targets, t12, t13, t14)
    assert {"geo_class", "ice_surface", "dust_level_rank", "cold_rank_E", "ice_E"}.issubset(e_out.columns)
    assert {"geo_unit", "geo_class", "geo_class_share", "cold_rank_T", "ice_T", "ice_source"}.issubset(t_out.columns)
    assert list(t_out["target_id"]) == ["a", "b"]

    shifted = earth.copy()
    shifted["lat"] = shifted["lat"] + 1.0
    with pytest.raises(ValueError):
        load_layers(shifted, targets, t12, t13, t14)
