from copy import deepcopy
import json
import io
from pathlib import Path
import sys
import unittest

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import environment_engine as engine


def policy():
    return json.loads((Path(engine.__file__).parent / "diagnostic_policy.json").read_text())


def example():
    candidates = pd.DataFrame({"candidate_id": ["b", "a", "c"], "region": ["r"] * 3})
    rows = []
    for candidate, solar, earth, slope in [("b", .7, .8, 5.), ("a", .7, .8, 5.), ("c", .9, 1., 9.)]:
        for metric, value in [("solar_visibility_median", solar), ("earth_visibility_median", earth), ("slope_q90_deg", slope)]:
            rows.append(engine.evidence_row(candidate, metric, value, 2, "observed", "fixture"))
    return candidates, pd.DataFrame(rows)


class EnvironmentEngineTests(unittest.TestCase):
    def test_gate_before_ranking_and_stable_ties(self):
        candidates, evidence = example()
        result, _, _, top = engine.evaluate(candidates, evidence, policy())
        self.assertEqual(top.candidate_id.tolist(), ["a", "b"])
        self.assertTrue(np.allclose(top.diagnostic_preference_score, .75))
        self.assertEqual(result.set_index("candidate_id").loc["c", "gate_status"], "fail")
        self.assertTrue(result.set_index("candidate_id").loc["c", "diagnostic_preference_score"] != 1.)

    def test_missing_required_data_unknown_not_pass(self):
        candidates, evidence = example()
        evidence = evidence.loc[~(evidence.candidate_id.eq("a") & evidence.metric.eq("solar_visibility_median"))]
        result, _, _, top = engine.evaluate(candidates, evidence, policy())
        self.assertEqual(result.set_index("candidate_id").loc["a", "gate_status"], "unknown")
        self.assertNotIn("a", set(top.candidate_id))

    def test_failure_dominates_unknown(self):
        candidates, evidence = example()
        evidence = evidence.loc[~(evidence.candidate_id.eq("c") & evidence.metric.eq("solar_visibility_median"))]
        result, _, _, _ = engine.evaluate(candidates, evidence, policy())
        self.assertEqual(result.set_index("candidate_id").loc["c", "gate_status"], "fail")

    def test_empty_hard_policy_is_unconfigured(self):
        candidates, evidence = example()
        config = policy(); config["hard_rules"] = []
        result, _, _, top = engine.evaluate(candidates, evidence, config)
        self.assertEqual(set(result.gate_status), {"unconfigured"})
        self.assertTrue(top.empty)

    def test_default_requirements_unknown(self):
        candidates, evidence = example()
        config = json.loads((Path(engine.__file__).parent / "environment_experiment.json").read_text())["policy"]
        result, checks, scores, top = engine.evaluate(candidates, evidence, config)
        self.assertEqual(len(checks), 15)
        self.assertEqual(set(result.gate_status), {"unknown"})
        self.assertTrue(top.empty)
        restored = pd.read_csv(io.StringIO(scores.to_csv(index=False)))
        self.assertTrue(restored.empty)
        self.assertIn("preference_id", restored.columns)

    def test_missing_soft_data_does_not_renormalize(self):
        candidates, evidence = example()
        config = policy()
        config["hard_rules"] = [r for r in config["hard_rules"] if r["metric"] != "solar_visibility_median"]
        evidence = evidence.loc[~(evidence.candidate_id.eq("a") & evidence.metric.eq("solar_visibility_median"))]
        result, _, _, top = engine.evaluate(candidates, evidence, config)
        a = result.set_index("candidate_id").loc["a"]
        self.assertEqual(a.gate_status, "pass")
        self.assertTrue(np.isnan(a.diagnostic_preference_score))
        self.assertNotIn("a", set(top.candidate_id))

    def test_context_cannot_be_scored(self):
        for metric in ["minirf_cpr_median", "shadowcam_radiance_median"]:
            config = policy(); config["soft_preferences"][0]["metric"] = metric
            with self.assertRaises(ValueError): engine.validate_policy(config)

    def test_scope_and_unit_contracts(self):
        for field, value in [("unit", "percent"), ("scope", "mission_continuity")]:
            config = policy(); config["hard_rules"][0][field] = value
            with self.assertRaises(ValueError): engine.validate_policy(config)

    def test_no_implicit_operational_proxy(self):
        config = policy(); config["mode"] = "evidence_only"
        with self.assertRaises(ValueError): engine.validate_policy(config)

    def test_duplicate_metric_and_bad_policy_rejected(self):
        config = policy()
        duplicate = deepcopy(config["soft_preferences"][0]); duplicate["id"] = "duplicate"
        config["soft_preferences"].append(duplicate)
        with self.assertRaises(ValueError): engine.validate_policy(config)
        for bad in [np.nan, True, -1]:
            config = policy(); config["soft_preferences"][0]["weight"] = bad
            with self.assertRaises(ValueError): engine.validate_policy(config)

    def test_duplicate_or_relabelled_evidence_rejected(self):
        candidates, evidence = example()
        with self.assertRaises(ValueError):
            engine.evaluate(candidates, pd.concat([evidence, evidence.iloc[:1]]), policy())
        evidence.loc[0, "scope"] = "mission_surface_exposure"
        with self.assertRaises(ValueError): engine.evaluate(candidates, evidence, policy())

    def test_unknown_must_not_contain_numeric_default(self):
        candidates, evidence = example(); evidence.loc[0, "status"] = "unknown"
        with self.assertRaises(ValueError): engine.evaluate(candidates, evidence, policy())

    def test_visibility_domain_and_support_count(self):
        candidates, evidence = example()
        evidence.loc[0, "value"] = 70
        with self.assertRaises(ValueError): engine.evaluate(candidates, evidence, policy())
        _, evidence = example(); evidence.loc[0, "support_count"] = -1
        with self.assertRaises(ValueError): engine.evaluate(candidates, evidence, policy())

    def test_lower_preference_and_fixed_bounds(self):
        candidates, evidence = example(); config = policy()
        config["soft_preferences"] = [{"id": "low_slope", "metric": "slope_q90_deg", "unit": "degree",
            "scope": "static_map_cell_summary", "direction": "lower", "lower": 0, "upper": 10,
            "weight": 2, "reason": "test explicit inverse utility"}]
        _, _, _, top = engine.evaluate(candidates, evidence, config)
        self.assertTrue(np.allclose(top.diagnostic_preference_score, .5))


if __name__ == "__main__":
    unittest.main()
