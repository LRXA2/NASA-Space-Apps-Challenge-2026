import unittest

import torch

from operational_cnn.labels.human_walkability import human_terrain_class
from operational_cnn.model.terrain_mobility_cnn import TerrainMobilityCNN


RULE = {
    'easy_min_crossings': 3,
    'easy_min_component_fraction': .6,
    'easy_max_p90_slope_deg': 10.,
    'caution_min_crossings': 1,
    'caution_min_component_fraction': .35,
    'caution_max_p90_slope_deg': 20.,
}


class HumanWalkabilityTests(unittest.TestCase):
    def classify(self, conservative: int, conservative_component: float,
                 permissive: int, permissive_component: float, slope: float) -> str:
        return human_terrain_class(
            conservative_crossings=conservative,
            conservative_largest_component_fraction=conservative_component,
            permissive_crossings=permissive,
            permissive_largest_component_fraction=permissive_component,
            slope_p90_deg=slope, **RULE)

    def test_easy_requires_all_three_conservative_conditions(self):
        self.assertEqual(self.classify(3, .7, 4, .9, 9), 'easy')
        self.assertEqual(self.classify(2, .7, 4, .9, 9), 'caution')
        self.assertEqual(self.classify(3, .5, 4, .9, 9), 'caution')
        self.assertEqual(self.classify(3, .7, 4, .9, 11), 'caution')

    def test_unsuitable_when_permissive_evidence_fails(self):
        self.assertEqual(self.classify(0, .1, 0, .9, 8), 'unsuitable')
        self.assertEqual(self.classify(0, .1, 1, .2, 8), 'unsuitable')
        self.assertEqual(self.classify(0, .1, 4, .9, 21), 'unsuitable')

    def test_three_head_model_shapes(self):
        rover, directions, human = TerrainMobilityCNN()(torch.zeros(2, 5, 32, 32))
        self.assertEqual(tuple(rover.shape), (2, 3))
        self.assertEqual(tuple(directions.shape), (2, 4))
        self.assertEqual(tuple(human.shape), (2, 3))


if __name__ == '__main__':
    unittest.main()
