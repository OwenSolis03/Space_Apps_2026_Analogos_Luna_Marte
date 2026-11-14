"""Extracción de parches locales sin distorsión en proyección AEQD."""

from __future__ import annotations

import math
import os

# Permite que PROJ transforme entre definiciones WKT/PROJ4 de cuerpos celestes
# cuando el radio coincide pero difiere el nombre del datum.
os.environ.setdefault("PROJ_IGNORE_CELESTIAL_BODY", "YES")

import numpy as np
import pyproj
from pyproj import CRS, Transformer
from rasterio.enums import Resampling
from rasterio.transform import Affine
from rasterio.warp import reproject, transform_bounds
from rasterio.windows import Window

from .config import (
    BODY_RADII_M,
    MAX_ABS_ELEV_M,
    MIN_VALID_FRAC,
    PATCH_RES_M,
    PATCH_SIZE_KM,
    WGS84_SEMI_MAJOR_M,
    WINDOW_MARGIN_PX,
)

ANTIMERIDIAN_SKIPPED_COUNT: int = 0

_CYLINDRICAL_METHOD_KEYWORDS = (
    "cylindrical",
    "mercator",
    "sinusoidal",
    "mollweide",
    "robinson",
    "eckert",
    "gall",
    "miller",
    "plate carree",
    "plate_carree",
)


def get_antimeridian_skipped_count() -> int:
    """Devuelve el conteo acumulado de parches omitidos por cruce de antimeridiano."""
    return ANTIMERIDIAN_SKIPPED_COUNT


def reset_antimeridian_skipped_count() -> None:
    """Reinicia el contador de parches omitidos por cruce de antimeridiano."""
    global ANTIMERIDIAN_SKIPPED_COUNT
    ANTIMERIDIAN_SKIPPED_COUNT = 0


def _normalize_body(body: str) -> str:
    norm = body.strip().capitalize()
    if norm not in BODY_RADII_M:
        raise ValueError(
            f"Cuerpo no soportado: {body!r}. Valores esperados: Earth, Moon o Mars."
        )
    return norm


def _resolve_crs_and_radius(
    src, lat: float, lon: float, body_norm: str
) -> tuple[CRS, CRS, float]:
    if src.crs is None:
        raise ValueError("El raster fuente no tiene CRS definido.")

    src_crs = pyproj.CRS.from_user_input(src.crs)
    ellipsoid = src_crs.ellipsoid

    if body_norm == "Earth":
        if ellipsoid is not None and ellipsoid.semi_major_metre is not None:
            r_src = float(ellipsoid.semi_major_metre)
            if (
                math.isfinite(r_src)
                and abs(r_src - WGS84_SEMI_MAJOR_M) / WGS84_SEMI_MAJOR_M >= 0.01
            ):
                raise ValueError(
                    f"El radio del CRS fuente ({r_src} m) no coincide con WGS84 "
                    f"({WGS84_SEMI_MAJOR_M} m)."
                )
        r_sphere = WGS84_SEMI_MAJOR_M
        dst_crs = CRS.from_proj4(
            f"+proj=aeqd +lat_0={lat} +lon_0={lon} +x_0=0 +y_0=0 +datum=WGS84 +units=m"
        )
        return src_crs, dst_crs, r_sphere

    expected_r = BODY_RADII_M[body_norm]
    if ellipsoid is not None and ellipsoid.semi_major_metre is not None:
        r_src = float(ellipsoid.semi_major_metre)
        if math.isfinite(r_src):
            if abs(r_src - expected_r) / expected_r >= 0.01:
                raise ValueError(
                    f"El radio del CRS fuente ({r_src} m) no coincide con {body_norm} "
                    f"({expected_r} m)."
                )
            r = r_src
        else:
            r = expected_r
    else:
        r = expected_r

    dst_crs = CRS.from_proj4(
        f"+proj=aeqd +lat_0={lat} +lon_0={lon} +x_0=0 +y_0=0 +R={r} +units=m"
    )
    return src_crs, dst_crs, r


