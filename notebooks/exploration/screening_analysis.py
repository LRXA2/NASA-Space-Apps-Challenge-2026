"""Declared exploratory land-cover policies; does not modify processed masks."""
import numpy as np


def screen_patch(coverage: np.ndarray, bare: np.ndarray, built: np.ndarray,
                 crop: np.ndarray, water: np.ndarray) -> dict[str, bool | float | int]:
    """Summarize land-cover policies for an already terrain-complete window."""
    arrays = [coverage, bare, built, crop, water]
    if coverage.ndim != 2 or not coverage.size or coverage.shape[0] != coverage.shape[1]:
        raise ValueError('Expected a nonempty square window')
    for values in arrays:
        if values.shape != coverage.shape or not np.issubdtype(values.dtype, np.number):
            raise ValueError('Fractions must be numeric arrays with matching shapes')
        if np.isinf(values).any() or ((values < 0) | (values > 1)).any():
            raise ValueError('Fractions must be in [0, 1], with NaN only for unknown support')
    finite = np.logical_and.reduce([np.isfinite(a) for a in arrays])
    supported = finite & (coverage >= .99)
    known = bool(supported.all())
    hard = known and bool(((built == 0) & (crop == 0) & (water == 0)).all())
    mean = float(np.mean(bare, dtype=np.float64))
    return {'known_landcover': known, 'hard_exclusions_pass': hard,
            'baseline': hard and bool((bare >= .8).all()), 'patch_mean_bare80': hard and mean >= .8,
            'no_bare_requirement': hard, 'bare_mean': mean,
            'bare_failure_cells': int((bare < .8).sum()), 'built_failure_cells': int((built > 0).sum()),
            'crop_failure_cells': int((crop > 0).sum()), 'water_failure_cells': int((water > 0).sum()),
            'unknown_support_cells': int((~supported).sum())}
