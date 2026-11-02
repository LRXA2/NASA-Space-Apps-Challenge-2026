"""Analytical vertical-scaling cases; no model-quality assumptions."""
import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parents[3]))
from terrain_perturbation import rescale_terrain


class PerturbationTests(unittest.TestCase):
    def test_identity_inverse_and_flat_controls(self):
        values = np.array([[[[-2., 2.], [-2., 2.]], [[10., 20.], [30., 40.]], [[1., 2.], [3., 4.]]]], dtype=np.float32)
        np.testing.assert_array_equal(rescale_terrain(values, 1.), values)
        np.testing.assert_allclose(rescale_terrain(rescale_terrain(values, 2.), .5), values, atol=1e-5)
        flat = np.zeros((1, 3, 2, 2), dtype=np.float32)
        np.testing.assert_array_equal(rescale_terrain(flat, 2.), flat)

    def test_invalid_physical_inputs_fail(self):
        values = np.zeros((1, 3, 2, 2), dtype=np.float32)
        for factor in [0., -1., np.inf, np.nan, True]:
            with self.subTest(factor=factor), self.assertRaises(ValueError):
                rescale_terrain(values, factor)
        for channel, value in [(0, np.nan), (1, -1.), (1, 90.), (2, -1.)]:
            invalid = values.copy()
            invalid[:, channel] = value
            with self.subTest(channel=channel, value=value), self.assertRaises(ValueError):
                rescale_terrain(invalid, 2.)

    def test_doubling_a_unit_gradient_changes_angle_not_linearly(self):
        # A plane rising 90 m over 90 m has gradient 1 and angle 45 degrees.
        # Doubling heights makes gradient 2: angle 63.4349488, not 90 degrees.
        values = np.array([[[[-45., 45.], [-45., 45.]],
                            [[45., 45.], [45., 45.]], [[30., 30.], [30., 30.]]]])
        original = values.copy()
        result = rescale_terrain(values, 2.)
        np.testing.assert_allclose(result[0, 0], [[-90., 90.], [-90., 90.]])
        np.testing.assert_allclose(result[0, 1], 63.4349488, atol=1e-5)
        np.testing.assert_allclose(result[0, 2], 60.)
        np.testing.assert_array_equal(values, original)


if __name__ == '__main__':
    unittest.main()
