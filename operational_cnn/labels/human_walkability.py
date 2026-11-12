"""Provisional macro-scale human terrain labels derived from Earth rasters.

These rules describe terrain connectivity at 30 m resolution. They do not
measure foot-scale hazards, spacesuit performance, fatigue, lighting, regolith
mechanics, or human safety.
"""
from __future__ import annotations

import math


HUMAN_TERRAIN_CLASSES = ('easy', 'caution', 'unsuitable')


def human_terrain_class(*, conservative_crossings: int,
                        conservative_largest_component_fraction: float,
                        permissive_crossings: int,
                        permissive_largest_component_fraction: float,
                        slope_p90_deg: float,
                        easy_min_crossings: int = 3,
                        easy_min_component_fraction: float = .6,
                        easy_max_p90_slope_deg: float = 10.,
                        caution_min_crossings: int = 1,
                        caution_min_component_fraction: float = .35,
                        caution_max_p90_slope_deg: float = 20.) -> str:
    """Collapse declared terrain-only evidence to an experimental class."""
    numbers = (conservative_largest_component_fraction, permissive_largest_component_fraction,
               slope_p90_deg, easy_min_component_fraction, easy_max_p90_slope_deg,
               caution_min_component_fraction, caution_max_p90_slope_deg)
    if (not all(math.isfinite(value) for value in numbers)
            or not 0 <= conservative_crossings <= 4
            or not 0 <= permissive_crossings <= 4
            or not 1 <= easy_min_crossings <= 4
            or not 1 <= caution_min_crossings <= 4
            or not 0 <= easy_min_component_fraction <= 1
            or not 0 <= caution_min_component_fraction <= 1
            or easy_max_p90_slope_deg <= 0
            or caution_max_p90_slope_deg < easy_max_p90_slope_deg):
        raise ValueError('Invalid human terrain label inputs or rule')
    if (conservative_crossings >= easy_min_crossings
            and conservative_largest_component_fraction >= easy_min_component_fraction
            and slope_p90_deg <= easy_max_p90_slope_deg):
        return 'easy'
    if (permissive_crossings >= caution_min_crossings
            and permissive_largest_component_fraction >= caution_min_component_fraction
            and slope_p90_deg <= caution_max_p90_slope_deg):
        return 'caution'
    return 'unsuitable'
