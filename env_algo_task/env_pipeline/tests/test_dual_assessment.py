"""Independent assessments reuse the legacy scorer without coupling their gates."""
from copy import deepcopy
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import env_pipeline as engine


class DualAssessmentTests(unittest.TestCase):
    def setUp(self):
        self.config, self.digest = engine.load_config(HERE / "config.yml")
        self.rows = engine.read_csv(HERE / "sample_input.csv", self.config)

    def evaluate(self, config=None, rows=None, profile=None):
        return engine.assess(self.rows if rows is None else rows,
                             self.config if config is None else config, self.digest, profile=profile)

    def test_independent_weights_and_default_allocation(self):
        cfg = self.config
        for profile in cfg["profiles"].values():
            self.assertEqual(sum(profile["operations"].values()), 100)
            self.assertEqual(sum(profile["survival"].values()), 100)
            self.assertFalse(set(profile["operations"]) & set(profile["survival"]))
            self.assertFalse({"seismic", "exosphere"} & (set(profile["operations"]) | set(profile["survival"])))
        self.assertTrue(all(not d["hard_gates_enabled"] for d in cfg["domains"].values()))

    def test_aggregates_match_unrounded_contributions(self):
        for row in self.evaluate():
            for name in engine.ASSESSMENTS:
                details = json.loads(row[f"{name}_details"]["domain_score_details"])
                parts = [d for d in details if d["included_in_final_score"] and d["domain_score"] != ""]
                expected = sum(d["domain_score"] * d["domain_multiplier"] for d in parts)
                expected /= sum(d["domain_multiplier"] for d in parts)
                self.assertAlmostEqual(row[f"{name}_score"], expected)
                self.assertEqual(row[f"{name}_status"], "Pass")

    def test_weight_scale_does_not_change_result(self):
        cfg = deepcopy(self.config)
        for weights in cfg["profiles"][cfg["mission_profile"]].values():
            for domain in weights:
                weights[domain] *= 3
        before, after = self.evaluate(), self.evaluate(cfg)
        for a, b in zip(before, after):
            for name in engine.ASSESSMENTS:
                self.assertAlmostEqual(a[f"{name}_score"], b[f"{name}_score"])

    def test_context_cannot_change_either_score(self):
        rows = deepcopy(self.rows[:1])
        rows[0].update(historical_median_vertical_seismic_rms_counts="999999",
                       historical_median_orbital_helium_density_per_cm3="999999")
        before, after = self.evaluate(rows=self.rows[:1])[0], self.evaluate(rows=rows)[0]
        for name in engine.ASSESSMENTS:
            self.assertEqual(before[f"{name}_score"], after[f"{name}_score"])

    def test_profiles_change_weights_not_measurements(self):
        before = deepcopy(self.rows)
        crewed = self.evaluate(profile="crewed")
        uncrewed = self.evaluate(profile="uncrewed")
        self.assertEqual(self.rows, before)
        self.assertEqual([r["operations_score"] for r in crewed], [r["operations_score"] for r in uncrewed])
        self.assertTrue(any(a["survival_score"] != b["survival_score"] for a, b in zip(crewed, uncrewed)))
        with self.assertRaises(ValueError):
            self.evaluate(profile="undefined")

    def test_failure_is_local_to_its_assessment(self):
        cfg = deepcopy(self.config)
        settings = cfg["assessments"]["operations"]
        settings["domain_overrides"]["communications_geometry"] = {"hard_gates_enabled": True}
        settings["metric_overrides"]["window_minimum_link_margin_db"] = {
            "role": "gate", "hard_gate": {"operator": "above_threshold", "threshold": 0}}
        rows = deepcopy(self.rows[:1])
        rows[0]["window_minimum_link_margin_db"] = "-1"
        row = self.evaluate(cfg, rows)[0]
        self.assertEqual(row["operations_status"], "Fail")
        self.assertEqual(row["operations_score"], "")
        self.assertIn("window_minimum_link_margin_db", row["operations_fail_reason"])
        self.assertEqual(row["survival_status"], "Pass")
        self.assertNotEqual(row["survival_score"], "")
        rows[0]["window_minimum_link_margin_db"] = "0"
        self.assertEqual(self.evaluate(cfg, rows)[0]["operations_status"], "Pass")

    def test_strict_missing_is_local(self):
        cfg = deepcopy(self.config)
        cfg["pipeline_mode"] = "strict"
        rows = deepcopy(self.rows[:1])
        rows[0]["soil_feo_wt_percent"] = ""
        row = self.evaluate(cfg, rows)[0]
        self.assertEqual(row["operations_status"], "Unknown")
        self.assertEqual(row["operations_score"], "")
        self.assertEqual(row["survival_status"], "Pass")
        self.assertNotEqual(row["survival_score"], "")

    def test_missing_window_for_supplied_gate_remains_unknown(self):
        cfg = deepcopy(self.config)
        settings = cfg["assessments"]["operations"]
        settings["domain_overrides"]["communications_geometry"] = {"hard_gates_enabled": True}
        settings["metric_overrides"]["window_minimum_link_margin_db"] = {
            "role": "gate", "hard_gate": {"operator": "above_threshold", "threshold": 0}}
        rows = deepcopy(self.rows[:1])
        rows[0].update(start_utc="", stop_utc="", window_minimum_link_margin_db="1")
        result = self.evaluate(cfg, rows)[0]
        self.assertEqual(result["operations_status"], "Unknown")
        self.assertEqual(result["operations_score"], "")
        self.assertEqual(result["survival_status"], "Pass")

    def test_reenabled_domain_still_validates_physical_input(self):
        cfg = deepcopy(self.config)
        cfg["domains"]["soil"]["enabled"] = False
        cfg["assessments"]["operations"]["domain_overrides"]["soil"] = {"enabled": True}
        row = deepcopy(self.rows[0])
        row["soil_feo_wt_percent"] = "101"
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "invalid.csv"
            with path.open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=list(row))
                writer.writeheader()
                writer.writerow(row)
            with self.assertRaises(ValueError):
                engine.read_csv(path, cfg)

    def test_available_data_omits_missing_not_zero(self):
        rows = deepcopy(self.rows[:1])
        rows[0]["soil_feo_wt_percent"] = ""
        result = self.evaluate(rows=rows)[0]
        self.assertEqual(result["operations_coverage"], "6/7")
        self.assertEqual(result["operations_status"], "Pass")
        for domain in self.config["profiles"]["crewed"]["operations"]:
            for metric in self.config["domains"][domain]["metrics"]:
                if metric["role"] == "score":
                    rows[0][metric["column"]] = ""
        result = self.evaluate(rows=rows)[0]
        self.assertEqual(result["operations_score"], "")
        self.assertEqual(result["operations_status"], "Unknown")
        self.assertEqual(result["survival_status"], "Pass")

    def test_overlapping_domain_can_have_independent_rules(self):
        cfg = deepcopy(self.config)
        cfg["profiles"]["crewed"]["survival"]["solar_illumination"] = 10
        cfg["assessments"]["survival"]["metric_overrides"]["median_sun_visibility_fraction"] = {
            "preference": {"direction": "lower", "lower": 0, "upper": 1}}
        row = self.evaluate(cfg, self.rows[:1])[0]
        self.assertAlmostEqual(row["operations_solar_illumination_score"] + row["survival_solar_illumination_score"], 100)
        self.assertNotEqual(row["operations_solar_illumination_score"], row["survival_solar_illumination_score"])

    def test_disabling_domain_removes_inputs_gates_and_weight(self):
        cfg = deepcopy(self.config)
        cfg["domains"]["soil"]["enabled"] = False
        row = self.evaluate(cfg, self.rows[:1])[0]
        self.assertEqual(row["operations_soil_score"], "")
        cfg["assessments"]["operations"]["domain_overrides"]["dust"] = {"include_in_score": False}
        row = self.evaluate(cfg, self.rows[:1])[0]
        expected = (row["operations_solar_illumination_score"] * 40 + row["operations_communications_geometry_score"] * 35) / 75
        self.assertAlmostEqual(row["operations_score"], expected)

    def test_reference_numbers_are_pinned_not_input_scaled(self):
        domains = self.config["domains"]
        get = lambda name: next(m["preference"] for m in domains[name]["metrics"] if m["role"] == "score")
        self.assertEqual((get("radiation")["lower"], get("radiation")["upper"]), (24, 104.5))
        self.assertAlmostEqual(get("uv")["upper"], .026638514010)
        self.assertEqual(get("dust")["preferred_lower"], 14332.5)
        self.assertAlmostEqual(get("plasma_charging")["upper"], 32.918969440460)

    def test_no_input_or_configuration_mutation(self):
        before = deepcopy((self.config, self.rows))
        self.evaluate()
        self.assertEqual((self.config, self.rows), before)

    def test_malformed_or_unused_settings_rejected(self):
        for mutate in [
            lambda c: c["profiles"]["crewed"]["operations"].update(typo=1),
            lambda c: c["profiles"]["crewed"]["operations"].update(soil=0),
            lambda c: c["assessments"]["operations"].update(typo=True),
            lambda c: c["assessments"]["operations"]["domain_overrides"].update(thermal={"enabled": True}),
            lambda c: c["assessments"]["survival"]["metric_overrides"].update(typo={}),
        ]:
            cfg = deepcopy(self.config)
            mutate(cfg)
            with self.assertRaises(ValueError):
                engine.validate_config(cfg)

    def test_legacy_three_remains_behaviourally_compatible(self):
        spec = importlib.util.spec_from_file_location("archived_engine", HERE / "legacy_3/env_pipeline.py")
        legacy = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(legacy)
        cfg, digest = legacy.load_config(HERE / "legacy_3/config.yml")
        rows = legacy.read_csv(HERE / "sample_input.csv", cfg)
        self.assertEqual(engine.assess(rows, cfg, digest), legacy.assess(rows, cfg, digest))

    def test_exports_and_standalone_copy(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            for name in ["env_pipeline.py", "config.yml", "sample_input.csv"]:
                (folder / name).write_bytes((HERE / name).read_bytes())
            output = folder / "results.csv"
            result = subprocess.run([sys.executable, str(folder / "env_pipeline.py"),
                                     "--input", str(folder / "sample_input.csv"),
                                     "--output", str(output), "--profile", "uncrewed"],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            with output.open(newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                self.assertEqual(reader.fieldnames[-2:], ["operations_score", "survival_score"])
                self.assertNotIn("final_habitability_score", reader.fieldnames)
                self.assertEqual(len(list(reader)), len(self.rows))
            with self.assertRaises(FileExistsError):
                engine.run(HERE / "sample_input.csv", output, HERE / "config.yml")
            engine.run(HERE / "sample_input.csv", output, HERE / "config.yml", overwrite=True, compact=False)
            with output.open(newline="", encoding="utf-8") as f:
                row = next(csv.DictReader(f))
            self.assertIn("score_details", json.loads(row["operations_details"]))


if __name__ == "__main__":
    unittest.main()
