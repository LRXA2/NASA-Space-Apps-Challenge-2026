"""Worked candidate pools protect coverage/ranking and no-match semantics."""
import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from notebooks.modeling.terrain_similarity.candidate_coverage import candidate_coverage


class CoverageTests(unittest.TestCase):
    def test_available_candidate_can_be_missed_by_top_five(self):
        # Only the final candidate meets BOTH tolerances, exactly at the boundary.
        pool = np.array([[20., 10.], [10., 20.], [30., 30.], [40., 40.], [50., 50.], [12., 13.]])
        result = candidate_coverage(np.array([10., 10.]), pool, np.array([2., 3.]), np.arange(6))
        self.assertEqual(result['compatible_count'], 1)
        self.assertEqual(result['first_compatible_rank'], 6)
        self.assertEqual(result['top5_hit'], 0)
        self.assertEqual(result['best_max_normalized_error'], 1)
        self.assertEqual(result['top1_max_normalized_error'], 5)
        self.assertAlmostEqual(result['compatible_fraction'], 1 / 6)

    def test_no_match_has_no_rank_and_short_pool_can_hit(self):
        query = np.array([0.])
        missing = candidate_coverage(query, np.array([[3.], [4.]]), np.array([1.]), np.array([1, 0]))
        self.assertEqual(missing['compatible_count'], 0)
        self.assertTrue(np.isnan(missing['first_compatible_rank']))
        self.assertEqual(missing['top5_hit'], 0)
        found = candidate_coverage(query, np.array([[3.], [1.]]), np.array([1.]), np.array([1, 0]))
        self.assertEqual(found['first_compatible_rank'], 1)
        self.assertEqual(found['top1_hit'], 1)
        self.assertEqual(found['top5_hit'], 1)

    def test_invalid_rankings_and_tolerances_fail(self):
        for order in [np.array([0, 0]), np.array([0]), np.array([0., 1.]), np.array([-1, 0])]:
            with self.subTest(order=order), self.assertRaises(ValueError):
                candidate_coverage(np.array([0.]), np.array([[1.], [2.]]), np.array([1.]), order)
        for tolerance in [0., -1., np.nan]:
            with self.subTest(tolerance=tolerance), self.assertRaises(ValueError):
                candidate_coverage(np.array([0.]), np.array([[1.]]), np.array([tolerance]), np.array([0]))


if __name__ == '__main__':
    unittest.main()
