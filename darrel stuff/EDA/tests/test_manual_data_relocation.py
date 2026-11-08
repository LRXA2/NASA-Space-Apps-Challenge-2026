import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import data_maintenance as maintenance
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from manual_raster_eda import manual_selection

NAMES = ["M013049982S_map_raw.tif", "M013049982S_map_raw.xml.txt",
         "global_cpr_128ppd_simp_0c.img", "global_cpr_128ppd_simp_0c.xml", "global_cpr_128ppd_simp_0c.lbl"]


class ManualRelocationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        for name in NAMES:
            path = self.root / name; path.write_bytes(name.encode())
            receipt = {"source": {"url": "https://example.org/" + name, "size_bytes": path.stat().st_size},
                       "sha256": maintenance.digest(path)}
            path.with_name(name + ".json").write_text(json.dumps(receipt))

    def test_preview_then_move_preserves_bytes_receipts_and_old_inventory(self):
        plan = maintenance.organize_manual_data(self.root)
        self.assertEqual(len(plan["files"]), 10)
        self.assertTrue(all((self.root / name).is_file() for name in NAMES))
        self.assertFalse((self.root / "manifests").exists())
        record = maintenance.organize_manual_data(self.root, apply=True)
        for item in record["files"]:
            self.assertFalse((self.root / item["from"]).exists())
            relocated = maintenance.resolve_data_path(self.root, item["from"])
            self.assertEqual(maintenance.digest(relocated), item["sha256"])
        inventory = self.root / "inventory.json"
        inventory.write_text(json.dumps({"files": [{"dataset": "D27", "role": "image", "relative_path": NAMES[0],
            "size_bytes": len(NAMES[0]), "url": "https://example.org/" + NAMES[0]}]}))
        paths = manual_selection(self.root, inventory, "D27")
        self.assertTrue(paths["image"].is_file())
        self.assertEqual(maintenance.organize_manual_data(self.root, apply=True), record)

    def test_hash_conflict_prevents_all_moves(self):
        (self.root / NAMES[-1]).write_text("changed")
        with self.assertRaises(ValueError): maintenance.organize_manual_data(self.root, apply=True)
        self.assertTrue(all((self.root / name).exists() for name in NAMES))
        self.assertFalse((self.root / "manifests/file_relocations.json").exists())

    def test_target_conflict_preserved(self):
        target = self.root / "moon/eda_pilots/D27/manual_M013049982S" / NAMES[0]
        target.parent.mkdir(parents=True); target.write_text("keep")
        with self.assertRaises(FileExistsError): maintenance.organize_manual_data(self.root, apply=True)
        self.assertEqual(target.read_text(), "keep")

    def test_resolve_conflict_and_unsafe_destination_fail(self):
        maintenance.organize_manual_data(self.root, apply=True)
        (self.root / NAMES[0]).write_text("conflict")
        with self.assertRaises(ValueError): maintenance.resolve_data_path(self.root, NAMES[0])
        (self.root / NAMES[0]).unlink()
        journal = self.root / "manifests/file_relocations.json"
        record = maintenance.read_json(journal); record["files"][0]["to"] = "../escape"
        journal.write_text(json.dumps(record))
        with self.assertRaises(ValueError): maintenance.resolve_data_path(self.root, NAMES[0])


if __name__ == "__main__":
    unittest.main()
