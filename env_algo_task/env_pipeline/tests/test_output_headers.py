"""Readable exported headers change labels only, not assessment values."""
import csv
from pathlib import Path
import sys
import tempfile
import unittest

import yaml

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import env_pipeline as engine
from test_env_pipeline import config, metric


class OutputHeaderTests(unittest.TestCase):
    def test_readable_csv_headers_and_internal_compatibility(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "config.yml").write_text(yaml.safe_dump(config()))
            (root / "sites.csv").write_text("id,sun,uv\na,.8,2\n")
            internal = engine.run(root / "sites.csv", root / "results.csv", root / "config.yml")[0]
            with (root / "results.csv").open(newline="") as handle:
                reader = csv.DictReader(handle)
                headers = reader.fieldnames
                exported = next(reader)
            for old, new in engine.OUTPUT_COLUMN_NAMES.items():
                self.assertNotIn(old, headers)
                self.assertIn(new, headers)
                self.assertEqual(exported[new], str(internal[old]))
            self.assertEqual(float(exported["final_recommendation_score"]), 80)
            self.assertEqual(internal["final_rec_score"], 80)
            self.assertEqual(len(headers), len(set(headers)))

    def test_radiation_value_and_gate_results_are_preserved(self):
        cfg = config()
        cfg["domains"]["uv"]["include_in_score"] = False
        cfg["domains"]["radiation"].update(include_in_score=True, metrics=[metric("radiation_input", 10, direction="lower")])
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "config.yml").write_text(yaml.safe_dump(cfg))
            (root / "sites.csv").write_text("id,sun,uv,radiation_input\na,.8,2,2\nb,.4,2,2\n")
            engine.run(root / "sites.csv", root / "results.csv", root / "config.yml")
            with (root / "results.csv").open(newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(float(rows[0]["radiation_score"]), 80)
            self.assertEqual(rows[0]["radiation_score_status"], "Scored")
            self.assertEqual(float(rows[0]["final_recommendation_score"]), 80)
            self.assertEqual(rows[1]["hard_gate_status"], "Failed")
            self.assertEqual(rows[1]["final_recommendation_score"], "")


if __name__ == "__main__":
    unittest.main()
