"""Calendar comparisons must retain UTC, edge periods, missingness and meaning."""
from pathlib import Path
import sys
import unittest
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'shared'))
from environment_time import bucket_bounds,calendar_summary,longest_true,fixed_month_comparison


def daily():
    return pd.DataFrame({'series_id':['x']*3,'date':pd.to_datetime(['2024-01-01','2024-01-03','2024-03-01'],utc=True),
        'daily_median':[2.,10.,np.nan],'daily_max':[7.,50.,np.nan],
        'recorded_samples':[100,1,8],'valid_samples':[100,1,0]})


class TimeTests(unittest.TestCase):
    def test_DJF_uses_year_of_january_not_december(self):
        start,stop,label=bucket_bounds('2023-12-12','calendar_season')
        self.assertEqual(label,'2024-DJF');self.assertEqual(start,pd.Timestamp('2023-12-01',tz='UTC'))
        self.assertEqual(stop,pd.Timestamp('2024-03-01',tz='UTC'))
        self.assertEqual(bucket_bounds('2024-02-29','calendar_season'),(start,stop,label))

    def test_two_year_and_half_year_are_distinct(self):
        self.assertEqual(bucket_bounds('2025-08-01','two_year')[2],'2024-2025')
        self.assertEqual(bucket_bounds('2025-08-01','half_year')[2],'2025-H2')

    def test_historical_two_year_anchor_supports_1971(self):
        self.assertEqual(bucket_bounds('1971-08-01','two_year')[2],'1970-1971')

    def test_quarter_and_four_month_term_are_not_confused(self):
        self.assertEqual(bucket_bounds('2024-04-01','quarter')[2],'2024Q2')
        self.assertEqual(bucket_bounds('2024-04-01','four_month_term')[2],'2024-T4M1')

    def test_timezone_is_converted_to_UTC_before_binning(self):
        self.assertEqual(bucket_bounds('2024-01-01T00:30:00+08:00','month')[2],'2023-12')

    def test_missing_kind_or_timestamp_fails(self):
        with self.assertRaises(ValueError):bucket_bounds('2024-01-01','lunar_season')
        with self.assertRaises(ValueError):bucket_bounds(pd.NaT,'month')

    def test_empty_month_and_leap_denominator_are_preserved(self):
        f=calendar_summary(daily(),['month'])
        feb=f.loc[f.period.eq('2024-02')].iloc[0]
        self.assertEqual(feb.expected_calendar_days,29);self.assertEqual(feb.valid_days,0)
        self.assertTrue(np.isnan(feb.median_of_daily_values));self.assertEqual(feb.longest_unsupported_date_run_days,29)

    def test_equal_weight_per_day_not_number_of_samples(self):
        jan=calendar_summary(daily(),['month']).iloc[0]
        self.assertEqual(jan.median_of_daily_values,6);self.assertEqual(jan.recorded_samples,101)
        self.assertEqual(jan.maximum_of_reported_daily_maxima,50)

    def test_longest_gap_keeps_partial_edge_periods(self):
        jan=calendar_summary(daily(),['month']).iloc[0]
        self.assertEqual(jan.longest_absent_date_run_days,28)
        self.assertEqual(jan.valid_day_fraction,2/31)
        march=calendar_summary(daily(),['month']).iloc[-1]
        self.assertTrue(march.partial_source_span_period)
        self.assertEqual(march.days_inside_observed_source_span,1)

    def test_duplicate_daily_identity_fails(self):
        with self.assertRaises(ValueError):calendar_summary(pd.concat([daily(),daily().head(1)]))

    def test_intraday_values_require_explicit_daily_aggregation(self):
        f=daily();f.loc[0,'date']+=pd.Timedelta(hours=1)
        with self.assertRaises(ValueError):calendar_summary(f)

    def test_valid_count_cannot_exceed_recorded_count(self):
        f=daily();f.loc[0,'valid_samples']=101
        with self.assertRaises(ValueError):calendar_summary(f)

    def test_calendar_windows_are_not_claimed_as_lunar_seasons(self):
        f=calendar_summary(daily())
        self.assertEqual(set(f.period_kind),{'month','quarter','four_month_term','half_year','year','two_year','calendar_season'})
        self.assertTrue(f.interpretation.str.contains('not lunar seasons').all())

    def test_fixed_month_comparison_keeps_record_support(self):
        f=fixed_month_comparison(daily(),1,3).iloc[0]
        self.assertEqual(f.expected_days,91);self.assertEqual(f.valid_days,2);self.assertEqual(f.median_daily_value,6)

    def test_longest_true_handles_empty_and_endpoints(self):
        self.assertEqual(longest_true([]),0);self.assertEqual(longest_true([1,1,0,1]),2)


if __name__=='__main__':unittest.main()
