from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import download_environmental as eda
import download_environmental as support
import download_environmental as wrapper


class ErrorContinuationTests(unittest.TestCase):
    def setUp(self):
        eda.DEFAULT_OUTPUT.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix=".continuation-test-", dir=eda.DEFAULT_OUTPUT)
        self.root = Path(self.temp.name).resolve()
        self.assertTrue(self.root.is_relative_to(eda.DEFAULT_OUTPUT.resolve()))
        self.addCleanup(self.temp.cleanup)
        eda.STOP.clear()

    def logs(self):
        handlers = eda.start_debug_log(self.root)
        def close():
            for handler in handlers:
                eda.LOG.removeHandler(handler)
                handler.close()
        self.addCleanup(close)

    def item(self, name="good.csv"):
        return {"dataset": "D13", "url": "https://example.test/" + name,
                "relative_path": "moon/eda_pilots/D13/" + name, "size_bytes": 4,
                "etag": '"v1"', "last_modified": None, "metadata": False}

    def cached(self, files):
        path = self.root / "old_run/run.json"
        path.parent.mkdir()
        path.write_text("{}")
        path.with_name("zenodo_record.json").write_text("{}")
        return patch.object(support, "saved_inventory", return_value=(path, files))

    def moon_item(self, name, fmt):
        return {"filename": name, "url": "https://example.test/" + name,
                "relative_path": "moon/support/" + name, "size_bytes": 4, "format": fmt}

    def test_transient_download_failure_retries_and_logs_before_success(self):
        self.logs()
        item = self.item()
        response = MagicMock()
        response.__enter__.return_value = response
        response.status_code = 200
        response.url = item["url"]
        response.headers = {"ETag": '"v1"'}
        response.iter_content.return_value = [b"data"]
        client = MagicMock()
        client.__enter__.return_value = client
        client.get.side_effect = [eda.requests.Timeout("fixture transient timeout"), response]
        with patch.object(eda, "session", return_value=client), patch.object(eda.time, "sleep") as sleep, redirect_stdout(io.StringIO()):
            self.assertEqual(eda.transfer(item, self.root, 5, 2), "downloaded")
        self.assertEqual(client.get.call_count, 2)
        sleep.assert_called_once()
        self.assertEqual((self.root / item["relative_path"]).read_bytes(), b"data")
        self.assertIn("fixture transient timeout", (self.root / "errors.txt").read_text())

    def test_inventory_skips_bad_candidate_but_keeps_later_science_group(self):
        self.logs()
        cfg = eda.catalog()["D13"]
        args = eda.argparse.Namespace(cookies=None, timeout=5, pages_per_dataset=2, files_per_dataset=2,
                                     max_file_mib=1, max_dataset_mib=1, max_total_mib=1)
        groups = [[{"url": "https://example.test/bad.csv"}], [{"url": "https://example.test/good.csv"}]]
        client = MagicMock()
        client.__enter__.return_value = client
        with patch.object(eda, "session", return_value=client), patch.object(eda, "discover", return_value=(groups, {})), patch.object(eda, "file_item", side_effect=[eda.requests.HTTPError("503 candidate failed"), self.item()]) as make_file, redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            record = eda.inventory([cfg], self.root, self.root, args, {})
        self.assertEqual(make_file.call_count, 2)
        self.assertEqual(len(record["files"]), 1)
        self.assertEqual(record["datasets"][0]["status"], "partial_inventory")
        self.assertEqual(len(record["datasets"][0]["file_errors"]), 1)
        self.assertIn("503 candidate failed", (self.root / "errors.txt").read_text())

    def test_eda_file_failure_is_logged_while_other_worker_finishes(self):
        items = [self.item("bad.csv"), self.item()]
        record = {"schema": 1, "pilot_only": True, "files": items,
                  "datasets": [{"id": "D13", "status": "planned"}]}
        pinned = self.root / "inventory.json"
        pinned.write_text(json.dumps(record))
        def transfer(item, *args):
            if item["relative_path"].endswith("bad.csv"):
                raise RuntimeError("fixture attempts exhausted")
            return "downloaded"
        with patch.object(eda, "transfer", side_effect=transfer) as worker, redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(eda.eda_main(["--output", str(self.root), "--from-inventory", str(pinned), "--download"]), 1)
        self.assertEqual(worker.call_count, 2)
        log = next((self.root / "manifests/eda_datasets").glob("*/errors.txt"))
        self.assertIn("fixture attempts exhausted", log.read_text())
        result = json.loads(log.with_name("download.json").read_text())
        self.assertEqual(result["status"], "failed")
        self.assertEqual({r["status"] for r in result["transfers"]}, {"failed", "downloaded"})

    def test_moon_transfer_failure_does_not_stop_remaining_files_or_verified_archives(self):
        files = [self.moon_item("bad.TIF", "TIF"), self.moon_item("good.TIF", "TIF"),
                 self.moon_item(support.REGIONS[0] + ".zip", "ZIP")]
        def outcome(client, item, *args):
            if item["filename"] == "bad.TIF":
                raise RuntimeError("503 exhausted")
            return self.root
        with self.cached(files), patch.object(support, "download_file", side_effect=outcome) as download, patch.object(support, "write_unit_policy"), patch.object(support, "extract_archive") as extract, redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(support.moon_support_main(["--output", str(self.root), "--from-inventory", "latest", "--download"]), 1)
        self.assertEqual(download.call_count, 3)
        extract.assert_called_once()
        log = next((self.root / "manifests/moon_support").glob("*/errors.txt"))
        self.assertIn("503 exhausted", log.read_text())
        record = json.loads(log.with_name("run.json").read_text())
        self.assertEqual(record["status"], "failed")
        self.assertEqual([f["status"] for f in record["files"]], ["failed", "verified_present", "verified_present"])
        self.assertEqual(record["errors"][0]["stage"], "download")

    def test_failed_label_skips_only_dependent_unit_policy(self):
        files = [self.moon_item("bad.lbl", "LBL"), self.moon_item("good.lbl", "LBL"),
                 self.moon_item(support.REGIONS[0] + ".zip", "ZIP")]
        def outcome(client, item, *args):
            if item["filename"] == "bad.lbl":
                raise RuntimeError("missing label")
            return self.root
        with self.cached(files), patch.object(support, "download_file", side_effect=outcome), patch.object(support, "write_unit_policy") as policy, patch.object(support, "extract_archive") as extract, redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(support.moon_support_main(["--output", str(self.root), "--from-inventory", "latest", "--download"]), 1)
        policy.assert_not_called()
        extract.assert_called_once()
        manifest = next((self.root / "manifests/moon_support").glob("*/run.json"))
        self.assertEqual(json.loads(manifest.read_text())["unit_policy_status"], "skipped_missing_labels")

    def test_failed_extraction_does_not_stop_other_verified_archives(self):
        files = [self.moon_item(r + ".zip", "ZIP") for r in support.REGIONS[:2]]
        with self.cached(files), patch.object(support, "download_file"), patch.object(support, "write_unit_policy"), patch.object(support, "extract_archive", side_effect=[zipfile.BadZipFile("damaged fixture archive"), None]) as extract, redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(support.moon_support_main(["--output", str(self.root), "--from-inventory", "latest", "--download"]), 1)
        self.assertEqual(extract.call_count, 2)
        manifest = next((self.root / "manifests/moon_support").glob("*/run.json"))
        record = json.loads(manifest.read_text())
        self.assertEqual(record["errors"][0]["stage"], "extraction")
        self.assertEqual(record["status"], "failed")

    def test_wrapper_continue_option_logs_failure_and_runs_other_jobs(self):
        failures = [subprocess.CalledProcessError(9, ["fixture child"]), None, None, None, None]
        with patch.object(wrapper.subprocess, "run", side_effect=failures) as run, redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(wrapper.core_main(["--output", str(self.root), "--continue-on-error"]), 1)
        self.assertEqual(run.call_count, 5)
        log = next((self.root / "manifests/environmental_runner").glob("*/errors.txt"))
        self.assertIn("earth-climate", log.read_text())


if __name__ == "__main__":
    unittest.main()
