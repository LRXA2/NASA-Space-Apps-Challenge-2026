"""Small domain-only fixtures and optional compact exports."""
import csv
from pathlib import Path
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import env_pipeline as engine


class CompactTestDataTests(unittest.TestCase):
    def test_fixture_is_mostly_populated_and_domain_only(self):
        with (HERE / "inputs/sites_test.csv").open(newline="") as handle:
            reader = csv.DictReader(handle)
            rows = list(reader)
            self.assertEqual(reader.fieldnames, ["ID", *engine.SCORES])
        self.assertEqual(len(rows), 30)
        self.assertEqual(sum(r[d] == "" for r in rows for d in engine.SCORES), 4)
        self.assertTrue(all(sum(r[d] != "" for d in engine.SCORES) >= 8 for r in rows))

    def test_compact_export_preserves_zero_and_missing_scores(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "results.csv"
            results = engine.run(HERE / "inputs/sites_test.csv", path, HERE / "config_test.yml", compact=True)
            with path.open(newline="") as handle:
                reader = csv.DictReader(handle)
                output = list(reader)
                self.assertEqual(reader.fieldnames, ["ID", *engine.SCORES])
            self.assertEqual(len(output), 30)
            for raw, compact in zip(results, output):
                self.assertEqual(raw["id"], compact["ID"])
                for domain, score_column in engine.SCORES.items():
                    self.assertEqual(str(raw[score_column]), compact[domain])
            self.assertEqual(results[20]["hard_gate_status"], "Failed")
            self.assertTrue(all(float(output[20][d]) == 0 for d in engine.SCORES))
            self.assertEqual(sum(r["hard_gate_status"] == "Unknown" for r in results), 4)

    def test_uppercase_id_input_keeps_internal_contract(self):
        cfg, _ = engine.load_config(HERE / "config_test.yml")
        rows = engine.read_csv(HERE / "inputs/sites_test.csv", cfg)
        self.assertTrue(all("id" in r and "ID" not in r for r in rows))


if __name__ == "__main__":
    unittest.main()
