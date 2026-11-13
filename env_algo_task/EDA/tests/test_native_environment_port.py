from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np
import rasterio
from rasterio.transform import from_origin
from scipy.ndimage import minimum_filter

sys.path[:0] = [str(Path(__file__).resolve().parents[1] / "shared"), str(Path(__file__).resolve().parents[1] / "Moon/Stage3_Requirements"), str(Path(__file__).resolve().parents[3])]
from terrain_followup_eda import support_policy_checks, source_crop_check


class NativeEnvironmentPortTests(unittest.TestCase):
    def arrays(self):
        elevation = np.ones((15, 15)); fraction = np.ones_like(elevation)
        fraction[7, 7] = 0; elevation[7, 7] = np.nan
        features = {}
        for name, width in [('slope_deg', 3), ('laplacian_per_m', 3), ('local_elevation_std_m', 11)]:
            valid = minimum_filter(np.isfinite(elevation).astype('uint8'), size=width, mode='constant', cval=0)
            features[name] = np.where(valid, 1., np.nan)
        return elevation, fraction, features

    def test_exact_policy_and_neighbourhoods(self):
        inside, result = support_policy_checks(*self.arrays())
        self.assertEqual(inside.sum(), 225); self.assertEqual(set(result.values()), {0})

    def test_mask_and_neighbourhood_regressions_fail(self):
        elevation, fraction, features = self.arrays(); elevation[7, 7] = 0
        with self.assertRaises(ValueError): support_policy_checks(elevation, fraction, features)
        elevation, fraction, features = self.arrays(); features['slope_deg'][7, 7] = 0
        with self.assertRaises(ValueError): support_policy_checks(elevation, fraction, features)

    def test_decode_source_once_and_preserve_missingness(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, crop = Path(tmp) / 'source.tif', Path(tmp) / 'crop.tif'
            profile = dict(driver='GTiff', height=3, width=3, count=1, crs='EPSG:4326', transform=from_origin(0, 3, 1, 1))
            data = np.arange(9, dtype='int16').reshape(3, 3); data[0, 0] = -999
            with rasterio.open(source, 'w', dtype='int16', nodata=-999, **profile) as src:
                src.write(data, 1); src.scales = (.01,)
            decoded = np.where(data == -999, np.nan, data * .01).astype('float32')
            with rasterio.open(crop, 'w', dtype='float32', nodata=np.nan, **profile) as dst: dst.write(decoded, 1)
            result = source_crop_check(source, crop)
            self.assertEqual(result['sample_positions'], 9); self.assertEqual(result['finite_pairs'], 8)
            self.assertLess(result['maximum_absolute_difference'], 1e-6)
            with rasterio.open(crop, 'r+') as dst: dst.scales = (.01,)
            with self.assertRaises(ValueError): source_crop_check(source, crop)


if __name__ == '__main__': unittest.main()
