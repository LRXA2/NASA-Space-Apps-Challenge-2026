"""Clean data-backed product exports; unit fixtures do not replace the real-data run."""
from contextlib import contextmanager, redirect_stdout
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import environment_engine as engine
from test_available_data_comparison import inputs


@contextmanager
def product_run(flags=(), change=None):
    candidates, evidence, _ = inputs()
    if change:
        candidates, evidence = change(candidates, evidence)
    frames = (candidates, evidence, pd.DataFrame(columns=["candidate_id", "metric"]),
              pd.DataFrame(columns=["candidate_id", "variable"]), pd.DataFrame(columns=["candidate_id"]))
    with tempfile.TemporaryDirectory(dir=engine.PIPELINE) as temp:
        config = json.loads((engine.PIPELINE/"environment_experiment.json").read_text())
        config["stage3_analysis"] = {}
        config["comparison_policy"] = str(engine.PIPELINE/"diagnostic_policy.json")
        config_path = Path(temp)/"config.json"
        config_path.write_text(json.dumps(config))
        with patch.object(engine, "OUTPUTS", Path(temp)/"outputs"), patch.object(engine, "load_evidence", return_value=frames), patch.object(engine, "load_sample_fixture", side_effect=AssertionError("No synthetic mission may be borrowed")), redirect_stdout(io.StringIO()):
            folder = engine.main(["--config", str(config_path), *flags])
        yield folder, json.loads((folder/"report.json").read_text()), Path(temp)/"outputs"


class ProductDeliveryTests(unittest.TestCase):
    def test_default_does_not_even_evaluate_missing_equipment(self):
        with patch.object(engine.stage3_assessment, "assess", side_effect=AssertionError("Not requested")), patch.object(engine.stage3_assessment, "profile_readiness", side_effect=AssertionError("No template dependency")):
            with product_run() as (folder, report, output):
                self.assertFalse(report["stage3_assessment_requested"])
                self.assertEqual(report["stage3_statuses"], {})
                self.assertEqual(report["mission_profile_origin"], "not_requested")
                self.assertFalse(any(folder.glob("stage3*")))
                self.assertFalse((folder/"candidate_assessments.csv").exists())
                self.assertFalse((folder/"stage3_evidence").exists())
                self.assertFalse((folder/"audit").exists())
                self.assertTrue((output/"LATEST_RESULTS.md").is_file())

    def test_ranked_and_excluded_candidates_are_both_retained_without_blank_scores(self):
        with product_run() as (folder, report, _):
            ranked = pd.read_csv(folder/"environmental_rankings.csv")
            excluded = pd.read_csv(folder/"excluded_candidates.csv")
            status = pd.read_csv(folder/"candidate_status.csv")
            self.assertEqual(ranked.candidate_id.tolist(), ["a", "b"])
            self.assertEqual(ranked.environmental_score.tolist(), [.75, .75])
            self.assertEqual(excluded.candidate_id.tolist(), ["c"])
            self.assertNotIn("environmental_score", excluded)
            self.assertEqual(len(status), report["candidates"])
            self.assertEqual(set(status.candidate_id), set(ranked.candidate_id) | set(excluded.candidate_id))
            for path in folder.glob("*.csv"):
                data = pd.read_csv(path)
                self.assertGreater(len(data), 0, path.name)
                self.assertFalse(data.isna().any().any(), path.name)
                self.assertFalse(data.astype(str).apply(lambda column: column.str.lower().eq("unknown").any()).any(), path.name)

    def test_unavailable_optional_product_is_explained_not_written_empty(self):
        with product_run() as (folder, _, _):
            catalog = pd.read_csv(folder/"output_catalog.csv").set_index("file")
            self.assertEqual(catalog.loc["thermal_profiles.csv", "status"], "omitted_empty")
            self.assertFalse((folder/"thermal_profiles.csv").exists())
            self.assertIn("No complete qualifying thermal profiles", catalog.loc["thermal_profiles.csv", "reason"])

    def test_no_passing_candidate_is_valid_negative_result_not_fake_score(self):
        def change(candidates, evidence):
            evidence.loc[evidence.metric.eq("slope_q90_deg"), "value"] = 10.
            return candidates, evidence
        with product_run(change=change) as (folder, report, _):
            self.assertEqual(report["primary_result"], "candidate_status.csv")
            self.assertFalse((folder/"environmental_rankings.csv").exists())
            self.assertFalse((folder/"environmental_top_k.csv").exists())
            self.assertEqual(len(pd.read_csv(folder/"excluded_candidates.csv")), 3)
            self.assertIn("No candidate currently", (folder/"RUN_SUMMARY.md").read_text())

    def test_missing_measurement_is_explicit_exclusion_not_zero_or_renormalized(self):
        def change(candidates, evidence):
            target = evidence.candidate_id.eq("a") & evidence.metric.eq("solar_visibility_median")
            evidence.loc[target, ["value", "status", "support_count"]] = [np.nan, "unknown", 0]
            return candidates, evidence
        with product_run(change=change) as (folder, _, _):
            ranked = pd.read_csv(folder/"environmental_rankings.csv")
            self.assertEqual(ranked.candidate_id.tolist(), ["b"])
            self.assertEqual(ranked.environmental_score.tolist(), [.75])
            status = pd.read_csv(folder/"candidate_status.csv").set_index("candidate_id")
            self.assertEqual(status.loc["a", "comparison_status"], "missing_comparable_evidence")
            self.assertIn("missing qualifying evidence", status.loc["a", "reason"])
            coverage = pd.read_csv(folder/"feature_usage.csv").set_index("metric")
            self.assertEqual(coverage.loc["solar_visibility_median", "unsupported_or_absent_candidates"], 1)
            known = pd.read_csv(folder/"environment_evidence.csv")
            self.assertFalse((known.candidate_id.eq("a") & known.metric.eq("solar_visibility_median")).any())

    def test_equipment_unknowns_exist_only_when_explicitly_requested(self):
        with product_run(flags=["--stage3"]) as (folder, report, output):
            self.assertTrue(report["stage3_assessment_requested"])
            self.assertEqual(report["stage3_statuses"], {"unknown": 3})
            self.assertTrue(pd.read_csv(folder/"stage3_operational_checks.csv").status.eq("unknown").all())
            self.assertFalse((output/"LATEST_RESULTS.md").exists())


if __name__ == "__main__":
    unittest.main()
