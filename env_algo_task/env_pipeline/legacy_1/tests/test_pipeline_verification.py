"""Output-location, readable-empty-result and full synthetic-flow regression checks."""
from contextlib import redirect_stdout
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


class PipelineVerificationTests(unittest.TestCase):
    def test_outputs_stay_in_pipeline_not_preprocessed_data(self):
        config = {"policy": {"mode": "evidence_only"}}
        with tempfile.TemporaryDirectory(dir=engine.PIPELINE) as temp:
            with patch.object(engine, "OUTPUTS", Path(temp)/"outputs"):
                with engine.PrototypeRun(config) as run:
                    self.assertTrue(run.directory.is_relative_to(engine.PIPELINE))
                    self.assertFalse(run.directory.is_relative_to(engine.LOCAL/"data"))
                    with self.assertRaises(ValueError):
                        run.path("../../../../outside.csv")
                    run.path("valid.csv").write_text("field\nvalue\n", encoding="utf-8")
                manifest = json.loads((run.directory/"provenance.json").read_text())
                self.assertEqual(manifest["status"], "complete")
                self.assertIn("valid.csv", [r["path"] for r in manifest["outputs"]])

    def test_all_ten_cases_through_the_real_engine(self):
        with tempfile.TemporaryDirectory(dir=engine.PIPELINE) as temp:
            with patch.object(engine, "OUTPUTS", Path(temp)/"outputs"), patch.object(engine, "load_evidence", side_effect=AssertionError("Synthetic test must not borrow real EDA")), redirect_stdout(io.StringIO()):
                folder = engine.main(["--sample"])
            summary = pd.read_csv(folder/"candidate_assessments.csv")
            checks = pd.read_csv(folder/"stage3_operational_checks.csv")
            top = pd.read_csv(folder/"stage3_top_k.csv")
            self.assertEqual(len(summary), 10)
            self.assertEqual(summary.stage3_status.value_counts().to_dict(), {"fail": 6, "pass": 2, "unknown": 2})
            self.assertEqual(top.candidate_id.tolist(), ["SYN_001", "SYN_002"])
            self.assertEqual(top.operational_preference_score.round(2).tolist(), [.85, .7])
            self.assertTrue(summary.loc[summary.stage3_status.ne("pass"), "operational_preference_score"].isna().all())
            self.assertTrue(pd.read_csv(folder/"sample_verification.csv").matches_expected.all())
            self.assertEqual(len(checks), 60)
            by_case = checks.set_index(["candidate_id", "requirement"])
            for candidate, rule in [("SYN_003", "consumables"), ("SYN_004", "power"),
                                    ("SYN_005", "thermal"), ("SYN_006", "communications"),
                                    ("SYN_007", "support_load")]:
                self.assertEqual(by_case.loc[(candidate, rule), "status"], "fail")
                self.assertLess(by_case.loc[(candidate, rule), "margin"], 0)
            self.assertIn("Surface radiometry", by_case.loc[("SYN_009", "thermal"), "reason"])
            self.assertEqual(by_case.loc[("SYN_010", "power"), "status"], "unknown")
            self.assertEqual(summary.set_index("candidate_id").loc["SYN_010", "stage3_status"], "fail")
            profile = json.loads((folder/"sample_inputs/mission_profile.json").read_text())
            for candidate in profile["candidate_inputs"].values():
                for evidence in candidate.values():
                    self.assertTrue((engine.PIPELINE/evidence["input_file"]).resolve().is_relative_to(folder))
            report = json.loads((folder/"report.json").read_text())
            self.assertTrue(report["is_synthetic"])
            self.assertFalse(report["certified_suitability"])
            self.assertEqual(report["data_basis"], "synthetic_fixture_only")
            catalog = pd.read_csv(folder/"output_catalog.csv")
            self.assertTrue(catalog.title.notna().all())
            self.assertTrue(catalog.loc[catalog.rows.eq(0), "reason"].str.len().gt(0).all())
            self.assertIn("SYNTHETIC SOFTWARE TEST ONLY", (folder/"RUN_SUMMARY.md").read_text())

    def test_expected_labels_are_not_used_as_features(self):
        with tempfile.TemporaryDirectory(dir=engine.PIPELINE) as temp:
            with patch.object(engine, "OUTPUTS", Path(temp)/"outputs"):
                with engine.PrototypeRun({"policy": {"mode": "diagnostic"}}, "synthetic_demo") as run:
                    candidates, _, _, _, _, profile = engine.load_sample_fixture(run)
                    candidates["expected_stage3_status"] = "pass"
                    result, _ = engine.stage3_assessment.assess(candidates, profile, engine.PIPELINE)
                    self.assertEqual(result.stage3_status.value_counts().to_dict(), {"fail": 6, "pass": 2, "unknown": 2})

    def test_csv_headers_stay_machine_readable_while_empty_result_is_explained(self):
        with tempfile.TemporaryDirectory(dir=engine.PIPELINE) as temp:
            with patch.object(engine, "OUTPUTS", Path(temp)/"outputs"):
                with engine.PrototypeRun({"policy": {"mode": "evidence_only"}}) as run:
                    report = {"run_kind": "evidence_only", "data_basis": "fixture", "candidates": 1,
                              "stage3_statuses": {"unknown": 1}, "gate_statuses": {"unknown": 1},
                              "top_k_returned": 0, "stage3_top_k_returned": 0,
                              "is_synthetic": False, "profile_missing_inputs": ["crew_count"]}
                    engine.export_tables(run, [("empty.csv", "A titled empty result", pd.DataFrame(columns=["candidate_id", "score"]), "No eligible candidates")], report)
                    self.assertEqual((run.directory/"empty.csv").read_text().strip(), "candidate_id,score")
                    self.assertTrue(pd.read_csv(run.directory/"empty.csv").empty)
                    catalog = pd.read_csv(run.directory/"output_catalog.csv")
                    self.assertEqual(catalog.iloc[0].reason, "No eligible candidates")
                    self.assertEqual(catalog.iloc[0].title, "A titled empty result")
                    self.assertIn("Missing: crew_count", (run.directory/"RUN_SUMMARY.md").read_text())

    def test_sample_cannot_be_mixed_with_a_real_profile(self):
        with redirect_stdout(io.StringIO()), patch("sys.stderr", new_callable=io.StringIO):
            with self.assertRaises(SystemExit) as error:
                engine.main(["--sample", "--mission-profile", "real.json"])
            self.assertEqual(error.exception.code, 2)

    def test_operational_top_export_retains_stage3_label(self):
        with tempfile.TemporaryDirectory(dir=engine.PIPELINE) as temp:
            with patch.object(engine, "OUTPUTS", Path(temp)/"outputs"), redirect_stdout(io.StringIO()):
                folder = engine.main(["--sample"])
            top = pd.read_csv(folder/"stage3_top_k.csv")
            self.assertEqual(top.stage3_status.tolist(), ["pass", "pass"])
            self.assertTrue(top.stage3_status.eq(top.gate_status).all())
            report = json.loads((folder/"report.json").read_text())
            self.assertFalse(report["operational_suitability_assessed"])
            self.assertTrue(report["margin_calculations_executed"])


if __name__ == "__main__":
    unittest.main()
