"""Operations/Survival allocation without a mission-profile selection layer."""
from copy import deepcopy
import csv
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import env_pipeline as engine


class TwoFlowConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.config, self.digest = engine.load_config(HERE / "config.yml")
        self.rows = engine.read_csv(HERE / "sample_input.csv", self.config)

    def test_exact_two_flows_and_preserved_weights(self):
        self.assertEqual(set(self.config["assessments"]), {"operations", "survival"})
        self.assertNotIn("profiles", self.config)
        self.assertNotIn("mission_profile", self.config)
        expected = {
            "operations": {"solar_illumination": 40, "communications_geometry": 35, "dust": 15, "soil": 10},
            "survival": {"radiation": 40, "thermal": 35, "plasma_charging": 15, "uv": 10}}
        for flow, weights in expected.items():
            self.assertEqual(self.config["assessments"][flow]["weights"], weights)

    def test_weight_changes_are_local(self):
        cfg = deepcopy(self.config)
        cfg["assessments"]["operations"]["weights"]["soil"] = 50
        before = engine.assess(self.rows, self.config, self.digest)
        after = engine.assess(self.rows, cfg, "changed")
        self.assertTrue(any(a["operations_score"] != b["operations_score"] for a, b in zip(before, after)))
        self.assertEqual([r["survival_score"] for r in before], [r["survival_score"] for r in after])

    def test_totals_use_actual_available_weights(self):
        for result in engine.assess(self.rows, self.config, self.digest):
            self.assertNotIn("mission_profile", result)
            for flow in engine.ASSESSMENTS:
                details = json.loads(result[flow + "_details"]["domain_score_details"])
                included = [d for d in details if d["included_in_final_score"] and d["domain_score"] != ""]
                expected = sum(d["domain_score"] * d["domain_multiplier"] for d in included)
                expected /= sum(d["domain_multiplier"] for d in included)
                self.assertAlmostEqual(result[flow + "_score"], expected)

    def test_global_modes_and_independent_failures(self):
        cfg = deepcopy(self.config)
        cfg["pipeline_mode"] = "strict"
        rows = deepcopy(self.rows[:1])
        rows[0]["soil_feo_wt_percent"] = ""
        result = engine.assess(rows, cfg, "strict")[0]
        self.assertEqual(result["operations_status"], "Unknown")
        self.assertEqual(result["survival_status"], "Pass")
        cfg["pipeline_mode"] = "available_data"
        self.assertEqual(engine.assess(rows, cfg, "available")[0]["operations_status"], "Pass")
        settings = cfg["assessments"]["operations"]
        settings["domain_overrides"]["solar_illumination"] = {"hard_gates_enabled": True}
        settings["metric_overrides"]["median_sun_visibility_fraction"] = {
            "hard_gate": {"operator": "above_threshold", "threshold": .5}}
        rows[0]["median_sun_visibility_fraction"] = ".1"
        result = engine.assess(rows, cfg, "gate")[0]
        self.assertEqual(result["operations_status"], "Fail")
        self.assertEqual(result["operations_score"], "")
        self.assertEqual(result["survival_status"], "Pass")

    def test_overlap_retains_independent_scoring_rules(self):
        cfg = deepcopy(self.config)
        settings = cfg["assessments"]["survival"]
        settings["weights"]["solar_illumination"] = 10
        settings["metric_overrides"]["median_sun_visibility_fraction"] = {
            "preference": {"direction": "lower", "lower": 0, "upper": 1}}
        result = engine.assess(self.rows[:1], cfg, "overlap")[0]
        self.assertAlmostEqual(result["operations_solar_illumination_score"] + result["survival_solar_illumination_score"], 100)

    def test_no_mutation_or_hidden_profile_fallback(self):
        original = deepcopy((self.rows, self.config))
        engine.assess(self.rows, self.config, self.digest)
        self.assertEqual((self.rows, self.config), original)
        cfg = deepcopy(self.config)
        cfg["mission_profile"] = "crewed"
        with self.assertRaises(ValueError):
            engine.validate_config(cfg)
        for mutate in [lambda c: c["assessments"]["operations"]["weights"].clear(),
                       lambda c: c["assessments"]["survival"]["weights"].update(radiation=0),
                       lambda c: c["assessments"]["operations"]["weights"].update(typo=5)]:
            cfg = deepcopy(self.config)
            mutate(cfg)
            with self.assertRaises(ValueError):
                engine.validate_config(cfg)

    def test_standalone_cli_and_simple_output(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            for name in ["env_pipeline.py", "config.yml", "sample_input.csv"]:
                (folder / name).write_bytes((HERE / name).read_bytes())
            output = folder / "results.csv"
            command = [sys.executable, str(folder / "env_pipeline.py"), "--input", str(folder / "sample_input.csv"),
                       "--output", str(output)]
            completed = subprocess.run(command, text=True, capture_output=True)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertNotIn("mission_profile", json.loads(completed.stdout))
            with output.open(newline="", encoding="utf-8") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames[-2:], ["operations_score", "survival_score"])
                self.assertFalse(set(reader.fieldnames) & {"mission_profile", "score_basis", "operations_coverage", "survival_coverage"})
                self.assertEqual(len(list(reader)), len(self.rows))
            old_option = subprocess.run(command + ["--profile", "crewed"], text=True, capture_output=True)
            self.assertNotEqual(old_option.returncode, 0)
            self.assertIn("unrecognized arguments", old_option.stderr)


if __name__ == "__main__":
    unittest.main()
