"""Optional assessment dates never erase evidence chronology or mix rank windows."""
from copy import deepcopy
import csv
import json
from pathlib import Path
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import run_pipeline as engine
import export_eda_input as exporter


def fixture():
    policy = engine.read_json(HERE / "examples/environment_only_policy.json")
    rows = engine.load_rows(HERE / "examples/environment_only_sites.csv", engine.validate_policy(policy)[0])
    meta = engine.read_json(HERE / "examples/environment_only_evidence.json")["rows"]
    return policy, rows, meta


class OptionalTimeTests(unittest.TestCase):
    def test_both_omitted_or_blank_is_allowed(self):
        self.assertEqual(engine.optional_window(), (None, None))
        self.assertEqual(engine.optional_window("", " "), (None, None))

    def test_partial_naive_and_reversed_dates_rejected(self):
        for start, stop in [(None, "2023-07-01T00:00:00Z"), ("2023-06-01T00:00:00Z", ""),
                            ("2023-06-01", "2023-07-01"),
                            ("2023-07-01T00:00:00Z", "2023-06-01T00:00:00Z")]:
            with self.subTest(start=start, stop=stop), self.assertRaises(ValueError):
                engine.optional_window(start, stop)

    def test_csv_time_columns_can_be_absent(self):
        policy, rows, _ = fixture()
        rows = [{k: v for k, v in r.items() if k not in {"start_utc", "stop_utc"}} for r in rows]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sites.csv"
            path.write_text(engine.csv_text(rows, list(rows[0])), encoding="utf-8")
            loaded = engine.load_rows(path, engine.validate_policy(policy)[0])
            self.assertTrue(all(r["start_utc"] == r["stop_utc"] == "" for r in loaded))

    def test_csv_empty_time_cells_allowed_but_one_date_rejected(self):
        policy, rows, _ = fixture()
        rows[0].update(start_utc="", stop_utc="")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sites.csv"
            path.write_text(engine.csv_text(rows[:1], list(rows[0])), encoding="utf-8")
            self.assertEqual(engine.load_rows(path, engine.validate_policy(policy)[0])[0]["start_utc"], "")
            rows[0]["start_utc"] = "2023-06-01T00:00:00Z"
            path.write_text(engine.csv_text(rows[:1], list(rows[0])), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Provide both"):
                engine.load_rows(path, engine.validate_policy(policy)[0])

    def test_dateless_assessment_uses_declared_local_summary_period(self):
        policy, rows, meta = fixture()
        row = {k: v for k, v in rows[0].items() if k not in {"start_utc", "stop_utc"}}
        result = engine.assess([row], policy, meta)[0][0]
        self.assertEqual(result["start_utc"], "")
        self.assertEqual(result["time_mode"], "source_spans")
        self.assertEqual(result["comparison_start_utc"], "2023-06-01T00:00:00+00:00")
        self.assertEqual(result["final_rec_score"], 80)

    def test_dateless_rows_with_different_local_periods_rank_separately(self):
        policy, rows, meta = fixture()
        left = {k: v for k, v in rows[0].items() if k not in {"start_utc", "stop_utc"}}
        right = {**left, "id": "another_period"}
        meta[right["id"]] = deepcopy(meta[left["id"]])
        meta[right["id"]]["demo_uv_W_m2"].update(start_utc="2024-06-01T00:00:00Z", stop_utc="2024-07-01T00:00:00Z")
        result = engine.assess([left, right], policy, meta)[0]
        self.assertEqual([r["rank"] for r in result], [1, 1])
        self.assertNotEqual(result[0]["comparison_start_utc"], result[1]["comparison_start_utc"])

    def test_noncontemporaneous_selected_inputs_withhold_aggregate(self):
        policy, rows, meta = fixture()
        row = {k: v for k, v in rows[0].items() if k not in {"start_utc", "stop_utc"}}
        policy["metrics"][0]["temporal_support"] = "window"
        meta[row["id"]]["solar_visibility_median"].update(temporal_support="window", start_utc="2024-06-01T00:00:00Z", stop_utc="2024-07-01T00:00:00Z")
        result = engine.assess([row], policy, meta)[0][0]
        self.assertEqual(result["hard_gate_status"], "Unknown")
        self.assertEqual(result["final_rec_score"], "")
        self.assertIn("different source spans", result["reason"])

    def test_omitting_requested_dates_does_not_invent_evidence_dates(self):
        policy, rows, meta = fixture()
        row = {k: v for k, v in rows[0].items() if k not in {"start_utc", "stop_utc"}}
        meta[row["id"]]["demo_uv_W_m2"].pop("start_utc")
        result = engine.assess([row], policy, meta)[0][0]
        self.assertEqual(result["final_rec_score"], "")
        self.assertEqual(result["uv_score_status"], "Unknown")

    def test_blank_evidence_dates_are_not_a_supported_window(self):
        policy, rows, meta = fixture()
        rows[0].update(start_utc="", stop_utc="")
        meta[rows[0]["id"]]["demo_uv_W_m2"].update(start_utc=" ", stop_utc=" ")
        result = engine.assess(rows[:1], policy, meta)[0][0]
        self.assertEqual(result["uv_score_status"], "Unknown")
        self.assertEqual(result["final_rec_score"], "")

    def test_unfiltered_daily_export_retains_each_source_span(self):
        rows = [dict(series_id="s", date="2013-01-01T00:00:00Z", daily_median="2", daily_max="4", valid_samples="1"),
                dict(series_id="s", date="2014-01-01T00:00:00Z", daily_median="6", daily_max="8", valid_samples="1")]
        value, support = exporter.daily_summary(rows, "s", None, None, "source_span")
        self.assertEqual(value, 4)
        self.assertEqual(support["time_relation"], "source_span")
        self.assertEqual(support["expected_days"], 366)
        self.assertEqual(support["valid_days"], 2)
        self.assertTrue(support["evidence_start_utc"].startswith("2013"))

    def test_export_rejects_partial_requested_window_before_reading_sources(self):
        with tempfile.TemporaryDirectory() as tmp, self.assertRaisesRegex(ValueError, "Provide both"):
            exporter.export(tmp, start="2023-06-01T00:00:00Z")

    def test_end_to_end_no_date_csv_has_explicit_output_mode(self):
        policy, rows, _ = fixture()
        row = {k: v for k, v in rows[0].items() if k not in {"start_utc", "stop_utc"}}
        row["evidence_ref"] = str((HERE / "examples/environment_only_evidence.json").resolve())
        with tempfile.TemporaryDirectory() as tmp:
            input_path, output = Path(tmp) / "sites.csv", Path(tmp) / "results.csv"
            input_path.write_text(engine.csv_text([row], list(row)), encoding="utf-8")
            record = engine.run(input_path, output, HERE / "examples/environment_only_policy.json")
            self.assertEqual(record["rows_without_requested_window"], 1)
            with output.open(newline="") as handle:
                result = next(csv.DictReader(handle))
            self.assertEqual(result["time_mode"], "source_spans")
            self.assertEqual(float(result["final_rec_score"]), 80)
            self.assertEqual(result["start_utc"], "")


if __name__ == "__main__":
    unittest.main()
