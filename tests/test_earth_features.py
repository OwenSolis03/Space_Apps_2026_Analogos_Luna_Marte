"""Pruebas unitarias sintéticas de T5 (Copernicus GLO-90 VRT, prefiltro y merge)."""

from __future__ import annotations

from pathlib import Path
import shutil

import numpy as np
import pandas as pd
import pytest
import rasterio
from rasterio.transform import from_origin

from pipeline.config import FEATURE_NAMES
from pipeline.earth_features import (
    CANDIDATE_COLUMNS,
    EARTH_COLUMNS,
    EARTH_FEATURE_COLUMNS,
    _compute_prefilter_masks,
    build_vrt,
    has_tile,
    merge_earth,
    parse_tile_cell,
    prefilter,
)
from pipeline.earth_layers import EARTH_ENV_COLUMNS, EarthLayers
from pipeline.geo import extract_patch

HAS_GDALBUILDVRT = shutil.which("gdalbuildvrt") is not None


def _write_synthetic_dem(
    path: Path,
    lon_min: float,
    lat_max: float,
    width: int,
    height: int,
    data: np.ndarray,
) -> None:
    res_x = 1.0 / width
    res_y = 1.0 / height
    profile = {
        "driver": "GTiff",
        "height": height,
        "width": width,
        "count": 1,
        "dtype": "float32",
        "crs": "EPSG:4326",
        "transform": from_origin(lon_min, lat_max, res_x, res_y),
    }
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(data.astype(np.float32), 1)


def test_parse_tile_cell() -> None:
    assert parse_tile_cell("S78_00_E162") == (-78, 162)
    assert parse_tile_cell("Copernicus_DSM_COG_30_S78_00_E162_00_DEM.tif") == (-78, 162)
    assert parse_tile_cell("N00_00_W001") == (0, -1)
    assert parse_tile_cell("N89_00_E179") == (89, 179)
    with pytest.raises(ValueError):
        parse_tile_cell("invalid_tile_name.tif")


def test_has_tile_negative_floor() -> None:
    cells = {(-1, -1)}
    got = has_tile(np.array([-0.5, 0.5]), np.array([-0.5, -0.5]), cells)
    assert got.tolist() == [True, False]


@pytest.mark.skipif(not HAS_GDALBUILDVRT, reason="gdalbuildvrt no está en PATH")
def test_build_vrt_masks_sea(tmp_path: Path) -> None:
    cop_dir = tmp_path / "cop"
    cop_dir.mkdir()

    yy, xx = np.mgrid[0:1200, 0:1200].astype(np.float32)
    land = 100.0 + 0.05 * xx + 0.05 * yy
    mixed = 200.0 + 0.05 * xx + 0.05 * yy
    mixed[:, :600] = 0.0  # mitad oeste es mar (= 0.0 sin nodata)

    _write_synthetic_dem(
        cop_dir / "Copernicus_DSM_COG_30_N10_00_E010_00_DEM.tif", 10.0, 11.0, 1200, 1200, land
    )
    _write_synthetic_dem(
        cop_dir / "Copernicus_DSM_COG_30_N10_00_E011_00_DEM.tif", 11.0, 11.0, 1200, 1200, mixed
    )

    vrt_path = tmp_path / "derived" / "copernicus_90m.vrt"
    build_vrt(cop_dir, vrt_path)

    with rasterio.open(vrt_path) as src:
        assert src.nodata == -9999.0
        sea_val = next(src.sample([(11.2, 10.5)]))[0]
        assert sea_val == -9999.0
        assert extract_patch(src, 10.5, 11.2, body="Earth") is None
        patch = extract_patch(src, 10.5, 10.5, body="Earth")
        assert patch is not None
        assert patch.shape == (64, 64)
        assert np.isfinite(patch).all()


@pytest.mark.skipif(not HAS_GDALBUILDVRT, reason="gdalbuildvrt no está en PATH")
def test_build_vrt_mixed_widths(tmp_path: Path) -> None:
    cop_dir = tmp_path / "cop_arctic"
    cop_dir.mkdir()

    south_tile = np.full((1200, 1200), 500.0, dtype=np.float32)
    north_tile = np.full((1200, 400), 600.0, dtype=np.float32)

    _write_synthetic_dem(
        cop_dir / "Copernicus_DSM_COG_30_N69_00_E020_00_DEM.tif", 20.0, 70.0, 1200, 1200, south_tile
    )
    _write_synthetic_dem(
        cop_dir / "Copernicus_DSM_COG_30_N70_00_E020_00_DEM.tif", 20.0, 71.0, 400, 1200, north_tile
    )

    vrt_path = tmp_path / "mixed.vrt"
    build_vrt(cop_dir, vrt_path)
    with rasterio.open(vrt_path) as src:
        patch = extract_patch(src, 70.0, 20.5, body="Earth")
        assert patch is not None
        assert patch.shape == (64, 64)
        assert np.isfinite(patch).all()


