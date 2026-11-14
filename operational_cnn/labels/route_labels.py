"""Pure operations for provisional directional terrain labels.

These labels describe connectivity under declared slope scenarios. They are
development targets for an experiment, not measured rover safety.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.ndimage import label, minimum_filter, uniform_filter


DIRECTIONS = ('north_south', 'east_west', 'northwest_southeast', 'northeast_southwest')


@dataclass(frozen=True)
class Connectivity:
    """Directional crossings and connected-area support for one scenario."""

    crossings: dict[str, bool]
    passable_fraction: float
    largest_component_fraction: float

    @property
    def crossing_count(self) -> int:
        return sum(self.crossings.values())


def local_elevation_std(elevation: np.ndarray, window: int) -> np.ndarray:
    """Return local elevation SD only where the full odd window is finite."""
    values = np.asarray(elevation, dtype=np.float64)
    if values.ndim != 2 or window < 3 or window % 2 != 1:
        raise ValueError('Expected a 2-D elevation grid and odd window >= 3')
    valid = np.isfinite(values)
    if not valid.any():
        raise ValueError('No finite elevation')
    safe = np.where(valid, values, 0.)
    full = minimum_filter(valid.astype(np.uint8), size=window, mode='constant', cval=0).astype(bool)
    mean = uniform_filter(safe, size=window, mode='constant')
    second = uniform_filter(safe * safe, size=window, mode='constant')
    result = np.sqrt(np.maximum(second - mean * mean, 0.))
    result[~full] = np.nan
    return result.astype(np.float32)


def _edge_labels(components: np.ndarray, direction: str) -> tuple[np.ndarray, np.ndarray]:
    """Return component labels touching the declared start and destination edges."""
    height, width = components.shape
    band_y, band_x = max(1, height // 3), max(1, width // 3)
    if direction == 'north_south':
        return components[0, :], components[-1, :]
    if direction == 'east_west':
        return components[:, 0], components[:, -1]
    if direction == 'northwest_southeast':
        start = np.concatenate((components[0, :band_x], components[:band_y, 0]))
        finish = np.concatenate((components[-1, -band_x:], components[-band_y:, -1]))
        return start, finish
    if direction == 'northeast_southwest':
        start = np.concatenate((components[0, -band_x:], components[:band_y, -1]))
        finish = np.concatenate((components[-1, :band_x], components[-band_y:, 0]))
        return start, finish
    raise ValueError(f'Unknown direction: {direction}')


def directional_connectivity(slope_deg: np.ndarray, hard_slope_deg: float) -> Connectivity:
    """Find 8-neighbor edge crossings below a declared slope ceiling."""
    slope = np.asarray(slope_deg, dtype=np.float64)
    if (slope.ndim != 2 or slope.shape[0] < 3 or slope.shape[1] < 3
            or not np.isfinite(hard_slope_deg) or hard_slope_deg <= 0):
        raise ValueError('Expected a terrain grid and positive finite slope ceiling')
    passable = np.isfinite(slope) & (slope <= hard_slope_deg)
    components, count = label(passable, structure=np.ones((3, 3), dtype=np.uint8))
    crossings: dict[str, bool] = {}
    for direction in DIRECTIONS:
        start, finish = _edge_labels(components, direction)
        start_ids = set(np.unique(start)) - {0}
        finish_ids = set(np.unique(finish)) - {0}
        crossings[direction] = bool(start_ids & finish_ids)
    sizes = np.bincount(components.ravel(), minlength=count + 1)
    largest = int(sizes[1:].max()) if count else 0
    return Connectivity(
        crossings=crossings,
        passable_fraction=float(passable.mean()),
        largest_component_fraction=float(largest / passable.size),
    )


def operational_class(nominal: Connectivity, permissive: Connectivity,
                      *, min_nominal_directions: int = 3,
                      min_largest_component_fraction: float = .5,
                      min_permissive_directions: int = 1) -> str:
    """Collapse continuous connectivity evidence to a provisional display class."""
    if (not 1 <= min_nominal_directions <= len(DIRECTIONS)
            or not 0 <= min_largest_component_fraction <= 1
            or not 1 <= min_permissive_directions <= len(DIRECTIONS)):
        raise ValueError('Invalid class rule')
    if (nominal.crossing_count >= min_nominal_directions
            and nominal.largest_component_fraction >= min_largest_component_fraction):
        return 'operable'
    if permissive.crossing_count >= min_permissive_directions:
        return 'marginal'
    return 'non_operable'


def spatial_group(region: str, center_x: float, center_y: float, block_m: int = 5000) -> str:
    """Create a stable region-local block ID used to prevent nearby split leakage."""
    if not region or not np.isfinite([center_x, center_y]).all() or block_m < 1:
        raise ValueError('Invalid spatial group inputs')
    return f'{region}:{np.floor(center_x / block_m):.0f}:{np.floor(center_y / block_m):.0f}'

