"""Unit tests for pipeline.minerals (T18 mineralogy context)."""

import math
import numpy as np
import pytest

from pipeline.minerals import (
    Grid,
    KAGUYA,
    TES,
    EMIT,
    sample_source,
    summarize_moon,
    summarize_mars,
    summarize_earth,
    enrich_universe,
)


def test_grid_index_and_bounds():
    """Verify Grid indexing and boundary conditions."""
    data = np.arange(12, dtype=np.float64).reshape((3, 4))
    grid = Grid(data, west=0.0, east=360.0, north=90.0, south=-90.0)

    # Valid query
    idx = grid.index(lat=45.0, lon=45.0)
    assert idx is not None
    assert idx == (0, 0)

    # Equator center
    idx_eq = grid.index(lat=0.0, lon=180.0)
    assert idx_eq is not None
    assert idx_eq == (1, 2)

    # Out of latitude bounds
    assert grid.index(lat=95.0, lon=0.0) is None
    assert grid.index(lat=-95.0, lon=0.0) is None


def test_grid_window_median():
    """Verify window median calculation and nodata handling."""
    data = np.full((10, 10), 15.0, dtype=np.float64)
    data[5, 5] = 999.0  # outlier
    grid = Grid(data, west=0.0, east=100.0, north=50.0, south=-50.0)

    # With range filter excluding 999
    val = grid.window_median(lat=0.0, lon=50.0, radius=1, lo=0.0, hi=50.0)
    assert val == 15.0

    # With empty valid range returns NaN
    val_nan = grid.window_median(lat=0.0, lon=50.0, radius=1, lo=500.0, hi=600.0)
    assert math.isnan(val_nan)


def test_summarize_moon():
    """Verify lunar mineralogy plain-language summaries."""
    # Mare-like basalt (high FeO)
    mare = {
        "feo": 16.5,
        "olivine": 10.0,
        "clinopyroxene": 45.0,
        "orthopyroxene": 15.0,
        "plagioclase": 30.0,
    }
    s_mare = summarize_moon(mare)
    assert "iron-rich, mare-like basalt" in s_mare
    assert "clinopyroxene (high-ca) (45%)" in s_mare

    # Highland rock (low FeO)
    highland = {
        "feo": 4.2,
        "olivine": 5.0,
        "clinopyroxene": 10.0,
        "orthopyroxene": 10.0,
        "plagioclase": 75.0,
    }
    s_highland = summarize_moon(highland)
    assert "iron-poor, highland-like rock" in s_highland
    assert "plagioclase (75%)" in s_highland


def test_summarize_mars():
    """Verify Martian mineralogy plain-language summaries."""
    vals = {
        "olivine": 12.0,
        "orthopyroxene": 8.0,
        "clinopyroxene": 25.0,
        "plagioclase": 55.0,
        "hematite": 7.0,
    }
    s_mars = summarize_mars(vals)
    assert "plagioclase (55%)" in s_mars
    assert "hematite present (7%)" in s_mars


def test_summarize_earth():
    """Verify Earth EMIT mineralogy plain-language summaries."""
    vals = {
        "calcite": 12.5,
        "goethite": 3.2,
        "hematite": 4.1,
        "kaolinite": 0.2,  # below 0.5% threshold
    }
    s_earth = summarize_earth(vals)
    assert "Mostly calcite (12.5%)" in s_earth
    assert "hematite (4.1%)" in s_earth
    assert "goethite (3.2%)" in s_earth
    assert "kaolinite" not in s_earth


def test_sample_source_coverage():
    """Verify coverage boundaries in sample_source."""
    data = np.full((10, 10), 10.0, dtype=np.float64)
    grid = Grid(data, west=-180.0, east=180.0, north=50.0, south=-50.0)
    grids = {v.key: grid for v in KAGUYA.vars}

    # Within Kaguya 50N-50S coverage
    res_ok = sample_source(KAGUYA, grids, lat=0.0, lon=0.0)
    assert res_ok["status"] == "ok"
    assert "values" in res_ok

    # Outside Kaguya coverage (polar latitude)
    res_out = sample_source(KAGUYA, grids, lat=80.0, lon=0.0)
    assert res_out["status"] == "outside_coverage"
    assert "note" in res_out


def test_enrich_universe_synthetic():
    """Verify universe enrichment preserves scores and metadata."""
    sample_universe = {
        "metadata": {"dimensions": []},
        "targets": [
            {
                "id": "t1",
                "name": "Target Alpha",
                "body": "Mars",
                "lat": 10.0,
                "lon": 20.0,
                "analogs": [
                    {
                        "id": "a1",
                        "lat": 25.0,
                        "lon": 45.0,
                        "sub_scores": {"topography": 0.85},
                    }
                ],
            }
        ],
    }

    # Enrich with synthetic TES grid (fractions 0.0 - 1.0)
    data = np.full((20, 20), 0.15, dtype=np.float64)
    grid = Grid(data, west=0.0, east=360.0, north=90.0, south=-90.0)
    tes_grids = {v.key: grid for v in TES.vars}

    out, counts = enrich_universe(sample_universe, tes=tes_grids)
    assert "mineralogy" in out["targets"][0]
    assert out["targets"][0]["mineralogy"]["status"] == "ok"
    assert out["targets"][0]["analogs"][0]["sub_scores"]["topography"] == 0.85
    assert counts["tes_bandfield2002"]["ok"] == 1
