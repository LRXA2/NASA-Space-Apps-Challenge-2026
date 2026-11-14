import unittest

import numpy as np
from affine import Affine
from rasterio.crs import CRS

from operational_cnn.inference.run_lunar_inference import extract_patches, predict
from operational_cnn.model.operability_cnn import TerrainOperabilityCNN


class LunarInferenceTests(unittest.TestCase):
    @staticmethod
    def layers() -> dict[str, np.ndarray]:
        elevation = np.arange(64 * 64, dtype=np.float32).reshape(64, 64)
        return {
            'elevation_m': elevation,
            'slope_deg': np.full((64, 64), 5, dtype=np.float32),
            'roughness_90m': np.full((64, 64), 1, dtype=np.float32),
            'roughness_330m': np.full((64, 64), 2, dtype=np.float32),
            'laplacian_per_m': np.zeros((64, 64), dtype=np.float32),
        }

    def test_extracts_nonoverlapping_complete_patches(self):
        values, records = extract_patches(
            self.layers(), np.ones((64, 64), dtype=bool), region='test_region',
            transform=Affine(30, 0, 0, 0, -30, 1920), crs=CRS.from_epsg(32612))
        self.assertEqual(values.shape, (4, 5, 32, 32))
        self.assertEqual(len(records), 4)
        self.assertAlmostEqual(float(values[0, 0].mean()), 0, places=5)
        self.assertEqual(records[0]['tensor_index'], 0)
        self.assertEqual(records[0]['center_x'], 480)
        self.assertEqual(records[0]['center_y'], 1440)

    def test_rejects_only_window_with_invalid_support(self):
        mask = np.ones((64, 64), dtype=bool)
        mask[2, 2] = False
        values, records = extract_patches(
            self.layers(), mask, region='test_region', transform=Affine.identity(),
            crs=CRS.from_epsg(32612))
        self.assertEqual(values.shape[0], 3)
        self.assertEqual(len(records), 3)
        self.assertNotIn('test_region:960:0:0', {record['patch_id'] for record in records})

    def test_prediction_shapes_and_class_probabilities(self):
        model = TerrainOperabilityCNN()
        physical = np.zeros((3, 5, 32, 32), dtype=np.float32)
        classes, directions, normalized = predict(
            model, physical, np.zeros(5, dtype=np.float32),
            np.ones(5, dtype=np.float32), batch_size=2)
        self.assertEqual(classes.shape, (3, 3))
        self.assertEqual(directions.shape, (3, 4))
        self.assertEqual(normalized.shape, physical.shape)
        np.testing.assert_allclose(classes.sum(axis=1), 1, rtol=1e-6)
        self.assertTrue(((directions >= 0) & (directions <= 1)).all())


if __name__ == '__main__':
    unittest.main()
