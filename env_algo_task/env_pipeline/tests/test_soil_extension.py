"""Experimental soil aggregation without changing existing domain or gate behaviour."""
from copy import deepcopy
import csv
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

HERE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("soil_engine", HERE / "env_pipeline.py")
engine = importlib.util.module_from_spec(spec)
spec.loader.exec_module(engine)


class SoilExtensionTests(unittest.TestCase):
    def setUp(self):
        self.config, self.digest = engine.load_config(HERE / "config.yml")
        self.rows = engine.read_csv(HERE / "sample_input.csv", self.config)

    def test_four_equal_categories_without_soil_gate(self):
        domain = self.config["domains"]["soil"]
        self.assertEqual(len(domain["metrics"]), 4)
        self.assertFalse(domain["hard_gates_enabled"])
        self.assertTrue(all(m["multiplier"] == 1 and m["hard_gate"] is None
                            for m in domain["metrics"]))

    def test_reference_band_boundaries(self):
        for metric in self.config["domains"]["soil"]["metrics"]:
            pref = metric["preference"]
            for key in ("lower", "upper"):
                self.assertAlmostEqual(engine.utility(pref[key], pref), 0)
            for key in ("preferred_lower", "preferred_upper"):
                self.assertAlmostEqual(engine.utility(pref[key], pref), 1)
            midpoint = (pref["lower"] + pref["preferred_lower"]) / 2
            self.assertAlmostEqual(engine.utility(midpoint, pref), .5)

    def test_existing_scores_gates_and_weighted_total(self):
        previous = deepcopy(self.config)
        del previous["domains"]["soil"]
        old = engine.assess(self.rows, previous, "baseline")
        new = engine.assess(self.rows, self.config, self.digest)
        for before, after in zip(old, new):
            self.assertEqual(before["hard_gate_status"], after["hard_gate_status"])
            self.assertEqual(before["fail_reason"], after["fail_reason"])
            for domain, column in engine.SCORES.items():
                if domain != "soil":
                    self.assertEqual(before[column], after[column])
            details = [d for d in json.loads(after["domain_score_details"])
                       if d["included_in_final_score"] and d["domain_score"] != ""]
            if after["final_habitability_score"] != "":
                expected = sum(d["domain_score"] * d["domain_multiplier"] for d in details)
                expected /= sum(d["domain_multiplier"] for d in details)
                self.assertAlmostEqual(after["final_habitability_score"], expected)

    def test_category_average(self):
        result = engine.assess(self.rows[:1], self.config, self.digest)[0]
        expected = sum(engine.utility(float(self.rows[0][m["column"]]), m["preference"])
                       for m in self.config["domains"]["soil"]["metrics"]) * 25
        self.assertAlmostEqual(result["soil_score"], expected)

    def test_missing_soil_uses_existing_available_data_policy(self):
        rows = deepcopy(self.rows[:1])
        for m in self.config["domains"]["soil"]["metrics"]:
            rows[0][m["column"]] = ""
        previous = deepcopy(self.config)
        del previous["domains"]["soil"]
        old = engine.assess(rows, previous, "baseline")[0]
        result = engine.assess(rows, self.config, self.digest)[0]
        self.assertEqual(result["soil_score"], "")
        self.assertEqual(result["final_habitability_score"], old["final_habitability_score"])

    def test_disabling_soil_restores_previous_total(self):
        disabled = deepcopy(self.config)
        disabled["domains"]["soil"]["enabled"] = False
        previous = deepcopy(self.config)
        del previous["domains"]["soil"]
        old = engine.assess(self.rows, previous, "baseline")
        new = engine.assess(self.rows, disabled, "disabled")
        self.assertEqual([r["final_habitability_score"] for r in old],
                         [r["final_habitability_score"] for r in new])

    def test_compact_output_keeps_final_score_last(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "results.csv"
            engine.run(HERE / "sample_input.csv", output, HERE / "config.yml", compact=True)
            with output.open(newline="", encoding="utf-8") as handle:
                reader = csv.DictReader(handle)
                self.assertIn("soil_score", reader.fieldnames)
                self.assertEqual(reader.fieldnames[-1], "final_habitability_score")
                self.assertEqual(len(list(reader)), len(self.rows))


if __name__ == "__main__":
    unittest.main()
