"""Synthetic checks that both lunar tile namings join on one shared tile ID."""
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd
from rasterio.crs import CRS
from rasterio.transform import from_origin

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from notebooks.shared.moon_tiles import build_tile_table, coverage_summary, tile_id
from notebooks.shared.processing import MOON_CRS
from operational_cnn.inference.run_lunar_inference import extract_patches

REGION = 'A3CLR22_2_Haworth'
CRS_WKT = CRS.from_user_input(MOON_CRS).to_wkt()


def similarity_patches(transform, shape, views=('full_context', 'image_supported'), skip=()):
    """Mirror terrain_dataset.extract_source: centre lattice 16 + 32k and window bounds."""
    rows = []
    for view in views:
        for center_row in range(16, shape[0] - 15, 32):
            for center_col in range(16, shape[1] - 15, 32):
                if (center_row, center_col) in skip:
                    continue
                row, col = center_row - 16, center_col - 16
                left, top = transform @ (col, row)
                right, bottom = transform @ (col + 32, row + 32)
                rows.append({'patch_id': f'{REGION}:{view}:{center_row}:{center_col}:960', 'body': 'moon',
                             'region': REGION, 'view': view, 'size_m': 960, 'left': left, 'right': right,
                             'bottom': bottom, 'top': top, 'crs_wkt': CRS_WKT})
    rows.append({'patch_id': 'wadi_rum:natural_screen:16:16:960', 'body': 'earth', 'region': 'wadi_rum',
                 'view': 'natural_screen', 'size_m': 960, 'left': 0., 'right': 960., 'bottom': 0.,
                 'top': 960., 'crs_wkt': CRS.from_epsg(32636).to_wkt()})
    return pd.DataFrame(rows)


def operability_predictions(transform, shape, missing=None):
    """Run the real operability patch extractor on synthetic complete layers."""
    names = ('elevation_m', 'slope_deg', 'roughness_90m', 'roughness_330m', 'laplacian_per_m')
    layers = {name: np.ones(shape, dtype=np.float32) for name in names}
    complete = np.ones(shape, dtype=bool)
    if missing is not None:
        complete[missing] = False
    _, records = extract_patches(layers, complete, region=REGION, transform=transform,
                                 crs=CRS.from_user_input(MOON_CRS))
    return pd.DataFrame(records)


class MoonTileTests(unittest.TestCase):
    transform = from_origin(-45240., 93900., 30., 30.)
    shape = (96, 128)

    def test_both_namings_join_on_one_tile(self):
        table, mapping = build_tile_table(similarity_patches(self.transform, self.shape),
                                          {'rover': operability_predictions(self.transform, self.shape)})
        self.assertEqual(len(table), 3 * 4)
        self.assertTrue(table[['in_similarity_full_context', 'in_similarity_image_supported', 'in_rover']]
                        .all(axis=None))
        first = table.set_index('rover_patch_id').loc[f'{REGION}:960:0:0']
        self.assertEqual(first['similarity_full_context_patch_id'], f'{REGION}:full_context:16:16:960')
        self.assertEqual(first['tile_id'], tile_id(REGION, -45240. + 480, 93900. - 480))
        self.assertEqual((first['xmax'] - first['xmin'], first['ymax'] - first['ymin']), (960., 960.))
        self.assertEqual(set(mapping['source']), {'similarity_full_context', 'similarity_image_supported', 'rover'})
        self.assertNotIn('wadi_rum', set(table['region']))

    def test_tiles_missing_from_one_source_are_kept_and_flagged(self):
        table, _ = build_tile_table(
            similarity_patches(self.transform, self.shape, skip={(48, 48)}),
            {'rover': operability_predictions(self.transform, self.shape, missing=np.s_[64:70, 96:100])})
        self.assertEqual(len(table), 12)
        summary = coverage_summary(table).iloc[0]
        self.assertEqual((summary['tiles'], summary['in_rover'], summary['in_similarity_full_context']),
                         (12, 11, 11))
        self.assertEqual(summary['in_all_sources'], 10)

    def test_grid_from_a_different_origin_is_refused(self):
        shifted = from_origin(-45240. + 30, 93900., 30., 30.)
        with self.assertRaisesRegex(ValueError, 'off the shared 960 m lattice by up to 30.0 m'):
            build_tile_table(similarity_patches(self.transform, self.shape),
                             {'rover': operability_predictions(shifted, self.shape)})

    def test_whole_tile_offsets_still_align(self):
        moved = from_origin(-45240. + 960, 93900. - 1920, 30., 30.)
        table, _ = build_tile_table(similarity_patches(self.transform, self.shape),
                                    {'rover': operability_predictions(moved, self.shape)})
        # One tile right and two down: three columns by one row overlap.
        self.assertEqual(int(table['in_rover'].sum()), 12)
        self.assertEqual(int((table['in_rover'] & table['in_similarity_full_context']).sum()), 3)
        self.assertEqual(len(table), 12 + 12 - 3)

    def test_invalid_inputs_are_refused(self):
        predictions = operability_predictions(self.transform, self.shape)
        with self.assertRaisesRegex(ValueError, 'unique patch IDs'):
            build_tile_table(operability={'rover': pd.concat([predictions, predictions.head(1)])})
        with self.assertRaisesRegex(ValueError, '960 m lunar tiles'):
            build_tile_table(operability={'rover': predictions.assign(size_m=600)})
        with self.assertRaisesRegex(ValueError, 'at least one'):
            build_tile_table()


if __name__ == '__main__':
    unittest.main()
