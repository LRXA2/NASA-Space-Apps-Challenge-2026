"""Windowed I/O must preserve notebook 05's scientific support and crop rules."""
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.transform import from_origin
from rasterio.warp import reproject

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "darrel stuff/EDA/shared"), str(ROOT / "darrel stuff/EDA/Moon/Stage3_Requirements"), str(ROOT)]
from notebooks.shared.processing import MOON_CRS, Grid, make_grid, warp, crop_native
from terrain_raster_io import raster_windows, image_supported_grid, crop_native_windowed


def write_fixture(path, values, transform, *, crs=MOON_CRS, scale=1., offset=0.):
    with rasterio.open(path, "w", driver="GTiff", width=values.shape[1], height=values.shape[0],
                       count=1, dtype="int16", nodata=-999, crs=crs, transform=transform) as dst:
        dst.write(values, 1)
        dst.scales = (scale,)
        dst.offsets = (offset,)
        dst.set_band_unit(1, "m")


class TerrainRasterIOTests(unittest.TestCase):
    def test_windows_cover_once_without_exceeding_tile_size(self):
        coverage = np.zeros((19, 23), dtype=int)
        for window in raster_windows(23, 19, 7):
            self.assertLessEqual(window.width, 7)
            self.assertLessEqual(window.height, 7)
            coverage[window.toslices()] += 1
        np.testing.assert_array_equal(coverage, 1)
        with self.assertRaises(ValueError):
            list(raster_windows(23, 19, 0))

    def test_support_matches_original_with_missing_coarser_count_coverage(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            source, mask = folder / "elevation.tif", folder / "count.tif"
            raw = np.arange(35*29, dtype="int16").reshape(35, 29)
            raw[10:14, 8:10] = -999
            write_fixture(source, raw, from_origin(0, 175, 5, 5), scale=.25, offset=-80.)
            counts = np.ones((10, 8), dtype="int16")
            counts[2:4, 2:4] = 0
            counts[6, 1] = -999
            write_fixture(mask, counts, from_origin(15, 160, 15, 15))
            with rasterio.open(source) as src:
                grid = make_grid(src.bounds, src.crs, 30)
                heights = src.read(1, masked=True).astype("float32").filled(np.nan)
                heights = heights * src.scales[0] + src.offsets[0]
                source_grid = Grid(src.crs, src.transform, src.width, src.height)
                aligned = warp(mask, source_grid, resampling=Resampling.nearest)
                supported = np.isfinite(heights) & np.isfinite(aligned) & (aligned > 0)
                heights[~supported] = np.nan
                expected = []
                for values in (heights, supported.astype("float32")):
                    destination = np.full((grid.height, grid.width), np.nan, dtype="float32")
                    reproject(values, destination, src_transform=src.transform, src_crs=src.crs,
                              src_nodata=np.nan, dst_transform=grid.transform, dst_crs=grid.crs,
                              dst_nodata=np.nan, resampling=Resampling.average)
                    expected.append(destination)
            for tile_size in (7, 16):
                actual = image_supported_grid(source, mask, grid, folder, tile_size=tile_size)
                for a, b in zip(actual, expected):
                    np.testing.assert_array_equal(np.isfinite(a), np.isfinite(b))
                    # File-backed and MEM-backed GDAL averages can differ by a
                    # float32 rounding step; missingness/support decisions cannot.
                    np.testing.assert_allclose(a, b, rtol=2*np.finfo("float32").eps,
                                               atol=0, equal_nan=True)
                np.testing.assert_array_equal(actual[1] < .99, expected[1] < .99)
                self.assertFalse(list(folder.glob("terrain_work_*")))

    def test_native_crop_pixels_metadata_and_missingness_match_original(self):
        for crs in (MOON_CRS, None):
            with self.subTest(crs=crs), tempfile.TemporaryDirectory() as folder:
                folder = Path(folder)
                source = folder / "source.tif"
                values = np.arange(31*23, dtype="int16").reshape(31, 23)
                values[4:7, 6:8] = -999
                write_fixture(source, values, from_origin(0, 155, 5, 5), crs=crs, scale=.01, offset=12.)
                kwargs = {"fallback_crs": MOON_CRS, "crs_evidence": "fixture README"} if crs is None else {}
                bounds = (-3, 2, 103, 151)
                original = folder / "original.tif"
                tiled = folder / "tiled.tif"
                before = crop_native(source, original, bounds, MOON_CRS, **kwargs)
                after = crop_native_windowed(source, tiled, bounds, MOON_CRS, tile_size=7, **kwargs)
                self.assertEqual(before, after)
                with rasterio.open(original) as a, rasterio.open(tiled) as b:
                    np.testing.assert_array_equal(a.read(1), b.read(1))
                    # NaN nodata values are unequal under dictionary equality.
                    profile_a, profile_b = dict(a.profile), dict(b.profile)
                    self.assertTrue(np.isnan(profile_a.pop("nodata")))
                    self.assertTrue(np.isnan(profile_b.pop("nodata")))
                    self.assertEqual(profile_a, profile_b)
                    self.assertEqual(a.tags(), b.tags())
                    self.assertEqual(a.units, b.units)

    def test_missing_crs_still_requires_documented_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "missing_crs.tif"
            write_fixture(source, np.ones((3, 3), dtype="int16"), from_origin(0, 15, 5, 5), crs=None)
            with self.assertRaisesRegex(ValueError, "documented fallback"):
                crop_native_windowed(source, Path(folder) / "bad.tif", (0, 0, 15, 15), MOON_CRS)


if __name__ == "__main__":
    unittest.main()
