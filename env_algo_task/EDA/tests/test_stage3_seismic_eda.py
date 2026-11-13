from pathlib import Path
import sys
import unittest
import numpy as np
from obspy import Trace,Inventory

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Moon/Stage3_Requirements'))
import stage3_seismic_eda as s


class SeismicTests(unittest.TestCase):
    def test_missing_codes_do_not_enter_raw_statistics(self):
        d=s.raw_statistics([-1,np.nan,1.,3.]);self.assertEqual(d['samples'],4)
        self.assertEqual(d['valid_samples'],2);self.assertEqual(d['raw_median'],2.)
        self.assertEqual(d['demeaned_rms_counts'],1.)

    def test_no_data_is_not_quiet_motion(self):
        d=s.raw_statistics([-1,np.nan]);self.assertTrue(np.isnan(d['demeaned_rms_counts']))
        self.assertTrue(np.isnan(d['maximum_absolute_deviation_counts']))

    def test_response_window_never_bridges_a_gap(self):
        self.assertEqual(s.first_valid_window([1,2,-1,3,4,5,6],4),3)
        self.assertIsNone(s.first_valid_window([1,2,-1,3,4],3))

    def test_fully_valid_short_or_empty_window_support(self):
        self.assertEqual(s.first_valid_window([1,2,3],3),0)
        self.assertIsNone(s.first_valid_window([],2))
        with self.assertRaises(ValueError):s.first_valid_window([1],1)

    def test_archive_date_and_monthly_mode_cohort(self):
        entries=[{'url':n,'relative_path':n} for n in ['xa.s12.00.mh1.1973.001.0.mseed','xa.s12.00.mh1.1973.002.0.mseed','xa.s12.00.mh1.1973.031.0.mseed','xa.s12.01.mh1.1973.002.0.mseed']]
        chosen=s.response_cohort(entries);self.assertEqual(len(chosen),3)
        self.assertNotIn(entries[1]['url'],chosen)
        self.assertEqual(s.archive_day(entries[0]['url']).year,1973)

    def test_missing_response_metadata_remains_explicit_unknown(self):
        t=Trace(data=np.ones(16));t.stats.network='XA';t.stats.station='S12';t.stats.channel='MH1';t.stats.location='00'
        metadata=s.channel_metadata(Inventory([],source='test'),t)
        self.assertTrue(metadata['response_status'].startswith('Unknown'))
        rows,psd=s.response_experiment(t,Inventory([],source='test'),metadata)
        self.assertTrue(rows[0]['experiment_status'].startswith('Unknown'));self.assertEqual(psd,[])

    def test_no_structural_limit_or_raw_count_safety_weight_is_adopted(self):
        f=s.proposals();self.assertTrue(f.current_outcome.eq('Unknown').all())
        self.assertTrue(f.limit_value.isna().all());self.assertTrue(f.preference_weight.isna().all())


if __name__=='__main__':unittest.main()
