from pathlib import Path
import sys
import unittest
import numpy as np
import pandas as pd

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Moon/Stage3_Requirements'))
import stage3_dust_eda as d


class DustTests(unittest.TestCase):
    def test_numerical_support_does_not_adopt_quality_or_saturation(self):
        f=pd.DataFrame({'MASS':[2.,3.,0.,2.,2.],'MASS_THRESHOLD':[1.,1.,1.,0.,1.],
                        'MASS_SIG':[0.,1.,0.,0.,-1.],'QUALITY':[1,99,0,0,0],'SATURATED':[0,3,0,0,0]})
        np.testing.assert_array_equal(d.numerical_mass_support(f),[True,True,False,False,False])

    def test_class_counts_preserve_unknowns(self):
        f=pd.DataFrame({'QUALITY':[1,1,np.nan],'SATURATED':[0,3,0]})
        out=d.class_counts(f)
        self.assertEqual(out.catalog_records.sum(),3)
        self.assertEqual(len(out),3)
        self.assertEqual(out.QUALITY.isna().sum(),1)

    def test_no_dust_limit_or_weight_is_adopted(self):
        f=d.proposals()
        self.assertTrue(f.current_outcome.eq('Unknown').all())
        self.assertTrue(f.limit_value.isna().all())
        self.assertTrue(f.preference_weight.isna().all())


if __name__=='__main__':unittest.main()
