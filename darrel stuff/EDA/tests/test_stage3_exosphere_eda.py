from pathlib import Path
import sys
import unittest
import numpy as np
import pandas as pd

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Moon/Stage3_Requirements'))
import stage3_exosphere_eda as e


class ExosphereTests(unittest.TestCase):
    def test_invalid_clock_is_retained_as_unknown(self):
        f=pd.DataFrame({'Year':[2013]*3,'Month':[12]*3,'Day':[1,1,32],'Hours':[0,24,0],'Minutes':[0]*3,'Seconds':[.5]*3})
        d=e.native_dates(f)
        self.assertEqual(d[0],pd.Timestamp('2013-12-01T00:00:00.5Z'))
        self.assertTrue(d[1:].isna().all())

    def test_negative_estimates_are_not_zero_filled(self):
        f=pd.DataFrame({'value':[-1,2,3,4],'std':[1,-1,np.nan,0]})
        np.testing.assert_array_equal(e.abundance_support(f,[True]*4),[True,False,False,True])

    def test_noncanonical_second_is_an_explicit_policy_difference_not_failed_replay(self):
        f=pd.DataFrame({'Year':[2014],'Month':[1],'Day':[31],'Hours':[21],'Minutes':[0],'Seconds':[60.]})
        self.assertTrue(e.native_dates(f).isna().all())
        self.assertEqual(e.original_archive_dates(f)[0],pd.Timestamp('2014-01-31T21:01:00Z'))

    def test_missing_geometry_does_not_replace_abundance_support(self):
        f=pd.DataFrame({'altitude':[10,-1,np.nan],'local_hour':[24,23,np.nan],'latitude':[-90,90,91]})
        b=e.geometry_bins(f)
        self.assertFalse(pd.isna(b.local_solar_hour_bin.iloc[0]))
        self.assertTrue(b.altitude_bin_km.iloc[1:].isna().all())
        self.assertTrue(pd.isna(b.latitude_bin_deg.iloc[2]))

    def test_strata_report_missing_geometry(self):
        f=pd.DataFrame({'species':['Ar']*2,'altitude':[10,np.nan],'latitude':[0,np.nan],
                        'local_hour':[1,np.nan],'value':[-1,2],'std':[1,1],'supported':[True,True],
                        'date':pd.to_datetime(['2013-12-01','2013-12-01'],utc=True)})
        s=e.stratum_summary(e.geometry_bins(f),['species','altitude_bin_km'])
        self.assertEqual(s.recorded.sum(),2);self.assertEqual(s.negative_supported_estimates.sum(),1)

    def test_proposals_do_not_adopt_concentrations_as_limits(self):
        f=e.proposals();self.assertTrue(f.current_outcome.eq('Unknown').all())
        self.assertTrue(f.limit_value.isna().all());self.assertTrue(f.preference_weight.isna().all())


if __name__=='__main__':unittest.main()
