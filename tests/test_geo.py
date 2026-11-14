"""Pruebas unitarias para pipeline/geo.py (T1)."""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pytest
import rasterio
from pyproj import CRS
from rasterio.enums import Resampling
from rasterio.transform import from_origin

from pipeline.geo import (
    extract_patch,
    get_antimeridian_skipped_count,
    reset_antimeridian_skipped_count,
)


def _create_vrt(vrt_path: Path, tile_paths: list[Path], bounds: tuple[float, float, float, float], res_deg: float) -> None:
    min_lon, min_lat, max_lon, max_lat = bounds
    total_w = int(round((max_lon - min_lon) / res_deg))
    total_h = int(round((max_lat - min_lat) / res_deg))

    sources_xml = []
    for tile in tile_paths:
        with rasterio.open(tile) as src:
            tb = src.bounds
            x_off = int(round((tb.left - min_lon) / res_deg))
            y_off = int(round((max_lat - tb.top) / res_deg))
            w = src.width
            h = src.height
            nodata_tag = f"<NODATA>{src.nodata}</NODATA>" if src.nodata is not None else ""
            sources_xml.append(
                f"""    <SimpleSource>
      <SourceFilename relativeToVRT="0">{tile.as_posix()}</SourceFilename>
      <SourceBand>1</SourceBand>
      <SourceProperties RasterXSize="{w}" RasterYSize="{h}" DataType="Float32" BlockXSize="{w}" BlockYSize="1" />
      <SrcRect xOff="0" yOff="0" xSize="{w}" ySize="{h}" />
      <DstRect xOff="{x_off}" yOff="{y_off}" xSize="{w}" ySize="{h}" />
      {nodata_tag}
    </SimpleSource>"""
            )

    srs_wkt = CRS.from_epsg(4326).to_wkt().replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    gt = f"{min_lon}, {res_deg}, 0.0, {max_lat}, 0.0, {-res_deg}"
    vrt_content = f"""<VRTDataset rasterXSize="{total_w}" rasterYSize="{total_h}">
  <SRS dataAxisToSRSAxisMapping="2,1">{srs_wkt}</SRS>
  <GeoTransform>{gt}</GeoTransform>
  <VRTRasterBand dataType="Float32" band="1">
    <NoDataValue>-9999.0</NoDataValue>
{chr(10).join(sources_xml)}
  </VRTRasterBand>
</VRTDataset>
"""
    vrt_path.write_text(vrt_content, encoding="utf-8")


def test_moon_equirectangular_slope_invariance_lat0_vs_lat70(tmp_path: Path) -> None:
    """Plano inclinado de 10° en Luna equirectangular da la misma pendiente en lat 0° y 70°."""
    radius_m = 1737400.0
    res_m = 200.0
    slope_target_deg = 10.0
    tan_slope = math.tan(math.radians(slope_target_deg))

    # Franja continua en equirectangular desde lat -1.5° hasta +72° y ±60 km en X.
    x_min = -60000.0
    x_max = 60000.0
    y_min = math.radians(-1.5) * radius_m
    y_max = math.radians(72.0) * radius_m

    width = int(round((x_max - x_min) / res_m))
    height = int(round((y_max - y_min) / res_m))
    transform = from_origin(x_min, y_max, res_m, res_m)
    eqc_crs = f"+proj=eqc +lat_ts=0 +lat_0=0 +lon_0=0 +x_0=0 +y_0=0 +R={radius_m} +units=m +no_defs"

    xs = x_min + (np.arange(width, dtype=np.float64) + 0.5) * res_m
    ys = y_max - (np.arange(height, dtype=np.float64) + 0.5) * res_m
    lon_rad = xs[None, :] / radius_m
    lat_rad = ys[:, None] / radius_m

    # Plano físico con pendiente de 10° hacia el este sobre la esfera.
    elev = (tan_slope * radius_m * np.cos(lat_rad) * np.sin(lon_rad)).astype(np.float32)

    dem_path = tmp_path / "moon_eqc_slope10.tif"
    with rasterio.open(
        dem_path,
        "w",
        driver="GTiff",
        height=height,
        width=width,
        count=1,
        dtype="float32",
        crs=eqc_crs,
        transform=transform,
        nodata=-9999.0,
    ) as dst:
        dst.write(elev, 1)

    with rasterio.open(dem_path) as src:
        patch_0 = extract_patch(src, lat=0.0, lon=0.0, body="Moon")
        patch_70 = extract_patch(src, lat=70.0, lon=0.0, body="Moon")

        # Verificar que sin reproyección (enfoque v1) la latitud alta falla severamente.
        row_70, col_70 = src.index(0.0, math.radians(70.0) * radius_m)
        raw_win = src.read(
            1,
            window=rasterio.windows.Window(col_70 - 32, row_70 - 32, 64, 64),
        )
        gy_raw, gx_raw = np.gradient(raw_win.astype(np.float64), res_m)
        raw_slope_70 = float(np.mean(np.degrees(np.arctan(np.hypot(gx_raw, gy_raw)))))
        assert abs(raw_slope_70 - slope_target_deg) > 5.0

    assert patch_0 is not None
    assert patch_70 is not None
    assert patch_0.shape == (64, 64)
    assert patch_70.shape == (64, 64)
    assert patch_0.dtype == np.float32
    assert patch_70.dtype == np.float32

    gy0, gx0 = np.gradient(patch_0.astype(np.float64), 500.0)
    slope_0 = float(np.mean(np.degrees(np.arctan(np.hypot(gx0, gy0)))))

    gy70, gx70 = np.gradient(patch_70.astype(np.float64), 500.0)
    slope_70 = float(np.mean(np.degrees(np.arctan(np.hypot(gx70, gy70)))))

    assert abs(slope_0 - slope_target_deg) <= 0.2
    assert abs(slope_70 - slope_target_deg) <= 0.2
    assert abs(slope_0 - slope_70) <= 0.2


