"""Independent examples protect fair cohorts and regional weighting."""

import unittest

import pandas as pd

from notebooks.modeling.terrain_similarity.model_comparison import (
    align_common_locations,
    summarize_comparison,
)


class ModelComparisonTests(unittest.TestCase):
    def test_views_align_by_location_instead_of_row_or_view_specific_patch_id(self):
        full = pd.DataFrame([
            ('full-b', 'b', 'moon', 'rim', 'holdout'),
            ('full-only', 'c', 'moon', 'rim', 'holdout'),
            ('earth-a', 'a', 'earth', 'desert', 'train'),
        ], columns=pd.Index(['patch_id', 'location_id', 'body', 'region', 'fold']))
        strict = pd.DataFrame([
            ('earth-a', 'a', 'earth', 'desert', 'train'),
            ('strict-b', 'b', 'moon', 'rim', 'holdout'),
        ], columns=full.columns)
        result = align_common_locations({'full': full, 'strict': strict})
        self.assertEqual(result['full'].patch_id.tolist(), ['earth-a', 'full-b'])
        self.assertEqual(result['strict'].patch_id.tolist(), ['earth-a', 'strict-b'])
        self.assertEqual(result['full'].location_id.tolist(), ['a', 'b'])
        self.assertEqual(full.patch_id.tolist(), ['full-b', 'full-only', 'earth-a'])

    def test_regions_get_equal_weight_and_unavailable_queries_stay_in_denominator(self):
        # Region A has three hits with errors 2, 4, 6; region B has no available
        # match and error 20. Regional averaging gives 50% hits and 12 m error,
        # not the query-pooled 75% and 8 m, nor conditional-only 100%.
        rows = []
        for query, region, hit, error in [('a1', 'A', 1, 2), ('a2', 'A', 1, 4),
                                           ('a3', 'A', 1, 6), ('b1', 'B', 0, 20)]:
            rows.append({
                'method': 'cnn', 'direction': 'moon_to_earth', 'case': 'both_heldout',
                'threshold': 'nominal', 'query_id': query, 'query_region': region,
                'available': hit, 'top1_hit': hit, 'top5_hit': hit,
                'top1_relief_error_m': error, 'top1_slope_error_deg': 1.,
                'top1_local_sd_error_m': 2.,
            })
        regional, macro = summarize_comparison(pd.DataFrame(rows))
        self.assertEqual(len(regional), 2)
        self.assertEqual(macro.iloc[0].top5_hit, .5)
        self.assertEqual(macro.iloc[0].available, .5)
        self.assertEqual(macro.iloc[0].top1_relief_error_m, 12.)
        self.assertEqual(macro.iloc[0].query_count, 4)
        self.assertEqual(macro.iloc[0].query_region_count, 2)

    def test_ambiguous_locations_or_disagreeing_splits_are_rejected(self):
        full = pd.DataFrame([('p', 'here', 'moon', 'rim', 'train')],
                            columns=pd.Index(['patch_id', 'location_id', 'body', 'region', 'fold']))
        for other in [pd.concat([full, full]), full.assign(fold='holdout'),
                      full.assign(location_id='elsewhere')]:
            with self.subTest(other=other.to_dict('records')), self.assertRaises(ValueError):
                align_common_locations({'full': full, 'other': other})

    def test_missing_or_duplicate_results_cannot_silently_change_denominators(self):
        row = {
            'method': 'cnn', 'direction': 'moon_to_earth', 'case': 'both_heldout',
            'threshold': 'nominal', 'query_id': 'q', 'query_region': 'rim',
            'available': 1., 'top1_hit': 0., 'top5_hit': 1.,
            'top1_relief_error_m': 12., 'top1_slope_error_deg': 2., 'top1_local_sd_error_m': 3.,
        }
        for frame in [pd.DataFrame([row, row]), pd.DataFrame([row]).assign(top5_hit=float('nan')),
                      pd.DataFrame([row]).assign(available=0.)]:
            with self.subTest(frame=frame.to_dict('records')), self.assertRaises(ValueError):
                summarize_comparison(frame)


if __name__ == '__main__':
    unittest.main()
