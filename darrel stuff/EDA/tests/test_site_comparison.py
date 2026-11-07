from pathlib import Path
import sys
import unittest

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / 'darrel stuff/EDA'), str(ROOT)]
from site_comparison import (cohort_rows, static_profiles, thermal_profiles, joint_state,
                              joint_sweep, thermal_joint_summary, rule_input_table)


def centers():
    return pd.DataFrame({'region': ['A']*3, 'clon': [1.,2.,3.], 'clat': [-85.]*3,
        'solar_visibility': [.8,.2,.8], 'earth_visibility': [.2,.8,.8], 'slope_deg': [5.,5.,20.],
        'spot_count': [1.,0.,1.], 'complete_common_cohort': [False,False,False]})


class SiteComparisonTests(unittest.TestCase):
    def test_marginal_conditions_do_not_prove_joint_observation(self):
        f = joint_sweep(centers(), [.5], [.5], [10.])
        row = f.loc[f.cohort.eq('available')].iloc[0]
        self.assertEqual(row.joint_centers, 0)
        self.assertEqual(row.solar_condition_centers, 2)
        self.assertTrue(row.marginals_exist_but_joint_absent)
        self.assertAlmostEqual(row.marginal_min_fraction_upper_bound, 2/3)

    def test_empty_fixed_cohort_is_unknown_fraction_not_zero_support_fraction(self):
        f = joint_sweep(centers(), [.5], [.5], [10.])
        row = f.loc[f.cohort.eq('fixed_common')].iloc[0]
        self.assertEqual(row.cohort_centers, 0)
        self.assertTrue(np.isnan(row.joint_observed_center_fraction))
        self.assertEqual(row.status, 'no_finite_cohort')

    def test_context_unknown_does_not_become_complement_or_pass(self):
        f = centers(); f.loc[0,'earth_visibility'] = np.nan
        result = joint_state(f,.5,.5,10.)
        self.assertTrue(pd.isna(result.iloc[0]))
        self.assertFalse(result.iloc[1])
        with self.assertRaises(ValueError):joint_state(f,2.,.5,10.)

    def test_static_profiles_are_not_phase_reweighted(self):
        f = centers()
        profile = static_profiles(f, {'solar_visibility':'fraction'})
        self.assertEqual(profile.loc[profile.cohort.eq('available'),'median'].iloc[0], .8)
        self.assertTrue(profile.loc[profile.cohort.eq('fixed_common'),'median'].isna().all())
        with self.assertRaisesRegex(ValueError,'Repeated centers'):
            static_profiles(pd.concat([f,f.iloc[[0]]]), {'solar_visibility':'fraction'})

    def test_common_product_profile_keeps_empty_cohort(self):
        r = pd.DataFrame({'region':['A','A','A'], 'common_product':[True,True,False],
                          'usable_rows':[3,3,3], 'tbol_median_K':[100.,200.,999.],
                          'fixed_common_rows':[0,0,0], 'fixed_common_tbol_median_K':[np.nan]*3})
        f = thermal_profiles(r)
        self.assertEqual(f.loc[f.cohort.eq('available'),'median_of_product_medians_K'].iloc[0], 150.)
        self.assertTrue(f.loc[f.cohort.eq('fixed_common'),'span_of_product_medians_K'].isna().all())

    def test_thermal_joint_summary_keeps_all_classes_and_products(self):
        c = centers(); c.loc[0,'earth_visibility'] = np.nan
        observations = pd.DataFrame({'clon':[1.,2.,3.], 'clat':[-85.]*3,
            'source_product':['P1']*3,'tbol':[100.,200.,300.], 'usable':[True]*3,
            'complete_common_cohort':[False]*3})
        f = thermal_joint_summary(observations,c,['P1','P2'],(.5,.5,10.))
        self.assertEqual(len(f),3*2*3)
        a=f.loc[f.cohort.eq('available') & f.source_product.eq('P1')]
        self.assertEqual(a.usable_rows.sum(),3)
        self.assertEqual(a.loc[a.condition_class.eq('unknown_context'),'usable_rows'].iloc[0],1)
        self.assertTrue(f.loc[f.source_product.eq('P2'),'tbol_median_K'].isna().all())

    def test_unmatched_or_duplicate_thermal_center_fails(self):
        c = centers()
        o = pd.DataFrame({'clon':[4.], 'clat':[-85.], 'source_product':['P1'],
            'tbol':[100.], 'usable':[True], 'complete_common_cohort':[False]})
        with self.assertRaisesRegex(ValueError,'absent'):
            thermal_joint_summary(o,c,['P1'],(.5,.5,10.))
        o['clon']=1.
        with self.assertRaisesRegex(ValueError,'Repeated'):
            thermal_joint_summary(pd.concat([o,o]),c,['P1'],(.5,.5,10.))

    def test_rule_inputs_have_values_but_no_invented_policy_scores(self):
        p=static_profiles(centers(), {'solar_visibility':'fraction','earth_visibility':'fraction','slope_deg':'degree'})
        f=rule_input_table(p)
        self.assertEqual(len(f),3)
        self.assertTrue(f.value.notna().all())
        self.assertTrue(f.preference_score.isna().all())
        self.assertTrue(f.requirement_status.eq('Unknown').all())
        self.assertTrue(f.rule_classification.eq('Unconfigured').all())


if __name__=='__main__':unittest.main()
