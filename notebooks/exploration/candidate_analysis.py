"""Component-level diagnostics for the fixed exploratory terrain bands."""
import numpy as np
from notebooks.shared.retrieval_analysis import terrain_discrepancies


def terrain_band_components(query: np.ndarray, candidates: np.ndarray) -> np.ndarray:
    """Return (n, 4) normalized median-slope/P90-slope/relief/planarity differences.

    Input columns/validity follow terrain_discrepancies. Preserve that historical
    helper unchanged; expose its fixed component bands for explanatory audits.
    These exploratory bands are not validated analog-equivalence thresholds.
    """
    terrain_discrepancies(query, candidates)  # Reuse the existing descriptor contract.
    query = np.asarray(query, dtype=np.float64)
    candidates = np.asarray(candidates, dtype=np.float64)
    delta = np.abs(candidates - query)
    return np.column_stack([delta[:, 0], delta[:, 1] / 2,
                            delta[:, 2] / np.maximum(5., .1 * np.minimum(query[2], candidates[:, 2])),
                            delta[:, 3] / .1])