def test_earth_vrt_seam_no_holes(tmp_path: Path) -> None:
    """Un parche de la Tierra que cruza el borde entre dos tiles en VRT no tiene huecos."""
    res_deg = 1.0 / 1200.0  # ~92 m en el ecuador (Copernicus GLO-90)
    tile_size = 1200  # 1° x 1°

    tile_specs = [
        (tmp_path / "tile_e10_n20.tif", 10.0, 21.0, 100.0),
        (tmp_path / "tile_e11_n20.tif", 11.0, 21.0, 100.0),
    ]

    tile_paths = []
    for path, left_lon, top_lat, base_elev in tile_specs:
        arr = np.full((tile_size, tile_size), base_elev, dtype=np.float32)
        with rasterio.open(
            path,
            "w",
            driver="GTiff",
            height=tile_size,
            width=tile_size,
            count=1,
            dtype="float32",
            crs="EPSG:4326",
            transform=from_origin(left_lon, top_lat, res_deg, res_deg),
            nodata=-9999.0,
        ) as dst:
            dst.write(arr, 1)
        tile_paths.append(path)

    vrt_path = tmp_path / "copernicus_mosaic.vrt"
    _create_vrt(vrt_path, tile_paths, bounds=(10.0, 20.0, 12.0, 21.0), res_deg=res_deg)

    with rasterio.open(vrt_path) as src:
        patch = extract_patch(src, lat=20.5, lon=11.0, body="Earth")

    assert patch is not None
    assert patch.shape == (64, 64)
    assert np.isnan(patch).sum() == 0
    assert np.allclose(patch, 100.0, atol=1e-3)


def test_ocean_and_nodata_returns_none(tmp_path: Path) -> None:
    """Un parche en océano (todo nodata, valores >1e5 o <90% válidos) devuelve None."""
    res_deg = 0.005
    size = 200  # 1° x 1°
    nodata_path = tmp_path / "ocean_nodata.tif"

    data = np.full((size, size), -9999.0, dtype=np.float32)
    with rasterio.open(
        nodata_path,
        "w",
        driver="GTiff",
        height=size,
        width=size,
        count=1,
        dtype="float32",
        crs="EPSG:4326",
        transform=from_origin(0.0, 1.0, res_deg, res_deg),
        nodata=-9999.0,
    ) as dst:
        dst.write(data, 1)

    with rasterio.open(nodata_path) as src:
        assert extract_patch(src, lat=0.5, lon=0.5, body="Earth") is None
        # Fuera de los límites del raster también devuelve None.
        assert extract_patch(src, lat=15.0, lon=15.0, body="Earth") is None

    # Raster con valores > 1e5 (centinelas no declarados como nodata) y < 90% válidos.
    extreme_path = tmp_path / "extreme_partial.tif"
    partial = np.full((size, size), 1e9, dtype=np.float32)
    partial[: size // 2, :] = 250.0  # solo ~50% válido
    with rasterio.open(
        extreme_path,
        "w",
        driver="GTiff",
        height=size,
        width=size,
        count=1,
        dtype="float32",
        crs="EPSG:4326",
        transform=from_origin(0.0, 1.0, res_deg, res_deg),
    ) as dst:
        dst.write(partial, 1)

    with rasterio.open(extreme_path) as src:
        assert extract_patch(src, lat=0.5, lon=0.5, body="Earth") is None


def test_antimeridian_crossing_returns_none(tmp_path: Path) -> None:
    """Un parche que cruza el antimeridiano ±180° se omite, cuenta y devuelve None."""
    reset_antimeridian_skipped_count()
    res_deg = 0.005
    size = 400
    path = tmp_path / "mars_antimeridian.tif"
    mars_crs = "+proj=longlat +R=3396190 +no_defs"

    data = np.full((size, size), 500.0, dtype=np.float32)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=size,
        width=size,
        count=1,
        dtype="float32",
        crs=mars_crs,
        transform=from_origin(178.0, 1.0, res_deg, res_deg),
        nodata=-9999.0,
    ) as dst:
        dst.write(data, 1)

    with rasterio.open(path) as src:
        patch = extract_patch(src, lat=0.0, lon=179.95, body="Mars")

    assert patch is None
    assert get_antimeridian_skipped_count() == 1


def test_radius_mismatch_raises_value_error(tmp_path: Path) -> None:
    """Si el radio del CRS fuente no coincide con el cuerpo pedido, lanza ValueError."""
    path = tmp_path / "wrong_body.tif"
    data = np.zeros((100, 100), dtype=np.float32)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=100,
        width=100,
        count=1,
        dtype="float32",
        crs="+proj=longlat +R=1737400 +no_defs",
        transform=from_origin(0.0, 1.0, 0.01, 0.01),
    ) as dst:
        dst.write(data, 1)

    with rasterio.open(path) as src:
        with pytest.raises(ValueError):
            extract_patch(src, lat=0.5, lon=0.5, body="Mars")
