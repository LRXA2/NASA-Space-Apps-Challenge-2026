"""EDA mapping keeps real quantities and historical/nonlocal evidence separate."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import run_pipeline as engine
import export_eda_input as exporter


def context():
    policy = engine.read_json(HERE / "environmental_policy.json")
    metric = next(m for m in policy["metrics"] if m["id"] == "reference_ldex_current_e_per_s")
    row = dict(id="a", candidate_id="Moon_site", start_utc="2023-06-01T00:00:00Z", stop_utc="2023-12-01T00:00:00Z", evidence_ref="fixture.json")
    row[metric["column"]] = "-3"
    meta = dict(body="Moon", basis="observed", quality="context_only", scope="orbital", source="Fictional unit-test data",
                unit=metric["unit"], quantity=metric["quantity"], support_count=1, temporal_support="window",
                evidence_start_utc="2013-10-24T00:00:00Z", evidence_stop_utc="2014-04-19T00:00:00Z", time_relation="historical_reference")
    return policy, metric, row, meta


class EdaInputTests(unittest.TestCase):
    def test_historical_signed_dust_is_context_not_deposition_or_zero(self):
        policy, metric, row, meta = context()
        item = engine.qualify(row, metric, meta, policy["mode"])
        self.assertEqual(item["status"], "Context_only")
        self.assertEqual(item["value"], -3)
        self.assertEqual(item["evidence_start_utc"], meta["evidence_start_utc"])

    def test_context_cannot_enter_hard_gates(self):
        policy, metric, _, _ = context()
        policy["hard_rules"] = [dict(id="invalid", metric=metric["id"], operator="le", limit=None, reason="Unit test")]
        with self.assertRaisesRegex(ValueError, "Context-only measurements"):
            engine.validate_policy(policy)

    def test_context_cannot_enter_soft_preferences(self):
        policy, metric, _, _ = context()
        policy["mode"] = "exploratory"
        domain = next(d for d in policy["domains"] if d["id"] == "dust")
        domain.update(weight=1, preferences=[dict(metric=metric["id"], direction="lower", lower=0, upper=1, weight=1, reason="Test", source="Test")])
        with self.assertRaisesRegex(ValueError, "Context-only measurements"):
            engine.validate_policy(policy)

    def test_nonmatching_current_context_is_not_historical_fallback(self):
        policy, metric, row, meta = context()
        meta["time_relation"] = "requested_window"
        item = engine.qualify(row, metric, meta, policy["mode"])
        self.assertEqual(item["status"], "Unknown")

    def test_candidate_point_context_requires_exact_id(self):
        policy, metric, row, meta = context()
        meta.update(scope="candidate_points", candidate_id="another_site")
        self.assertEqual(engine.qualify(row, metric, meta, policy["mode"])["status"], "Unknown")

    def test_invalid_context_time_or_units_is_an_error(self):
        policy, metric, row, meta = context()
        wrong = deepcopy(meta); wrong["unit"] = "mg/m2/day"
        with self.assertRaisesRegex(ValueError, "unit/quantity"):
            engine.qualify(row, metric, wrong, policy["mode"])
        wrong = deepcopy(meta); wrong["evidence_stop_utc"] = wrong["evidence_start_utc"]
        with self.assertRaisesRegex(ValueError, "invalid period"):
            engine.qualify(row, metric, wrong, policy["mode"])

    def test_daily_summary_uses_equal_day_weight_and_explicit_span(self):
        rows = [dict(series_id="s", date="2013-01-01T00:00:00Z", daily_median="-4", daily_max="2", valid_samples="100"),
                dict(series_id="s", date="2013-01-03T00:00:00Z", daily_median="8", daily_max="20", valid_samples="1")]
        value, support = exporter.daily_summary(rows, "s", engine.utc("2023-06-01T00:00:00Z"), engine.utc("2023-07-01T00:00:00Z"), "historical_reference")
        self.assertEqual(value, 2)
        self.assertEqual(support["expected_days"], 3)
        self.assertEqual(support["valid_days"], 2)
        self.assertTrue(support["evidence_start_utc"].startswith("2013"))
        value, support = exporter.daily_summary(rows, "s", engine.utc("2023-06-01T00:00:00Z"), engine.utc("2023-07-01T00:00:00Z"), "requested_window")
        self.assertEqual(value, "")
        self.assertEqual(support["valid_days"], 0)

    def test_missing_series_and_duplicate_days_fail(self):
        start, stop = engine.utc("2023-01-01T00:00:00Z"), engine.utc("2023-02-01T00:00:00Z")
        with self.assertRaisesRegex(ValueError, "absent"):
            exporter.daily_summary([], "s", start, stop, "requested_window")
        row = dict(series_id="s", date=start.isoformat(), daily_median="1", valid_samples="1")
        with self.assertRaisesRegex(ValueError, "Repeated"):
            exporter.daily_summary([row, row], "s", start, stop, "requested_window")

    def test_accepted_source_hash_is_checked_before_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); folder = root / "run"; folder.mkdir()
            source = folder / "value.csv"; source.write_text("x\n1\n")
            provenance = dict(status="complete", outputs=[dict(path="value.csv", sha256=engine.sha256(source))])
            (folder / "provenance.json").write_text(json.dumps(provenance))
            with patch.object(exporter, "HERE", root), patch.object(exporter, "DATA", root):
                self.assertEqual(exporter.accepted_table("run", "value.csv", {})[0], [{"x": "1"}])
                source.write_text("x\n2\n")
                with self.assertRaisesRegex(ValueError, "changed EDA"):
                    exporter.accepted_table("run", "value.csv", {})

    def test_default_schema_and_export_mapping_are_exact(self):
        policy = engine.read_json(HERE / "environmental_policy.json")
        sources = engine.read_json(HERE / "eda_sources.json")
        self.assertEqual({m["id"] for m in policy["metrics"]}, set(sources["features"]))
        self.assertEqual({m["domain"] for m in policy["metrics"]}, set(engine.DOMAIN_COLUMNS))
        self.assertFalse(any("deposition" in m["quantity"] for m in policy["metrics"]))

    def test_eight_category_demo_has_no_terrain_input_or_output(self):
        policy = engine.read_json(HERE / "examples/environment_only_policy.json")
        self.assertEqual({d["id"] for d in policy["domains"]}, engine.ENVIRONMENT_DOMAINS)
        self.assertFalse(any(m["domain"] == "terrain" for m in policy["metrics"]))
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "results.csv"
            record = engine.run(HERE / "examples/environment_only_sites.csv", output,
                                HERE / "examples/environment_only_policy.json")
            with output.open(newline="") as handle:
                import csv
                reader = csv.DictReader(handle)
                self.assertNotIn("terrain_score", reader.fieldnames)
                rows = list(reader)
            self.assertEqual(record["ranked_rows"], 1)
            self.assertEqual(float(rows[0]["final_rec_score"]), 80)
            self.assertEqual(rows[1]["hard_gate_status"], "Failed")
            self.assertEqual(rows[2]["hard_gate_status"], "Unknown")
            self.assertEqual(rows[3]["final_rec_score"], "")


if __name__ == "__main__":
    unittest.main()
