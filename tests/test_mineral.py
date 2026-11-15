"""Unit tests for pipeline.mineral (Option B scored Mars mineral dimension)."""

import math
import numpy as np
import pandas as pd
import pytest

from pipeline.mineral import (
    MINERAL_RANK_SIGMA,
    MISMATCH_RANK,
    S_mineral,
    ferric_box_mean,
)
from pipeline.match import (
    PRESETS,
    PRESET_KEYS,
    EarthArrays,
    TargetVec,
    available_dims,
    build_earth_arrays,
    layer_mismatches,
    mineral_scores,
    msi,
    preset_status,
)


def test_s_mineral_basic():
    """Verify S_mineral RBF properties and NaN handling."""
    # Equal ranks -> 1.0
    assert pytest.approx(1.0, 1e-6) == S_mineral(0.5, 0.5)

    # Difference of 1 sigma (0.15) -> exp(-0.5) ~ 0.60653
    expected_1sigma = math.exp(-0.5)
    assert pytest.approx(expected_1sigma, 1e-4) == S_mineral(0.65, 0.50)
    assert pytest.approx(expected_1sigma, 1e-4) == S_mineral(0.35, 0.50)

    # NaN on either side -> NaN
    assert math.isnan(S_mineral(np.nan, 0.5))
    assert math.isnan(S_mineral(0.5, np.nan))
    assert math.isnan(S_mineral(np.nan, np.nan))


def test_ferric_box_mean_synthetic():
    """Verify ferric_box_mean on synthetic grid."""
    # Synthetic raster mock
    class MockRaster:
        def __init__(self, data, transform, nodata=-9999.0):
            self.data = data
            self.transform = transform
            self.nodata = nodata

        def read(self, band, window=None):
            if window is None:
                return self.data.copy()
            # Extract sub-window
            r0, r1 = int(window.row_off), int(window.row_off + window.height)
            c0, c1 = int(window.col_off), int(window.col_off + window.width)
            r0, r1 = max(0, r0), min(self.data.shape[0], r1)
            c0, c1 = max(0, c0), min(self.data.shape[1], c1)
            return self.data[r0:r1, c0:c1].copy()

    from affine import Affine

    # Constant field at 0.42 covering [-10, 10] lon, [0, 20] lat
    data = np.full((800, 800), 0.42, dtype=np.float32)
    # 40 px/deg -> dx = 1/40 = 0.025, west=-10.0, north=20.0
    transform = Affine(0.025, 0.0, -10.0, 0.0, -0.025, 20.0)
    raster = MockRaster(data, transform)

    # Normal box
    val = ferric_box_mean(raster, lat=10.0, lon=0.0)
    assert pytest.approx(0.42, 1e-4) == val

    # Polar latitude (|lat| > 88) -> NaN
    assert math.isnan(ferric_box_mean(raster, lat=89.0, lon=0.0))
    assert math.isnan(ferric_box_mean(raster, lat=-89.0, lon=0.0))

    # Antimeridian boundary crossing -> NaN
    assert math.isnan(ferric_box_mean(raster, lat=0.0, lon=180.0))
    assert math.isnan(ferric_box_mean(raster, lat=0.0, lon=-180.0))


def test_available_dims_mineral():
    """Verify mineral dimension availability across bodies and data presence."""
    # Mars with finite mineral_rank -> contains mineral
    tv_mars_ok = TargetVec(
        body="Mars",
        z_t=np.zeros(6),
        zt_t=30.0,
        lat=0.0,
        geo_class="VOLCANIC_BASIC",
        dust_level_rank=0.5,
        dust_season_rank=0.5,
        dust_phase=180.0,
        cold_rank=np.nan,
        ice_t=0.0,
        mineral_rank=0.75,
    )
    dims_mars = available_dims(tv_mars_ok)
    assert "mineral" in dims_mars

    # Mars with NaN mineral_rank -> does not contain mineral
    tv_mars_nan = TargetVec(
        body="Mars",
        z_t=np.zeros(6),
        zt_t=30.0,
        lat=0.0,
        geo_class="VOLCANIC_BASIC",
        dust_level_rank=0.5,
        dust_season_rank=0.5,
        dust_phase=180.0,
        cold_rank=np.nan,
        ice_t=0.0,
        mineral_rank=np.nan,
    )
    assert "mineral" not in available_dims(tv_mars_nan)

    # Moon -> never contains mineral (even if mineral_rank was finite)
    tv_moon = TargetVec(
        body="Moon",
        z_t=np.zeros(6),
        zt_t=np.nan,
        lat=-85.0,
        geo_class="IMPACT",
        dust_level_rank=np.nan,
        dust_season_rank=np.nan,
        dust_phase=np.nan,
        cold_rank=0.95,
        ice_t=1.0,
        mineral_rank=0.5,
    )
    assert "mineral" not in available_dims(tv_moon)


