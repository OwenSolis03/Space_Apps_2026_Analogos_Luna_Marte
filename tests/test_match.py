"""Synthetic unit tests for T7 matching logic (pipeline/match.py)."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from pipeline.match import (
    EARTH_RADIUS_KM,
    MATCH_FEATURES,
    Normalizer,
    dimension_scores,
    format_earth_id,
    mismatches,
    msi,
    preprocess_feature,
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
