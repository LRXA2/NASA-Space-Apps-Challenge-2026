"""Deterministic physical discrepancy scenarios for exploratory terrain retrieval."""
from typing import TypedDict

import numpy as np


class Discrepancies(TypedDict):
    baseline: np.ndarray
    with_planarity: np.ndarray
    with_local_sd: np.ndarray


def terrain_discrepancies(query: np.ndarray, candidates: np.ndarray) -> Discrepancies:
    """Return per-candidate worst normalized discrepancy for three scenarios.

    Columns: median slope (deg), P90 slope (deg), central relief (m),
    plane residual fraction, median local elevation SD (m).
    Fixed exploratory bands: 1 deg, 2 deg, max(5 m, 10% smaller relief),
    0.1 residual fraction, max(1 m, 10% smaller local SD). No fitted scaling.
    Score <=1 means every included discrepancy fits its declared band;
    it is not a validated analog-equivalence or equipment threshold.
    """
    if query.shape != (5,) or candidates.ndim != 2 or candidates.shape[1] != 5:
        raise ValueError('Expected query shape (5,) and candidate shape (n, 5)')
    for values in [query[None, :], candidates]:
        if not np.isfinite(values).all() or (values < 0).any():
            raise ValueError('Descriptors must be finite and nonnegative')
        if (values[:, :2] > 90).any() or (values[:, 0] > values[:, 1]).any() or (values[:, 3] > 1).any():
            raise ValueError('Invalid slope quantiles or planarity fraction')
    query = np.asarray(query, dtype=np.float64)
    candidates = np.asarray(candidates, dtype=np.float64)
    delta = np.abs(candidates - query)
    relief_band = np.maximum(5., .1 * np.minimum(query[2], candidates[:, 2]))
    local_sd_band = np.maximum(1., .1 * np.minimum(query[4], candidates[:, 4]))
    baseline = np.maximum.reduce([delta[:, 0], delta[:, 1] / 2., delta[:, 2] / relief_band])
    return {
        'baseline': baseline,
        'with_planarity': np.maximum(baseline, delta[:, 3] / .1),
        'with_local_sd': np.maximum(baseline, delta[:, 4] / local_sd_band),
    }
