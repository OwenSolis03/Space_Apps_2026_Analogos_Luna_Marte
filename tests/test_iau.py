"""Unit tests for pipeline/iau.py (T4 IAU planetary nomenclature and geodetic lookups)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from pipeline.config import BODY_RADII_M
from pipeline.iau import find_feature, haversine_km, iau_label, load_gazetteer


def test_load_gazetteer_normalizes_lon_and_https(tmp_path: Path, monkeypatch) -> None:
    """Converts longitudes [0, 360] to [-180, 180] and normalizes links http -> https."""
    raw_dir = tmp_path / "data" / "raw"
    shp_path = raw_dir / "nomenclature" / "MOON_nomenclature_center_pts.shp"
    shp_path.parent.mkdir(parents=True)
    shp_path.write_text("placeholder", encoding="utf-8")

    fake_gdf = pd.DataFrame(
        [
            {
                "name": "Haworth",
                "clean_name": "Haworth",
                "type": "Crater, craters",
                "diameter": 51.42,
                "center_lat": -87.45,
                "center_lon": 354.83,
                "link": "http://planetarynames.wr.usgs.gov/Feature/14502",
            },
            {
                "name": "",
                "clean_name": "",
                "type": "Crater",
                "diameter": 10.0,
                "center_lat": 0.0,
                "center_lon": 0.0,
                "link": None,
            },
        ]
    )
    monkeypatch.setattr("pipeline.iau.gpd.read_file", lambda p: fake_gdf)

    gaz = load_gazetteer("Moon", raw_dir)
    assert len(gaz) == 1
    assert abs(float(gaz.iloc[0]["lon"]) - (-5.17)) < 1e-6
    assert gaz.iloc[0]["link"] == "https://planetarynames.wr.usgs.gov/Feature/14502"


def test_haversine_moon_one_degree_equator() -> None:
    """Haversine distance between (0, 0) and (0, 1°) on the Moon is ~30.32 km (±0.01)."""
    r_moon_km = BODY_RADII_M["Moon"] / 1000.0
    d = float(haversine_km(0.0, 0.0, 0.0, 1.0, r_moon_km))
    assert abs(d - 30.32) <= 0.01


def test_iau_label_near_and_far_and_find_feature() -> None:
    """Verifies direct feature label at 10 km, regional fallback at 200 km, and find_feature lookup."""
    r_moon_km = BODY_RADII_M["Moon"] / 1000.0
    gaz = pd.DataFrame(
        [
            {
                "name": "Tiny Crater",
                "type": "Crater",
                "diameter_km": 5.0,
                "lat": 0.0,
                "lon": 0.0,
                "link": "https://planetarynames.wr.usgs.gov/Feature/1",
            },
            {
                "name": "Giant Basin",
                "type": "Mare",
                "diameter_km": 120.0,
                "lat": 0.0,
                "lon": 10.0,
                "link": "https://planetarynames.wr.usgs.gov/Feature/2",
            },
        ]
    )

    # ~10 km east of (0, 0) -> ~0.33° longitude on the Moon
    near_res = iau_label(0.0, 0.33, gaz, radius_km=r_moon_km)
    assert near_res["nearest_feature"] == "Tiny Crater"
    assert near_res["display_label"] == "Tiny Crater (Crater)"
    assert near_res["link"] == "https://planetarynames.wr.usgs.gov/Feature/1"
    assert abs(float(near_res["distance_km"]) - 10.0) < 0.5

    # ~200 km west of (0, 0) -> ~-6.6° longitude (distant from Tiny Crater and Giant Basin)
    far_res = iau_label(0.0, -6.6, gaz, radius_km=r_moon_km)
    assert far_res["display_label"] == "Near Giant Basin (Mare)"
    assert far_res["regional_landmark"] == "Giant Basin"
    assert far_res["link"] == "https://planetarynames.wr.usgs.gov/Feature/2"
    assert float(far_res["distance_km"]) > 190.0

    row = find_feature(gaz, "giant basin")
    assert row["name"] == "Giant Basin"
    with pytest.raises(KeyError):
        find_feature(gaz, "NoExiste")
