import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path[:0] = [str(Path(__file__).resolve().parents[1] / "shared"), str(Path(__file__).resolve().parents[1] / "Moon/Stage3_Requirements")]
import stage3_expanded_eda as eda


class ExpandedEDAContracts(unittest.TestCase):
    def test_local_basis_is_orthonormal(self):
        basis=np.array(eda.local_basis(35., -85.))
        np.testing.assert_allclose(basis@basis.T,np.eye(3),atol=1e-14)

    def test_angles_follow_north_clockwise_convention(self):
        east,north,up=eda.local_basis(35.,-85.)
        az,alt=eda.angles(np.array([north,east,-north,-east,up]),(east,north,up))
        np.testing.assert_allclose(az[:4],[0,90,180,270],atol=1e-12)
        np.testing.assert_allclose(alt[:4],0,atol=1e-12)
        self.assertAlmostEqual(alt[4],90.)

    def test_curved_sphere_flat_surface_is_not_flat_tangent_plane(self):
        from pyproj import Geod
        radius=1737400.;lon,lat=35.,-85.
        lon2,lat2,_=Geod(a=radius,b=radius).fwd(lon,lat,73.,20000.)
        _,alt=eda.angles(eda.cartesian(lon2,lat2,radius)-eda.cartesian(lon,lat,radius),eda.local_basis(lon,lat))
        self.assertAlmostEqual(float(alt),-np.rad2deg(20000/(2*radius)),places=9)

    def test_horizon_lookup_wraps_bearings_without_interpolation(self):
        p=pd.DataFrame({'azimuth_deg':[0,90,180,270],'horizon_deg':[1.,2.,3.,4.]})
        np.testing.assert_array_equal(eda.lookup_horizon(p,[359.,1.,91.,-90.]),[1.,1.,2.,4.])

    def test_partial_azimuth_grid_rejected(self):
        p=pd.DataFrame({'azimuth_deg':[0,90,180],'horizon_deg':[1.,2.,3.]})
        with self.assertRaises(ValueError):eda.lookup_horizon(p,[10.])

    def test_sample_runs_keep_censoring_and_sample_span(self):
        t=pd.date_range('2020-01-01',periods=6,freq='1h',tz='UTC')
        rows=eda.sampled_runs(t,[True,True,False,True,False,True])
        self.assertEqual([r['sample_span_hours'] for r in rows],[1.,0.,0.])
        self.assertTrue(rows[0]['left_censored'])
        self.assertTrue(rows[-1]['right_censored'])
        self.assertFalse(rows[1]['left_censored'])

    def test_missing_cadence_cannot_be_bridged(self):
        t=pd.DatetimeIndex(['2020-01-01T00:00Z','2020-01-01T01:00Z','2020-01-01T03:00Z'])
        with self.assertRaises(ValueError):eda.sampled_runs(t,[True]*3)

    def observations(self):
        return pd.DataFrame({'timestamp':pd.date_range('2024-01-01',periods=2,freq='5min',tz='UTC'),
            'sensor':[0,0],'channel':[0,0],'lower_energy_keV':[1000,1000],'upper_energy_keV':[2000,2000],
            'flux':[5.,8.],'strict_quality':[False,False],'finite_nonnegative':[True,True],
            'lookup_tables_matched':[False,False]})

    def test_no_qualified_exposure_stays_missing(self):
        f=self.observations();result=eda.goes_daily(f)
        self.assertTrue(pd.isna(result.supported_bin_integral.iloc[0]))
        self.assertTrue(pd.isna(result.qualified_max_flux.iloc[0]))
        self.assertEqual(result.qualified_seconds.iloc[0],0)
        self.assertEqual(result.raw_finite_median_not_quality_approved.iloc[0],6.5)

    def test_partial_supported_integral_does_not_fill_other_bins(self):
        f=self.observations();f.loc[0,'strict_quality']=True
        r=eda.goes_daily(f)
        self.assertEqual(r.supported_bin_integral.iloc[0],1500.)
        self.assertEqual(r.qualified_bins.iloc[0],1)
        self.assertEqual(r.qualified_peak_utc.iloc[0],f.timestamp.iloc[0])

    def test_duplicate_time_identity_rejected(self):
        f=self.observations();f.loc[1,'timestamp']=f.timestamp.iloc[0]
        with self.assertRaises(ValueError):eda.goes_daily(f)


if __name__=='__main__':unittest.main()
