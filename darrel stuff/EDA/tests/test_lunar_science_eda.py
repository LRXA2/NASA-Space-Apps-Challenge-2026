from pathlib import Path
import sys
import unittest

import numpy as np
import pandas as pd

sys.path[:0] = [str(Path(__file__).resolve().parents[1] / "shared"), str(Path(__file__).resolve().parents[1] / "Moon/Stage3_Requirements")]
from lunar_science_eda import derive_profiles, indicator_contract, long_indicators, plasma_reference_cases


def fixtures():
    candidates=pd.DataFrame({"candidate_id":["a","b"],"region":["south","south"]})
    rows=[]
    for cid in candidates.candidate_id:
        for variable,unit,value in [("solar_visibility","fraction",.6),("earth_visibility","fraction",.8),
                                    ("sky_view_sr","steradian",6.4),("permanent_shadow","binary",.1)]:
            rows.append(dict(candidate_id=cid,variable=variable,unit=unit,median=value,mean=value,cells=10,finite_cells=10))
    thermal=pd.DataFrame([dict(candidate_id=cid,cohort="fixed_common",supported_products=17,
                              minimum_centers_per_product=2,minimum_product_median_K=100,
                              maximum_product_median_K=150,span_of_product_medians_K=50) for cid in candidates.candidate_id])
    support=pd.DataFrame({"candidate_id":["a","b"],"expected_common_products":[17,17]})
    return candidates,pd.DataFrame(rows),thermal,support


class ScienceIndicatorTests(unittest.TestCase):
    def test_sky_is_fraction_of_4pi_and_not_clipped_at_hemisphere(self):
        p=derive_profiles(*fixtures())
        self.assertTrue(np.allclose(p.sky_visible_fraction_4pi,6.4/(4*np.pi)))
        self.assertTrue(p.sky_visible_fraction_4pi.gt(.5).all())

    def test_uv_and_photoemission_are_explicitly_shared_input_proxies(self):
        p=derive_profiles(*fixtures())
        self.assertTrue(p.uv_sun_visibility_opportunity_proxy.eq(.6).all())
        self.assertTrue(p.photoemission_opportunity_proxy.eq(.6).all())
        self.assertTrue(np.allclose(p.shadow_opportunity_proxy,.4))
        c=indicator_contract().set_index("metric")
        self.assertEqual(c.loc["uv_sun_visibility_opportunity_proxy","shared_input_family"],"solar_visibility")

    def test_partial_spatial_support_is_unknown_not_zero(self):
        c,s,t,u=fixtures();s.loc[s.variable.eq("sky_view_sr"),"finite_cells"]=9
        p=derive_profiles(c,s,t,u)
        self.assertTrue(p.sky_visible_fraction_4pi.isna().all())
        out=long_indicators(p)
        self.assertTrue(out.loc[out.metric.eq("sky_visible_fraction_4pi"),"basis"].eq("Unknown").all())

    def test_incomplete_thermal_cohort_cannot_supply_a_preference(self):
        c,s,t,u=fixtures();t["supported_products"]=16
        self.assertTrue(derive_profiles(c,s,t,u).thermal_phase_median_span_K.isna().all())

    def test_unit_mismatch_fails(self):
        c,s,t,u=fixtures();s.loc[s.variable.eq("sky_view_sr"),"unit"]="fraction"
        with self.assertRaisesRegex(ValueError,"unit"):
            derive_profiles(c,s,t,u)

    def test_invalid_solid_angle_fails(self):
        c,s,t,u=fixtures();s.loc[s.variable.eq("sky_view_sr"),"median"]=13
        with self.assertRaisesRegex(ValueError,"domain"):
            derive_profiles(c,s,t,u)

    def test_missing_required_profile_record_fails_clearly(self):
        c,s,t,u=fixtures()
        with self.assertRaisesRegex(ValueError,"disappeared"):
            derive_profiles(c,s.iloc[1:],t,u)

    def test_inconsistent_thermal_range_fails(self):
        c,s,t,u=fixtures();t["span_of_product_medians_K"]=20
        with self.assertRaisesRegex(ValueError,"range"):
            derive_profiles(c,s,t,u)

    def test_no_candidate_dose_or_voltage_invented(self):
        p=derive_profiles(*fixtures())
        self.assertFalse(any("dose" in n or "voltage" in n for n in p.columns))
        self.assertTrue(long_indicators(p).candidate_operational_conclusion.eq("Unknown").all())
        refs=plasma_reference_cases()
        self.assertTrue(refs.local_surface_potential_V.isna().all())
        self.assertTrue(refs.operational_status.eq("Unknown").all())


if __name__=="__main__":unittest.main()
