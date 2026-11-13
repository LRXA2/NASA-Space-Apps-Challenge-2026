from contextlib import redirect_stderr, redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import download_environmental as eda


class ValidationRecoveryTests(unittest.TestCase):
    def setUp(self):
        eda.DEFAULT_OUTPUT.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix=".validation-recovery-test-", dir=eda.DEFAULT_OUTPUT)
        self.root = Path(self.temp.name).resolve()
        self.assertTrue(self.root.is_relative_to(eda.DEFAULT_OUTPUT.resolve()))
        self.addCleanup(self.temp.cleanup)
        eda.STOP.clear()
        self.args = eda.argparse.Namespace(workers=1, timeout=5, attempts=1, cookies=None,
            connection_retries=1, max_file_mib=1, max_dataset_mib=1, max_total_mib=1)

    def image_fixture(self):
        payload = b"\x00\x01\x00\x02"
        item = {"dataset": "D26", "relative_path": "D26/data.img", "url": "https://example.test/data.img",
                "size_bytes": len(payload), "etag": '"v1"', "last_modified": None, "metadata": False}
        text = ('PDS_VERSION_ID = "PDS3"\nFILE_NAME = "data.img"\n'
                '^IMAGE = ("data.img", 1 <BYTES>)\nOBJECT = IMAGE\n'
                ' BANDS = 1\n LINES = 1\n LINE_SAMPLES = 2\n SAMPLE_BITS = 16\nEND_OBJECT = IMAGE\n')
        label_item = {**item, "relative_path": "D26/data.lbl", "url": "https://example.test/data.lbl",
                      "metadata": True, "size_bytes": len(text)}
        label = self.root / label_item["relative_path"]
        label.parent.mkdir(parents=True)
        label.write_bytes(text.encode("ascii"))
        eda.json_save(label.with_name(label.name + ".json"), {"source": eda.identity(label_item),
                      "sha256": hashlib.sha256(label.read_bytes()).hexdigest()})
        return item, label_item, payload, label

    def test_d26_discovery_requires_detached_label_and_does_not_claim_embedded_header(self):
        cfg = eda.catalog()["D26"]
        html = b'<a href="data.img">data</a><a href="data.lbl">label</a>'
        with patch.object(eda, "metadata", return_value=(html, cfg["root"])):
            groups, _ = eda.listing(None, cfg, 5, 1, 1)
        self.assertEqual(len(groups), 1)
        self.assertNotIn("embedded_label", groups[0][0])
        with patch.object(eda, "metadata", return_value=(b'<a href="data.img">data</a>', cfg["root"])):
            groups, _ = eda.listing(None, cfg, 5, 1, 1)
        self.assertFalse(groups)

    def test_detached_label_filename_dimensions_and_receipt_are_validated(self):
        item, label_item, payload, label = self.image_fixture()
        part = (self.root / item["relative_path"]).with_name("data.img.part")
        part.write_bytes(payload)
        eda.validate_payload(part, item)
        receipt = label.with_name(label.name + ".json")
        original = label.read_text()
        wrong = original.replace('FILE_NAME = "data.img"', 'FILE_NAME = "else.img"')
        label.write_bytes(wrong.encode("ascii"))
        eda.json_save(receipt, {"source": {**eda.identity(label_item), "size_bytes": len(wrong)},
                               "sha256": hashlib.sha256(label.read_bytes()).hexdigest()})
        with self.assertRaisesRegex(ValueError, "FILE_NAME"):
            eda.validate_payload(part, item)
        wrong = original.replace("LINE_SAMPLES = 2", "LINE_SAMPLES = 3")
        label.write_bytes(wrong.encode("ascii"))
        eda.json_save(receipt, {"source": {**eda.identity(label_item), "size_bytes": len(wrong)},
                               "sha256": hashlib.sha256(label.read_bytes()).hexdigest()})
        with self.assertRaisesRegex(ValueError, "size disagrees"):
            eda.validate_payload(part, item)
        receipt.write_text("{}")
        with self.assertRaisesRegex(ValueError, "evidence"):
            eda.validate_payload(part, item)

    def test_complete_legacy_d26_partial_is_finalised_offline_with_label_first(self):
        item, label_item, payload, label = self.image_fixture()
        item["embedded_label"] = True
        path = self.root / item["relative_path"]
        path.with_name(path.name + ".part").write_bytes(payload)
        eda.json_save(path.with_name(path.name + ".eda-part.json"), eda.identity(item))
        record = {"schema": 1, "pilot_only": True, "files": [item, label_item],
                  "datasets": [{"id": "D26", "status": "planned"}]}
        eda.validate_inventory(record, self.root, self.args)
        self.assertNotIn("embedded_label", item)
        with patch.object(eda, "session") as client, redirect_stdout(io.StringIO()):
            self.assertEqual(eda.run_downloads(record, self.root, self.root, self.args), 0)
        client.return_value.__enter__.return_value.get.assert_not_called()
        self.assertEqual(path.read_bytes(), payload)
        self.assertFalse(path.with_name(path.name + ".part").exists())
        self.assertEqual(record["dataset_outcomes"]["D26"]["status"], "complete")

    def test_failed_label_prevents_image_transfer_without_deadlock(self):
        item, label_item, _, _ = self.image_fixture()
        record = {"files": [item, label_item], "datasets": [{"id": "D26", "status": "planned"}]}
        with patch.object(eda, "transfer", side_effect=ValueError("label failed")) as transfer, redirect_stderr(io.StringIO()):
            self.assertEqual(eda.run_downloads(record, self.root, self.root, self.args), 1)
        self.assertEqual(transfer.call_count, 1)
        self.assertEqual(record["dataset_outcomes"]["D26"]["status"], "transfer_failed")

    def test_shadowcam_xml_is_not_classified_as_float32_tiff(self):
        entry = {"url": "https://example.test/map_raw.xml", "metadata": True, "float32_tiff": True}
        with patch.object(eda, "remote_info", return_value={"url": entry["url"], "size_bytes": 100}):
            item = eda.file_item(None, entry, "D27", 5)
        self.assertNotIn("float32_tiff", item)

    def test_complete_legacy_shadowcam_xml_partial_is_finalised_without_network(self):
        payload = b'<Product_Browse><File><file_name>map_raw.tif</file_name></File></Product_Browse>'
        item = {"dataset": "D27", "relative_path": "map_raw.xml", "url": "https://example.test/map_raw.xml",
                "size_bytes": len(payload), "etag": '"v1"', "last_modified": None, "metadata": True,
                "float32_tiff": True}
        path = self.root / item["relative_path"]
        path.with_name(path.name + ".part").write_bytes(payload)
        eda.json_save(path.with_name(path.name + ".eda-part.json"), eda.identity(item))
        record = {"schema": 1, "pilot_only": True, "files": [item], "datasets": [{"id": "D27", "status": "planned"}]}
        eda.validate_inventory(record, self.root, self.args)
        with patch.object(eda, "session") as client, redirect_stdout(io.StringIO()):
            self.assertEqual(eda.run_downloads(record, self.root, self.root, self.args), 0)
        client.return_value.__enter__.return_value.get.assert_not_called()
        self.assertEqual(path.read_bytes(), payload)
        path.write_bytes(payload.replace(b'map_raw.tif', b'bad_raw.tif'))
        with self.assertRaisesRegex(ValueError, "reference"):
            eda.validate_payload(path, item)

    def test_legacy_policy_upgrade_still_rejects_a_changed_source(self):
        item, _, _, _ = self.image_fixture()
        saved = {**eda.identity(item), "embedded_label": True}
        self.assertTrue(eda.compatible_partial_state(saved, item))
        saved["url"] = "https://different.example/data.img"
        self.assertFalse(eda.compatible_partial_state(saved, item))

    def test_outcomes_include_transfer_failures_not_just_planned_inventory(self):
        record = {"files": [{"dataset": "D26", "relative_path": "raw.img"},
                            {"dataset": "D27", "relative_path": "map.tif"}],
                  "datasets": [{"id": "D26", "status": "planned"},
                               {"id": "D27", "status": "planned", "excluded": [{"reason": "pilot_byte_limit"}]}],
                  "transfers": [{"path": "raw.img", "status": "failed"},
                                {"path": "map.tif", "status": "downloaded"}]}
        outcomes = eda.dataset_outcomes(record)
        self.assertEqual(outcomes["D26"]["status"], "transfer_failed")
        self.assertEqual(outcomes["D26"]["failed_files"], ["raw.img"])
        self.assertEqual(outcomes["D27"]["status"], "partial_selection")


if __name__ == "__main__":
    unittest.main()
