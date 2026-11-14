"""Synthetic unit tests for T14 geology rules, GLiM lookup, and similarity matrix."""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd

from pipeline.geology import glim_at, load_glim, sample_earth_geology
from pipeline.geology_rules import (
    GEO_CLASSES,
    GEO_SIMILARITY,
    classify_unit,
    classify_unit_table,
    geology_similarity,
)


def test_glim_at_corners_and_coast_fallback(tmp_path: Path) -> None:
    """Verify glim_at corner cells, 3x3 coast fallback from wb/nd/-9999, and load_glim."""
    # 6x6 global grid: each row = 30 deg lat, each col = 60 deg lon.
    # Disjoint 3x3 neighborhoods: [0..2, 0..2] around (1, 1) and [4..5, 0..1] around (5, 0).
    grid = np.full((6, 6), 11, dtype=np.int16)  # 11 = wb (water bodies)
    grid[0, 0] = 16  # top-left corner: ig (ice and glaciers)
    grid[5, 5] = 3   # bottom-right corner: ss (siliciclastic sedimentary)

    # Center cell (1, 1) at (lat=45.0, lon=-90.0) is wb, surrounded by 3 vb (2) and 1 su (1).
    grid[0, 1] = 2
    grid[1, 0] = 2
    grid[2, 1] = 2
    grid[2, 2] = 1

    # Isolated cell (5, 0) at (lat=-75.0, lon=-150.0) surrounded only by wb/nd/-9999 -> None.
    grid[5, 0] = -9999
    grid[4, 0] = 15  # nd

    codes = glim_at(
        grid,
        lat=np.array([89.9, -89.9, 45.0, -75.0]),
        lon=np.array([-179.9, 179.9, -90.0, -150.0]),
    )
    assert codes.tolist() == ["ig", "ss", "vb", None]

    # All-wb grid must return None everywhere.
    all_wb = np.full((6, 6), 11, dtype=np.int16)
    res_wb = glim_at(all_wb, lat=np.array([0.0, 45.0]), lon=np.array([0.0, -90.0]))
    assert res_wb.tolist() == [None, None]

    # Verify ESRI ASCII load_glim (6 header lines) + sample_earth_geology labels.
    asc_path = tmp_path / "glim_tiny.asc"
    header = (
        "ncols 6\n"
        "nrows 6\n"
        "xllcorner -180\n"
        "yllcorner -90\n"
        "cellsize 30\n"
        "NODATA_value -9999\n"
    )
    body = "\n".join(" ".join(str(int(v)) for v in row) for row in grid) + "\n"
    asc_path.write_text(header + body, encoding="utf-8")

    loaded = load_glim(asc_path)
    assert loaded.shape == (6, 6)
    assert loaded.dtype == np.int16
    assert np.array_equal(loaded, grid)

    df = sample_earth_geology(
        pd.DataFrame({"lat": [89.9, 45.0, -75.0], "lon": [-179.9, -90.0, -150.0]}),
        loaded,
    )
    assert df["geo_class"].iloc[0] == "ICE"
    assert bool(df["ice_surface"].iloc[0]) is True
    assert bool(df["lava_tube_terrain"].iloc[0]) is False
    assert df["geo_class"].iloc[1] == "VOLCANIC_BASIC"
    assert bool(df["lava_tube_terrain"].iloc[1]) is True
    assert pd.isna(df["geo_class"].iloc[2])


def test_geo_similarity_symmetry_diagonal_and_pairs() -> None:
    """Verify GEO_SIMILARITY contains all 8 classes, is symmetric, 1 on diagonal, exact off-diagonals."""
    assert list(GEO_SIMILARITY.keys()) == list(GEO_CLASSES)

    expected_pairs = {
        ("VOLCANIC_BASIC", "PYROCLASTIC"): 0.6,
        ("VOLCANIC_BASIC", "VOLCANIC_OTHER"): 0.5,
        ("VOLCANIC_OTHER", "PYROCLASTIC"): 0.5,
        ("CRYSTALLINE", "IMPACT"): 0.4,
        ("SEDIMENTARY", "EVAPORITE"): 0.6,
        ("SEDIMENTARY", "IMPACT"): 0.2,
    }

    for c1 in GEO_CLASSES:
        assert GEO_SIMILARITY[c1][c1] == 1.0
        assert GEO_SIMILARITY[(c1, c1)] == 1.0
        for c2 in GEO_CLASSES:
            v12 = GEO_SIMILARITY[c1][c2]
            v21 = GEO_SIMILARITY[c2][c1]
            assert v12 == v21
            if c1 == c2:
                assert v12 == 1.0
            else:
                expected = expected_pairs.get((c1, c2), expected_pairs.get((c2, c1), 0.0))
                assert v12 == expected
                assert geology_similarity(c1, c2) == expected

    assert np.isnan(geology_similarity(None, "VOLCANIC_BASIC"))


def test_keyword_rules_moon_mars_and_default_logging(caplog) -> None:
    """Verify Moon & Mars keyword rules, word boundaries ('edifice' != 'ice'), and default logs."""
    caplog.set_level(logging.WARNING)

    moon_units = pd.DataFrame(
        [
            {"unit": "Im", "description": "Mare basalt plains"},
            {"unit": "Idm", "description": "Dark mantle pyroclastic glass"},
            {"unit": "Ic", "description": "Crater ejecta material"},
            {"unit": "Ntp", "description": "Light plains and terra"},
            {"unit": "Xunk", "description": "Unclassified smooth mystery terrain"},
        ]
    )
    moon_out = classify_unit_table(moon_units, body="Moon")
    assert moon_out["geo_class"].tolist() == [
        "VOLCANIC_BASIC",
        "PYROCLASTIC",
        "IMPACT",
        "CRYSTALLINE",
        "CRYSTALLINE",
    ]
    assert moon_out["rule_matched"].iloc[-1] == "default"
    assert any("default rule" in rec.message for rec in caplog.records)

    caplog.clear()
    mars_units = pd.DataFrame(
        [
            {"unit": "Apu", "description": "Polar layered deposits"},
            {"unit": "Ave", "description": "Amazonian volcanic edifice on Tharsis"},
            {"unit": "HNh", "description": "Noachian heavily battered highland"},
            {"unit": "lHl", "description": "Vastitas Borealis lowland sedimentary plain"},
            {"unit": "Zzz", "description": "Mysterious feature X"},
        ]
    )
    mars_out = classify_unit_table(mars_units, body="Mars")
    assert mars_out["geo_class"].iloc[0] == "ICE"
    assert mars_out["geo_class"].iloc[1] == "VOLCANIC_BASIC"
    assert mars_out["geo_class"].iloc[2] == "IMPACT"
    assert mars_out["geo_class"].iloc[3] == "SEDIMENTARY"
    assert pd.isna(mars_out["geo_class"].iloc[4])
    assert mars_out["rule_matched"].iloc[4] == "default"
    assert any("default rule" in rec.message for rec in caplog.records)

    # Standalone classify_unit helper check
    c_mare, _ = classify_unit("Moon", "Mare basalt")
    c_ice, _ = classify_unit("Mars", "Polar layered deposits")
    assert c_mare == "VOLCANIC_BASIC"
    assert c_ice == "ICE"
