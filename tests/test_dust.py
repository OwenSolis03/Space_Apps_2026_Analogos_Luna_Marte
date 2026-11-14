"""Synthetic unit tests for T13 dust metrics, solar longitude, local phase, and S_dust."""

from __future__ import annotations

import math

import numpy as np

from pipeline.dust import Ls_E, S_dust, circular_diff, compute_curve_metrics, local_phase


def test_earth_ls_seasonal_benchmarks() -> None:
    """Mid-March ~ 0 deg, mid-June ~ 90 deg, mid-December ~ 270 deg (+/- 5 deg)."""
    ls_mar = Ls_E(79.5)   # March equinox (~mid/late March)
    ls_mar_mid = Ls_E(75.0)  # March 16
    ls_jun = Ls_E(166.0)  # June 15
    ls_dec = Ls_E(349.0)  # Dec 15

    assert circular_diff(ls_mar, 0.0) < 1.0
    assert circular_diff(ls_mar_mid, 0.0) <= 5.0
    assert circular_diff(ls_jun, 90.0) <= 5.0
    assert circular_diff(ls_dec, 270.0) <= 5.0


def test_local_phase_and_circular_diff() -> None:
    """Southern sites shift Ls by 180 deg; circular_diff(350, 10) == 20."""
    assert local_phase(45.0, 20.0) == 45.0
    assert local_phase(45.0, -20.0) == 225.0
    assert local_phase(225.0, -5.0) == 45.0
    assert local_phase(45.0, 0.0) == 45.0

    phases = local_phase(np.array([10.0, 200.0]), np.array([15.0, -15.0]))
    assert np.allclose(phases, [10.0, 20.0])

    assert circular_diff(350.0, 10.0) == 20.0
    assert circular_diff(10.0, 350.0) == 20.0
    assert circular_diff(0.0, 180.0) == 180.0


def test_curve_metrics_peak_bin7_and_seasonality() -> None:
    """12-bin curve peaking at bin 7 has local peak phase 225 N / 45 S and exact seasonality."""
    curve = np.array([0.2] * 12, dtype=np.float64)
    curve[0] = 0.1
    curve[7] = 1.3  # bin 7 center = 30*7 + 15 = 225 deg

    mean_expected = float(np.mean(curve))
    season_expected = (1.3 - 0.1) / (mean_expected + 1e-6)

    lvl_n, seas_n, ph_n, n_n = compute_curve_metrics(curve, lat=30.0)
    assert int(n_n) == 12
    assert math.isclose(float(lvl_n), mean_expected, rel_tol=1e-9)
    assert math.isclose(float(seas_n), season_expected, rel_tol=1e-9)
    assert math.isclose(float(ph_n), 225.0, abs_tol=1e-9)

    lvl_s, seas_s, ph_s, _ = compute_curve_metrics(curve, lat=-30.0)
    assert math.isclose(float(lvl_s), mean_expected, rel_tol=1e-9)
    assert math.isclose(float(seas_s), season_expected, rel_tol=1e-9)
    assert math.isclose(float(ph_s), 45.0, abs_tol=1e-9)

    # Fewer than 9 valid bins must yield NaN
    sparse = curve.copy()
    sparse[:4] = np.nan
    lvl_bad, seas_bad, ph_bad, n_bad = compute_curve_metrics(sparse, lat=10.0, min_valid_bins=9)
    assert int(n_bad) == 8
    assert np.isnan(lvl_bad) and np.isnan(seas_bad) and np.isnan(ph_bad)


def test_s_dust_similarity() -> None:
    """S_dust is 1.0 for identical inputs, < 0.5 for 180 deg phase shift, NaN on missing."""
    same = S_dust(0.8, 0.5, 225.0, 0.8, 0.5, 225.0)
    assert math.isclose(float(same), 1.0, abs_tol=1e-12)

    opp = S_dust(0.8, 0.5, 45.0, 0.8, 0.5, 225.0)
    # (180 / 60)^2 / 6 = 9 / 6 = 1.5 -> exp(-1.5) ~= 0.2231 < 0.5
    assert math.isclose(float(opp), math.exp(-1.5), rel_tol=1e-9)
    assert float(opp) < 0.5

    # Vectorised check + NaN handling
    vec = S_dust(
        np.array([0.8, np.nan]),
        np.array([0.5, 0.5]),
        np.array([225.0, 225.0]),
        0.8,
        0.5,
        225.0,
    )
    assert math.isclose(float(vec[0]), 1.0, abs_tol=1e-12)
    assert np.isnan(vec[1])
    assert np.isnan(S_dust(0.8, 0.5, 225.0, float("nan"), 0.5, 225.0))
