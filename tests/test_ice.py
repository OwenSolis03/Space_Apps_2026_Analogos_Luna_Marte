"""Synthetic unit tests for T12 ice_E tiers and S_ice null handling."""

from __future__ import annotations

import math

import numpy as np

from pipeline.ice import S_ice, compute_ice_e


def test_ice_e_tiers() -> None:
    """ice_E returns 1.0 for ice_surface, 0.5 for frozen ground without ice_surface, else 0.0."""
    ice_surf = np.array([True, True, False, False, False])
    lst_day = np.array([-20.0, 2.0, -5.0, 0.0, 15.0])
    out = compute_ice_e(ice_surf, lst_day)
    assert np.allclose(out, [1.0, 1.0, 0.5, 0.0, 0.0])

    # NaN LST without ice_surface -> 0.0
    out_nan = compute_ice_e(False, float("nan"))
    assert out_nan == 0.0


def test_s_ice_scoring_and_null_rules() -> None:
    """S_ice is NaN for Mars ice_T=0 and Moon without Diviner, and computes RBF otherwise."""
    # Mars with ice_T == 0 must be null
    s_mars_zero = S_ice("Mars", np.array([0.9, 0.2]), np.array([1.0, 0.0]), None, 0.0)
    assert np.all(np.isnan(s_mars_zero))

    # Mars with ice_T > 0 scores based on ice_E vs ice_T
    s_mars_ice = S_ice("Mars", np.array([0.9, 0.5, 0.1]), np.array([1.0, 0.5, 0.0]), None, 1.0)
    assert math.isclose(float(s_mars_ice[0]), 1.0, rel_tol=1e-9)
    assert math.isclose(float(s_mars_ice[1]), math.exp(-0.5 * ((0.5 - 1.0) / 0.5) ** 2), rel_tol=1e-9)
    assert math.isclose(float(s_mars_ice[2]), math.exp(-0.5 * ((0.0 - 1.0) / 0.5) ** 2), rel_tol=1e-9)

    # Moon without Diviner (cold_rank_T is NaN) must be null
    s_moon_nodiv = S_ice("Moon", np.array([0.9, 0.5]), np.array([1.0, 0.0]), float("nan"), float("nan"))
    assert np.all(np.isnan(s_moon_nodiv))

    # Moon with Diviner: identical cold_rank and ice -> 1.0
    s_moon_ok = S_ice("Moon", 0.95, 1.0, 0.95, 1.0)
    assert math.isclose(float(s_moon_ok), 1.0, abs_tol=1e-12)