def _has_antimeridian_cut(src_crs: CRS) -> bool:
    if src_crs.is_geographic:
        return True
    op = src_crs.coordinate_operation
    if op is None or not op.method_name:
        return False
    method = op.method_name.lower()
    return any(kw in method for kw in _CYLINDRICAL_METHOD_KEYWORDS)


def _patch_crosses_antimeridian(
    dst_crs: CRS,
    body_norm: str,
    r_sphere: float,
    half_m: float,
    lat: float,
    lon_norm: float,
) -> bool:
    if abs(lon_norm) <= 90.0:
        return False

    geo_crs = (
        CRS.from_proj4("+proj=longlat +datum=WGS84 +no_defs")
        if body_norm == "Earth"
        else CRS.from_proj4(f"+proj=longlat +R={r_sphere} +no_defs")
    )
    transformer = Transformer.from_crs(dst_crs, geo_crs, always_xy=True)

    edge = np.linspace(-half_m, half_m, 21)
    xs = np.concatenate([edge, np.full(21, half_m), edge[::-1], np.full(21, -half_m)])
    ys = np.concatenate([np.full(21, -half_m), edge, np.full(21, half_m), edge[::-1]])
    lons, _ = transformer.transform(xs, ys)
    lons_arr = np.asarray(lons, dtype=np.float64)
    if not np.all(np.isfinite(lons_arr)):
        return True
    if float(np.max(lons_arr) - np.min(lons_arr)) > 180.0:
        return True

    cos_lat = max(abs(math.cos(math.radians(lat))), 1e-6)
    delta_lon = math.degrees((half_m * math.sqrt(2.0)) / (r_sphere * cos_lat))
    return (abs(lon_norm) + delta_lon) > 180.0


def _patch_contains_pole(lat: float, half_m: float, r_sphere: float) -> int:
    """Devuelve -1 si el parche contiene el polo sur, +1 si contiene el norte y 0 si no.

    Criterio: distancia angular del centro al polo <= semidiagonal angular del parche.
    """
    half_diag_deg = math.degrees(half_m * math.sqrt(2.0) / r_sphere)
    if 90.0 - lat <= half_diag_deg:
        return 1
    if 90.0 + lat <= half_diag_deg:
        return -1
    return 0


def _clean_nodata(
    data: np.ndarray,
    nodata: float | int | None,
    scale: float | None = 1.0,
    offset: float | None = 0.0,
) -> np.ndarray:
    arr = data.astype(np.float32, copy=True)
    arr[~np.isfinite(arr)] = np.nan
    # Filtrar centinelas gigantes (p. ej. nodata=-3.4e38 en float32) antes de np.isclose
    # para evitar overflow en float32 y antes de aplicar scale/offset.
    arr[np.abs(arr) > MAX_ABS_ELEV_M] = np.nan
    if nodata is not None:
        nodata_f = float(nodata)
        if math.isfinite(nodata_f) and abs(nodata_f) <= MAX_ABS_ELEV_M:
            arr[np.isclose(arr, np.float32(nodata_f))] = np.nan

    scale_f = 1.0 if scale is None else float(scale)
    offset_f = 0.0 if offset is None else float(offset)
    if scale_f != 1.0 or offset_f != 0.0:
        arr = arr * np.float32(scale_f) + np.float32(offset_f)

    arr[np.abs(arr) > MAX_ABS_ELEV_M] = np.nan
    return arr


