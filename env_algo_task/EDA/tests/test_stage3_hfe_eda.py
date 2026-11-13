from pathlib import Path
import sys
import unittest
import numpy as np
import pandas as pd

SUBJECT=Path(__file__).resolve().parents[1]/'Moon/Stage3_Requirements'
sys.path.insert(0,str(SUBJECT))
import stage3_hfe_eda as h


class HFETests(unittest.TestCase):
    def test_signed_difference_reconstructs_upper_lower(self):
        a,b=h.bridge_values(np.array([250.,250.]),np.array([4.,-4.]))
        np.testing.assert_array_equal(a,[248.,252.])
        np.testing.assert_array_equal(b,[252.,248.])
        np.testing.assert_array_equal(b-a,[4.,-4.])

    def test_bitmask_counts_overlapping_features_not_categories(self):
        f=pd.DataFrame(h.flag_counts([0,1,12,1024,np.nan,16384]))
        self.assertEqual(f.loc[f.bit.eq(4),'records'].item(),1)
        self.assertEqual(f.loc[f.bit.eq(8),'records'].item(),1)
        self.assertEqual(f.loc[f.bit.eq(-1),'records'].item(),1)
        self.assertEqual(f.loc[f.bit.eq(-2),'records'].item(),1)

    def test_depth_source_preserves_above_surface_and_probe_identity(self):
        text=(h.LOCAL/'data/moon/eda_support/D28/bundle_documentation.md').read_text()
        d=h.depths_from_document(text)
        self.assertEqual(len(d),48)
        self.assertEqual(d['a15','p2','TG11A']['depth_cm'],-6)
        self.assertEqual(d['a17','p2','TG12B']['depth_cm'],234)
        self.assertTrue(np.isnan(d['a15','p1','TC13']['depth_cm']))

    def test_depth_contract_changes_fail_clearly(self):
        with self.assertRaises(ValueError):h.depths_from_document('No sensor table')

    def test_proposed_thermal_limits_are_not_adopted(self):
        f=h.proposals()
        self.assertTrue(f.current_outcome.eq('Unknown').all())
        self.assertTrue(f.limit_value.isna().all())
        self.assertTrue(f.preference_weight.isna().all())


if __name__=='__main__':unittest.main()
