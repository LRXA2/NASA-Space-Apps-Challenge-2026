"""Availability/audit semantics only: file presence is not qualified exposure."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

sys.path[:0] = [str(Path(__file__).resolve().parents[1] / "shared"), str(Path(__file__).resolve().parents[1] / "Moon/Stage3_Requirements")]
import stage3_download_review as review


class DownloadReviewTests(unittest.TestCase):
    def test_missing_dates_and_longest_run_are_not_span(self):
        files = [{"relative_path": f"CRAT_L2_SEC_{d}_V01.TAB"}
                 for d in ["2024001", "2024002", "2024004"]]
        row = review.availability(files).iloc[0]
        self.assertEqual(row.unique_dates, 3)
        self.assertEqual(row.missing_dates_within_span, 1)
        self.assertEqual(row.longest_consecutive_available_dates, 2)
        self.assertFalse(row.two_year_uninterrupted_availability)

    def test_primary_secondary_and_platforms_are_separate(self):
        paths = ["CRAT_L2_SEC_2024001_V01.TAB", "CRAT_L2_PRI_2024001_V01.TAB",
                 "sci_sgps-l2-avg5m_g16_d20240101_v3-0-2.nc",
                 "sci_sgps-l2-avg5m_g19_d20240101_v3-0-2.nc"]
        result = review.availability([{"relative_path": p} for p in paths])
        self.assertEqual(set(result.instrument_family), {"CRaTER_SEC", "CRaTER_PRI", "GOES_16", "GOES_19"})
        self.assertTrue(result.scope.str.contains("not qualified").all())

    def test_versions_are_not_extra_observation_dates(self):
        result = review.availability([{"relative_path": f"CRAT_L2_SEC_2024001_V{v}.TAB"} for v in ["01", "02"]])
        self.assertEqual(result.iloc[0].files, 2)
        self.assertEqual(result.iloc[0].unique_dates, 1)

    def test_two_year_marker_requires_730_uninterrupted_dates(self):
        files = [{"relative_path": "CRAT_L2_SEC_" + d.strftime("%Y%j") + "_V01.TAB"}
                 for d in pd.date_range("2023-01-01", periods=730)]
        self.assertTrue(review.availability(files).iloc[0].two_year_uninterrupted_availability)
        self.assertFalse(review.availability(files[:-1]).iloc[0].two_year_uninterrupted_availability)

    def test_labels_do_not_count_as_extra_days(self):
        files = [{"relative_path": "CRAT_L2_SEC_2024001_V01." + ext} for ext in ["TAB", "xml"]]
        self.assertEqual(review.availability(files).iloc[0].files, 1)

    def test_verified_job_with_missing_payload_is_held(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inventory = root / "inventory.json"
            inventory.write_text(json.dumps({"files": [{"relative_path": "absent.nc", "url": "https://example.invalid/file"}]}))
            results = root / "results.json"
            results.write_text(json.dumps([{"key": "D08", "status": "verified_existing", "checkpoint": str(inventory)}]))
            with patch.object(review, "CONFIG", root / "config.json"), contextlib.redirect_stdout(io.StringIO()):
                review.freeze(results, root)
            config = json.loads((root / "config.json").read_text())
            self.assertEqual(config["ready_files"], [])
            self.assertEqual(len(config["holds"]), 1)

    def test_inventory_must_be_inside_selected_root(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            selected = root / "selected"
            selected.mkdir()
            results = selected / "results.json"
            results.write_text(json.dumps([{"key": "D08", "status": "downloaded", "checkpoint": str(root / "outside.json")}]))
            with self.assertRaisesRegex(ValueError, "outside"):
                review.freeze(results, selected)

    def test_changed_frozen_snapshot_fails_before_processing(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "config.json"
            config.write_text(json.dumps({"schema": 1, "result_snapshot": [], "result_snapshot_sha256": "invalid"}))
            with patch.object(review, "CONFIG", config), self.assertRaisesRegex(ValueError, "snapshot identity"):
                review.execute(sample=True)


if __name__ == "__main__":
    unittest.main()