def extract_patch(
    src,
    lat: float,
    lon: float,
    body: str,
    size_km: float = PATCH_SIZE_KM,
    res_m: float = PATCH_RES_M,
    resampling: Resampling = Resampling.average,
) -> np.ndarray | None:
    """Extrae un parche cuadrado de elevación en proyección AEQD local centrada en (lat, lon).

    Devuelve un arreglo float32 de forma (N, N) (por defecto 64x64 a 500 m/px),
    o None si el parche cruza el antimeridiano, cae fuera del raster o tiene menos
    del 90 % de píxeles válidos.
    """
    global ANTIMERIDIAN_SKIPPED_COUNT

    body_norm = _normalize_body(body)
    lat_f = float(lat)
    lon_norm = ((float(lon) + 180.0) % 360.0) - 180.0

    src_crs, dst_crs, r_sphere = _resolve_crs_and_radius(src, lat_f, lon_norm, body_norm)

    n_px = int(round((size_km * 1000.0) / res_m))
    if n_px <= 0:
        raise ValueError("El tamaño del parche y la resolución deben producir > 0 píxeles.")

    half_m = size_km * 500.0
    dst_shape = (n_px, n_px)
    dst_transform = Affine(res_m, 0.0, -half_m, 0.0, -res_m, half_m)
    bounds = (-half_m, -half_m, half_m, half_m)

    has_cut = _has_antimeridian_cut(src_crs)
    pole_sign = _patch_contains_pole(lat_f, half_m, r_sphere) if has_cut else 0

    if pole_sign != 0:
        half_diag_deg = math.degrees(half_m * math.sqrt(2.0) / r_sphere)
        if pole_sign == -1:
            lat_lim = min(90.0, -90.0 + (90.0 + lat_f) + half_diag_deg + 0.05)
            lat_pole = -90.0
        else:
            lat_lim = max(-90.0, 90.0 - (90.0 - lat_f) - half_diag_deg - 0.05)
            lat_pole = 90.0

        if src_crs.is_geographic:
            x_lim, y_lim = 0.0, lat_lim
            x_pole, y_pole = 0.0, lat_pole
        else:
            geo_crs = (
                CRS.from_proj4("+proj=longlat +datum=WGS84 +no_defs")
                if body_norm == "Earth"
                else CRS.from_proj4(f"+proj=longlat +R={r_sphere} +no_defs")
            )
            tr = Transformer.from_crs(geo_crs, src_crs, always_xy=True)
            x_lim, y_lim = tr.transform(0.0, lat_lim)
            x_pole, y_pole = tr.transform(0.0, lat_pole)

        if not (
            math.isfinite(x_lim)
            and math.isfinite(y_lim)
            and math.isfinite(x_pole)
            and math.isfinite(y_pole)
        ):
            return None

        row_lim, _ = src.index(x_lim, y_lim)
        row_pole, _ = src.index(x_pole, y_pole)
        r0 = max(0, min(math.floor(row_lim), math.floor(row_pole)) - WINDOW_MARGIN_PX)
        r1 = min(src.height, max(math.ceil(row_lim), math.ceil(row_pole)) + WINDOW_MARGIN_PX)
        c0, c1 = 0, src.width
        if c1 <= c0 or r1 <= r0:
            return None

        read_win = Window(c0, r0, c1 - c0, r1 - r0)
        res_y_m = (
            abs(src.res[1]) * math.radians(1.0) * r_sphere
            if src_crs.is_geographic
            else abs(src.res[1])
        )
        factor_polar = max(1, int(math.floor(res_m / res_y_m))) if res_y_m > 0 else 1
        out_h = (
            max(1, int(read_win.height // factor_polar))
            if factor_polar >= 2 and read_win.height >= factor_polar * 2
            else int(read_win.height)
        )
        out_w = min(int(src.width), 8192)

        if out_h != read_win.height or out_w != read_win.width:
            raw = src.read(
                1,
                window=read_win,
                out_shape=(out_h, out_w),
                resampling=Resampling.average,
                out_dtype="float32",
                masked=False,
            )
            win_transform = src.window_transform(read_win) @ Affine.scale(
                read_win.width / out_w, read_win.height / out_h
            )
        else:
            raw = src.read(1, window=read_win, out_dtype="float32", masked=False)
            win_transform = src.window_transform(read_win)
    else:
        if has_cut and _patch_crosses_antimeridian(
            dst_crs, body_norm, r_sphere, half_m, lat_f, lon_norm
        ):
            ANTIMERIDIAN_SKIPPED_COUNT += 1
            return None

        left, bottom, right, top = transform_bounds(
            dst_crs, src.crs, *bounds, densify_pts=21
        )
        if not (
            math.isfinite(left)
            and math.isfinite(bottom)
            and math.isfinite(right)
            and math.isfinite(top)
        ):
            if has_cut and abs(lon_norm) > 90.0:
                ANTIMERIDIAN_SKIPPED_COUNT += 1
            return None

        if left >= right or bottom >= top:
            if has_cut and abs(lon_norm) > 90.0:
                ANTIMERIDIAN_SKIPPED_COUNT += 1
            return None

        if has_cut:
            max_span = (
                180.0 if src_crs.is_geographic else math.pi * r_sphere
            )
            if (right - left) > max_span and (size_km * 1000.0) < max_span:
                ANTIMERIDIAN_SKIPPED_COUNT += 1
                return None

        win = src.window(left, bottom, right, top)

        col_off = math.floor(win.col_off) - WINDOW_MARGIN_PX
        row_off = math.floor(win.row_off) - WINDOW_MARGIN_PX
        col_end = math.ceil(win.col_off + win.width) + WINDOW_MARGIN_PX
        row_end = math.ceil(win.row_off + win.height) + WINDOW_MARGIN_PX

        c0 = max(0, col_off)
        r0 = max(0, row_off)
        c1 = min(src.width, col_end)
        r1 = min(src.height, row_end)
        if c1 <= c0 or r1 <= r0:
            return None

        read_win = Window(c0, r0, c1 - c0, r1 - r0)

        # Estimar resolución fuente en metros para reducir lectura en rasters muy finos.
        if src_crs.is_geographic:
            res_y_m = abs(src.res[1]) * math.radians(1.0) * r_sphere
            res_x_m = (
                abs(src.res[0])
                * math.radians(1.0)
                * r_sphere
                * max(0.05, abs(math.cos(math.radians(lat_f))))
            )
            res_source_m = max(res_x_m, res_y_m)
        else:
            res_source_m = max(abs(src.res[0]), abs(src.res[1]))

        factor = int(math.floor(res_m / res_source_m)) if res_source_m > 0 else 1

        if factor >= 2 and read_win.height >= factor * 2 and read_win.width >= factor * 2:
            out_h = max(1, int(read_win.height // factor))
            out_w = max(1, int(read_win.width // factor))
            raw = src.read(
                1,
                window=read_win,
                out_shape=(out_h, out_w),
                resampling=Resampling.average,
                out_dtype="float32",
                masked=False,
            )
            win_transform = src.window_transform(read_win) @ Affine.scale(
                read_win.width / out_w, read_win.height / out_h
            )
        else:
            raw = src.read(1, window=read_win, out_dtype="float32", masked=False)
            win_transform = src.window_transform(read_win)

    scales = getattr(src, "scales", None)
    offsets = getattr(src, "offsets", None)
    scale = scales[0] if scales else 1.0
    offset = offsets[0] if offsets else 0.0
    data = _clean_nodata(raw, src.nodata, scale=scale, offset=offset)
    if not np.any(np.isfinite(data)):
        return None

    dst = np.full(dst_shape, np.nan, dtype=np.float32)
    reproject(
        source=data,
        destination=dst,
        src_transform=win_transform,
        src_crs=src.crs,
        src_nodata=np.nan,
        dst_transform=dst_transform,
        dst_crs=dst_crs,
        dst_nodata=np.nan,
        resampling=resampling,
    )

    dst[~np.isfinite(dst)] = np.nan
    dst[np.abs(dst) > MAX_ABS_ELEV_M] = np.nan

    if float(np.isfinite(dst).mean()) < MIN_VALID_FRAC:
        return None

    return dst.astype(np.float32, copy=False)
