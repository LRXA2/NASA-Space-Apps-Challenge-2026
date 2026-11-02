"""Physical descriptors of complete terrain patches; no file or plotting operations."""
from typing import TypedDict

import numpy as np


class PatchMetrics(TypedDict):
    elevation_mean_m: float
    relief_m: float
    central_relief_m: float
    slope_median_deg: float
    slope_p90_deg: float
    local_sd_median_m: float


class PlaneMetrics(TypedDict):
    plane_residual_rms_m: float
    plane_residual_fraction: float


def measure_planarity(elevation: np.ndarray) -> PlaneMetrics:
    """Deviation from a least-squares plane on a uniform square grid.

    The fraction is residual RMS divided by elevation population SD; zero
    for a constant patch. Uniform grid spacing does not affect fitted heights.
    This measures planarity, not roughness, traversability or a landform class.
    """
    if elevation.ndim != 2 or elevation.shape[0] < 2 or elevation.shape[0] != elevation.shape[1]:
        raise ValueError('Planarity requires a square grid with at least two cells per side')
    if not np.isfinite(elevation).all():
        raise ValueError('Planarity requires complete finite elevation')
    heights = np.asarray(elevation, dtype=np.float64) - float(elevation[0, 0])
    heights -= heights.mean()
    side = heights.shape[0]
    coordinate = np.arange(side, dtype=np.float64) - (side - 1) / 2
    denominator = side * float(coordinate @ coordinate)
    along_columns = float((heights * coordinate[None, :]).sum()) / denominator
    along_rows = float((heights * coordinate[:, None]).sum()) / denominator
    residual = heights - along_columns * coordinate[None, :] - along_rows * coordinate[:, None]
    residual_rms = float(np.sqrt(np.mean(residual**2)))
    height_sd = float(np.sqrt(np.mean(heights**2)))
    return {
        'plane_residual_rms_m': residual_rms,
        'plane_residual_fraction': min(1., residual_rms / height_sd) if height_sd else 0.,
    }


def measure_patch(
    elevation: np.ndarray, slope: np.ndarray, local_sd: np.ndarray,
) -> PatchMetrics:
    """Measure a complete square patch in physical units, without normalization."""
    if elevation.ndim != 2 or elevation.size == 0 or elevation.shape[0] != elevation.shape[1]:
        raise ValueError('Terrain patches must be nonempty two-dimensional squares')
    if slope.shape != elevation.shape or local_sd.shape != elevation.shape:
        raise ValueError('Patch layers must have the same shape')
    if not all(np.isfinite(layer).all() for layer in (elevation, slope, local_sd)):
        raise ValueError('Patch metrics require complete finite inputs')
    if (slope < 0).any() or (slope > 90).any() or (local_sd < 0).any():
        raise ValueError('Slope must be in [0, 90] degrees and local SD nonnegative')
    heights = np.asarray(elevation, dtype=np.float64)
    height_quantiles = np.quantile(heights, [.05, .95], method='linear')
    slope_quantiles = np.quantile(slope, [.5, .9], method='linear')
    return {
        'elevation_mean_m': float(heights.mean()),
        'relief_m': float(heights.max() - heights.min()),
        'central_relief_m': float(height_quantiles[1] - height_quantiles[0]),
        'slope_median_deg': float(slope_quantiles[0]),
        'slope_p90_deg': float(slope_quantiles[1]),
        'local_sd_median_m': float(np.median(local_sd)),
    }
