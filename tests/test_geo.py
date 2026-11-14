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


def test_int16_scale_and_offset_applied_to_meters(tmp_path: Path) -> None:
    """GeoTIFF int16 con scale=0.5 y offset!=0 devuelve elevación y pendiente en metros reales."""
    from pipeline.features import compute_features

    radius_m = 1737400.0
    res_m = 200.0
    width, height = 240, 240
    eqc_crs = f"+proj=eqc +lat_ts=0 +lat_0=0 +lon_0=0 +x_0=0 +y_0=0 +R={radius_m} +units=m +no_defs"
    transform = from_origin(-24000.0, 24000.0, res_m, res_m)

    # Queremos pendiente física de 10° en metros tras aplicar scale=0.5 y offset=100.0.
    slope_target_deg = 10.0
    xs = -24000.0 + (np.arange(width, dtype=np.float64) + 0.5) * res_m
    elev_m = (math.tan(math.radians(slope_target_deg)) * xs)[None, :].repeat(height, axis=0)
    offset_m = 100.0
    scale = 0.5
    raw_int16 = np.rint((elev_m - offset_m) / scale).astype(np.int16)
    # Incluir algunos píxeles nodata (< 1 %) para verificar que se enmascaran antes de escalar.
    raw_int16[10:12, 10:12] = -32768

    path = tmp_path / "moon_int16_scaled.tif"
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=height,
        width=width,
        count=1,
        dtype="int16",
        crs=eqc_crs,
        transform=transform,
        nodata=-32768,
    ) as dst:
        dst.write(raw_int16, 1)
        dst.scales = (scale,)
        dst.offsets = (offset_m,)

    with rasterio.open(path) as src:
        patch = extract_patch(src, lat=0.0, lon=0.0, body="Moon")

    assert patch is not None
    assert patch.shape == (64, 64)
    assert patch.dtype == np.float32

    feats = compute_features(patch, res_m=500.0)
    # Centro x=0 -> elev_m promedio debe quedar centrado cerca de 0 m (no -100 m ni 2*elev),
    # así que si la rampa en metros tenía media 0 antes de offset, con offset=100 m raw tendría media -200
    # y tras scale=0.5 + offset=100 vuelve a ~0 m; validemos con un offset distinto en la rampa:
    assert abs(float(feats["mean_slope_deg"]) - slope_target_deg) <= 0.2
    assert abs(float(feats["mean_elev_m"])) < 25.0

    # Caso directo: parche plano con valor crudo 400 -> 400 * 0.5 + 100 = 300 m exactos.
    flat_path = tmp_path / "moon_int16_flat_scaled.tif"
    flat_raw = np.full((height, width), 400, dtype=np.int16)
    flat_raw[0:5, 0:5] = -32768
    with rasterio.open(
        flat_path,
        "w",
        driver="GTiff",
        height=height,
        width=width,
        count=1,
        dtype="int16",
        crs=eqc_crs,
        transform=transform,
        nodata=-32768,
    ) as dst:
        dst.write(flat_raw, 1)
        dst.scales = (0.5,)
        dst.offsets = (100.0,)

    with rasterio.open(flat_path) as src:
        flat_patch = extract_patch(src, lat=0.0, lon=0.0, body="Moon")

    assert flat_patch is not None
    assert np.allclose(flat_patch[np.isfinite(flat_patch)], 300.0, atol=1e-3)


def test_uint8_wac_scale_offset_and_giant_float32_nodata(tmp_path: Path) -> None:
    """Aplica scale/offset de WAC (uint8 a 100 m) y filtra nodata=-3.4e38 sin overflow."""
    import warnings

    from pipeline.geo import _clean_nodata

    # (a) Caso LROC WAC: uint8 a 100 m/px (activa out_shape), nodata=0, scale=1.00395, offset=-0.00395.
    radius_m = 1737400.0
    res_m = 100.0
    width, height = 400, 400
    eqc_crs = f"+proj=eqc +lat_ts=0 +lat_0=0 +lon_0=0 +x_0=0 +y_0=0 +R={radius_m} +units=m +no_defs"
    transform = from_origin(-20000.0, 20000.0, res_m, res_m)

    raw_wac = np.full((height, width), 128, dtype=np.uint8)
    raw_wac[0:10, 0:10] = 0  # nodata=0 (< 1 % del parche)
    wac_path = tmp_path / "moon_wac_uint8.tif"
    with rasterio.open(
        wac_path,
        "w",
        driver="GTiff",
        height=height,
        width=width,
        count=1,
        dtype="uint8",
        crs=eqc_crs,
        transform=transform,
        nodata=0,
    ) as dst:
        dst.write(raw_wac, 1)
        dst.scales = (1.00395,)
        dst.offsets = (-0.00395,)

    with rasterio.open(wac_path) as src:
        wac_patch = extract_patch(src, lat=0.0, lon=0.0, body="Moon", resampling=Resampling.average)

    assert wac_patch is not None
    assert wac_patch.shape == (64, 64)
    expected_wac = 128.0 * 1.00395 - 0.00395
    assert np.allclose(wac_patch[np.isfinite(wac_patch)], expected_wac, atol=1e-2)

    # (b) Caso IceFavorabilityIndex: float32 con nodata=-3.4e38 sin RuntimeWarning de overflow.
    ice_arr = np.array([[0.0, 0.45, -3.4e38, -3.4028235e38]], dtype=np.float32)
    with warnings.catch_warnings():
        warnings.simplefilter("error", RuntimeWarning)
        cleaned = _clean_nodata(ice_arr, nodata=-3.4e38, scale=1.0, offset=0.0)
        wac_cleaned = _clean_nodata(
            np.array([[0, 1, 255]], dtype=np.uint8),
            nodata=0,
            scale=1.00395,
            offset=-0.00395,
        )

    assert np.allclose(cleaned[0, :2], [0.0, 0.45], atol=1e-6)
    assert np.isnan(cleaned[0, 2]) and np.isnan(cleaned[0, 3])
    assert np.isnan(wac_cleaned[0, 0])
    assert np.isclose(float(wac_cleaned[0, 1]), 1.0, atol=1e-4)
    assert np.isclose(float(wac_cleaned[0, 2]), 255.0 * 1.00395 - 0.00395, atol=1e-2)
