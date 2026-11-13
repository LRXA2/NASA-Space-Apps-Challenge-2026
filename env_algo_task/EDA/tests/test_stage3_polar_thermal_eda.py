from pathlib import Path
import sys
import unittest
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Moon/Stage3_Requirements'))
import stage3_polar_thermal_eda as t


class PolarThermalTests(unittest.TestCase):
    def test_triangle_area_has_explicit_km2_to_m2_conversion(self):
        np.testing.assert_allclose(t.triangle_area([[[0,0,0],[2,0,0],[0,3,0]]]),[3e6])

    def test_triangle_shape_contract(self):
        with self.assertRaises(ValueError):t.triangle_area(np.zeros((3,3)))

    def test_area_and_triangle_means_are_distinct(self):
        s=t.histogram_state([0,1,2,3]);t.add_histogram(s,[.5,2.5],[1,3]);r=t.state_row(s)
        self.assertEqual(r['triangle_weighted_mean'],1.5)
        self.assertEqual(r['facet_area_weighted_mean'],2.)
        self.assertEqual(r['supported_triangles'],2)

    def test_histogram_preserves_tails_and_quantile_intervals(self):
        s=t.histogram_state([0,1,2]);t.add_histogram(s,[-3,.5,1.5,4],[2,1,1,2])
        self.assertEqual(s['under_count'],1);self.assertEqual(s['over_area'],2)
        self.assertEqual(t.quantile_interval(s,0,True),(-3,0))
        self.assertEqual(t.quantile_interval(s,1,True),(2,4))
        self.assertEqual(t.quantile_interval(s,.5,False),(0,1))

    def test_invalid_support_remains_unknown(self):
        s=t.histogram_state([0,1]);t.add_histogram(s,[.5,np.nan,.5],[0,1,np.nan])
        self.assertEqual(s['count'],0)
        self.assertTrue(np.isnan(t.state_row(s)['facet_area_weighted_mean']))

    def test_zero_quantile_does_not_select_an_empty_leading_bin(self):
        s=t.histogram_state([0,100,200,300]);t.add_histogram(s,[150,250],[1,2])
        self.assertEqual(t.quantile_interval(s,0),(100,200))
        self.assertEqual(t.quantile_interval(s,0,True),(100,200))

    def test_no_thermal_limit_or_resource_pass_is_adopted(self):
        f=t.proposals();self.assertTrue(f.limit_value.isna().all())
        self.assertTrue(f.preference_weight.isna().all());self.assertTrue(f.current_outcome.eq('Unknown').all())


if __name__=='__main__':unittest.main()
