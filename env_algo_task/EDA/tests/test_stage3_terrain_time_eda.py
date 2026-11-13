from pathlib import Path
import sys
import unittest
import numpy as np
import pandas as pd

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Moon/Stage3_Requirements'))
import stage3_terrain_time_eda as t


def frame(states,start='2020-02-01T00:00:00Z'):
    return pd.DataFrame({'utc':pd.date_range(start,periods=len(states),freq='h'),
                         'center_blocked_by_sampled_terrain':states,'clearance_deg':np.where(states,-1.,1.)})


class TerrainTimeTests(unittest.TestCase):
    def test_equal_visibility_fraction_can_have_different_observed_spans(self):
        a=t.period_geometry(frame([1,1,0,0,1,1,0,0]),['month'],60).iloc[0]
        b=t.period_geometry(frame([1,1,1,1,0,0,0,0]),['month'],60).iloc[0]
        self.assertEqual(a.sampled_blocked_fraction,b.sampled_blocked_fraction)
        self.assertEqual(a.longest_observed_blocked_sample_span_hours,1.)
        self.assertEqual(b.longest_observed_blocked_sample_span_hours,3.)

    def test_full_leap_month_denominator_and_partial_window(self):
        f=t.period_geometry(frame([1,1,0,0]),['month'],60).iloc[0]
        self.assertEqual(f.expected_calendar_samples,29*24)
        self.assertTrue(f.partial_source_span_period)

    def test_period_boundary_censoring_and_isolated_blocked_sample(self):
        f=t.period_geometry(frame([1,1,1],start='2020-01-31T22:00:00Z'),['month'],60)
        feb=f.loc[f.period.eq('2020-02')].iloc[0]
        self.assertEqual(feb.observed_blocked_run_count,1)
        self.assertEqual(feb.longest_observed_blocked_sample_span_hours,0.)
        self.assertEqual(feb.left_censored_runs,1)

    def test_irregular_cadence_is_not_bridged(self):
        f=frame([1,1,1]);f.loc[1,'utc']+=pd.Timedelta(minutes=1)
        with self.assertRaises(ValueError):t.period_geometry(f,['month'],60)

    def test_unknown_blocking_cannot_become_clear(self):
        f=frame([True,True]);f['center_blocked_by_sampled_terrain']=pd.array([True,None],dtype='boolean')
        with self.assertRaises(ValueError):t.period_geometry(f,['month'],60)

    def test_calendar_groups_have_declared_meaning(self):
        f=t.period_geometry(frame([False]*48),['calendar_season','two_year','half_year'],60)
        self.assertEqual(set(f.period_kind),{'calendar_season','two_year','half_year'})
        self.assertTrue(f.meaning.str.contains('NOT guaranteed').all())

    def test_operational_limits_and_preference_weights_are_not_invented(self):
        f=t.proposals();self.assertTrue(f.limit_value.isna().all());self.assertTrue(f.preference_weight.isna().all())
        self.assertTrue(f.current_outcome.eq('Unknown').all())


if __name__=='__main__':unittest.main()
