"""In-memory contracts for terrain tensors and development-only retrieval."""
from dataclasses import dataclass

import numpy as np
from notebooks.shared.retrieval_analysis import terrain_discrepancies


@dataclass(frozen=True)
class SplitFootprint:
    """Conservative context bounds in one shared metric CRS per body."""

    body: str
    region: str
    role: str
    bounds: tuple[float, float, float, float]

    def __post_init__(self) -> None:
        if self.body not in {'earth', 'moon'} or self.role not in {'train', 'holdout'} or not self.region:
            raise ValueError('Only named Earth/Moon development train or holdout regions are allowed')
        left, bottom, right, top = self.bounds
        if not np.isfinite(self.bounds).all() or left >= right or bottom >= top:
            raise ValueError('Invalid context bounds')


def validate_split_footprints(footprints: list[SplitFootprint]) -> None:
    """Reject regional or geographic leakage between development fold roles."""
    for index, first in enumerate(footprints):
        for second in footprints[index + 1:]:
            if first.body != second.body or first.role == second.role:
                continue
            a, b = first.bounds, second.bounds
            overlaps = a[0] <= b[2] and a[2] >= b[0] and a[1] <= b[3] and a[3] >= b[1]
            if first.region == second.region or overlaps:
                raise ValueError(f'Cross-role region/context overlap: {first.region}, {second.region}')


def prepare_patch(elevation: np.ndarray, slope: np.ndarray, local_sd: np.ndarray) -> np.ndarray:
    """Return CHW relative elevation (m), slope (deg), local elevation SD (m)."""
    if elevation.ndim != 2 or elevation.shape[0] < 2 or elevation.shape[0] != elevation.shape[1]:
        raise ValueError('Expected square terrain with at least two cells per side')
    if slope.shape != elevation.shape or local_sd.shape != elevation.shape:
        raise ValueError('Terrain channels must align')
    values = np.stack([elevation, slope, local_sd]).astype(np.float64)
    if np.isinf(values).any() or not np.isfinite(elevation).any():
        raise ValueError('Infinite terrain or no finite elevation')
    if ((slope < 0) | (slope > 90)).any() or (local_sd < 0).any():
        raise ValueError('Invalid slope or local elevation SD')
    values[0] -= np.nanmean(values[0])
    return values.astype(np.float32)


def fit_scaler(tensors: np.ndarray, roles: list[str], regions: list[str]) -> tuple[np.ndarray, np.ndarray]:
    """Fit population mean/SD on train only, giving each train region equal mass."""
    if tensors.ndim != 4 or tensors.shape[1] != 3 or not tensors.size:
        raise ValueError('Expected nonempty NCHW tensors with three channels')
    if len(roles) != len(tensors) or len(regions) != len(tensors) or not set(roles) <= {'train', 'holdout'}:
        raise ValueError('Aligned development fold roles and regions are required')
    region_array = np.asarray(regions)
    role_array = np.asarray(roles)
    for region in set(regions):
        if len(set(role_array[region_array == region])) != 1:
            raise ValueError('One region cannot appear on both sides of a fold')
    train_regions = sorted(set(region_array[role_array == 'train']))
    if not train_regions:
        raise ValueError('No training regions')
    means, second_moments = [], []
    for region in train_regions:
        values = tensors[region_array == region].astype(np.float64)
        if not np.isfinite(values).all():
            raise ValueError('Initial scaler requires complete training patches')
        means.append(values.mean(axis=(0, 2, 3)))
        second_moments.append(np.square(values).mean(axis=(0, 2, 3)))
    mean = np.mean(means, axis=0)
    scale = np.sqrt(np.maximum(0., np.mean(second_moments, axis=0) - mean**2))
    return mean, np.where(scale > 1e-8, scale, 1.)


def normalize_tensors(tensors: np.ndarray, mean: np.ndarray, scale: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return normalized NCHW values plus validity; zero-fill only after scaling."""
    if tensors.ndim != 4 or tensors.shape[1] != 3 or mean.shape != (3,) or scale.shape != (3,):
        raise ValueError('Expected NCHW terrain and three-channel scaler')
    if not np.isfinite(mean).all() or not np.isfinite(scale).all() or (scale <= 0).any() or np.isinf(tensors).any():
        raise ValueError('Invalid scaler or infinite terrain')
    valid = np.isfinite(tensors)
    normalized = (tensors - mean[None, :, None, None]) / scale[None, :, None, None]
    return np.where(valid, normalized, 0.).astype(np.float32), valid


def rank_candidates(query: np.ndarray, candidates: np.ndarray, ids: list[str], k: int = 5) -> tuple[np.ndarray, np.ndarray]:
    """Existing physical bands plus planarity; stable ties by candidate ID."""
    if len(ids) != len(candidates) or len(set(ids)) != len(ids):
        raise ValueError('Unique candidate IDs must align with descriptors')
    if isinstance(k, bool) or not isinstance(k, int) or k < 1:
        raise ValueError('k must be a positive integer')
    scores = terrain_discrepancies(query, candidates)['with_planarity']
    order = np.lexsort((np.asarray(ids, dtype=str), scores))[:k]
    return order, scores[order]
