"""Cálculo de rasgos geomorfométricos sobre parches AEQD de 64x64."""

from __future__ import annotations

import numpy as np

from .config import PATCH_RES_M


def compute_features(
    z: np.ndarray,
    res_m: float = PATCH_RES_M,
) -> dict[str, np.float32]:
    """Calcula los 7 rasgos geomorfométricos de un parche de elevación (metros).

    Antes de calcular, rellena cualquier NaN/no finito restante con la mediana del parche.
    Todos los rasgos se devuelven como np.float32 con los nombres exactos de la v2.
    """
    arr = np.asarray(z, dtype=np.float64)
    if arr.ndim != 2:
        raise ValueError(f"Se esperaba un arreglo 2D, se recibió ndim={arr.ndim}.")
    h, w = arr.shape
    if h < 3 or w < 3:
        raise ValueError(
            f"El parche debe ser de al menos 3x3 píxeles para calcular TRI, recibido {arr.shape}."
        )
    if res_m <= 0:
        raise ValueError(f"res_m debe ser positivo, recibido {res_m}.")

    valid = np.isfinite(arr)
    if not np.any(valid):
        raise ValueError("El parche no contiene píxeles finitos.")

    med = float(np.median(arr[valid]))
    z_clean = np.where(valid, arr, med)

    res = float(res_m)
    gy, gx = np.gradient(z_clean, res, res)
    slope_deg = np.degrees(np.arctan(np.hypot(gx, gy)))

    mean_slope_deg = np.float32(np.mean(slope_deg))
    p90_slope_deg = np.float32(np.percentile(slope_deg, 90))

    p95, p5 = np.percentile(z_clean, [95, 5])
    relief_m = np.float32(p95 - p5)

    z_min = float(np.min(z_clean))
    z_max = float(np.max(z_clean))
    z_mean = float(np.mean(z_clean))
    if z_max == z_min:
        hypso = 0.5
    else:
        hypso = (z_mean - z_min) / (z_max - z_min)
    hypsometric_integral = np.float32(hypso)

    # Ajuste de plano z ≈ a*x + b*y + c por mínimos cuadrados.
    x_coords = (np.arange(w, dtype=np.float64) - (w - 1) / 2.0) * res
    y_coords = (np.arange(h, dtype=np.float64) - (h - 1) / 2.0) * res
    xx, yy = np.meshgrid(x_coords, y_coords)
    design = np.column_stack([xx.ravel(), yy.ravel(), np.ones(h * w, dtype=np.float64)])
    coeffs, _, _, _ = np.linalg.lstsq(design, z_clean.ravel(), rcond=None)
    plane = (design @ coeffs).reshape(h, w)
    detrended_std_m = np.float32(np.std(z_clean - plane))

    # TRI de Riley: sqrt(sum((z_vecino - z_centro)^2)) sobre los 8 vecinos en píxeles interiores.
    center = z_clean[1:-1, 1:-1]
    sq_sum = np.zeros_like(center, dtype=np.float64)
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0:
                continue
            neighbor = z_clean[1 + dr : h - 1 + dr, 1 + dc : w - 1 + dc]
            diff = neighbor - center
            sq_sum += diff * diff
    tri_m = np.float32(np.mean(np.sqrt(sq_sum)))

    mean_elev_m = np.float32(z_mean)

    return {
        "mean_slope_deg": mean_slope_deg,
        "p90_slope_deg": p90_slope_deg,
        "relief_m": relief_m,
        "hypsometric_integral": hypsometric_integral,
        "detrended_std_m": detrended_std_m,
        "tri_m": tri_m,
        "mean_elev_m": mean_elev_m,
    }


extract_features = compute_features
