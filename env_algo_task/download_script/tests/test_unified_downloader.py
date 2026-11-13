"""Consolidation, exact retry budget, core threading and reference selections."""
from contextlib import redirect_stdout, redirect_stderr
import io
import json
from pathlib import Path
import sys
import tempfile
import threading
from unittest.mock import MagicMock, patch
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import download_environmental as env


class UnifiedDownloadTests(unittest.TestCase):
    def setUp(self):
        env.DEFAULT_OUTPUT.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix=".unified-test-", dir=env.DEFAULT_OUTPUT)
        self.root = Path(self.temp.name).resolve()
        self.assertTrue(self.root.is_relative_to(env.DEFAULT_OUTPUT.resolve()))
        self.addCleanup(self.temp.cleanup)
        env.STOP.clear()
        env.original_helpers()

    def test_public_default_runs_both_scopes_and_continues_after_failed_core(self):
        with patch.object(env, "core_main", return_value=1) as core, patch.object(env, "eda_main", return_value=0) as research, redirect_stdout(io.StringIO()):
            self.assertEqual(env.main(["--download", "--workers", "6"]), 1)
        core.assert_called_once()
        research.assert_called_once()
        for flags in [core.call_args.args[0], research.call_args.args[0]]:
            self.assertEqual(flags[flags.index("--connection-retries") + 1], "3")
            self.assertEqual(flags[flags.index("--attempts") + 1], "1")
            self.assertEqual(flags[flags.index("--workers") + 1], "6")
        self.assertIn("--continue-on-error", core.call_args.args[0])

    def test_default_preview_is_offline_and_does_not_create_output(self):
        output = self.root / "must-not-be-created"
        with patch.object(env, "session") as network, patch.object(env.subprocess, "run") as child, redirect_stdout(io.StringIO()):
            self.assertEqual(env.main(["--dry-run", "--output", str(output)]), 0)
        network.assert_not_called()
        child.assert_not_called()
        self.assertFalse(output.exists())

    def test_explicit_research_selection_does_not_restore_unselected_core(self):
        with patch.object(env, "core_main") as core, patch.object(env, "eda_main", return_value=0) as eda, redirect_stdout(io.StringIO()):
            self.assertEqual(env.main(["--scope", "all", "--datasets", "D13", "R02"]), 0)
        core.assert_not_called()
        flags = eda.call_args.args[0]
        start = flags.index("--datasets")
        self.assertEqual(flags[start + 1:start + 3], ["D13", "R02"])

    def test_reference_scope_contains_only_two_actual_reference_datasets(self):
        with patch.object(env, "core_main") as core, patch.object(env, "eda_main", return_value=0) as eda, redirect_stdout(io.StringIO()):
            self.assertEqual(env.main(["--scope", "references"]), 0)
        core.assert_not_called()
        flags = eda.call_args.args[0]
        self.assertEqual(flags[flags.index("--datasets") + 1:flags.index("--datasets") + 3], ["R01", "R02"])
        client = MagicMock()
        groups, info = env.discover(client, env.catalog()["R02"], 5, 1, 1, {}, self.root)
        client.get.assert_not_called()
        self.assertEqual(len(groups), 1)
        self.assertEqual(len(groups[0]), 22)
        self.assertEqual(sum(e["url"].endswith(".tab") for e in groups[0]), 6)
        self.assertTrue(all(e["url"].startswith("https://pds-geosciences.wustl.edu/") for e in groups[0]))
        self.assertFalse(any("thumbnail" in e["url"] for e in groups[0]))

    def test_zero_retries_means_one_attempt_not_an_infinite_loop(self):
        operation = MagicMock(side_effect=env.requests.Timeout("offline"))
        with self.assertRaises(env.requests.Timeout), patch.object(env.time, "sleep") as sleep:
            env.retry_connections(operation, "fixture", MagicMock(), retries=0)
        self.assertEqual(operation.call_count, 1)
        sleep.assert_not_called()

    def test_transient_http_gets_three_retries_but_auth_and_tls_get_none(self):
        for status, expected in [(503, 4), (429, 4), (401, 1), (403, 1), (404, 1)]:
            response = MagicMock(status_code=status)
            operation = MagicMock(side_effect=env.requests.HTTPError(response=response))
            with self.subTest(status=status), patch.object(env.time, "sleep"), redirect_stderr(io.StringIO()), self.assertRaises(env.requests.HTTPError):
                env.retry_connections(operation, "fixture", MagicMock())
            self.assertEqual(operation.call_count, expected)
        operation = MagicMock(side_effect=env.requests.exceptions.SSLError("untrusted certificate"))
        with self.assertRaises(env.requests.exceptions.SSLError):
            env.retry_connections(operation, "fixture", MagicMock())
        self.assertEqual(operation.call_count, 1)

    def test_moon_transfer_releases_own_lock_and_does_not_remove_another_instances_lock(self):
        item = {"relative_path": "moon/test.TIF"}
        path = self.root / item["relative_path"]
        path.parent.mkdir()
        lock = path.with_name(path.name + ".download.lock")
        args = env.argparse.Namespace(timeout=5, connection_retries=3)
        with patch.object(env, "download_file", return_value=path) as download, patch.object(env, "session"):
            self.assertEqual(env.moon_support_transfer(item, self.root, args), path)
        self.assertEqual(download.call_args.args[-1], 1)
        self.assertFalse(lock.exists())
        lock.write_text("another process", encoding="utf-8")
        with self.assertRaises(FileExistsError), patch.object(env, "download_file") as download:
            env.moon_support_transfer(item, self.root, args)
        download.assert_not_called()
        self.assertEqual(lock.read_text(), "another process")

    def test_core_climate_threads_files_and_continues_after_exactly_four_failed_calls(self):
        import download_terraclimate as climate
        destination = self.root / "earth/climate"
        catalogue = {f"TERRACLIMATE_ALL/data/TerraClimate_tmin_{year}.nc": "fixed" for year in [2015, 2016]}
        rendezvous = threading.Barrier(2)
        calls, mutex = [], threading.Lock()

        def download(client, path, source, variable, year, bounds, timeout, attempts):
            self.assertEqual(attempts, 1)
            with mutex:
                first = year not in calls
                calls.append(year)
            if first:
                rendezvous.wait(timeout=5)
            if year == 2015:
                raise env.requests.Timeout("fixture dropped connection")
            path.write_bytes(b"fixture")
            return "downloaded"

        flags = ["earth-climate-expansion", "--data-root", str(self.root), "--output", str(destination),
                 "--bbox", "0", "0", "1", "1", "--variables", "tmin", "--start-year", "2015", "--end-year", "2016",
                 "--workers", "2", "--download"]
        with patch.object(env, "metadata", return_value=(b"<catalog/>", climate.CATALOG)), patch.object(climate, "catalog_entries", return_value=catalogue), patch.object(climate, "download", side_effect=download), patch.object(env, "session"), patch.object(env.STOP, "wait", return_value=False), redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(env.core_worker(flags), 1)
        self.assertEqual(calls.count(2015), 4)
        self.assertEqual(calls.count(2016), 1)
        record = json.loads(next((destination / "manifests").glob("*_run.json")).read_text())
        self.assertEqual(record["status"], "failed")
        self.assertEqual({job["status"] for job in record["jobs"]}, {"failed", "downloaded"})
        self.assertFalse(list(destination.rglob("*.download.lock")))
        error_log = next((self.root / "manifests/core").glob("*/*/errors.txt"))
        self.assertIn("fixture dropped connection", error_log.read_text())

    def test_diviner_core_keeps_full_tables_and_labels_and_publishes_original_csv_shape(self):
        import download_diviner_south_polar as diviner
        entries = [diviner.RemoteFile("seasonal", "test" + ext, "https://example.test/test" + ext, None)
                   for ext in [".tab", ".xml"]]
        destination = self.root / "moon/diviner"

        def file_item(client, entry, dataset, timeout):
            return {"dataset": dataset, "url": entry["url"], "relative_path": entry["relative_path"],
                    "size_bytes": 8, "etag": None, "last_modified": None}

        with patch.object(diviner, "fetch_inventory", return_value=entries), patch.object(env, "file_item", side_effect=file_item), patch.object(env, "run_downloads", return_value=0) as download, patch.object(env, "session"), redirect_stdout(io.StringIO()):
            self.assertEqual(env.core_worker(["lunar-temperature", "--data-root", str(self.root),
                                             "--output", str(destination), "--download"]), 0)
        self.assertEqual(len(download.call_args.args[0]["files"]), 2)
        text = (destination / "download_manifest.csv").read_text()
        self.assertIn("collection,filename,size_bytes,size_gib,url", text)
        self.assertIn("seasonal,test.tab,8,", text)
        self.assertIn("seasonal,test.xml,8,", text)

    def test_auth_sources_stay_kiv_without_a_download_request(self):
        client = MagicMock()
        for key in ["D21", "D22", "D23", "D24"]:
            groups, info = env.discover(client, env.catalog()[key], 5, 1, 1, {}, self.root)
            self.assertEqual(groups, [])
            self.assertEqual(info["status"], "login_required")
        client.get.assert_not_called()

    def test_support_scope_dispatches_in_process_without_recursive_child_launch(self):
        with patch.object(env, "core_main") as core, patch.object(env, "moon_support_main", return_value=0) as moon, redirect_stdout(io.StringIO()):
            self.assertEqual(env.main(["--scope", "moon-support", "--from-inventory", "latest", "--download"]), 0)
        core.assert_not_called()
        moon.assert_called_once()
        flags = moon.call_args.args[0]
        self.assertEqual(flags[flags.index("--from-inventory") + 1], "latest")

    def test_child_interrupt_does_not_launch_remaining_scopes(self):
        interrupted = env.subprocess.CalledProcessError(130, ["fixture child"])
        with patch.object(env.subprocess, "run", side_effect=interrupted) as child, redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(env.core_main(["--continue-on-error", "--output", str(self.root)]), 130)
        self.assertEqual(child.call_count, 1)


if __name__ == "__main__":
    unittest.main()
