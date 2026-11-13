"""Shape and split tests for the provisional operability CNN."""
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from operational_cnn.model.operability_cnn import TerrainOperabilityCNN
from operational_cnn.training.train_operability import assign_splits


class OperabilityCNNTests(unittest.TestCase):
    def test_model_outputs_class_and_direction_logits(self):
        model = TerrainOperabilityCNN()
        classes, directions = model(torch.zeros(2, 5, 32, 32))
        self.assertEqual(tuple(classes.shape), (2, 3))
        self.assertEqual(tuple(directions.shape), (2, 4))
        with self.assertRaises(ValueError):
            model(torch.zeros(2, 3, 32, 32))

    def test_spatial_groups_never_cross_roles(self):
        frame = pd.DataFrame({
            'region': ['a', 'a', 'a', 'b', 'b', 'test'],
            'spatial_group': ['a1', 'a1', 'a2', 'b1', 'b2', 't1'],
        })
        roles = assign_splits(frame, 'test', .25, 1)
        for group in frame['spatial_group'].unique():
            self.assertEqual(len(set(roles[frame['spatial_group'].to_numpy() == group])), 1)
        self.assertEqual(set(roles[frame['region'].to_numpy() == 'test']), {'test'})


if __name__ == '__main__':
    unittest.main()

