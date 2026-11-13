"""Tests for generated route evidence and leakage groups."""
import json
import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from operational_cnn.data.build_operability_eda import validate_config
from operational_cnn.labels.route_labels import (
    directional_connectivity,
    local_elevation_std,
    operational_class,
    spatial_group,
)


class RouteLabelTests(unittest.TestCase):
    def test_flat_patch_crosses_every_direction_and_is_operable(self):
        result = directional_connectivity(np.zeros((32, 32)), 15.)
        self.assertEqual(result.crossing_count, 4)
        self.assertEqual(result.passable_fraction, 1.)
        self.assertEqual(operational_class(result, result), 'operable')

    def test_horizontal_barrier_blocks_north_south(self):
        slope = np.zeros((32, 32))
        slope[15:17, :] = 30.
        nominal = directional_connectivity(slope, 15.)
        self.assertFalse(nominal.crossings['north_south'])
        self.assertTrue(nominal.crossings['east_west'])

    def test_permissive_only_crossing_is_marginal(self):
        slope = np.full((32, 32), 18.)
        nominal = directional_connectivity(slope, 15.)
        permissive = directional_connectivity(slope, 20.)
        self.assertEqual(nominal.crossing_count, 0)
        self.assertEqual(permissive.crossing_count, 4)
        self.assertEqual(operational_class(nominal, permissive), 'marginal')

    def test_impossible_patch_is_non_operable(self):
        slope = np.full((32, 32), 30.)
        result = directional_connectivity(slope, 20.)
        self.assertEqual(operational_class(result, result), 'non_operable')

    def test_local_std_requires_full_support(self):
        elevation = np.arange(25, dtype=float).reshape(5, 5)
        result = local_elevation_std(elevation, 3)
        self.assertTrue(np.isnan(result[0]).all())
        self.assertTrue(np.isfinite(result[1:-1, 1:-1]).all())
        elevation[2, 2] = np.nan
        result = local_elevation_std(elevation, 3)
        self.assertTrue(np.isnan(result[1:4, 1:4]).all())

    def test_spatial_group_keeps_nearby_points_together(self):
        self.assertEqual(spatial_group('a', 101., 4999.), spatial_group('a', 4999., 1.))
        self.assertNotEqual(spatial_group('a', 4999., 1.), spatial_group('a', 5001., 1.))

    def test_checked_in_config_is_valid(self):
        path = Path(__file__).resolve().parents[1] / 'configs/operability_config.json'
        config = json.loads(path.read_text(encoding='utf-8'))
        validate_config(config)
        config['minimum_natural_fraction'] = 2
        with self.assertRaises(ValueError):
            validate_config(config)


if __name__ == '__main__':
    unittest.main()
