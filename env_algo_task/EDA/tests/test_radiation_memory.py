"""Smaller CRaTER parsing batches must not change daily/hourly summaries."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace
import hashlib
import json
import xml.etree.ElementTree as ET

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "darrel stuff/EDA/shared"), str(ROOT / "darrel stuff/EDA/Moon/Stage3_Requirements"), str(ROOT)]
import stage3_annual_radiation_eda as eda
import stage3_mission_eda as mission


def write_secondary_fixture(folder):
    ns = "{http://pds.nasa.gov/pds4/pds/v1}"
    root = ET.Element(ns+"Product_Observational")
    area = ET.SubElement(root, ns+"File_Area_Observational")
    file = ET.SubElement(area, ns+"File")
    ET.SubElement(file, ns+"file_name").text = "secondary.tab"
    table = ET.SubElement(area, ns+"Table_Character")
    ET.SubElement(table, ns+"offset").text = "0"
    ET.SubElement(table, ns+"records").text = "9"
    record = ET.SubElement(table, ns+"Record_Character")
    names = [("TIME", 24, "ASCII_Date_Time_YMD")]
    names += [(name, 8, "ASCII_Real") for name in
              ["BIASCMD", "CALLOW", "CALHIGH", "GOOD", "REJECT", "TOTAL"]
              + [f"PROCDFLAG {i}" for i in range(1, 7)]]
    position = 1
    for name, width, dtype in names:
        field = ET.SubElement(record, ns+"Field_Character")
        for key, value in [("name", name), ("field_location", position),
                           ("field_length", width), ("data_type", dtype)]:
            ET.SubElement(field, ns+key).text = str(value)
        position += width
    ET.SubElement(record, ns+"record_length").text = str(position)
    lines = []
    for i in range(9):
        values = {"TIME": f"2024-01-01T00:00:{i+i//4:02d}", "BIASCMD": int(i != 5),
                  "CALLOW": 0, "CALHIGH": 0, "GOOD": -1 if i == 3 else i*2,
                  "REJECT": i, "TOTAL": i*3}
        values.update({f"PROCDFLAG {d}": 1 for d in range(1, 7)})
        lines.append("".join(str(values[name]).rjust(width) for name, width, _ in names)+"\n")
    (folder/"secondary.tab").write_bytes("".join(lines).encode("ascii"))
    label = folder/"secondary.xml"
    ET.ElementTree(root).write(label)
    return label


class RadiationMemoryTests(unittest.TestCase):
    def test_smaller_hash_buffer_preserves_receipt_checks(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            path, receipt = folder/"input.tab", folder/"input.tab.json"
            expected = hashlib.sha256()
            block = b"verified-source-record\n"*3000
            with path.open("wb") as stream:
                for _ in range(32):
                    stream.write(block)
                    expected.update(block)
            item = {"relative_path": path.name, "receipt": receipt.name,
                    "size_bytes": path.stat().st_size, "sha256": expected.hexdigest(),
                    "url": "https://example.invalid/test-fixture"}
            receipt.write_text(json.dumps({"sha256": item["sha256"], "source": {"url": item["url"]}}))
            run = SimpleNamespace(record={"inputs": {}})
            self.assertEqual(mission.external_input(run, {"external_root": directory}, item), path)
            self.assertEqual(run.record["inputs"]["external_data/input.tab"]["sha256"], expected.hexdigest())
            receipt.write_text(json.dumps({"sha256": "changed", "source": {"url": item["url"]}}))
            with self.assertRaisesRegex(ValueError, "receipt changed"):
                mission.external_input(run, {"external_root": directory}, item)

    def test_small_batches_keep_all_statistics_and_cross_batch_gaps(self):
        with tempfile.TemporaryDirectory() as directory:
            label = write_secondary_fixture(Path(directory))
            old_row, old_hourly = eda.crater_day(label, "2024-01-01")
            new_row, new_hourly = eda.crater_day(label, "2024-01-01", chunk_rows=3)
            self.assertEqual(old_row, new_row)
            pd.testing.assert_frame_equal(old_hourly, new_hourly)
            self.assertEqual(new_row["records"], 9)
            self.assertEqual(new_row["cadence_gaps_over_1_01s"], 2)
            self.assertEqual(new_row["negative_or_missing_counter_rows"], 1)

    def test_chunk_size_reaches_reader_and_wrong_dates_still_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            label = write_secondary_fixture(Path(directory))
            with patch.object(eda, "read_pds4", wraps=eda.read_pds4) as reader:
                with self.assertRaises(ValueError):
                    eda.crater_day(label, "2024-01-02", chunk_rows=3)
                self.assertEqual(reader.call_args.kwargs["chunk_rows"], 3)

    def test_invalid_chunk_size_fails_without_reading(self):
        for size in (0, -1, True, 1.5):
            with self.subTest(size=size), self.assertRaises(ValueError):
                eda.crater_day(Path("not-read.xml"), "2024-01-01", chunk_rows=size)


if __name__ == "__main__":
    unittest.main()
