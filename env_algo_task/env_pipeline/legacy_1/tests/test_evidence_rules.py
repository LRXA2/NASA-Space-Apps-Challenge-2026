"""Evidence-use contracts, not fabricated site-safety labels."""
import copy
import json
from pathlib import Path
import sys
import unittest

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import environment_engine as engine
import evidence_rules as rules


def source_fixtures():
    return {
        "dated_thermal/dated_thermal_support.csv": pd.DataFrame({"strict_rows": [0]}),
        "apollo/primary_resource_changes.csv": pd.DataFrame({"actual_remaining": [.4],
            "reported_actual_redline": [.4], "historical_remaining_minus_source_redline": [0.]}),
        "geometry/reference_observers.csv": pd.DataFrame({"region": ["synthetic_reference_region"]}),
        "geometry/terrain_geometry_summary.csv": pd.DataFrame({"region": ["synthetic_reference_region"]}),
    }


class EvidenceRuleTests(unittest.TestCase):
    def register(self):
        return json.loads((engine.LOCAL/"research/environment_rule_register.json").read_text(encoding="utf-8"))

    def policy(self):
        return json.loads((engine.PIPELINE/"diagnostic_policy.json").read_text(encoding="utf-8"))

    def test_registry_classifies_references_and_requirements_without_limits(self):
        register=self.register();rules.validate_register(register)
        roles={r["role"] for r in register["rules"]}
        self.assertEqual(roles,rules.ROLES)
        self.assertTrue(all(r["limit_state"]=="not_adopted" for r in register["rules"]))
        self.assertTrue(any(r["id"]=="H_RAD" and "cutoff" in r["effect"] for r in register["rules"]))

    def test_duplicate_register_identity_rejected(self):
        r=self.register();r["rules"].append(copy.deepcopy(r["rules"][0]))
        with self.assertRaises(ValueError):rules.validate_register(r)

    def test_unsourced_numeric_operational_limit_rejected(self):
        r=self.register();r["rules"][0]["limit"]=100
        with self.assertRaises(ValueError):rules.validate_register(r)

    def test_missing_source_or_applicability_is_not_hidden(self):
        for field in ["source","applicability","required_inputs"]:
            r=self.register();r["rules"][0][field]=""
            with self.subTest(field=field):
                with self.assertRaises(ValueError):rules.validate_register(r)

    def test_policy_override_values_and_bounds_are_compiled_not_replaced(self):
        p=self.policy();p["hard_rules"][0]["limit"]=.65
        p["soft_preferences"][0].update(weight=3,lower=.2,upper=.9)
        before=copy.deepcopy(p)
        r=rules.compile_register(self.register(),p,"explicit_unit_fixture_policy.json").set_index("id")
        self.assertEqual(r.loc["comparison_filter::illustrative_solar","limit"],.65)
        self.assertEqual(r.loc["comparison_preference::sunlight_context","weight"],3)
        self.assertEqual(r.loc["comparison_preference::sunlight_context","lower"],.2)
        self.assertEqual(r.loc["comparison_preference::sunlight_context","upper"],.9)
        self.assertEqual(p,before)

    def test_zero_strict_observations_fails_use_not_physical_site(self):
        f=rules.evidence_use_checks(source_fixtures()).set_index("check_id")
        self.assertEqual(f.loc["qualified_dated_thermal_history","data_use_status"],"Failed")
        self.assertTrue(f.assessment_domain.eq("evidence_use_NOT_site_safety").all())
        self.assertTrue(f.candidate_operational_conclusion_from_these_sources.eq("Unknown").all())

    def test_positive_observation_count_cannot_certify_mission_history(self):
        frames=source_fixtures();frames["dated_thermal/dated_thermal_support.csv"].loc[0,"strict_rows"]=1
        f=rules.evidence_use_checks(frames).set_index("check_id")
        self.assertEqual(f.loc["qualified_dated_thermal_history","data_use_status"],"Unknown")

    def test_counter_and_reference_geometry_cannot_be_promoted(self):
        f=rules.evidence_use_checks(source_fixtures()).set_index("check_id")
        for id in ["orbital_data_to_shielded_dose","reference_point_to_component_history","catalog_to_local_event_probability"]:
            self.assertEqual(f.loc[id,"data_use_status"],"Failed")

    def test_ref_geometry_candidate_relabelling_rejected(self):
        frames=source_fixtures();frames["geometry/terrain_geometry_summary.csv"]["candidate_id"]="fictional"
        with self.assertRaises(ValueError):rules.evidence_use_checks(frames)

    def test_duplicate_or_missing_reference_observer_rejected(self):
        for frame in [pd.DataFrame({"region":["a","a"]}),pd.DataFrame({"region":["other"]})]:
            frames=source_fixtures();frames["geometry/reference_observers.csv"]=frame
            with self.assertRaises(ValueError):rules.evidence_use_checks(frames)

    def test_historical_equality_is_not_current_equipment_pass(self):
        f=rules.evidence_use_checks(source_fixtures()).set_index("check_id")
        self.assertEqual(f.loc["historical_reserve_arithmetic","data_use_status"],"Passed")
        self.assertEqual(f.loc["historical_limit_to_new_configuration","data_use_status"],"Failed")
        self.assertEqual(f.loc["historical_reserve_arithmetic","candidate_operational_conclusion_from_these_sources"],"Unknown")

    def test_corrupt_historical_headroom_is_an_error_not_a_default(self):
        frames=source_fixtures();frames["apollo/primary_resource_changes.csv"].loc[0,"historical_remaining_minus_source_redline"]=1
        with self.assertRaises(ValueError):rules.evidence_use_checks(frames)

    def test_missing_required_eda_table_is_not_silently_skipped(self):
        frames=source_fixtures();del frames["dated_thermal/dated_thermal_support.csv"]
        with self.assertRaises(KeyError):rules.evidence_use_checks(frames)

    def test_configuration_path_escape_rejected(self):
        with self.assertRaises(ValueError):rules.local_file("../../outside_rule_register.json")

    def test_hazard_context_does_not_create_candidate_measurements(self):
        candidates=pd.DataFrame({"candidate_id":["fictional_a","fictional_b"],"region":["unit_fixture"]*2})
        hazards=pd.DataFrame({"hazard":["unit_radiation"],"available_evidence":["orbital context"],
            "essential_limitations":["no local transported dose"],"risk_principle_not_implemented_rule":["applicable excess cannot be offset"]})
        out=rules.candidate_limits(candidates,hazards)
        self.assertEqual(len(out),2)
        self.assertTrue(out.candidate_specific_conclusion.eq("Unknown").all())
        self.assertNotIn("value",out)
        self.assertNotIn("score",out)


if __name__=="__main__":unittest.main()
