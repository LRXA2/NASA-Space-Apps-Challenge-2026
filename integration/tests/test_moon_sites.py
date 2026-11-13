"""Synthetic checks for the per-tile terrain table and region-level environment join."""
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd
from rasterio.transform import from_origin

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from integration.moon_sites import build_moon_sites, environment_scores, summary_by_region, terrain_sites
from notebooks.shared.moon_tiles import tile_id
from notebooks.shared.tests.test_moon_tiles import REGION, operability_predictions

TRANSFORM = from_origin(-45240., 93900., 30., 30.)
FIRST_TILE = tile_id(REGION, -44760., 93420.)


def walkability_predictions() -> pd.DataFrame:
    """Real patch records with the walkability run's class and crossing columns."""
    frame = operability_predictions(TRANSFORM, (64, 64))
    classes = ['operable', 'marginal', 'non_operable', 'operable']
    frame['predicted_rover_class'] = classes
    frame['predicted_rover_probability'] = 0.9
    for name in ('operable', 'marginal', 'non_operable'):
        frame[f'rover_probability_{name}'] = [0.9 if c == name else 0.05 for c in classes]
    frame['predicted_human_terrain_class'] = ['easy', 'caution', 'unsuitable', 'caution']
    frame['predicted_human_terrain_probability'] = 0.8
    for name in ('easy', 'caution', 'unsuitable'):
        frame[f'human_probability_{name}'] = 0.1
    for index, name in enumerate(('north_south', 'east_west', 'northwest_southeast', 'northeast_southwest')):
        frame[f'predicted_{name}'] = [True, True, False, index < 2]
    return frame


def environment_results(ids: list[str]) -> pd.DataFrame:
    """The environment pipeline's compact Operations/Survival output layout."""
    count = len(ids)
    return pd.DataFrame({'ID': ids, 'operations_solar_illumination_score': [11.33] * count,
                         'survival_radiation_score': [74.85] * count,
                         'operations_status': (['Pass', 'Fail'] * count)[:count],
                         'survival_status': ['Pass'] * count,
                         'operations_fail_reason': (['', 'solar_illumination: too short'] * count)[:count],
                         'survival_fail_reason': [''] * count,
                         'operations_score': [35.24] * count, 'survival_score': [64.38] * count})


class MoonSiteTests(unittest.TestCase):
    def test_terrain_rows_get_tile_ids_and_crossing_counts(self):
        sites = terrain_sites(walkability_predictions())
        self.assertEqual(len(sites), 4)
        self.assertEqual(sites.loc[0, 'tile_id'], FIRST_TILE)
        self.assertEqual(sites.loc[0, 'terrain_patch_id'], f'{REGION}:960:0:0')
        self.assertEqual(sites['predicted_crossing_count'].tolist(), [4, 4, 0, 2])
        self.assertIn('predicted_human_terrain_class', sites.columns)

    def test_rover_only_run_column_names_are_accepted(self):
        frame = walkability_predictions().drop(
            columns=[c for c in walkability_predictions().columns if c.startswith(('human_', 'predicted_human'))])
        frame = frame.rename(columns={'predicted_rover_class': 'predicted_class',
                                      'predicted_rover_probability': 'predicted_class_probability',
                                      'rover_probability_operable': 'probability_operable',
                                      'rover_probability_marginal': 'probability_marginal',
                                      'rover_probability_non_operable': 'probability_non_operable'})
        sites = terrain_sites(frame)
        self.assertEqual(sites['predicted_rover_class'].tolist(),
                         ['operable', 'marginal', 'non_operable', 'operable'])
        self.assertNotIn('predicted_human_terrain_class', sites.columns)

    def test_region_scores_reach_every_tile_in_the_region(self):
        sites = build_moon_sites(walkability_predictions(), environment_results(['eda_004', 'eda_001', 'dummy_001']))
        self.assertTrue(sites['env_assessed'].all())
        self.assertEqual(set(sites['env_id']), {'eda_004'})
        self.assertEqual(set(sites['env_scope']), {'region'})
        self.assertEqual(sites.loc[0, 'env_operations_score'], 35.24)
        self.assertEqual(sites.loc[3, 'env_survival_radiation_score'], 74.85)
        self.assertNotIn('env_ID', sites.columns)
        summary = summary_by_region(sites).iloc[0]
        self.assertEqual((summary['tiles'], summary['env_assessed']), (4, 4))
        self.assertEqual((summary['env_operations_pass'], summary['env_survival_pass']), (4, 4))
        self.assertEqual(summary['env_survival_score'], 64.38)
        self.assertEqual((summary['rover_operable'], summary['human_caution']), (2, 2))

    def test_other_environment_rows_are_skipped_and_reported(self):
        _, skipped = environment_scores(environment_results(['eda_001', 'eda_008', 'synthetic_001']))
        self.assertEqual(skipped, ['eda_008', 'synthetic_001'])

    def test_failed_region_status_is_kept(self):
        frame = environment_results(['eda_001', 'eda_004'])
        sites = build_moon_sites(walkability_predictions(), frame)
        self.assertEqual(set(sites['env_operations_status']), {'Fail'})
        self.assertEqual(summary_by_region(sites).iloc[0]['env_operations_pass'], 0)

    def test_without_environment_every_tile_is_unassessed(self):
        sites = build_moon_sites(walkability_predictions())
        self.assertFalse(sites['env_assessed'].any())
        self.assertEqual(summary_by_region(sites).iloc[0]['env_assessed'], 0)

    def test_invalid_environment_results_are_refused(self):
        with self.assertRaisesRegex(ValueError, 'none of the region baselines'):
            build_moon_sites(walkability_predictions(), environment_results([FIRST_TILE]))
        with self.assertRaisesRegex(ValueError, 'compact'):
            legacy = pd.DataFrame({'ID': ['eda_004'], 'hard_gate_status': ['Passed'],
                                   'final_habitability_score': [57.2]})
            build_moon_sites(walkability_predictions(), legacy)
        with self.assertRaisesRegex(ValueError, 'unique ID'):
            build_moon_sites(walkability_predictions(), environment_results(['eda_004', 'eda_004']))
        with self.assertRaisesRegex(ValueError, 'missing columns'):
            build_moon_sites(walkability_predictions().drop(columns='predicted_east_west'))


if __name__ == '__main__':
    unittest.main()
