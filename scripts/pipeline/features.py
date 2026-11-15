"""Computation of geomorphometric features on 64x64 AEQD elevation patches.

This module provides the single unified implementation for extracting terrain morphology
metrics across Earth, Moon, and Mars. Evaluating patches at an identical metric scale
(32x32 km at 500 m/pixel) ensures that slope, roughness, and relief are directly comparable
without scale-dependent bias.
"""

from __future__ import annotations

import numpy as np

from .config import PATCH_RES_M


def compute_features(
    z: np.ndarray,
    res_m: float = PATCH_RES_M,
) -> dict[str, np.float32]:
    """Calculate the 7 canonical geomorphometric features of an elevation patch (meters).

    Before feature calculation, any remaining non-finite / NaN values are imputed with the
    patch median elevation. All computed metrics are returned as np.float32 values.

    Parameters:
        z: 2D numpy array containing patch elevation data in meters.
        res_m: Grid cell spatial resolution in meters (default: 500 m).

    Returns:
        dict containing the 7 terrain metrics:
            - mean_slope_deg: Mean terrain slope in degrees.
            - p90_slope_deg: 90th percentile slope in degrees (steepness metric).
            - relief_m: Vertical relief (95th - 5th percentile) in meters.
            - hypsometric_integral: Dimensionless hypsometry ratio (mean-min)/(max-min).
            - detrended_std_m: Roughness standard deviation after subtracting planar trend.
            - tri_m: Riley's Terrain Ruggedness Index over 8-neighborhood interior pixels.
            - mean_elev_m: Mean elevation in meters (stored for context, not matched across bodies).

    Raises:
        ValueError: If array is not 2D, smaller than 3x3, res_m <= 0, or contains no finite pixels.
    """
    arr = np.asarray(z, dtype=np.float64)
    if arr.ndim != 2:
        raise ValueError(f"Expected 2D array, got ndim={arr.ndim}.")
    h, w = arr.shape
    if h < 3 or w < 3:
        raise ValueError(
            f"Patch must be at least 3x3 pixels to compute TRI, received {arr.shape}."
        )
    if res_m <= 0:
        raise ValueError(f"res_m must be strictly positive, received {res_m}.")

    valid = np.isfinite(arr)
    if not np.any(valid):
        raise ValueError("Patch contains no finite pixels.")

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

    # 2D planar trend fitting: z ~ a*x + b*y + c via ordinary least squares.
    x_coords = (np.arange(w, dtype=np.float64) - (w - 1) / 2.0) * res
    y_coords = (np.arange(h, dtype=np.float64) - (h - 1) / 2.0) * res
    xx, yy = np.meshgrid(x_coords, y_coords)
    design = np.column_stack([xx.ravel(), yy.ravel(), np.ones(h * w, dtype=np.float64)])
    coeffs, _, _, _ = np.linalg.lstsq(design, z_clean.ravel(), rcond=None)
    plane = (design @ coeffs).reshape(h, w)
    detrended_std_m = np.float32(np.std(z_clean - plane))

    # Riley's Terrain Ruggedness Index: sqrt(sum((z_neighbor - z_center)^2)) across 8 neighbors.
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
