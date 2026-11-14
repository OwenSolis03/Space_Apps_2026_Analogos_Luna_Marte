"""Pruebas unitarias sintéticas de T6 (sin HDF4 ni pyhdf)."""

from __future__ import annotations

import sys

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import LineString, Point, box

from pipeline.earth_layers import (
    EARTH_ENV_COLUMNS,
    MODIS_GRID_SHAPE,
    NUMERIC_ENV_COLUMNS,
    TEXT_ENV_COLUMNS,
    Countries,
    EarthLayers,
    KnownRegions,
    Logistics,
    cell_index,
    finalize_mean,
    lst_c_from_raw,
    ndvi_from_raw,
    patch_window_stat,
    running_nanmax,
    running_sum_count,
)


def test_ndvi_from_raw() -> None:
    raw = np.array([-3000, -2500, -2000, 0, 2500, 10000, 12000], dtype=np.int16)
    got = ndvi_from_raw(raw)
    assert got.dtype == np.float32
    assert np.isnan(got[0])
    assert np.isnan(got[1])
    np.testing.assert_allclose(got[2:6], [-0.2, 0.0, 0.25, 1.0], atol=1e-6)
    assert np.isnan(got[6])


def test_lst_c_from_raw() -> None:
    raw = np.array([0, 7499, 14658, 65535], dtype=np.uint16)
    got = lst_c_from_raw(raw)
    assert got.dtype == np.float32
    assert np.isnan(got[0])
    assert np.isnan(got[1])
    assert abs(float(got[2]) - 20.01) <= 0.01
    assert np.isfinite(got[3])


def test_running_ops() -> None:
    m1 = np.array([[1.0, np.nan], [2.0, 5.0]], dtype=np.float32)
    m2 = np.array([[3.0, 4.0], [np.nan, 6.0]], dtype=np.float32)
    m3 = np.array([[2.0, np.nan], [np.nan, 7.0]], dtype=np.float32)

    acc = None
    s = None
    c = None
    for m in (m1, m2, m3):
        acc = running_nanmax(acc, m)
        s, c = running_sum_count(s, c, m)

    np.testing.assert_allclose(acc, [[3.0, 4.0], [2.0, 7.0]], atol=1e-6)
    assert c.tolist() == [[3, 1], [1, 3]]
    mean_arr = finalize_mean(s, c, min_count=3)
    assert abs(float(mean_arr[0, 0]) - 2.0) < 1e-6
    assert abs(float(mean_arr[1, 1]) - 6.0) < 1e-6
    assert np.isnan(mean_arr[0, 1])
    assert np.isnan(mean_arr[1, 0])

    # Exactamente 2 meses válidos con min_count=3 -> NaN
    s2, c2 = running_sum_count(None, None, np.array([[10.0]], dtype=np.float32))
    s2, c2 = running_sum_count(s2, c2, np.array([[20.0]], dtype=np.float32))
    s2, c2 = running_sum_count(s2, c2, np.array([[np.nan]], dtype=np.float32))
    assert np.isnan(finalize_mean(s2, c2, min_count=3)[0, 0])


def test_cell_index_edges() -> None:
    assert cell_index(90.0, -180.0) == (0, 0)
    assert cell_index(-90.0, 180.0) == (3599, 0)
    assert cell_index(0.0, 0.0) == (1800, 3600)


def test_patch_window_stat_antimeridian() -> None:
    grid = np.full(MODIS_GRID_SHAPE, np.nan, dtype=np.float32)
    grid[:, 0] = 1.0
    grid[:, 7199] = 0.0
    val = patch_window_stat(grid, np.array([0.0]), np.array([179.99]), half_km=16.0, stat="max")
    assert val[0] == 1.0


def test_patch_window_stat_lat() -> None:
    grid = np.broadcast_to(np.arange(7200, dtype=np.float32), MODIS_GRID_SHAPE)
    center_col = 3600
    lon_center = 0.025
    max_eq = float(patch_window_stat(grid, 0.0, lon_center, half_km=16.0, stat="max")[0])
    max_60 = float(patch_window_stat(grid, 60.0, lon_center, half_km=16.0, stat="max")[0])
    cols_eq = 2 * (max_eq - center_col) + 1
    cols_60 = 2 * (max_60 - center_col) + 1
    assert abs(cols_60 - 2.0 * cols_eq) <= 1.0


