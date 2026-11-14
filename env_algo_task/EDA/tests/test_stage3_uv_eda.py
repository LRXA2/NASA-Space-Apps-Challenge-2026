"""Spectral support, uncertainty and native-map streaming contracts."""
from pathlib import Path
import sys
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Moon/Stage3_Requirements'))
import stage3_uv_eda as a


class UVTests(unittest.TestCase):
    def test_integral_and_uncertainty_assumptions_are_distinct(self):
        w=np.arange(115.5,180);r=a.band_metrics(w,np.ones(65)*2,np.ones(65)*.1,115,180)
        self.assertEqual(r['integral_W_m2'],130)
        self.assertAlmostEqual(r['absolute_error_sum_bound_W_m2'],13)
        self.assertAlmostEqual(r['rss_error_if_independent_W_m2'],.2*np.sqrt(65))

    def test_model_partition_does_not_mark_every_EGS_bin_observed(self):
        self.assertEqual(a.model_assisted_bins([26.5,100.5,115.5,121.5,128.5,150.5]).tolist(),[True,False,True,False,True,False])

    def test_zero_bin_withholds_full_band_instead_of_partial_sum(self):
        w=np.arange(115.5,180);x=np.ones(65);x[0]=0
        r=a.band_metrics(w,x,np.ones(65),115,180)
        self.assertFalse(r['complete_positive_band']);self.assertTrue(np.isnan(r['integral_W_m2']))

    def test_streaming_mean_and_histogram_match_direct_counts(self):
        state=a.hist_state([0,1,2,3]);a.hist_add(state,[0,.5,1.5]);a.hist_add(state,[2.5,3,np.nan])
        self.assertEqual(state['hist'].tolist(),[2,1,2]);self.assertEqual(state['count'],5)
        self.assertEqual(a.hist_row(state)['mean'],1.5)
        self.assertEqual(a.quantile_bounds(state,.5),(1,2))

    def test_histogram_tails_are_not_silently_clipped(self):
        state=a.hist_state([0,1]);a.hist_add(state,[-5,-3,2,4])
        self.assertEqual(state['under'],2);self.assertEqual(state['over'],2)
        self.assertEqual(a.quantile_bounds(state,0),(-5,0));self.assertEqual(a.quantile_bounds(state,1),(1,4))

    def test_empty_region_is_unknown_not_zero_reflectance(self):
        r=a.hist_row(a.hist_state([0,1]));self.assertEqual(r['finite_pixels'],0)
        self.assertTrue(np.isnan(r['mean']));self.assertTrue(np.isnan(r['p50_hist_lower']))

    def test_stage4_proposals_do_not_adopt_limits_or_weights(self):
        f=a.uv_proposals();self.assertTrue(f.limit_value.isna().all());self.assertTrue(f.preference_weight.isna().all())
        self.assertTrue(f.limit_state.eq('not_adopted').all());self.assertIn('UV-H01',set(f.id))
        self.assertTrue(f.status.str.contains('not loaded by pipeline').all())


if __name__=='__main__':unittest.main()
