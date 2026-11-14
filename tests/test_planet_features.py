"""Pruebas unitarias para pipeline/planet_features.py (T3)."""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from rasterio.transform import from_origin

from pipeline.config import BODY_RADII_M, FEATURE_NAMES
from pipeline.planet_features import (
    MARS_COLUMNS,
    MOON_COLUMNS,
    apply_limit,
    compute_lunar_wac_percentile,
    generate_grid,
    prepare_diviner_parquet,
    run_body_extraction,
    select_stripe,
)


def test_generate_grid_counts() -> None:
    """La grilla de 32 km produce ~141k puntos en Marte y ~37k en la Luna (±5 %)."""
    mars_pts = generate_grid("Mars")
    moon_pts = generate_grid("Moon")

    assert abs(len(mars_pts) - 141546) / 141546 <= 0.05
    assert abs(len(moon_pts) - 37041) / 37041 <= 0.05

    for pts in (mars_pts, moon_pts):
        lats = [p[0] for p in pts]
        lons = [p[1] for p in pts]
        assert min(lats) >= -88.0 and max(lats) <= 88.0
        assert min(lons) >= -180.0 and max(lons) <= 180.0


def test_select_stripe_and_limit_partition_all_points() -> None:
    """Las franjas particionan la grilla completa sin duplicados ni pérdidas."""
    pts = [(float(i), 0.0) for i in range(103)]
    seen: list[tuple[float, float]] = []
    for k in range(16):
        seen.extend(select_stripe(pts, stripe_idx=k, num_stripes=16))
    assert seen == pts

    limited = apply_limit(pts, limit=10)
    assert len(limited) == 10
    assert limited[0] == (0.0, 0.0)
    assert limited[-1][0] >= 80.0


def test_run_planet_features_synthetic(tmp_path: Path) -> None:
    """Corrida sintética de Moon con --limit escribe el parquet esperado y el PNG."""
    radius_m = BODY_RADII_M["Moon"]
    res_m = 500.0
    width, height = 300, 300
    x0, y0 = -75000.0, 75000.0
    crs_moon = f"+proj=eqc +lat_ts=0 +lat_0=0 +lon_0=0 +x_0=0 +y_0=0 +R={radius_m} +units=m +no_defs"
    transform = from_origin(x0, y0, res_m, res_m)

    raw_dir = tmp_path / "data" / "raw"
    moon_dir = raw_dir / "moon"
    moon_dir.mkdir(parents=True)

    xs = np.arange(width, dtype=np.float32) * res_m
    elev = (xs[None, :] * math.tan(math.radians(8.0))).repeat(height, axis=0).astype(np.float32)

    dem_path = moon_dir / "synthetic_moon_dem.tif"
    with rasterio.open(
        dem_path,
        "w",
        driver="GTiff",
        height=height,
        width=width,
        count=1,
        dtype="float32",
        crs=crs_moon,
        transform=transform,
        nodata=-9999.0,
    ) as dst:
        dst.write(elev, 1)

    wac_path = moon_dir / "synthetic_moon_wac.tif"
    wac = np.full((height, width), 0.18, dtype=np.float32)
    with rasterio.open(
        wac_path,
        "w",
        driver="GTiff",
        height=height,
        width=width,
        count=1,
        dtype="float32",
        crs=crs_moon,
        transform=transform,
        nodata=-9999.0,
    ) as dst:
        dst.write(wac, 1)

    out_dir = tmp_path / "runs" / "test_run"
    # Puntos cercanos al centro (lat=0, lon=0) caen dentro del raster sintético de 150x150 km.
    # Probamos directamente run_body_extraction usando limit grande sobre una franja o parcheando grid;
    # aquí usamos monkeypatch implícito vía submuestreo con un raster que cubre varios puntos del ecuador.
    # Como la grilla global con --limit 10 cubre puntos globales, verificamos también que al menos
    # el centro (0, 0) sea extraído si restringimos con un test específico de worker + parquet.
    stripe_path = run_body_extraction(
        body="Moon",
        raw_dir=raw_dir,
        out_dir=out_dir,
        stripe_idx=0,
        num_stripes=1,
        workers=1,
        limit=10,
        file_overrides={"dem": dem_path, "wac_reflectance": wac_path},
    )

    assert stripe_path.exists()
    assert (out_dir / "features_moon.parquet").exists()
    assert (out_dir / "map_moon_mean_slope_deg.png").exists()

    df = pd.read_parquet(out_dir / "features_moon.parquet")
    assert list(df.columns) == MOON_COLUMNS
    for feat in FEATURE_NAMES:
        assert feat in df.columns


