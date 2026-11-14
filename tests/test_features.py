"""Pruebas unitarias para pipeline/features.py (T2)."""

from __future__ import annotations

import math

import numpy as np
import pytest

from pipeline.config import FEATURE_NAMES
from pipeline.features import compute_features


def test_inclined_plane_10_deg() -> None:
    """Plano inclinado 10°: pendiente ≈ 10°, residuo ≈ 0 y TRI de Riley exacto."""
    res_m = 500.0
    n = 64
    x = np.arange(n, dtype=np.float64) * res_m
    z = (x[None, :] * math.tan(math.radians(10.0))).repeat(n, axis=0).astype(np.float32)

    feats = compute_features(z, res_m=res_m)

    assert list(feats.keys()) == FEATURE_NAMES
    assert abs(float(feats["mean_slope_deg"]) - 10.0) <= 0.1
    assert abs(float(feats["p90_slope_deg"]) - 10.0) <= 0.1
    assert abs(float(feats["detrended_std_m"])) < 1e-3

    expected_tri = math.sqrt(6.0) * res_m * math.tan(math.radians(10.0))
    assert abs(float(feats["tri_m"]) - expected_tri) < 1e-2


def test_horizontal_plane() -> None:
    """Plano horizontal: pendientes y rugosidad ≈ 0, integral hipsométrica = 0.5."""
    z = np.full((64, 64), 1200.0, dtype=np.float32)
    feats = compute_features(z, res_m=500.0)

    assert float(feats["mean_slope_deg"]) == pytest.approx(0.0, abs=1e-6)
    assert float(feats["p90_slope_deg"]) == pytest.approx(0.0, abs=1e-6)
    assert float(feats["relief_m"]) == pytest.approx(0.0, abs=1e-6)
    assert float(feats["detrended_std_m"]) == pytest.approx(0.0, abs=1e-6)
    assert float(feats["tri_m"]) == pytest.approx(0.0, abs=1e-6)
    assert float(feats["hypsometric_integral"]) == pytest.approx(0.5, abs=1e-6)
    assert float(feats["mean_elev_m"]) == pytest.approx(1200.0, abs=1e-4)


def test_synthetic_cone_hypsometric_integral() -> None:
    """Cono sintético inscrito: integral hipsométrica ≈ 1/3 (±0.05)."""
    res_m = 500.0
    n = 64
    coords = (np.arange(n, dtype=np.float64) - (n - 1) / 2.0) * res_m
    xx, yy = np.meshgrid(coords, coords)
    r = np.hypot(xx, yy)

    # Radio igual a la mitad del lado del parche -> en un círculo inscrito la integral es ~1/3,
    # con ajuste por las esquinas cuadradas usando r_base = half_size * (2 / sqrt(pi)).
    half_size = (n - 1) * 0.5 * res_m
    r_base = half_size * (2.0 / math.sqrt(math.pi))
    z = np.maximum(0.0, 1000.0 * (1.0 - r / r_base)).astype(np.float32)

    feats = compute_features(z, res_m=res_m)

    assert abs(float(feats["hypsometric_integral"]) - (1.0 / 3.0)) <= 0.05


def test_nan_filling_and_dtypes() -> None:
    """Los NaN restantes se rellenan con la mediana y todas las salidas son float32."""
    n = 64
    res_m = 500.0
    x = np.arange(n, dtype=np.float64) * res_m
    z = (x[None, :] * 0.05).repeat(n, axis=0).astype(np.float32)
    z[0, 0] = np.nan
    z[31, 31] = np.nan
    z[63, 63] = np.nan

    feats = compute_features(z, res_m=res_m)

    expected_filled = np.where(np.isfinite(z), z, np.nanmedian(z))
    assert float(feats["mean_elev_m"]) == pytest.approx(float(np.mean(expected_filled)), rel=1e-5)

    assert len(feats) == 7
    for name in FEATURE_NAMES:
        assert name in feats
        assert isinstance(feats[name], np.float32)
        assert np.isfinite(feats[name])
