"""Matched-grid surface diagnostics, without acquisition or datum conversion."""
from typing import TypedDict

import numpy as np


class SurfaceComparison(TypedDict):
    mean_offset_m: float
    offset_removed_rmse_m: float
    offset_removed_p95_abs_m: float


def compare_elevation_surfaces(reference: np.ndarray, estimate: np.ndarray) -> SurfaceComparison:
    """Compare complete co-registered grids; offset removal is not datum conversion."""
    if reference.ndim != 2 or reference.size == 0 or reference.shape != estimate.shape:
        raise ValueError('Surface comparison requires equal nonempty two-dimensional grids')
    if not np.isfinite(reference).all() or not np.isfinite(estimate).all():
        raise ValueError('Surface comparison requires complete finite support')
    difference = np.asarray(estimate, dtype=np.float64) - np.asarray(reference, dtype=np.float64)
    offset = float(difference.mean())
    centered = difference - offset
    return {'mean_offset_m': offset,
            'offset_removed_rmse_m': float(np.sqrt(np.mean(centered**2))),
            'offset_removed_p95_abs_m': float(np.quantile(np.abs(centered), .95))}
