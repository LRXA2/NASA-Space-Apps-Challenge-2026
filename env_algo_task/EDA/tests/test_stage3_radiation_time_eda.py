from pathlib import Path
import sys
import unittest
import numpy as np
import pandas as pd

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Moon/Stage3_Requirements'))
import stage3_radiation_time_eda as r


class RadiationTimeTests(unittest.TestCase):
    def test_missing_date_splits_upper_tail_segments(self):
        f=pd.DataFrame({'series_id':['x']*5,'date':pd.to_datetime(['2024-01-01','2024-01-02','2024-01-04','2024-01-05','2024-01-06'],utc=True),'daily_max':[0.,10.,11.,0.,0.]})
        thresholds,segments=r.upper_tail_segments(f,.5)
        self.assertEqual(thresholds.strictly_above_dates.item(),2)
        self.assertEqual(len(segments),2)
        self.assertEqual(segments.consecutive_high_summary_dates.max(),1)

    def test_no_data_does_not_become_zero_risk(self):
        f=pd.DataFrame({'series_id':['x'],'date':pd.to_datetime(['2024-01-01'],utc=True),'daily_max':[np.nan]})
        thresholds,segments=r.upper_tail_segments(f)
        self.assertTrue(np.isnan(thresholds.sample_daily_max_quantile.item()))
        self.assertTrue(segments.empty)

    def test_tail_threshold_is_not_operational_limit(self):
        with self.assertRaises(ValueError):r.upper_tail_segments(pd.DataFrame(),1.)
        f=r.proposals()
        self.assertTrue(f.current_outcome.eq('Unknown').all())
        self.assertTrue(f.limit_value.isna().all())

    def test_differences_require_consecutive_common_dates(self):
        dates=pd.date_range('2024-01-01',periods=40,tz='UTC').delete(20)
        f=pd.DataFrame({'series_id':'x','date':dates,'daily_median':np.arange(39.)})
        solar=f[['date','daily_median']].copy()
        summary,pairs=r.solar_association(f,solar)
        self.assertEqual(summary.iloc[0].paired_valid_dates,39)
        self.assertEqual(summary.iloc[0].consecutive_daily_difference_pairs,37)
        self.assertEqual(len(pairs),39)

    def test_duplicate_solar_dates_fail(self):
        f=pd.DataFrame({'series_id':['x'],'date':pd.to_datetime(['2024-01-01'],utc=True),'daily_median':[1.]})
        with self.assertRaises(ValueError):r.solar_association(f,pd.concat([f,f]))

    def test_sparse_or_constant_correlation_remains_unknown(self):
        self.assertTrue(np.isnan(r.correlation(pd.Series([1.,2.]),pd.Series([1.,2.]))))
        self.assertTrue(np.isnan(r.correlation(pd.Series([1.]*40),pd.Series(range(40)))))


if __name__=='__main__':unittest.main()