def test_build_vrt_does_not_overwrite(tmp_path: Path) -> None:
    vrt_path = tmp_path / "existing.vrt"
    vrt_path.write_text("<VRTDataset/>", encoding="utf-8")
    mtime_before = vrt_path.stat().st_mtime_ns
    out = build_vrt(tmp_path / "nonexistent_dir", vrt_path)
    assert out == vrt_path
    assert vrt_path.stat().st_mtime_ns == mtime_before


def test_prefilter_counts() -> None:
    ndvi = np.full((180, 360), np.nan, dtype=np.float32)
    lst_day = np.full((180, 360), np.nan, dtype=np.float32)
    lst_night = np.full((180, 360), np.nan, dtype=np.float32)

    # Fila para lat 10.5 (1°/celda): row = floor(90 - 10.5) = 79
    # Cols: 180 + lon -> lon 0.5=180, 5.5=185, 10.5=190, 15.5=195, 20.5=200
    ndvi[79, 185] = 0.4  # vegetado
    ndvi[79, 190] = 0.2  # árido válido
    lst_day[79, 195] = -15.0  # NDVI NaN pero LST finito (hielo/Antártida)
    # 79, 200 queda con NDVI NaN y LST NaN (mar)

    layers = EarthLayers.from_arrays(ndvi_max=ndvi, lst_day_c=lst_day, lst_night_c=lst_night)
    lat = np.array([10.5, 10.5, 10.5, 10.5, 10.5], dtype=np.float64)
    lon = np.array([0.5, 5.5, 10.5, 15.5, 20.5], dtype=np.float64)
    cells = {(10, 5), (10, 10), (10, 15), (10, 20)}

    mask, counts = prefilter(lat, lon, cells, layers)
    _, ndvi_missing_mask, _, _ = _compute_prefilter_masks(lat, lon, cells, layers)

    assert mask.tolist() == [False, False, True, True, False]
    assert ndvi_missing_mask.tolist() == [False, False, False, True, False]
    assert counts == {
        "grid": 5,
        "no_tile": 1,
        "vegetated": 1,
        "no_land_data": 1,
        "ndvi_missing": 1,
        "kept": 2,
    }


def test_merge_join(tmp_path: Path) -> None:
    cand_rows = []
    for i in range(5):
        cand_rows.append(
            {
                "lat": 20.0 + i,
                "lon": -110.0 + i,
                "ndvi_max": np.float32(0.1 + 0.01 * i),
                "lst_day_c": np.float32(30.0 + i),
                "lst_night_c": np.float32(10.0 + i),
                "lst_amplitude_c": np.float32(20.0),
                "dist_road_km": np.float32(5.0 + i),
                "dist_airport_km": np.float32(25.0 + i),
                "nearest_airport_iata": "HMO" if i % 2 == 0 else None,
                "nearest_airport_name": f"Airport {i}",
                "country": "Mexico",
                "known_region": "utah-mdrs" if i == 0 else None,
                "classification": "KNOWN_ANALOG" if i == 0 else "NEW_CANDIDATE",
                "ndvi_missing": False,
            }
        )
    cand_df = pd.DataFrame(cand_rows)[CANDIDATE_COLUMNS]
    for col in EARTH_ENV_COLUMNS:
        if cand_df[col].dtype == object:
            cand_df[col] = cand_df[col].astype("string")
    cand_df.to_parquet(tmp_path / "candidates.parquet", index=False)

    def _feat_row(idx: int) -> dict[str, object]:
        row: dict[str, object] = {"lat": float(20.0 + idx), "lon": float(-110.0 + idx)}
        for j, name in enumerate(FEATURE_NAMES):
            row[name] = np.float32(idx + j)
        row["valid_frac"] = np.float32(1.0)
        return row

    s0 = pd.DataFrame([_feat_row(0), _feat_row(2)])[EARTH_FEATURE_COLUMNS]
    s1 = pd.DataFrame([_feat_row(4)])[EARTH_FEATURE_COLUMNS]
    p0 = tmp_path / "features_earth_0.parquet"
    p1 = tmp_path / "features_earth_1.parquet"
    s0.to_parquet(p0, index=False)
    s1.to_parquet(p1, index=False)

    merged_path = merge_earth(tmp_path, num_stripes=2)
    merged = pd.read_parquet(merged_path)
    assert len(merged) == 3
    assert list(merged.columns) == EARTH_COLUMNS
    assert (merged["body"] == "Earth").all()
    assert list(merged["known_region"].astype(object).where(merged["known_region"].notna(), None)) == [
        "utah-mdrs",
        None,
        None,
    ]

    p1.unlink()
    with pytest.raises(FileNotFoundError):
        merge_earth(tmp_path, num_stripes=2, allow_missing=False)

    partial_path = merge_earth(tmp_path, num_stripes=2, allow_missing=True)
    partial = pd.read_parquet(partial_path)
    assert len(partial) == 2
