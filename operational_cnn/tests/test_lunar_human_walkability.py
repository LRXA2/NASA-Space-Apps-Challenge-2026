import unittest

import numpy as np

from operational_cnn.inference.run_lunar_human_walkability import (
    add_direct_rule_evidence, add_predictions, predict,
)
from operational_cnn.model.terrain_mobility_cnn import TerrainMobilityCNN


class LunarHumanWalkabilityInferenceTests(unittest.TestCase):
    def test_prediction_shapes(self):
        physical = np.zeros((3, 5, 32, 32), dtype=np.float32)
        rover, directions, human, normalized = predict(
            TerrainMobilityCNN(), physical, np.zeros(5, dtype=np.float32),
            np.ones(5, dtype=np.float32), batch_size=2)
        self.assertEqual(rover.shape, (3, 3))
        self.assertEqual(directions.shape, (3, 4))
        self.assertEqual(human.shape, (3, 3))
        self.assertEqual(normalized.shape, physical.shape)
        np.testing.assert_allclose(rover.sum(axis=1), 1, rtol=1e-6)
        np.testing.assert_allclose(human.sum(axis=1), 1, rtol=1e-6)

    def test_adds_separate_rover_and_human_fields(self):
        records = [{'patch_id': 'one'}]
        add_predictions(records, np.array([[.1, .2, .7]]), np.array([[.6, .4, .8, .2]]),
                        np.array([[.8, .1, .1]]), .5)
        self.assertEqual(records[0]['predicted_rover_class'], 'non_operable')
        self.assertEqual(records[0]['predicted_human_terrain_class'], 'easy')
        self.assertTrue(records[0]['predicted_north_south'])
        self.assertFalse(records[0]['predicted_east_west'])

    def test_direct_rule_evidence_is_marked_separately(self):
        records = [{'predicted_human_terrain_class': 'easy'}]
        physical = np.zeros((1, 5, 32, 32), dtype=np.float32)
        rule = {
            'easy_min_crossings': 3, 'easy_min_component_fraction': .6,
            'easy_max_p90_slope_deg': 10., 'caution_min_crossings': 1,
            'caution_min_component_fraction': .35, 'caution_max_p90_slope_deg': 20.,
        }
        add_direct_rule_evidence(records, physical, rule)
        self.assertEqual(records[0]['direct_human_terrain_rule'], 'easy')
        self.assertTrue(records[0]['cnn_agrees_with_direct_human_rule'])


if __name__ == '__main__':
    unittest.main()
