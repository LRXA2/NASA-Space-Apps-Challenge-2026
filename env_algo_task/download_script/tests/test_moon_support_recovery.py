from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import download_environmental as support
import download_environmental as entrypoint
import download_environmental as eda


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        support.DEFAULT_OUTPUT.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix=".support-recovery-test-", dir=support.DEFAULT_OUTPUT)
        self.root = Path(self.temp.name).resolve()
        self.assertTrue(self.root.is_relative_to(support.DEFAULT_OUTPUT.resolve()))
        self.addCleanup(self.temp.cleanup)

    def fixture(self):
        folder = self.root / "manifests/moon_support/20260101"
        folder.mkdir(parents=True)
        names = [*(r + ".zip" for r in support.REGIONS), "README.md"]
        publisher = {"id": int(support.ZENODO_RECORD), "files": [
            {"key": name, "size": 11, "checksum": "md5:" + "a" * 32,
             "links": {"self": f"https://zenodo.org/api/records/{support.ZENODO_RECORD}/files/{name}/content"}}
            for name in names]}
        files = support.select_sdem_files(publisher)
        for name in support.LOLA_FILES:
            files.append({"filename": name, "url": "https://pgda.gsfc.nasa.gov/data/LOLA_20mpp/" + name,
                          "relative_path": "moon/lola_product90/large_area_dem/" + name, "format": "TIF", "size_bytes": 11})
        _, illum, _ = support.original_helpers()
        for stem, category, resolution in illum.products("south"):
            name = stem.lower() + ".lbl"
            files.append({"filename": name, "url": illum.PDS_IMG + name, "format": "LBL", "size_bytes": 11,
                          "relative_path": "moon/illumination_2016/documentation/labels/" + name,
                          "stem": stem, "category": category, "resolution_m": resolution})
        name = "readme_illumination_2016.txt"
        files.append({"filename": name, "url": illum.PDS_BASE + name, "format": "TXT", "size_bytes": 11,
                      "relative_path": "moon/illumination_2016/documentation/" + name})
        record = {"regions": list(support.REGIONS), "lola_files": list(support.LOLA_FILES),
                  "status": "failed", "files": [{**item, "status": "verified_present"} for item in files]}
        path = folder / "run.json"
        path.write_text(json.dumps(record), encoding="utf-8")
        path.with_name("zenodo_record.json").write_text(json.dumps(publisher), encoding="utf-8")
        return path, record

    def test_latest_uses_complete_inventory_not_latest_failed_discovery(self):
        path, record = self.fixture()
        failed = self.root / "manifests/moon_support/99999999/run.json"
        failed.parent.mkdir()
        failed.write_text('{"files": []}')
        source, files = support.saved_inventory(Path("latest"), self.root)
        self.assertEqual(source, path.resolve())
        self.assertEqual(len(files), 25)
        self.assertTrue(all("status" not in f for f in files))

    def test_cached_source_paths_sizes_and_publisher_checksums_are_protected(self):
        path, record = self.fixture()
        for field, bad_value in [("url", "https://different.example/file.zip"),
                                 ("relative_path", "../escape"), ("size_bytes", 22), ("md5", "b" * 32)]:
            changed = json.loads(json.dumps(record))
            changed["files"][0][field] = bad_value
            path.write_text(json.dumps(changed))
            with self.subTest(field=field), self.assertRaises(ValueError):
                support.saved_inventory(path, self.root)

    def test_cached_inventory_bypasses_network_discovery_and_saves_debug(self):
        self.fixture()
        with patch.object(support, "make_inventory") as discover, redirect_stdout(io.StringIO()):
            self.assertEqual(support.moon_support_main(["--output", str(self.root), "--from-inventory", "latest"]), 0)
        discover.assert_not_called()
        newest = sorted((self.root / "manifests/moon_support").glob("*/debug.txt"))[-1]
        self.assertIn("cached inventory", newest.read_text(encoding="utf-8"))
        record = json.loads(newest.with_name("run.json").read_text())
        self.assertEqual(len(record["files"]), 25)
        self.assertIn("cached_inventory_sha256", record)

    def test_http_retry_policy_and_failure_traceback_are_recorded(self):
        error = support.requests.HTTPError("503 Service Temporarily Unavailable")
        client = MagicMock()
        client.__enter__.return_value = client
        with patch.object(support.requests, "Session", return_value=client), patch.object(support, "make_inventory", side_effect=error), redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(support.moon_support_main(["--output", str(self.root), "--attempts", "5"]), 1)
        policy = client.mount.call_args.args[1].max_retries
        self.assertEqual(policy.total, 0)  # One outer retry budget, no hidden adapter retries.
        response = MagicMock(status_code=503)
        self.assertTrue(support.is_transient_http_error(support.requests.HTTPError(response=response)))
        log = next((self.root / "manifests/moon_support").glob("*/debug.txt"))
        text = log.read_text(encoding="utf-8")
        self.assertIn("Traceback", text)
        self.assertIn("503 Service Temporarily Unavailable", text)

    def test_wrapper_forwards_cache_selection_without_changing_default_jobs(self):
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(entrypoint.core_main(["--restore-moon-support", "--moon-support-inventory", "latest", "--dry-run"]), 0)
        self.assertIn("--from-inventory latest", output.getvalue())
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
            entrypoint.core_main(["--datasets", "lunar-temperature", "--moon-support-inventory", "latest"])
        self.assertEqual(error.exception.code, 2)

    def test_eda_debug_file_contains_incomplete_reason_without_cookie_contents(self):
        with redirect_stdout(io.StringIO()):
            self.assertEqual(eda.eda_main(["--datasets", "D21", "--output", str(self.root)]), 2)
        log = next((self.root / "manifests/eda_datasets").glob("*/debug.txt"))
        self.assertIn("login_required", log.read_text(encoding="utf-8"))
        self.assertFalse(eda.LOG.handlers[-1].__class__.__name__ == "FileHandler")


if __name__ == "__main__":
    unittest.main()
