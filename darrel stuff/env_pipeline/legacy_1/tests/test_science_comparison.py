from pathlib import Path
import sys
import unittest

import numpy as np
import pandas as pd

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import environment_engine
from science_comparison import compare, pareto_fronts, operational_unknowns, align_profiles


def objective(metric,direction="lower"):
    return {"metric":metric,"direction":direction}


class SciencePreferenceTests(unittest.TestCase):
    def test_unassociated_candidates_are_unknown_without_geographic_substitution(self):
        source=pd.DataFrame({"candidate_id":["known"],"region":["south"],"sky_visible_fraction_4pi":[.5]})
        candidates=pd.DataFrame({"candidate_id":["known","other"],"region":["south","elsewhere"]})
        f=align_profiles(candidates,source).set_index("candidate_id")
        self.assertEqual(f.loc["known","sky_visible_fraction_4pi"],.5)
        self.assertTrue(np.isnan(f.loc["other","sky_visible_fraction_4pi"]))
        self.assertEqual(f.loc["other","science_profile_status"],"Unknown_no_associated_source_profile")

    def test_reusing_an_id_for_a_different_region_fails(self):
        source=pd.DataFrame({"candidate_id":["known"],"region":["south"],"sky_visible_fraction_4pi":[.5]})
        with self.assertRaisesRegex(ValueError,"regions"):
            align_profiles(pd.DataFrame({"candidate_id":["known"],"region":["north"]}),source)

    def test_lower_and_higher_preferences_are_applied(self):
        frame=pd.DataFrame({"candidate_id":["a","b","c"],"exposure":[1,2,1],"contact":[.9,.8,.9]})
        fronts,pairs=pareto_fronts(frame,[objective("exposure"),objective("contact","higher")])
        self.assertEqual(fronts,{"a":1,"c":1,"b":2})
        self.assertEqual(set(pairs.dominated_candidate_id),{"b"})

    def test_tradeoffs_do_not_become_arbitrary_composite_weights(self):
        frame=pd.DataFrame({"candidate_id":["a","b"],"exposure":[1,2],"contact":[.5,.9]})
        fronts,_=pareto_fronts(frame,[objective("exposure"),objective("contact","higher")])
        self.assertEqual(fronts,{"a":1,"b":1})

    def test_unknown_cannot_enter_front(self):
        with self.assertRaisesRegex(ValueError,"Unknown"):
            pareto_fronts(pd.DataFrame({"candidate_id":["a"],"x":[np.nan]}),[objective("x")])

    def test_duplicate_objectives_are_rejected(self):
        with self.assertRaisesRegex(ValueError,"Unique"):
            pareto_fronts(pd.DataFrame({"candidate_id":["a"],"x":[1]}),[objective("x"),objective("x")])

    def test_live_context_gates_and_missing_objectives_are_preserved(self):
        p=pd.DataFrame({"candidate_id":["a","b","c","d"],"region":["r"]*4,"sky_visible_fraction_4pi":[.4,.3,np.nan,.5]})
        ranking=pd.DataFrame({"candidate_id":["a","b","c","d"],"context_filter_status":["pass","fail","pass","pass"],"environmental_score":[.7,np.nan,.8,.6]})
        original=ranking.copy(deep=True)
        f,_=compare(p,ranking,[{"id":"test","objectives":[objective("sky_visible_fraction_4pi")],"meaning":"exploratory"}])
        self.assertEqual(f.set_index("candidate_id").preference_status.to_dict(),{"a":"compared_context_only","b":"excluded_by_current_context_filters","c":"Unknown","d":"compared_context_only"})
        self.assertTrue(f.loc[f.candidate_id.isin(["b","c"]),"pareto_front"].isna().all())
        pd.testing.assert_frame_equal(original,ranking)

    def test_single_supported_candidate_is_not_a_winner_by_missing_competitors(self):
        p=pd.DataFrame({"candidate_id":["a","b"],"region":["r"]*2,"sky_visible_fraction_4pi":[.4,np.nan]})
        r=pd.DataFrame({"candidate_id":["a","b"],"context_filter_status":["pass"]*2,"environmental_score":[.8,.7]})
        f,_=compare(p,r,[{"id":"test","objectives":[objective("sky_visible_fraction_4pi")],"meaning":"test"}])
        self.assertEqual(f.set_index("candidate_id").loc["a","preference_status"],"insufficient_comparable_candidates")
        self.assertTrue(f.pareto_front.isna().all())

    def test_unknown_hard_context_is_not_called_failed_or_passed(self):
        p=pd.DataFrame({"candidate_id":["a","b"],"region":["r"]*2,"sky_visible_fraction_4pi":[.4,.5]})
        r=pd.DataFrame({"candidate_id":["a","b"],"context_filter_status":["unknown","pass"],"environmental_score":[np.nan,.7]})
        f,_=compare(p,r,[{"id":"test","objectives":[objective("sky_visible_fraction_4pi")],"meaning":"test"}])
        self.assertEqual(f.set_index("candidate_id").loc["a","preference_status"],"withheld_unknown_context_filters")
        self.assertTrue(f.pareto_front.isna().all())

    def test_uv_solar_double_count_is_rejected(self):
        p=pd.DataFrame({"candidate_id":["a"],"region":["r"]})
        r=pd.DataFrame({"candidate_id":["a"],"context_filter_status":["pass"],"environmental_score":[.8]})
        view={"id":"bad","objectives":[objective("solar_opportunity_fraction_median","higher"),objective("uv_sun_visibility_opportunity_proxy")],"meaning":"bad"}
        with self.assertRaisesRegex(ValueError,"double-count"):
            compare(p,r,[view])

    def test_arbitrary_weights_are_rejected_in_pareto_views(self):
        p=pd.DataFrame({"candidate_id":["a"],"region":["r"],"x":[.1]})
        r=pd.DataFrame({"candidate_id":["a"],"context_filter_status":["pass"],"environmental_score":[.8]})
        with self.assertRaisesRegex(ValueError,"weights"):
            compare(p,r,[{"id":"bad","objectives":[dict(objective("x"),weight=1)],"meaning":"bad"}])

    def test_plasma_cannot_be_ranked_lowest_is_safest(self):
        p=pd.DataFrame({"candidate_id":["a"],"region":["r"],"plasma_density":[.1]})
        r=pd.DataFrame({"candidate_id":["a"],"context_filter_status":["pass"],"environmental_score":[.8]})
        with self.assertRaisesRegex(ValueError,"plasma"):
            compare(p,r,[{"id":"bad","objectives":[objective("plasma_density")],"meaning":"bad"}])

    def test_psr_fraction_is_not_a_standalone_charging_safety_score(self):
        p=pd.DataFrame({"candidate_id":["a"],"region":["r"],"psr_fraction_cells":[.1]})
        r=pd.DataFrame({"candidate_id":["a"],"context_filter_status":["pass"],"environmental_score":[.8]})
        with self.assertRaisesRegex(ValueError,"supported preference"):
            compare(p,r,[{"id":"bad","objectives":[objective("psr_fraction_cells")],"meaning":"bad"}])

    def test_all_physical_requirements_remain_unknown_without_limits(self):
        result=operational_unknowns(pd.DataFrame({"candidate_id":["a","b"],"region":["r"]*2}))
        self.assertEqual(len(result),6)
        self.assertTrue(result.status.eq("Unknown").all())
        self.assertTrue(result.margin.isna().all())


if __name__=="__main__":unittest.main()