def test_run_planet_features_valid_moon_and_mars_patches(tmp_path: Path, monkeypatch) -> None:
    """Extrae parches válidos reales sobre rasters sintéticos de Luna y Marte."""
    out_dir = tmp_path / "runs" / "valid_patches"
    raw_dir = tmp_path / "data" / "raw"
    (raw_dir / "moon").mkdir(parents=True)
    (raw_dir / "mars").mkdir(parents=True)

    # Luna: raster alrededor de (0°, 0°)
    r_moon = BODY_RADII_M["Moon"]
    crs_moon = f"+proj=eqc +lat_ts=0 +lat_0=0 +lon_0=0 +x_0=0 +y_0=0 +R={r_moon} +units=m +no_defs"
    moon_dem = raw_dir / "moon" / "dem.tif"
    moon_wac = raw_dir / "moon" / "wac.tif"
    arr = np.fromfunction(lambda r, c: c * 500.0 * math.tan(math.radians(10.0)), (140, 140)).astype(np.float32)
    for path, data in [(moon_dem, arr), (moon_wac, np.full((140, 140), 0.25, dtype=np.float32))]:
        with rasterio.open(
            path,
            "w",
            driver="GTiff",
            height=140,
            width=140,
            count=1,
            dtype="float32",
            crs=crs_moon,
            transform=from_origin(-35000.0, 35000.0, 500.0, 500.0),
            nodata=-9999.0,
        ) as dst:
            dst.write(data, 1)

    monkeypatch.setattr("pipeline.planet_features.generate_grid", lambda body, size_km=32.0: [(0.0, 0.0), (0.0, 0.2)])
    run_body_extraction(
        body="Moon",
        raw_dir=raw_dir,
        out_dir=out_dir,
        workers=1,
        file_overrides={"dem": moon_dem, "wac_reflectance": moon_wac},
    )
    df_moon = pd.read_parquet(out_dir / "features_moon.parquet")
    assert list(df_moon.columns) == MOON_COLUMNS
    assert len(df_moon) == 2
    assert abs(float(df_moon["mean_slope_deg"].iloc[0]) - 10.0) <= 0.2
    assert float(df_moon["wac_reflectance"].iloc[0]) == np.float32(0.25)
    assert np.isnan(df_moon["ice_favorability"].iloc[0])
    assert (out_dir / "map_moon_mean_slope_deg.png").exists()

    # Marte: raster alrededor de (0°, 0°) con THEMIS Day y Night
    r_mars = BODY_RADII_M["Mars"]
    crs_mars = f"+proj=eqc +lat_ts=0 +lat_0=0 +lon_0=0 +x_0=0 +y_0=0 +R={r_mars} +units=m +no_defs"
    mars_dem = raw_dir / "mars" / "dem.tif"
    mars_day = raw_dir / "mars" / "day.tif"
    mars_night = raw_dir / "mars" / "night.tif"
    for path, data in [
        (mars_dem, arr),
        (mars_day, np.full((140, 140), 180.0, dtype=np.float32)),
        (mars_night, np.full((140, 140), 110.0, dtype=np.float32)),
    ]:
        with rasterio.open(
            path,
            "w",
            driver="GTiff",
            height=140,
            width=140,
            count=1,
            dtype="float32",
            crs=crs_mars,
            transform=from_origin(-35000.0, 35000.0, 500.0, 500.0),
            nodata=-9999.0,
        ) as dst:
            dst.write(data, 1)

    run_body_extraction(
        body="Mars",
        raw_dir=raw_dir,
        out_dir=out_dir,
        workers=1,
        file_overrides={
            "dem": mars_dem,
            "themis_day": mars_day,
            "themis_night": mars_night,
        },
    )
    df_mars = pd.read_parquet(out_dir / "features_mars.parquet")
    assert list(df_mars.columns) == MARS_COLUMNS
    assert len(df_mars) == 2
    assert float(df_mars["themis_day"].iloc[0]) == np.float32(180.0)
    assert float(df_mars["themis_night"].iloc[0]) == np.float32(110.0)
    assert float(df_mars["themis_delta"].iloc[0]) == np.float32(70.0)
    assert (out_dir / "map_mars_mean_slope_deg.png").exists()


