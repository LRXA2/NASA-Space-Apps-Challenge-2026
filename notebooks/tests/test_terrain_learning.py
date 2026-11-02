"""Small analytical cases for leakage, physical amplitudes and retrieval."""
import json
import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parents[1]))
import terrain_learning as learning
from terrain_dataset import validate_config


class TerrainLearningTests(unittest.TestCase):
    def test_noninteger_dimensions_are_rejected_before_raster_reads(self):
        config_path = Path(__file__).parents[1] / 'modeling/terrain_similarity/terrain_dataset.json'
        for field, value in [('patch_size_m', 960.0), ('spacing_m', 30.0),
                             ('schema_version', True), ('context_m', True)]:
            config = json.loads(config_path.read_text(encoding='utf-8'))
            config[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_config(config)

    def test_reserves_and_unassigned_roles_fail_before_data_access(self):
        config_path = Path(__file__).parents[1] / 'modeling/terrain_similarity/terrain_dataset.json'
        config = json.loads(config_path.read_text(encoding='utf-8'))
        validate_config(config)
        for field, value in [('region', 'Mauna Loa'), ('role', 'final'), ('fold', 'test')]:
            altered = json.loads(config_path.read_text(encoding='utf-8'))
            altered['regions'][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_config(altered)

    def test_normalization_zero_fill_is_distinguishable_from_valid_zero(self):
        values = np.array([[[[2., np.nan]], [[4., 6.]], [[0., 2.]]]])
        normalized, valid = learning.normalize_tensors(values, np.array([2., 4., 0.]), np.array([2., 2., 1.]))
        np.testing.assert_allclose(normalized, [[[[0., 0.]], [[0., 1.]], [[0., 2.]]]])
        self.assertTrue(valid[0, 0, 0, 0])
        self.assertFalse(valid[0, 0, 0, 1])

    def test_baseline_has_stable_ties_and_no_threshold_as_label(self):
        query = np.array([1., 2., 10., .1, 1.])
        candidates = np.array([[1., 2., 10., .3, 1.], [1., 2., 10., .1, 1.], [1., 2., 10., .1, 1.]])
        order, scores = learning.rank_candidates(query, candidates, ['far', 'b', 'a'], k=3)
        np.testing.assert_array_equal(order, [2, 1, 0])
        np.testing.assert_allclose(scores, [0., 0., 2.])
        order, scores = learning.rank_candidates(query, np.empty((0, 5)), [], k=5)
        self.assertEqual(order.size, 0)
        self.assertEqual(scores.size, 0)

    def test_scaler_uses_training_only_and_equal_region_mass(self):
        # Region A has two patches at 1; B has one at 3. Equal-region moments
        # are mean 2, variance 1, regardless of held-out region C at 100.
        values = np.broadcast_to(np.array([1., 1., 3., 100.])[:, None, None, None], (4, 3, 2, 2))
        mean, scale = learning.fit_scaler(values, ['train', 'train', 'train', 'holdout'], ['a', 'a', 'b', 'c'])
        np.testing.assert_allclose(mean, [2., 2., 2.])
        np.testing.assert_allclose(scale, [1., 1., 1.])
        with self.assertRaises(ValueError):
            learning.fit_scaler(values, ['train', 'holdout', 'train', 'holdout'], ['a', 'a', 'b', 'c'])

    def test_tensor_retains_missingness_and_physical_height_amplitude(self):
        heights = np.array([[10., 12.], [14., np.nan]])
        slope = np.array([[0., 2.], [4., np.nan]])
        roughness = np.ones((2, 2))
        result = learning.prepare_patch(heights, slope, roughness)
        np.testing.assert_allclose(result[0], [[-2., 0.], [2., np.nan]], equal_nan=True)
        np.testing.assert_allclose(result[1], slope, equal_nan=True)
        double = learning.prepare_patch(heights * 2, slope, roughness)
        np.testing.assert_allclose(double[0], [[-4., 0.], [4., np.nan]], equal_nan=True)
        with self.assertRaises(ValueError):
            learning.prepare_patch(heights, np.full((2, 2), 91.), roughness)

    def test_split_rejects_same_region_and_context_overlap(self):
        train = learning.SplitFootprint('moon', 'a', 'train', (0, 0, 100, 100))
        for heldout in [
            learning.SplitFootprint('moon', 'a', 'holdout', (500, 500, 600, 600)),
            learning.SplitFootprint('moon', 'b', 'holdout', (90, 0, 200, 100)),
            learning.SplitFootprint('moon', 'b', 'holdout', (100, 0, 200, 100)),
        ]:
            with self.subTest(heldout=heldout), self.assertRaises(ValueError):
                learning.validate_split_footprints([train, heldout])
        learning.validate_split_footprints([
            train, learning.SplitFootprint('moon', 'b', 'holdout', (101, 0, 200, 100)),
            learning.SplitFootprint('earth', 'c', 'holdout', (0, 0, 100, 100)),
        ])


if __name__ == '__main__':
    unittest.main()
