"""Checks for the pipeline runner; the real Haworth run is opt-in (RUN_PIPELINE_SMOKE=1)."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from integration.moon_sites import build_moon_sites
from integration.run_all import (DEFAULT_CONFIG, PipelineConfig, load_config, region_summary, run_all,
                                 score_environment, select_regions)
from integration.tests.test_moon_sites import environment_results, walkability_predictions
from notebooks.shared.tests.test_moon_tiles import REGION

REGIONS = ['A3CLR22_10_Leibnitz_Beta_Plateau', 'A3CLR22_2_Haworth', 'A3CLR22_4_deGerlache_Rim_2']


class RunAllTests(unittest.TestCase):
    def test_short_region_names_resolve_to_full_ids(self):
        self.assertEqual(select_regions(REGIONS, None), sorted(REGIONS))
        self.assertEqual(select_regions(REGIONS, ('haworth', 'A3CLR22_4_deGerlache_Rim_2')),
                         ['A3CLR22_2_Haworth', 'A3CLR22_4_deGerlache_Rim_2'])
        with self.assertRaisesRegex(ValueError, 'matches nothing'):
            select_regions(REGIONS, ('Malapert',))

    def test_config_file_and_overrides(self):
        config = load_config(DEFAULT_CONFIG)
        self.assertIsNone(config.regions)
        self.assertTrue((ROOT / config.environment_input).is_file())
        self.assertEqual(load_config(DEFAULT_CONFIG, regions=['Haworth'], top_k_per_site=5).regions, ('Haworth',))
        with self.assertRaisesRegex(ValueError, 'positive integer'):
            PipelineConfig(terrain_run='x', top_k_per_site=0)
        self.assertEqual(config.environment_scope, 'tile')
        self.assertEqual(load_config(DEFAULT_CONFIG, environment_scope='region').environment_scope, 'region')
        with self.assertRaisesRegex(ValueError, 'environment_scope'):
            PipelineConfig(terrain_run='x', environment_scope='site')
        with self.assertRaisesRegex(ValueError, 'needs environment_input'):
            PipelineConfig(terrain_run='x', environment_config='config.yml')

    def test_environment_scorer_writes_compact_output(self):
        config = load_config(DEFAULT_CONFIG)
        with tempfile.TemporaryDirectory() as folder:
            output = score_environment(ROOT, config, Path(folder) / 'environment.csv')
            frame = pd.read_csv(output)
        self.assertEqual(len(frame), 83)
        self.assertTrue({'ID', 'operations_score', 'survival_score'} <= set(frame.columns))
        self.assertIsNone(score_environment(ROOT, PipelineConfig(terrain_run='x'), Path('unused.csv')))

    def test_environment_scorer_failure_is_reported(self):
        config = PipelineConfig(terrain_run='x', environment_input='missing/sites.csv')
        with tempfile.TemporaryDirectory() as folder, self.assertRaisesRegex(RuntimeError, 'scorer failed'):
            score_environment(ROOT, config, Path(folder) / 'environment.csv')

    def test_region_summary_counts_best_earth_sites(self):
        sites = build_moon_sites(walkability_predictions(), environment_results(['eda_004']))
        tiles = sites['tile_id'].tolist()
        matches = pd.DataFrame({'tile_id': tiles * 2, 'overall_rank': [1] * 4 + [2] * 4,
                                'earth_region': ['wadi_rum', 'wadi_rum', 'death_valley', 'wadi_rum'] + ['x'] * 4,
                                'cosine_similarity': [0.9, 0.8, 0.7, 0.6] + [0.1] * 4})
        row = region_summary(sites, matches).iloc[0]
        self.assertEqual(row['region'], REGION)
        self.assertEqual((row['tiles_matched'], row['best_site_wadi_rum'], row['best_site_death_valley']), (4, 3, 1))
        self.assertAlmostEqual(row['median_best_cosine'], 0.75)
        self.assertNotIn('best_site_x', row.index)

    @unittest.skipUnless(os.environ.get('RUN_PIPELINE_SMOKE') == '1', 'set RUN_PIPELINE_SMOKE=1 with processed data')
    def test_haworth_end_to_end(self):
        run = run_all(ROOT, load_config(DEFAULT_CONFIG, regions=['Haworth']))
        summary = json.loads((run / 'summary.json').read_text())
        self.assertEqual(summary['regions'], ['A3CLR22_2_Haworth'])
        self.assertEqual(summary['tiles'], summary['tiles_matched'])
        self.assertEqual(summary['environment_assessed_tiles'], summary['tiles'])
        sites, matches = pd.read_csv(run / 'moon_sites.csv'), pd.read_csv(run / 'earth_matches.csv')
        self.assertTrue(sites['tile_id'].is_unique)
        self.assertEqual(set(matches['tile_id']), set(sites['tile_id']))
        self.assertEqual(len(matches), len(sites) * len(summary['earth_sites']) * summary['top_k_per_site'])


if __name__ == '__main__':
    unittest.main()