def test_diviner_prp_csv_parsing_and_polar_patch(tmp_path: Path, monkeypatch) -> None:
    """Lee dlre_prp_south.tab (CSV con espacios y -999), cachea parquet y consulta mediana polar."""
    r_moon = BODY_RADII_M["Moon"]
    raw_dir = tmp_path / "data" / "raw"
    derived_dir = tmp_path / "data" / "derived"
    out_dir = tmp_path / "runs" / "diviner_test"
    (raw_dir / "moon" / "diviner").mkdir(parents=True)

    # DEM polar sur en proyección estereográfica lunar cubriendo ±60 km alrededor del polo sur.
    stere_crs = f"+proj=stere +lat_0=-90 +lon_0=0 +x_0=0 +y_0=0 +R={r_moon} +units=m +no_defs"
    dem_path = raw_dir / "moon" / "polar_dem.tif"
    arr = np.fromfunction(lambda r, c: (c * 500.0 * 0.1), (240, 240)).astype(np.float32)
    with rasterio.open(
        dem_path,
        "w",
        driver="GTiff",
        height=240,
        width=240,
        count=1,
        dtype="float32",
        crs=stere_crs,
        transform=from_origin(-60000.0, 60000.0, 500.0, 500.0),
        nodata=-9999.0,
    ) as dst:
        dst.write(arr, 1)

    # Tabla sintética con formato real de dlre_prp_south.tab:
    # Dos triángulos cerca de (-89.5, 0.0) con hielo y uno sin hielo (-999),
    # más dos cerca de (-89.5, 180.0) todos sin hielo (-999).
    tab_path = raw_dir / "moon" / "diviner" / "dlre_prp_south.tab"
    tab_path.write_text(
        "\n".join(
            [
                "tri1_x, tri1_y, tri1_z, tri2_x, tri2_y, tri2_z, tri3_x, tri3_y, tri3_z, tri_clon, tri_clat, tri_calt, temp_avg, temp_max, ice_depth",
                "0, 0, 0, 0, 0, 0, 0, 0, 0, 0.0, -89.5, 100.0, 40.0, 90.0, 0.20",
                "0, 0, 0, 0, 0, 0, 0, 0, 0, 0.1, -89.5, 100.0, 50.0, 100.0, 0.40",
                "0, 0, 0, 0, 0, 0, 0, 0, 0, -0.1, -89.5, 100.0, 60.0, 110.0, -999",
                "0, 0, 0, 0, 0, 0, 0, 0, 0, 180.0, -89.5, 100.0, 70.0, 130.0, -999",
            ]
        ),
        encoding="utf-8",
    )

    pq_path = prepare_diviner_parquet(tab_path, derived_dir / "diviner_prp_south.parquet")
    assert pq_path is not None and pq_path.exists()

    monkeypatch.setattr(
        "pipeline.planet_features.generate_grid",
        lambda body, size_km=32.0: [(-89.5, 0.0), (-89.5, 180.0)],
    )
    run_body_extraction(
        body="Moon",
        raw_dir=raw_dir,
        out_dir=out_dir,
        derived_dir=derived_dir,
        workers=1,
        file_overrides={"dem": dem_path, "diviner_prp": tab_path},
    )

    df = pd.read_parquet(out_dir / "features_moon.parquet")
    assert len(df) == 2

    row0 = df.iloc[0]
    assert float(row0["diviner_tavg_k"]) == np.float32(50.0)
    assert float(row0["diviner_tmax_k"]) == np.float32(100.0)
    # -999 ignorado en la mediana -> mediana de [0.20, 0.40] = 0.30
    assert abs(float(row0["ice_depth_m"]) - 0.30) < 1e-4

    row1 = df.iloc[1]
    assert float(row1["diviner_tavg_k"]) == np.float32(70.0)
    assert float(row1["diviner_tmax_k"]) == np.float32(130.0)
    assert np.isnan(row1["ice_depth_m"])


def test_compute_lunar_wac_percentile() -> None:
    """Convierte brillo relativo WAC a percentil [0, 1] dentro de la distribución lunar."""
    series = pd.Series([10.0, 20.0, 30.0, np.nan, 40.0], index=["a", "b", "c", "d", "e"])
    pct = compute_lunar_wac_percentile(series)

    assert isinstance(pct, pd.Series)
    assert list(pct.index) == ["a", "b", "c", "d", "e"]
    assert np.isnan(pct.loc["d"])
    assert np.allclose(pct.dropna().to_numpy(), [0.125, 0.375, 0.625, 0.875], atol=1e-6)

    # Referencia separada, empates, extremos y escalar.
    ref = np.array([10.0, 20.0, 20.0, 40.0, np.nan], dtype=np.float32)
    assert abs(float(compute_lunar_wac_percentile(20.0, reference=ref)) - 0.5) < 1e-6
    assert float(compute_lunar_wac_percentile(5.0, reference=ref)) == 0.0
    assert float(compute_lunar_wac_percentile(50.0, reference=ref)) == 1.0
    assert np.isnan(compute_lunar_wac_percentile(np.nan, reference=ref))
    assert np.isnan(compute_lunar_wac_percentile(25.0, reference=np.array([np.nan, np.nan])))
