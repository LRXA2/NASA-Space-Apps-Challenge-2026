"""Explicit stages preserve the previously tested public evaluation contract."""
import json
from pathlib import Path
import sys
import unittest

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import environment_engine as engine


class PipelineStageTests(unittest.TestCase):
    def inputs(self):
        candidates = pd.DataFrame({"candidate_id": ["allowed", "blocked"], "region": ["r", "r"]})
        rows = []
        for candidate, slope in [("allowed", 5), ("blocked", 9)]:
            for metric, value in [("solar_visibility_median", .6), ("earth_visibility_median", .7), ("slope_q90_deg", slope)]:
                rows.append(engine.evidence_row(candidate, metric, value, 1, "observed", "fixture"))
        policy = json.loads(Path(engine.__file__).with_name("diagnostic_policy.json").read_text())
        return candidates, pd.DataFrame(rows), policy

    def test_explicit_stages_equal_evaluate(self):
        candidates, evidence, policy = self.inputs()
        gates, checks = engine.run_eligibility(candidates, evidence, policy)
        scored, utilities = engine.run_scoring(gates, evidence, policy)
        summary = candidates.merge(scored, on="candidate_id", validate="one_to_one")
        top = engine.run_recommendations(summary, policy["top_k"])
        combined = engine.evaluate(candidates, evidence, policy)
        for expected, actual in zip(combined, [summary, checks, utilities, top]):
            pd.testing.assert_frame_equal(expected, actual)
        self.assertEqual(top.candidate_id.tolist(), ["allowed"])
        self.assertTrue(utilities.loc[utilities.candidate_id.eq("blocked"), "utility"].isna().all())

    def test_recommendations_cannot_bypass_gate(self):
        candidates, evidence, policy = self.inputs()
        summary, _, _, _ = engine.evaluate(candidates, evidence, policy)
        summary.loc[summary.candidate_id.eq("blocked"), "diagnostic_preference_score"] = 1
        self.assertEqual(engine.run_recommendations(summary, 5).candidate_id.tolist(), ["allowed"])

    def test_invalid_stage_states_rejected(self):
        candidates, evidence, policy = self.inputs()
        gates, _ = engine.run_eligibility(candidates, evidence, policy)
        gates.loc[0, "gate_status"] = "assumed_pass"
        with self.assertRaises(ValueError): engine.run_scoring(gates, evidence, policy)
        with self.assertRaises(ValueError): engine.run_recommendations(pd.DataFrame(), 0)


if __name__ == "__main__":
    unittest.main()