def test_case_c_earth_missing_mineral():
    """Verify Case C: Mars target with mineral, Earth patch missing mineral -> scored as 0.0."""
    exp_weights = PRESETS["geology_and_materials_mineral_exp"]["weights"]
    # Target has mineral active
    tdims = frozenset(["topography", "roughness", "environment", "geology", "mineral"])

    scores = {
        "topography": np.array([1.0, 1.0]),
        "roughness": np.array([1.0, 1.0]),
        "environment": np.array([1.0, 1.0]),
        "thermal": np.array([np.nan, np.nan]),
        "geology": np.array([1.0, 1.0]),
        "dust": np.array([np.nan, np.nan]),
        "ice": np.array([np.nan, np.nan]),
        "mineral": np.array([0.9, np.nan]),  # patch 1 has mineral, patch 2 missing
    }

    # Under T16, patch 2 counts 0.0 for mineral:
    # sum(w) = 0.2 + 0.1 + 0.1 + 0.4 + 0.2 = 1.0
    # patch 1: 0.2(1) + 0.1(1) + 0.1(1) + 0.4(1) + 0.2(0.9) = 0.8 + 0.18 = 0.98
    # patch 2: 0.2(1) + 0.1(1) + 0.1(1) + 0.4(1) + 0.2(0.0) = 0.80
    msi_res = msi(scores, exp_weights, target_dims=tdims)
    assert pytest.approx(0.98, 1e-3) == msi_res[0]
    assert pytest.approx(0.80, 1e-3) == msi_res[1]


def test_non_regression_existing_presets():
    """Verify that existing 5 presets have mineral weight 0.0 and identical scores."""
    existing_presets = [
        "mobility_and_traction",
        "construction_and_base",
        "geology_and_materials",
        "dust_and_seasons",
        "isru_and_ice",
    ]
    for pkey in existing_presets:
        assert PRESETS[pkey]["weights"]["mineral"] == 0.00


def test_preset_status_without_mineral_dir():
    """Verify preset status when mineral dimension is missing for Mars target."""
    exp_weights = PRESETS["geology_and_materials_mineral_exp"]["weights"]
    applies = PRESETS["geology_and_materials_mineral_exp"]["applies_to"]

    # When mineral layer is missing, available dims does NOT include mineral
    tdims_no_mineral = frozenset(["topography", "roughness", "environment", "geology"])
    status, cov, missing = preset_status(exp_weights, "Mars", applies, tdims_no_mineral)

    # Coverage should be (0.2+0.1+0.1+0.4)/1.0 = 0.8 >= MIN_PRESET_COVERAGE (0.6)
    assert status == "ok"
    assert pytest.approx(0.8, 1e-2) == cov
    assert missing == ["mineral"]


def test_layer_mismatches_mineral():
    """Verify layer_mismatches emits mineral_rank mismatch for Mars when |Δ| > 0.30."""
    # Mars with gap > 0.30 -> mismatch
    mm_mars = layer_mismatches(
        body="Mars",
        e_geo="VOLCANIC_BASIC",
        t_geo="VOLCANIC_BASIC",
        e_level=np.nan,
        t_level=np.nan,
        e_season=np.nan,
        t_season=np.nan,
        e_phase=np.nan,
        t_phase=np.nan,
        e_lat=0.0,
        t_lat=0.0,
        e_cold=np.nan,
        t_cold=np.nan,
        e_min=0.85,
        t_min=0.40,  # diff = 0.45 > 0.30
    )
    feats = [m["feature"] for m in mm_mars]
    assert "mineral_rank" in feats

    # Moon -> never emits mineral_rank mismatch
    mm_moon = layer_mismatches(
        body="Moon",
        e_geo="IMPACT",
        t_geo="IMPACT",
        e_level=np.nan,
        t_level=np.nan,
        e_season=np.nan,
        t_season=np.nan,
        e_phase=np.nan,
        t_phase=np.nan,
        e_lat=0.0,
        t_lat=0.0,
        e_cold=np.nan,
        t_cold=np.nan,
        e_min=0.85,
        t_min=0.40,
    )
    feats_moon = [m["feature"] for m in mm_moon]
    assert "mineral_rank" not in feats_moon
