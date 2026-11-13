"""Full-cohort plasma comparisons preserve quality, identity and uncertainty."""
from pathlib import Path
import sys,json
import unittest
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Moon/Stage3_Requirements'))
import stage3_plasma_eda as a


class PlasmaTests(unittest.TestCase):
    def test_pairing_does_not_fill_unmatched_or_unsupported_dates(self):
        f=pd.DataFrame({'series_id':['a','a','b','b'],'date':pd.to_datetime(['2024-01-01','2024-01-02','2024-01-01','2024-01-03'],utc=True),
            'daily_median':[2,9,1,10],'valid_samples':[10]*4})
        pair,summary=a.paired_daily(f,'a','b','test')
        self.assertEqual(len(pair),1);self.assertEqual(pair.positive_value_ratio.iloc[0],2)
        self.assertTrue(np.isnan(summary['spearman_descriptive']))

    def test_zero_ratio_denominator_remains_unknown(self):
        f=pd.DataFrame({'series_id':['a','b'],'date':pd.to_datetime(['2024-01-01']*2,utc=True),'daily_median':[2,0],'valid_samples':[1,1]})
        pair,_=a.paired_daily(f,'a','b','test')
        self.assertTrue(np.isnan(pair.positive_value_ratio.iloc[0]))

    def test_screening_support_changes_are_visible(self):
        f=pd.DataFrame({'series_id':['ESA_v01_x'],'date':pd.to_datetime(['2024-01-01'],utc=True),
            'daily_median':[1.],'daily_max':[2.],'daily_p95':[1.9],'recorded_samples':[10],'valid_samples':[9]})
        altered=f.copy();altered['daily_median']=np.nan
        check=a.screening_crosscheck(altered,f)
        self.assertEqual(check.loc[check.quantity.eq('daily_median'),'support_changed_rows'].item(),1)

    def test_default_and_full_selection_are_explicit_options(self):
        import inspect
        sig=inspect.signature(a.acquired.esa)
        self.assertFalse(sig.parameters['all_files'].default)
        self.assertFalse(sig.parameters['flag_diagnostics'].default)

    def test_quality_counts_are_records_not_elapsed_seconds(self):
        d=pd.DataFrame({'file':['thb_l2_esa_20240101_v01.cdf'],'mode':['peir'],'recorded':[10],
            'quality_zero':[2],'ambiguous_or_missing_clock_records':[1],'outside_nominal_day':[0],'median_spacing_s':[4.],
            'quality_flag_counts_in_nominal_day':[json.dumps({'0':2,'8':8})]})
        days,flags,years=a.quality_tables(d)
        self.assertEqual(days.quality_zero_fraction.iloc[0],.2)
        self.assertEqual(flags.records.sum(),10)
        self.assertEqual(years.pooled_record_good_fraction.iloc[0],.2)
        self.assertIn('not elapsed',years.interpretation.iloc[0])

    def test_no_potential_or_density_safety_limit_is_adopted(self):
        f=a.proposals();self.assertTrue(f.current_outcome.eq('Unknown').all())
        self.assertTrue(f.limit_value.isna().all());self.assertTrue(f.preference_weight.isna().all())
        self.assertTrue(f.status.str.contains('not consumed').all())


if __name__=='__main__':unittest.main()