def test_logistics_densify() -> None:
    roads = gpd.GeoDataFrame(
        {"featurecla": ["Road", "Ferry"]},
        geometry=[
            LineString([(0.0, 0.0), (10.0, 0.0)]),
            LineString([(4.5, 0.5), (5.5, 0.5)]),
        ],
        crs="EPSG:4326",
    )
    airports = gpd.GeoDataFrame(
        {"type": ["mid"], "iata_code": ["TST"], "name": ["Test Field"]},
        geometry=[Point(0.0, 0.0)],
        crs="EPSG:4326",
    )
    log = Logistics(roads, airports)
    dist = float(log.dist_road_km(0.5, 5.0)[0])
    assert abs(dist - 55.6) <= 1.5


def test_airports_exclude_military() -> None:
    roads = gpd.GeoDataFrame(
        {"featurecla": ["Road"]},
        geometry=[LineString([(0.0, 0.0), (1.0, 0.0)])],
        crs="EPSG:4326",
    )
    airports = gpd.GeoDataFrame(
        {
            "type": ["military", "mid"],
            "iata_code": ["MIL", "-"],
            "name": ["Mil Base", "Civil Mid"],
        },
        geometry=[Point(0.01, 0.0), Point(0.45, 0.0)],
        crs="EPSG:4326",
    )
    log = Logistics(roads, airports)
    dist, iata, name = log.nearest_airport(0.0, 0.0)
    assert 45.0 <= float(dist[0]) <= 55.0
    assert name[0] == "Civil Mid"
    assert iata[0] is None


def test_countries_lookup() -> None:
    gdf = gpd.GeoDataFrame(
        {"ADMIN": ["Testland"]},
        geometry=[box(0.0, 0.0, 1.0, 1.0)],
        crs="EPSG:4326",
    )
    countries = Countries(gdf)
    res = countries.lookup([0.5, 0.5, 0.5], [0.5, 1.1, 3.0], max_coast_km=25.0)
    assert res[0] == "Testland"
    assert res[1] == "Testland"
    assert res[2] is None


def test_known_regions_real_file() -> None:
    kr = KnownRegions()
    assert len(kr.regions) == 12
    assert len({r["id"] for r in kr.regions}) == 12
    res = kr.lookup([38.4064, 29.07], [-110.7919, -110.96])
    assert res[0] == "utah-mdrs"
    assert res[1] is None


def test_sample_schema() -> None:
    assert "pyhdf" not in sys.modules
    ndvi = np.full((180, 360), 0.1, dtype=np.float32)
    lst_day = np.full((180, 360), 30.0, dtype=np.float32)
    lst_night = np.full((180, 360), 10.0, dtype=np.float32)

    roads = gpd.GeoDataFrame(
        {"featurecla": ["Road"]},
        geometry=[LineString([(-112.0, 38.0), (-110.0, 38.0)])],
        crs="EPSG:4326",
    )
    airports = gpd.GeoDataFrame(
        {"type": ["mid"], "iata_code": ["SLC"], "name": ["Salt Lake"]},
        geometry=[Point(-111.9, 40.7)],
        crs="EPSG:4326",
    )
    countries = Countries(
        gpd.GeoDataFrame(
            {"ADMIN": ["United States", "Mexico"]},
            geometry=[box(-125.0, 30.0, -100.0, 49.0), box(-115.0, 20.0, -100.0, 30.0)],
            crs="EPSG:4326",
        )
    )
    layers = EarthLayers.from_arrays(
        ndvi_max=ndvi,
        lst_day_c=lst_day,
        lst_night_c=lst_night,
        logistics=Logistics(roads, airports),
        countries=countries,
        known_regions=KnownRegions(),
    )
    df = layers.sample([38.4064, 29.07], [-110.7919, -110.96])
    assert list(df.columns) == EARTH_ENV_COLUMNS
    for col in NUMERIC_ENV_COLUMNS:
        assert df[col].dtype == np.float32
    for col in TEXT_ENV_COLUMNS:
        assert isinstance(df[col].dtype, pd.StringDtype)
    assert list(df["classification"]) == ["KNOWN_ANALOG", "NEW_CANDIDATE"]
    assert df["known_region"].iloc[0] == "utah-mdrs"
    assert pd.isna(df["known_region"].iloc[1])
