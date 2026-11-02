"""Physical candidate availability and ranking diagnostics, not relevance labels."""
import numpy as np


def candidate_coverage(query: np.ndarray, candidates: np.ndarray,
                       tolerances: np.ndarray, order: np.ndarray) -> dict[str, float]:
    """Summarize a complete ranking against inclusive per-feature tolerances."""
    if (query.ndim != 1 or not query.size or candidates.ndim != 2
            or candidates.shape[1] != query.size or not len(candidates)
            or tolerances.shape != query.shape):
        raise ValueError('Expected a feature vector, nonempty candidate matrix and aligned tolerances')
    if (not np.isfinite(query).all() or not np.isfinite(candidates).all()
            or not np.isfinite(tolerances).all() or (tolerances <= 0).any()):
        raise ValueError('Features must be finite and tolerances positive')
    if (order.ndim != 1 or not np.issubdtype(order.dtype, np.integer)
            or not np.array_equal(np.sort(order), np.arange(len(candidates)))):
        raise ValueError('Order must be a complete permutation of candidate indices')
    errors = np.max(np.abs(candidates - query) / tolerances, axis=1)
    compatible = errors <= 1.
    ranks = np.flatnonzero(compatible[order]) + 1
    return {
        'compatible_count': int(compatible.sum()),
        'compatible_fraction': float(compatible.mean()),
        'first_compatible_rank': float(ranks[0]) if len(ranks) else np.nan,
        'top5_hit': float(compatible[order[:5]].any()),
        'top1_hit': float(compatible[order[0]]),
        'best_max_normalized_error': float(errors.min()),
        'top1_max_normalized_error': float(errors[order[0]]),
    }
