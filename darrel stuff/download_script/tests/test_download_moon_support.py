"""Small offline fixtures for restoration scope, safe extraction and verified metadata."""
from contextlib import redirect_stdout, redirect_stderr
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch
import zipfile

SCRIPT_ROOT = Path(__file__).resolve().parents[1]


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, SCRIPT_ROOT / filename)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


support = module("moon_support", "download_moon_support.py")
entrypoint = module("environmental_restore_entrypoint", "download_environmental.py")


def label(stem):
    if stem.startswith("SKYV_"):
        units, scale, offset, description = "STERADIAN", ".0002", "6.2832", "visible sky solid angle in steradians"
    elif stem.startswith("LPSR_"):
        units, scale, offset, description = "NONE", ".000025", ".5", "binary permanent shadow: 1 or 0"
    else:
        units, scale, offset, description = "NONE", ".00004", "0", "average visibility continuous between 0 and 1"
    return (f'PRODUCT_ID = "{stem}"\nDESCRIPTION = "{description}"\n'
            f'SAMPLE_TYPE = LSB_INTEGER\nSAMPLE_BITS = 16\nUNIT = {units}\n'
            f'SCALING_FACTOR = {scale}\nOFFSET = {offset}\n')


class SupportTests(unittest.TestCase):
    def setUp(self):
        support.DEFAULT_OUTPUT.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix=".moon-support-test-", dir=support.DEFAULT_OUTPUT)
        self.root = Path(self.temp.name).resolve()
        # The only recursive cleanup target is a newly created fixture under Darrel's data.
        self.assertTrue(self.root.is_relative_to(support.DEFAULT_OUTPUT.resolve()))
        self.addCleanup(self.temp.cleanup)

    def test_default_entrypoint_adds_support_and_explicit_p1_selection_stays_restricted(self):
        with patch.object(entrypoint.subprocess, "run") as run, redirect_stdout(io.StringIO()):
            self.assertEqual(entrypoint.main(["--download", "--output", str(self.root)]), 0)
        self.assertEqual(run.call_count, 5)
        self.assertEqual(Path(run.call_args_list[-1].args[0][1]).name, "download_moon_support.py")
        for call in run.call_args_list:
            self.assertIn("--download", call.args[0])
            self.assertEqual(call.kwargs, {"check": True})
        with patch.object(entrypoint.subprocess, "run") as run, redirect_stdout(io.StringIO()):
            self.assertEqual(entrypoint.main(["--datasets", "lunar-temperature", "--output", str(self.root)]), 0)
        self.assertEqual(run.call_count, 1)
        self.assertEqual(Path(run.call_args.args[0][1]).name, "download_diviner_south_polar.py")

    def test_support_only_and_dry_run_do_not_revisit_finished_primary_downloads(self):
        with patch.object(entrypoint.subprocess, "run") as run, redirect_stdout(io.StringIO()):
            self.assertEqual(entrypoint.main(["--restore-moon-support", "--output", str(self.root)]), 0)
        self.assertEqual(run.call_count, 1)
        with patch.object(entrypoint.subprocess, "run") as run, redirect_stdout(io.StringIO()):
            self.assertEqual(entrypoint.main(["--restore-moon-support", "--dry-run", "--download"]), 0)
        run.assert_not_called()
        missing = self.root / "not created"
        with patch.object(support.requests, "Session") as session, redirect_stdout(io.StringIO()):
            self.assertEqual(support.main(["--dry-run", "--output", str(missing)]), 0)
        session.assert_not_called()
        self.assertFalse(missing.exists())

    def test_zenodo_selection_excludes_reserves_and_requires_publisher_identity(self):
        names = [*(r + ".zip" for r in support.REGIONS), "README.md", "A3CLR22_0_Amundsen_Rim.zip"]
        record = {"id": 17954508, "files": [
            {"key": name, "size": 123, "checksum": "md5:" + "a" * 32,
             "links": {"self": f"https://zenodo.org/api/records/17954508/files/{name}/content"}}
            for name in names]}
        selected = support.select_sdem_files(record)
        self.assertEqual(len(selected), 8)
        self.assertFalse(any("Amundsen" in r["filename"] for r in selected))
        record["files"][0]["checksum"] = "unverified"
        with self.assertRaises(ValueError):
            support.select_sdem_files(record)
        record["id"] = 1
        with self.assertRaises(ValueError):
            support.select_sdem_files(record)

    def archive(self, extra=None):
        region = support.REGIONS[0]
        path = self.root / (region + ".zip")
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr(region + "/README.txt", "original region metadata")
            archive.writestr(region + "/terrain_GLDELEV_005.tif", b"II*\x00elevation fixture")
            archive.writestr(region + "/terrain_GLDMASK_005.tif", b"II*\x00mask fixture")
            archive.writestr("__MACOSX/._ignored", "ignored metadata")
            if extra:
                info, payload = extra
                if isinstance(info, str):
                    # Windows' normal ZIP writer replaces backslashes. Preserve the
                    # literal malicious member name so the rejection test is real.
                    raw_info = zipfile.ZipInfo()
                    raw_info.filename = info
                    info = raw_info
                archive.writestr(info, payload)
        return path

    def test_extraction_is_idempotent_and_preserves_conflicting_existing_data(self):
        path = self.archive()
        with redirect_stdout(io.StringIO()):
            support.extract_archive(path, self.root)
            support.extract_archive(path, self.root)
        target = self.root / "moon/sdem/regions" / path.stem / "terrain_GLDELEV_005.tif"
        target.write_bytes(b"conflicting data")
        with self.assertRaisesRegex(ValueError, "preserved"):
            support.extract_archive(path, self.root)
        self.assertEqual(target.read_bytes(), b"conflicting data")

    def test_archive_traversal_wrong_roots_duplicates_and_symlinks_are_rejected(self):
        region = support.REGIONS[0]
        for name in ["../outside.txt", "/absolute.txt", "C:/outside.txt", region + "\\bad.txt", "other/file.txt",
                     region + "/TERRAIN_GLDELEV_005.TIF"]:
            with self.subTest(name=name):
                path = self.archive((name, b"bad"))
                with zipfile.ZipFile(path) as archive, self.assertRaises(ValueError):
                    support.archive_members(archive, region, self.root / "regions")
        info = zipfile.ZipInfo(region + "/link")
        info.create_system = 3
        info.external_attr = (stat.S_IFLNK | 0o777) << 16
        path = self.archive((info, "../outside"))
        with zipfile.ZipFile(path) as archive, self.assertRaises(ValueError):
            support.archive_members(archive, region, self.root / "regions")
        with self.assertRaises(ValueError):
            support.destination(self.root, "../outside")

    def test_verified_byte_transfer_reuses_existing_archives_and_rejects_corruption(self):
        payload = b"small checksum-protected archive fixture"
        item = {"filename": "sample.zip", "url": "https://example.test/sample.zip", "size_bytes": len(payload),
                "md5": hashlib.md5(payload).hexdigest(), "relative_path": "moon/sdem/archives/sample.zip", "format": "ZIP"}
        session = MagicMock();response = MagicMock()
        response.__enter__.return_value = response
        response.status_code = 200
        response.headers = {"Content-Length": str(len(payload))}
        response.iter_content.return_value = [payload]
        session.get.return_value = response
        with redirect_stdout(io.StringIO()):
            path = support.download_file(session, item, self.root, 5, 1)
            support.download_file(session, item, self.root, 5, 1)
        self.assertEqual(session.get.call_count, 1)
        path.write_bytes(b"bad")
        with self.assertRaises(ValueError):
            support.download_file(session, item, self.root, 5, 1)
        self.assertEqual(path.read_bytes(), b"bad")

    def test_existing_archive_without_receipt_can_be_verified_against_publisher_md5(self):
        payload = b"already downloaded bytes"
        item = {"filename": "existing.zip", "url": "https://example.test/existing.zip", "size_bytes": len(payload),
                "md5": hashlib.md5(payload).hexdigest(), "relative_path": "moon/sdem/archives/existing.zip", "format": "ZIP"}
        path = self.root / item["relative_path"];path.parent.mkdir(parents=True);path.write_bytes(payload)
        session = MagicMock()
        with redirect_stdout(io.StringIO()):
            self.assertEqual(support.download_file(session, item, self.root, 5, 1), path)
        session.get.assert_not_called()
        self.assertEqual(path.read_bytes(), payload)
        self.assertTrue(path.with_name(path.name + ".json").is_file())

    def test_tiff_transfer_requires_matching_source_receipt_and_preserves_unidentified_partials(self):
        payload = b"II*\x00small TIFF fixture"
        item = {"filename": "map.TIF", "url": "https://example.test/map.TIF", "size_bytes": len(payload),
                "relative_path": "moon/lola_product90/large_area_dem/map.TIF", "format": "TIF"}
        session = MagicMock();response = MagicMock()
        response.__enter__.return_value = response
        response.status_code = 200
        response.headers = {"Content-Length": str(len(payload))}
        response.iter_content.return_value = [payload]
        session.get.return_value = response
        with redirect_stdout(io.StringIO()):
            path = support.download_file(session, item, self.root, 5, 1)
            support.download_file(session, item, self.root, 5, 1)
        self.assertEqual(session.get.call_count, 1)
        path.write_bytes(b"bad")
        with self.assertRaises(ValueError):
            support.download_file(session, item, self.root, 5, 1)
        self.assertEqual(path.read_bytes(), b"bad")
        other = {**item, "filename": "other.TIF", "relative_path": "other.TIF"}
        partial = self.root / "other.TIF.part";partial.write_bytes(b"unknown source")
        with self.assertRaisesRegex(ValueError, "preserved"):
            support.download_file(session, other, self.root, 5, 1)
        self.assertEqual(partial.read_bytes(), b"unknown source")

    def test_label_semantics_and_packing_cannot_be_guessed(self):
        for stem, unit in [("AVGVISIB_85S_060M_201608", "fraction"),
                           ("AVGVISIB_85S_060M_201608_EARTH", "fraction"),
                           ("LPSR_85S_060M_201608", "binary"), ("SKYV_65S_240M", "sr")]:
            self.assertEqual(support.label_unit(label(stem), stem)["unit"], unit)
        stem = "SKYV_65S_240M"
        with self.assertRaises(ValueError):
            support.label_unit(label(stem).replace(".0002", ".2"), stem)
        with self.assertRaises(ValueError):
            support.label_unit(label(stem).replace("STERADIAN", "NONE"), stem)
        with self.assertRaises(ValueError):
            support.label_unit(label(stem).replace(stem, "different"), stem)

    def test_unit_policy_contains_evidence_and_existing_conflicts_are_preserved(self):
        _, illumination, _ = support.original_helpers()
        files = []
        for stem, _, _ in illumination.products("south"):
            relative = "labels/" + stem.lower() + ".lbl"
            path = self.root / relative;path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(label(stem), encoding="ascii")
            files.append({"format": "LBL", "stem": stem, "relative_path": relative, "url": "https://example.test/" + stem})
        with redirect_stdout(io.StringIO()):
            policy = support.write_unit_policy(self.root, files)
        rows = json.loads(policy.read_text())
        self.assertEqual(len(rows), 70)
        self.assertTrue(all(r["status"] == "documented" and len(r["source_label_sha256"]) == 64 for r in rows))
        before = policy.read_bytes()
        with redirect_stdout(io.StringIO()):
            support.write_unit_policy(self.root, files)
        self.assertEqual(policy.read_bytes(), before)
        for row in rows:
            row["unit"] = "incorrect"
        policy.write_text(json.dumps(rows))
        with self.assertRaisesRegex(ValueError, "preserved"):
            support.write_unit_policy(self.root, files)
        self.assertEqual(json.loads(policy.read_text())[0]["unit"], "incorrect")


if __name__ == "__main__":
    unittest.main()
