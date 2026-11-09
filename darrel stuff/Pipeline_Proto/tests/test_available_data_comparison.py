"""Available-data comparison is independent of operational readiness; unit fixtures only."""
from contextlib import redirect_stdout
import ast
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import environment_engine as engine


def inputs():
    candidates = pd.DataFrame({"candidate_id": ["a", "b", "c"], "region": ["unit_fixture"]*3})
    rows = []
    for candidate, slope in [("a", 5), ("b", 6), ("c", 9)]:
        for metric, value in [("solar_visibility_median", .7), ("earth_visibility_median", .8), ("slope_q90_deg", slope)]:
            rows.append(engine.evidence_row(candidate, metric, value, 1, "observed", "unit_fixture"))
    policy = json.loads((engine.PIPELINE/"diagnostic_policy.json").read_text())
    return candidates, pd.DataFrame(rows), policy


class AvailableDataComparisonTests(unittest.TestCase):
    def test_comparison_preserves_existing_scores_filters_and_ties(self):
        candidates, evidence, policy = inputs()
        summary, checks, _, _ = engine.evaluate(candidates, evidence, policy)
        ranking, top, usage = engine.environmental_tables(summary, evidence, checks, policy)
        self.assertEqual(top.candidate_id.tolist(), ["a", "b"])
        self.assertEqual(top.environmental_rank.tolist(), [1, 2])
        self.assertEqual(top.environmental_score.tolist(), [.75, .75])
        excluded = ranking.set_index("candidate_id").loc["c"]
        self.assertEqual(excluded.comparison_status, "excluded_by_context_filter")
        self.assertTrue(pd.isna(excluded.environmental_score))
        self.assertIn("slope_q90_deg", excluded.reason)
        self.assertFalse(usage.set_index("metric").loc["slope_q90_deg", "used_in_score"])

    def test_missing_soft_factor_does_not_reweight_or_rank(self):
        candidates, evidence, policy = inputs()
        policy["hard_rules"] = [r for r in policy["hard_rules"] if r["metric"] != "solar_visibility_median"]
        evidence = evidence.loc[~(evidence.candidate_id.eq("a") & evidence.metric.eq("solar_visibility_median"))]
        summary, checks, _, _ = engine.evaluate(candidates, evidence, policy)
        ranking, top, _ = engine.environmental_tables(summary, evidence, checks, policy)
        self.assertEqual(ranking.set_index("candidate_id").loc["a", "comparison_status"], "missing_comparable_evidence")
        self.assertTrue(pd.isna(ranking.set_index("candidate_id").loc["a", "environmental_score"]))
        self.assertNotIn("a", top.candidate_id.tolist())

    def test_partial_thermal_and_context_are_visible_not_automatic_score_factors(self):
        candidates, evidence, policy = inputs()
        extra = pd.DataFrame([engine.evidence_row("a", "thermal_phase_median_span_K", 20, 1, "observed", "unit_fixture"),
                              engine.evidence_row("a", "minirf_cpr_median", .4, 1, "observed", "unit_fixture")])
        evidence = pd.concat([evidence, extra], ignore_index=True)
        summary, checks, _, _ = engine.evaluate(candidates, evidence, policy)
        _, top, usage = engine.environmental_tables(summary, evidence, checks, policy)
        self.assertEqual(top.environmental_score.tolist(), [.75, .75])
        usage = usage.set_index("metric")
        self.assertEqual(usage.loc["thermal_phase_median_span_K", "supported_candidates"], 1)
        self.assertEqual(usage.loc["thermal_phase_median_span_K", "unsupported_or_absent_candidates"], 2)
        self.assertFalse(usage.loc["thermal_phase_median_span_K", "used_in_score"])
        self.assertIn("forbids scoring", usage.loc["minirf_cpr_median", "reason"])

    def run_configured(self, extra):
        candidates, evidence, _ = inputs()
        empty_context = pd.DataFrame(columns=["candidate_id", "metric", "median"])
        empty_static = pd.DataFrame(columns=["candidate_id", "variable", "unit"])
        empty_support = pd.DataFrame(columns=["candidate_id", "expected_common_products"])
        with tempfile.TemporaryDirectory(dir=engine.PIPELINE) as temp:
            config = json.loads((engine.PIPELINE/"environment_experiment.json").read_text())
            config["stage3_analysis"] = {}
            config["comparison_policy"] = str(engine.PIPELINE/"diagnostic_policy.json")
            config_path = Path(temp)/"config.json"
            config_path.write_text(json.dumps(config))
            with patch.object(engine, "OUTPUTS", Path(temp)/"outputs"), patch.object(engine, "load_evidence", return_value=(candidates,evidence,empty_context,empty_static,empty_support)), patch.object(engine, "load_sample_fixture", side_effect=AssertionError("Default must not borrow synthetic scenario")), redirect_stdout(io.StringIO()):
                folder = engine.main(["--config", str(config_path), *extra])
            report = json.loads((folder/"report.json").read_text())
            ranking = pd.read_csv(folder/"environmental_rankings.csv")
            summary = (folder/"RUN_SUMMARY.md").read_text()
            provenance = json.loads((folder/"provenance.json").read_text())
            return report, ranking, summary, provenance

    def test_default_comparison_not_blocked_by_blank_equipment_profile(self):
        report, ranking, summary, provenance = self.run_configured([])
        self.assertEqual(report["run_kind"], "environment_comparison")
        self.assertFalse(report["stage3_assessment_requested"])
        self.assertEqual(report["stage3_statuses"], {})
        self.assertEqual(report["mission_profile_origin"], "not_requested")
        self.assertEqual(report["environmental_comparison_statuses"], {"ranked_context_only": 2, "excluded_by_context_filter": 1})
        self.assertEqual(ranking.environmental_score.notna().sum(), 2)
        self.assertFalse(report["is_synthetic"])
        self.assertFalse(report["operational_suitability_assessed"])
        self.assertIn("Primary result", summary)
        self.assertIn("darrel stuff/Pipeline_Proto/diagnostic_policy.json", {name.replace('\\','/') for name in provenance["inputs"]})

    def test_legacy_evidence_only_remains_explicitly_available(self):
        report, ranking, _, _ = self.run_configured(["--evidence-only"])
        self.assertEqual(report["run_kind"], "evidence_only")
        self.assertTrue(ranking.environmental_score.isna().all())
        self.assertEqual(report["stage3_statuses"], {"unknown": 3})

    def test_notebook_synthetic_scenario_is_guarded_off_by_default(self):
        notebook = json.loads((engine.PIPELINE/"Dar_028_environment_pipeline.ipynb").read_text(encoding="utf-8"))
        cell = next(c for c in notebook["cells"] if c["id"] == "env-sample-check")
        tree = ast.parse("".join(cell["source"]))
        self.assertIsInstance(tree.body[0], ast.Assign)
        self.assertEqual(tree.body[0].targets[0].id, "RUN_SYNTHETIC_TEST")
        self.assertIs(tree.body[0].value.value, False)
        self.assertIsInstance(tree.body[1], ast.If)
        self.assertEqual(tree.body[1].test.id, "RUN_SYNTHETIC_TEST")


if __name__ == "__main__":
    unittest.main()
