import csv
from contextlib import redirect_stderr, redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import sys
import struct
import tempfile
import threading
import time
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import download_environmental as eda


def response(payload=b"example", *, status=200, headers=None, url="https://science.example/data.csv"):
    result = MagicMock()
    result.__enter__.return_value = result
    result.status_code = status
    result.url = url
    result.headers = headers or {}
    result.iter_content.return_value = [payload]
    return result


class EDADownloadTests(unittest.TestCase):
    def setUp(self):
        eda.DEFAULT_OUTPUT.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix=".eda-downloader-test-", dir=eda.DEFAULT_OUTPUT)
        self.root = Path(self.temp.name).resolve()
        self.assertTrue(self.root.is_relative_to(eda.DEFAULT_OUTPUT.resolve()))
        self.addCleanup(self.temp.cleanup)
        eda.STOP.clear()
        eda.original_helpers()

    def item(self, payload=b"example", name="data.csv"):
        return {"dataset": "D13", "url": "https://science.example/" + name,
                "relative_path": "moon/eda_pilots/D13/" + name, "size_bytes": len(payload),
                "etag": '"v1"', "last_modified": None, "metadata": False}

    def test_all_36_selected_datasets_and_offline_preview(self):
        expected = ({f"D{i:02}" for i in range(1, 39)} - {"D17", "D25"}) | {"R01", "R02"}
        self.assertEqual(set(eda.catalog()), expected)
        output = self.root / "not-created"
        with patch.object(eda, "session") as network, redirect_stdout(io.StringIO()):
            self.assertEqual(eda.eda_main(["--dry-run", "--output", str(output)]), 0)
        network.assert_not_called()
        self.assertFalse(output.exists())

    def test_path_and_url_restrictions(self):
        for relative in ["../outside", "/outside", "C:/outside", "a\\b", "x/../../outside"]:
            with self.subTest(relative=relative), self.assertRaises(ValueError):
                eda.safe_path(self.root, relative)
        for url in ["http://example.org/a", "file:///a", "https://user:secret@example.org/a", "https://example.org/a#fragment"]:
            with self.subTest(url=url), self.assertRaises(ValueError):
                eda.safe_url(url)

    def test_download_then_verified_skip_and_corruption_preserved(self):
        payload = b"example"
        item = self.item(payload)
        client = MagicMock()
        client.__enter__.return_value = client
        client.get.return_value = response(payload, headers={"ETag": '"v1"'}, url=item["url"])
        with patch.object(eda, "session", return_value=client), redirect_stdout(io.StringIO()):
            self.assertEqual(eda.transfer(item, self.root, 10, 1), "downloaded")
            self.assertEqual(eda.transfer(item, self.root, 10, 1), "verified_existing")
        self.assertEqual(client.get.call_count, 1)
        path = self.root / item["relative_path"]
        self.assertEqual(path.read_bytes(), payload)
        path.write_bytes(b"damaged")
        with self.assertRaises(ValueError):
            eda.transfer(item, self.root, 10, 1)
        self.assertEqual(path.read_bytes(), b"damaged")
        self.assertFalse(path.with_name(path.name + ".download.lock").exists())

    def test_validated_range_resume(self):
        item = self.item()
        path = self.root / item["relative_path"]
        path.parent.mkdir(parents=True)
        part = path.with_name(path.name + ".part")
        part.write_bytes(b"exa")
        eda.json_save(path.with_name(path.name + ".eda-part.json"), eda.identity(item))
        client = MagicMock()
        client.__enter__.return_value = client
        client.get.return_value = response(b"mple", status=206,
            headers={"Content-Range": "bytes 3-6/7", "ETag": '"v1"'}, url=item["url"])
        with patch.object(eda, "session", return_value=client), redirect_stdout(io.StringIO()):
            self.assertEqual(eda.transfer(item, self.root, 10, 1), "downloaded")
        self.assertEqual(path.read_bytes(), b"example")
        self.assertEqual(client.get.call_args.kwargs["headers"], {"Range": "bytes=3-", "If-Range": '"v1"'})

    def test_unknown_partial_or_changed_remote_is_preserved(self):
        item = self.item()
        path = self.root / item["relative_path"]
        path.parent.mkdir(parents=True)
        part = path.with_name(path.name + ".part")
        part.write_bytes(b"exa")
        with self.assertRaisesRegex(ValueError, "identity"):
            eda.transfer(item, self.root, 10, 1)
        self.assertEqual(part.read_bytes(), b"exa")
        eda.json_save(path.with_name(path.name + ".eda-part.json"), eda.identity(item))
        client = MagicMock()
        client.__enter__.return_value = client
        client.get.return_value = response(b"changed", headers={"ETag": '"v2"'}, url=item["url"])
        with patch.object(eda, "session", return_value=client), self.assertRaises(ValueError):
            eda.transfer(item, self.root, 10, 1)
        self.assertEqual(part.read_bytes(), b"exa")
        self.assertFalse(path.exists())

    def test_login_page_and_publisher_checksum_failure_never_promote(self):
        for payload, md5 in [(b"<html>login</html>", None), (b"example", "0" * 32)]:
            item = self.item(payload, "file" + str(len(payload)) + ".csv")
            if md5:
                item["md5"] = md5
            client = MagicMock()
            client.__enter__.return_value = client
            client.get.return_value = response(payload, headers={"ETag": '"v1"'}, url=item["url"])
            with patch.object(eda, "session", return_value=client), self.assertRaises(ValueError):
                eda.transfer(item, self.root, 10, 1)
            self.assertFalse((self.root / item["relative_path"]).exists())

    def test_source_identity_receipts_and_output_lock(self):
        item = self.item()
        path = self.root / item["relative_path"]
        path.parent.mkdir(parents=True)
        path.write_bytes(b"example")
        with self.assertRaisesRegex(ValueError, "receipt"):
            eda.verify_existing(path, item, self.root)
        eda.json_save(path.with_name(path.name + ".json"), {
            "source": {**eda.identity(item), "url": "https://other.example/file"},
            "sha256": hashlib.sha256(b"example").hexdigest()})
        with self.assertRaises(ValueError):
            eda.verify_existing(path, item, self.root)
        lock = path.with_name(path.name + ".download.lock")
        lock.write_text("another process")
        with self.assertRaises(FileExistsError):
            eda.transfer(item, self.root, 10, 1)
        self.assertEqual(lock.read_text(), "another process")

    def test_parent_source_hash_keeps_detached_labels_next_to_science(self):
        client = MagicMock()
        client.head.return_value = response(headers={"Content-Length": "7"})
        data = eda.file_item(client, {"url": "https://science.example/collection/data.tab"}, "D13", 10)
        label = eda.file_item(client, {"url": "https://science.example/collection/data.xml", "metadata": True}, "D13", 10)
        self.assertEqual(Path(data["relative_path"]).parent, Path(label["relative_path"]).parent)

    def test_listing_only_collects_science_and_companion_labels_with_bounded_pages(self):
        html = b'<a href="data.tab">data</a><a href="data.xml">label</a><a href="readme.txt">doc</a><a href="../other/">parent</a><a href="https://evil.example/data.tab">external</a>'
        with patch.object(eda, "metadata", return_value=(html, "https://science.example/collection/")) as get:
            groups, info = eda.listing(None, {"root": "https://science.example/collection/", "pattern": r"\.tab$"}, 10, 2, 1)
        self.assertEqual(len(groups), 1)
        self.assertEqual([x["url"] for x in groups[0]], ["https://science.example/collection/data.tab", "https://science.example/collection/data.xml"])
        self.assertEqual(get.call_count, 1)
        self.assertEqual(len(info["visited_pages"]), 1)

    def test_listing_dispatch_and_kernel_bundle(self):
        cfg = eda.catalog()["D13"]
        with patch.object(eda, "listing", return_value=([[]], {"scope": "fixture"})) as listing:
            self.assertEqual(eda.discover(None, cfg, 10, 2, 1, {}, self.root), ([[]], {"scope": "fixture"}))
        listing.assert_called_once()
        groups, info = eda.discover(None, eda.catalog()["D19"], 10, 2, 1, {}, self.root)
        self.assertEqual(len(groups), 1)
        self.assertEqual(len(groups[0]), 5)

    def test_checksum_pinned_transfer_does_not_trust_transient_last_modified(self):
        item = self.item()
        item.update({"md5": hashlib.md5(b"example").hexdigest(), "last_modified": "old-server-date"})
        client = MagicMock()
        client.__enter__.return_value = client
        client.get.return_value = response(b"example", headers={"Last-Modified": "new-server-date"}, url=item["url"])
        with patch.object(eda, "session", return_value=client), redirect_stdout(io.StringIO()):
            self.assertEqual(eda.transfer(item, self.root, 10, 1), "downloaded")

    def test_legacy_source_size_record_establishes_a_local_not_publisher_hash(self):
        item = self.item()
        item["relative_path"] = "moon/diviner/seasonal/data.csv"
        path = self.root / item["relative_path"]
        path.parent.mkdir(parents=True)
        path.write_bytes(b"example")
        manifest = self.root / "moon/diviner/download_manifest.csv"
        with manifest.open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=["filename", "url", "size_bytes"])
            writer.writeheader()
            writer.writerow({"filename": "data.csv", "url": item["url"], "size_bytes": 7})
        with redirect_stdout(io.StringIO()):
            self.assertEqual(eda.verify_existing(path, item, self.root), hashlib.sha256(b"example").hexdigest())
        receipt = json.loads(path.with_name(path.name + ".json").read_text())
        self.assertIn("no publisher checksum", receipt["verification"])

    def test_pinned_inventory_rejects_unsafe_duplicates_and_per_dataset_overflow(self):
        args = eda.argparse.Namespace(max_file_mib=2, max_dataset_mib=1, max_total_mib=8)
        item = self.item()
        record = {"schema": 1, "pilot_only": True, "files": [item], "datasets": [{"id": "D13", "status": "planned"}]}
        eda.validate_inventory(record, self.root, args)
        self.assertEqual(record["selected_bytes"], 7)
        record["files"] = [item, dict(item)]
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            eda.validate_inventory(record, self.root, args)
        record["files"] = [{**item, "size_bytes": 1500000}]
        with self.assertRaisesRegex(ValueError, "dataset/total"):
            eda.validate_inventory(record, self.root, args)
        record["files"] = [{**item, "relative_path": "../escape"}]
        with self.assertRaises(ValueError):
            eda.validate_inventory(record, self.root, args)

    def test_auth_and_missing_selections_are_not_successful_downloads(self):
        for key, status in [("D21", "login_required")]:
            groups, info = eda.discover(None, eda.catalog()[key], 10, 2, 1, {}, self.root)
            self.assertFalse(groups)
            self.assertEqual(info["status"], status)
        with self.assertRaises(ValueError):
            eda.discover(None, eda.catalog()["D15"], 10, 2, 1, {"D15": {"scope": "missing groups"}}, self.root)
        args = eda.argparse.Namespace(workers=2, timeout=10, attempts=1, cookies=None)
        record = {"files": [], "datasets": [{"id": "D21", "status": "login_required"}]}
        self.assertEqual(eda.run_downloads(record, self.root, self.root, args), 2)
        self.assertEqual(record["status"], "incomplete")

    def test_migrated_pds_object_listing_selects_calibrated_nac_and_labels(self):
        cfg = eda.catalog()["D15"]
        prefix = cfg["prefix"]
        xml = (f'<ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">'
               f'<Contents><Key>{prefix}M123LC.IMG</Key></Contents>'
               f'<Contents><Key>{prefix}M123LC.xml</Key></Contents>'
               f'<Contents><Key>{prefix}W123.IMG</Key></Contents>'
               '<IsTruncated>false</IsTruncated></ListBucketResult>').encode()
        with patch.object(eda, "metadata", return_value=(xml, cfg["base"])):
            groups, info = eda.discover(None, cfg, 10, 2, 1, {}, self.root)
        self.assertEqual(len(groups), 1)
        self.assertEqual(len(groups[0]), 2)
        self.assertTrue(groups[0][0]["url"].endswith("M123LC.IMG"))
        self.assertTrue(groups[0][1]["metadata"])
        self.assertEqual(len(info["visited_pages"]), 1)

    def test_shadowcam_requires_float32_not_stretched_samples(self):
        path = self.root / "map.tif"
        item = self.item(name="map.tif")
        item["float32_tiff"] = True
        for bits, fmt, valid in [(32, 3, True), (8, 1, False), (32, 1, False)]:
            payload = (b"II*\x00" + struct.pack("<I", 8) + struct.pack("<H", 2)
                       + struct.pack("<HHII", 258, 3, 1, bits)
                       + struct.pack("<HHII", 339, 3, 1, fmt) + b"\x00" * 4)
            path.write_bytes(payload)
            if valid:
                eda.validate_payload(path, item)
            else:
                with self.assertRaisesRegex(ValueError, "32-bit"):
                    eda.validate_payload(path, item)
        for order, magic in [("<", b"II+\x00"), (">", b"MM\x00+")]:
            def inline_short(value):
                return struct.unpack(order + "Q", struct.pack(order + "H", value) + b"\x00" * 6)[0]
            payload = (magic + struct.pack(order + "HHQ", 8, 0, 16) + struct.pack(order + "Q", 2)
                       + struct.pack(order + "HHQQ", 258, 3, 1, inline_short(32))
                       + struct.pack(order + "HHQQ", 339, 3, 1, inline_short(3)) + b"\x00" * 8)
            path.write_bytes(payload)
            eda.validate_payload(path, item)

    def test_byte_caps_exclude_whole_science_label_groups(self):
        cfg = eda.catalog()["D13"]
        args = eda.argparse.Namespace(timeout=10, cookies=None, pages_per_dataset=2, files_per_dataset=2,
            max_file_mib=1, max_dataset_mib=1, max_total_mib=1)
        client = MagicMock()
        client.__enter__.return_value = client
        groups = [[{"url": "https://science.example/data.tab"}, {"url": "https://science.example/data.xml"}]]
        def fake_item(client, entry, key, timeout):
            return {**self.item(name=Path(entry["url"]).name), "size_bytes": 800000}
        with patch.object(eda, "session", return_value=client), patch.object(eda, "discover", return_value=(groups, {})), patch.object(eda, "file_item", side_effect=fake_item), redirect_stdout(io.StringIO()):
            record = eda.inventory([cfg], self.root, self.root, args, {})
        self.assertFalse(record["files"])
        self.assertEqual(record["datasets"][0]["status"], "byte_limit")

    def test_thread_pool_runs_concurrently_and_preserves_failure_status(self):
        state = {"active": 0, "peak": 0}
        guard = threading.Lock()
        def worker(item, *args):
            with guard:
                state["active"] += 1
                state["peak"] = max(state["peak"], state["active"])
            time.sleep(.03)
            with guard:
                state["active"] -= 1
            if item["relative_path"].endswith("3.csv"):
                raise ValueError("fixture failure")
            return "downloaded"
        args = eda.argparse.Namespace(workers=3, timeout=10, attempts=1, cookies=None)
        record = {"files": [self.item(name=f"{i}.csv") for i in range(5)],
                  "datasets": [{"id": "D13", "status": "planned"}]}
        with patch.object(eda, "transfer", side_effect=worker), redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(eda.run_downloads(record, self.root, self.root, args), 1)
        self.assertGreater(state["peak"], 1)
        self.assertLessEqual(state["peak"], 3)
        self.assertEqual(record["status"], "failed")
        self.assertEqual(len(record["transfers"]), 5)


if __name__ == "__main__":
    unittest.main()
