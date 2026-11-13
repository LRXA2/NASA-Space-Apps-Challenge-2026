from pathlib import Path
import sys
import unittest
import numpy as np
import pandas as pd

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Moon/Stage3_Requirements'))
import stage3_neutron_eda as n


class NeutronTests(unittest.TestCase):
    def test_raw_rate_does_not_divide_by_zero_or_accept_bad_support(self):
        np.testing.assert_allclose(n.raw_rate([4,4,4,4],[2,0,np.nan,1],[True,True,True,False]),[2,np.nan,np.nan,np.nan],equal_nan=True)

    def test_observed_zero_is_not_unknown(self):
        d=n.daily_record('x',pd.Timestamp('2024-01-01',tz='UTC'),[0,np.nan],2)
        self.assertEqual(d['valid_samples'],1);self.assertEqual(d['daily_max'],0)
        self.assertTrue(np.isnan(d['valid_seconds']))

    def test_no_coverage_has_no_zero_fallback(self):
        d=n.daily_record('x',pd.Timestamp('2024-01-01',tz='UTC'),[],0)
        self.assertTrue(np.isnan(d['daily_max']));self.assertEqual(d['valid_samples'],0)

    def test_missing_dates_split_zero_state_runs(self):
        f=pd.DataFrame({'series_id':['x']*3,'date':pd.to_datetime(['2024-01-01','2024-01-02','2024-01-04'],utc=True),
                        'daily_max':[0.,0.,0.],'valid_samples':[1,1,1]})
        s=n.zero_state_summary(f).iloc[0]
        self.assertEqual(s.all_supported_values_zero_dates,3)
        self.assertEqual(s.longest_consecutive_observed_zero_dates,2)
        self.assertFalse(s.science_response_qualified)

    def test_zero_median_with_positive_max_is_not_all_zero(self):
        f=pd.DataFrame({'series_id':['x'],'date':pd.to_datetime(['2024-01-01'],utc=True),'daily_max':[1.],'valid_samples':[5]})
        self.assertEqual(n.zero_state_summary(f).all_supported_values_zero_dates.item(),0)

    def test_resource_dependency_is_conditional_and_limits_unadopted(self):
        f=n.proposals();self.assertTrue(f.current_outcome.eq('Unknown').all())
        self.assertTrue(f.limit_value.isna().all());self.assertTrue(f.preference_weight.isna().all())
        self.assertIn('Only mandatory',f.loc[f.id.eq('NE-H02'),'decision_logic'].item())


if __name__=='__main__':unittest.main()
