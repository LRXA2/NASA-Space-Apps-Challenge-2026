"""Offline safety/regression cases for cleanup and the download-gap report."""
from pathlib import Path
import hashlib
import json
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import data_maintenance as maintenance


class DataMaintenanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve() / "data"
        self.root.mkdir()

    def json(self, relative, value):
        p = self.root / relative
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(value), encoding="utf-8")
        return p

    def failed_run(self, status="failed"):
        relative = "processed/analysis/example/run"
        p = self.root / relative / "intermediate.csv"
        p.parent.mkdir(parents=True)
        p.write_bytes(b"a,b\n1,2\n")
        record = {"status": status, "inputs": {}, "outputs": [
            {"path": p.name, "bytes": p.stat().st_size,
             "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}]}
        self.json(relative + "/provenance.json", record)
        (p.parent / "error.txt").write_text("diagnostic", encoding="utf-8")
        return p

    def test_failed_output_preview_then_apply_preserves_failure_evidence(self):
        p = self.failed_run()
        result = maintenance.cleanup_failed_run(p.parent, self.root, apply=False, references=set())
        self.assertEqual(len(result), 1)
        self.assertTrue(p.exists())
        maintenance.cleanup_failed_run(p.parent, self.root, references=set())
        self.assertFalse(p.exists())
        for name in ["provenance.json", "error.txt", "cleanup.json"]:
            self.assertTrue((p.parent / name).exists())

    def test_completed_running_or_changed_outputs_are_never_pruned(self):
        for status in ["complete", "running"]:
            with self.subTest(status=status):
                p = self.failed_run(status)
                self.assertEqual(maintenance.cleanup_failed_run(p.parent, self.root, references=set()), [])
                self.assertTrue(p.exists())
                # Only fixture files, so the next subcase can reuse the name.
                for q in p.parent.iterdir():
                    q.unlink()
                p.parent.rmdir()
        p = self.failed_run()
        p.write_bytes(b"user edited this file")
        self.assertEqual(maintenance.cleanup_failed_run(p.parent, self.root, references=set()), [])

    def test_referenced_artifact_or_manifest_is_protected(self):
        p = self.failed_run()
        for reference in [p, p.parent / "provenance.json"]:
            self.assertEqual(maintenance.cleanup_failed_run(p.parent, self.root, references={reference}), [])
            self.assertTrue(p.exists())

    def test_registered_downstream_input_protects_failed_output(self):
        p = self.failed_run()
        self.json("processed/analysis/consumer/run/provenance.json", {
            "status": "complete", "inputs": {str(p): {}}, "outputs": []})
        self.assertIn(p, maintenance.referenced_inputs(self.root))
        self.assertEqual(maintenance.cleanup_failed_run(p.parent, self.root), [])

    def test_path_escape_and_failed_output_traversal_are_rejected(self):
        for path in [self.root, self.root.parent / "outside", "../outside"]:
            with self.assertRaises(ValueError):
                maintenance.checked_path(self.root, path)
        p = self.failed_run()
        manifest = p.parent / "provenance.json"
        record = json.loads(manifest.read_text())
        record["outputs"][0]["path"] = "../../../../outside.csv"
        manifest.write_text(json.dumps(record))
        with self.assertRaises(ValueError):
            maintenance.cleanup_failed_run(p.parent, self.root, references=set())
        self.assertTrue(p.exists())

    def test_runtime_cleanup_only_owned_folders_after_process_exit(self):
        run = self.root / "verification/execution"
        cache = run / "ipythondir/profile/startup.txt"
        cache.parent.mkdir(parents=True)
        cache.write_text("generated cache")
        keep = run / "verification.json"
        keep.write_text("{}")
        with patch.object(maintenance, "runtime_in_use", return_value=True):
            self.assertEqual(maintenance.cleanup_execution_runtime(run, self.root), [])
        with patch.object(maintenance, "runtime_in_use", return_value=False):
            self.assertEqual(len(maintenance.cleanup_execution_runtime(run, self.root, apply=False)), 1)
            self.assertTrue(cache.exists())
            maintenance.cleanup_execution_runtime(run, self.root)
        self.assertFalse((run / "ipythondir").exists())
        self.assertTrue(keep.exists())

    def test_completed_identity_cleanup_retains_final_receipt_and_resumable_bytes(self):
        p = self.root / "moon/map.tif"
        p.parent.mkdir()
        p.write_bytes(b"source")
        item = {"size_bytes": 6, "url": "https://example.test/map"}
        identity = self.json("moon/map.tif.part.json", item)
        receipt = self.json("moon/map.tif.json", {"source": item, "sha256": "a" * 64})
        partial = p.with_name(p.name + ".part")
        partial.write_bytes(b"resumable")
        self.assertEqual(maintenance.cleanup_completed_transfer_state(self.root, p), [])
        partial.unlink()
        self.assertEqual(len(maintenance.cleanup_completed_transfer_state(self.root, p, apply=False)), 1)
        self.assertTrue(identity.exists())
        maintenance.cleanup_completed_transfer_state(self.root, p)
        self.assertFalse(identity.exists())
        self.assertTrue(p.exists() and receipt.exists())

    def test_conflicting_identity_is_preserved(self):
        p = self.root / "moon/map.tif"
        p.parent.mkdir()
        p.write_bytes(b"source")
        identity = self.json("moon/map.tif.part.json", {"size_bytes": 6, "url": "https://a.test/map"})
        self.json("moon/map.tif.json", {"source": {"size_bytes": 6, "url": "https://b.test/map"}, "sha256": "a" * 64})
        self.assertEqual(maintenance.cleanup_completed_transfer_state(self.root, p), [])
        self.assertTrue(identity.exists())

    def research(self, run, status, files=None):
        return self.json(f"manifests/eda_datasets/{run}/download.json", {
            "datasets": [{"id": "D21", "name": "thermal pilot", "status": status,
                          "sources": "https://archive.test/login"}],
            "files": files or [], "dataset_outcomes": {"D21": {"status": status}}})

    def test_error_report_gated_url_and_missing_file_then_success_supersedes(self):
        self.research("001", "login_required")
        report = maintenance.write_error_log(self.root)
        self.assertIn("login_required", report.read_text(encoding="utf-8"))
        self.assertIn("https://archive.test/login", report.read_text(encoding="utf-8"))
        files = [{"dataset": "D21", "relative_path": "moon/a.tab", "size_bytes": 2,
                  "url": "https://archive.test/a.tab"}]
        self.research("002", "complete", files)
        text = maintenance.write_error_log(self.root).read_text(encoding="utf-8")
        self.assertIn("missing selected file", text)
        self.assertIn("https://archive.test/a.tab", text)
        p = self.root / "moon/a.tab"
        p.parent.mkdir()
        p.write_bytes(b"ok")
        text = maintenance.write_error_log(self.root).read_text(encoding="utf-8")
        self.assertNotIn("login_required", text)
        self.assertNotIn("missing selected file", text)

    def test_size_mismatch_and_recorded_validation_failure_are_not_passed(self):
        p = self.root / "bad.tab"
        p.write_bytes(b"x")
        files = [{"dataset": "D21", "relative_path": "bad.tab", "size_bytes": 2,
                  "url": "https://archive.test/bad.tab"}]
        manifest = self.research("001", "complete", files)
        self.assertIn("unexpected size", maintenance.write_error_log(self.root).read_text())
        p.write_bytes(b"xx")
        record = json.loads(manifest.read_text())
        record["transfers"] = [{"path": "bad.tab", "status": "failed", "error": "checksum mismatch"}]
        manifest.write_text(json.dumps(record))
        self.assertIn("checksum mismatch", maintenance.write_error_log(self.root).read_text())

    def test_partial_selection_is_not_claimed_as_a_missing_selected_file(self):
        self.research("001", "partial_selection")
        text = maintenance.write_error_log(self.root).read_text()
        self.assertIn("broader groups were excluded", text)
        self.assertNotIn("missing selected file:", text)

    def test_climate_failure_keeps_exact_subset_url_even_if_bytes_exist(self):
        p = self.root / "earth/terraclimate/subsets/a.nc"
        p.parent.mkdir(parents=True)
        p.write_bytes(b"invalid response")
        self.json("earth/terraclimate/manifests/001_run.json", {
            "status": "failed", "jobs": [{"path": "subsets/a.nc", "status": "failed",
                "error": "invalid NetCDF", "source": {"url": "https://archive.test/ncss/a.nc",
                    "params": {"var": "tmin", "west": 1}}}]})
        text = maintenance.write_error_log(self.root).read_text()
        self.assertIn("recorded transfer failure: invalid NetCDF", text)
        self.assertIn("https://archive.test/ncss/a.nc?var=tmin&west=1", text)

    def test_empty_or_malformed_manifests_do_not_imply_download_completeness(self):
        self.assertIn("UNKNOWN", maintenance.write_error_log(self.root).read_text())
        p = self.research("001", "complete")
        p.write_text("not json")
        self.assertIn("could not be interpreted", maintenance.write_error_log(self.root).read_text())

    def test_report_scrubs_credentials_and_signed_query(self):
        result = maintenance.public_url("https://user:secret@host.test/a?token=private")
        self.assertEqual(result, "https://host.test/a")
        self.assertEqual(maintenance.public_url("https://host.test/a?var=tmin&token=private"),
                         "https://host.test/a?var=tmin")

    def test_atomic_write_failure_removes_only_its_own_temporary(self):
        target = self.root / "error_log.txt"
        target.write_text("previous report")
        with patch.object(Path, "replace", side_effect=PermissionError("fixture")):
            with self.assertRaises(PermissionError):
                maintenance.atomic_text(target, "new report")
        self.assertEqual(target.read_text(), "previous report")
        self.assertEqual(list(self.root.glob("*.tmp")), [])

    def test_linked_runtime_path_aborts_before_removing_any_files(self):
        run = self.root / "verification/execution"
        folder = run / "ipythondir"
        folder.mkdir(parents=True)
        cache = folder / "cache.txt"
        cache.write_text("keep on unsafe path")
        with patch.object(maintenance, "runtime_in_use", return_value=False), \
                patch.object(Path, "is_symlink", lambda path: path == cache):
            with self.assertRaises(ValueError):
                maintenance.cleanup_execution_runtime(run, self.root)
        self.assertTrue(cache.exists())

    def test_full_cleanup_sample_preview_and_apply_preserve_source_and_code(self):
        failed = self.failed_run()
        source = self.root / "moon/source.tab"
        source.parent.mkdir()
        source.write_text("source")
        code = self.root / "verification/generator.py"
        code.parent.mkdir()
        code.write_text("# keep generator")
        runtime = self.root / "verification/execution/ipythondir/cache.txt"
        runtime.parent.mkdir(parents=True)
        runtime.write_text("cache")
        self.json("verification/execution/verification.json", {"status": "executed"})
        item = {"size_bytes": source.stat().st_size, "url": "https://example.test/source"}
        identity = self.json("moon/source.tab.part.json", item)
        receipt = self.json("moon/source.tab.json", {"source": item, "sha256": "a" * 64})
        with patch.object(maintenance, "runtime_in_use", return_value=False):
            preview = maintenance.clean_generated(self.root)
            self.assertEqual(len(preview["files"]), 3)
            self.assertTrue(all(p.exists() for p in [failed, runtime, identity]))
            result = maintenance.clean_generated(self.root, apply=True)
        self.assertEqual(len(result["files"]), 3)
        self.assertFalse(any(p.exists() for p in [failed, runtime, identity]))
        self.assertTrue(all(p.exists() for p in [source, code, receipt, failed.parent / "provenance.json"]))

    def test_local_run_exit_keeps_complete_outputs_and_cleans_failed_intermediates(self):
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        from environment_workflow import LocalRun
        for error in [None, ValueError("fixture failure")]:
            run = object.__new__(LocalRun)
            run.root = self.root.parent
            run.directory = self.root / "processed/analysis/local_exit" / ("complete" if error is None else "failed")
            run.directory.mkdir(parents=True)
            run.record = {"stage": "analysis/local_exit", "inputs": {}}
            output = run.directory / "data.csv"
            output.write_text("a\n1\n")
            run.__exit__(None if error is None else type(error), error, None)
            self.assertEqual(output.exists(), error is None)
            record = json.loads((run.directory / "provenance.json").read_text())
            self.assertEqual(record["status"], "complete" if error is None else "failed")
            self.assertFalse((run.directory / "provenance.json.tmp").exists())


if __name__ == "__main__":
    unittest.main()
