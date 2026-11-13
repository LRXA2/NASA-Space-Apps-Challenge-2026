"""Instrument identity and bounded primary-sample semantics."""
from pathlib import Path
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

import numpy as np
import pandas as pd

sys.path[:0] = [str(Path(__file__).resolve().parents[1] / "shared"), str(Path(__file__).resolve().parents[1] / "Moon/Stage3_Requirements")]
from stage3_radiation_refresh import platform_summary, primary_sample, sample_record_indices
from research_p1_readers import read_pds4


def primary_fixture(directory, rows=7):
    ns = "http://pds.nasa.gov/pds4/pds/v1"
    tag = lambda name: "{"+ns+"}"+name
    root = ET.Element(tag("Product_Observational"))
    area = ET.SubElement(root, tag("File_Area_Observational"))
    f = ET.SubElement(area, tag("File")); ET.SubElement(f, tag("file_name")).text = "primary.TAB"
    table = ET.SubElement(area, tag("Table_Character"))
    ET.SubElement(table, tag("offset")).text = "0"
    ET.SubElement(table, tag("records")).text = str(rows)
    record = ET.SubElement(table, tag("Record_Character"))
    names = [("TIME", 25, "ASCII_Date_Time_YMD", None), ("DQI", 8, "ASCII_Real", None)]
    names += [(f"{name} Item {d}", 8, "ASCII_Real", unit) for name, unit in
              [("ENERGY", "keV"), ("LET", "keV/micron"), ("MAXSIGFLAGS", None), ("GTLLDFLAGS", None)]
              for d in range(1,7)]
    location = 1
    for name, width, dtype, unit in names:
        field = ET.SubElement(record, tag("Field_Character"))
        for key, value in [("name", name), ("field_location", str(location)),
                           ("field_length", str(width)), ("data_type", dtype)]:
            ET.SubElement(field, tag(key)).text = value
        if unit:
            ET.SubElement(field, tag("unit")).text = unit
        location += width
    ET.SubElement(record, tag("record_length")).text = str(location)
    tab = Path(directory)/"primary.TAB"
    with tab.open("wb") as stream:
        for i in range(rows):
            text = ""
            for name, width, _, _ in names:
                value = f"2024-01-01T00:00:{i:02d}.000" if name == "TIME" else str(i)
                text += value.rjust(width)
            stream.write((text+"\n").encode())
    label = Path(directory)/"primary.xml"
    ET.ElementTree(root).write(label)
    return label, tab


class RadiationRefreshTests(unittest.TestCase):
    def test_distributed_blocks_are_bounded_unique_and_span_file(self):
        indices = sample_record_indices(4_000_000, 20_000)
        self.assertEqual(len(indices), 20_000)
        self.assertEqual(len(np.unique(indices)), 20_000)
        self.assertEqual(indices[0], 0)
        self.assertEqual(indices[-1], 3_999_999)
        self.assertEqual(int(np.sum(np.diff(indices) != 1))+1, 32)

    def test_invalid_sample_size_is_rejected(self):
        with self.assertRaises(ValueError):
            sample_record_indices(10, 0)

    def test_primary_positions_match_established_reader(self):
        with tempfile.TemporaryDirectory() as d:
            label, tab = primary_fixture(d)
            sample, records = primary_sample(label, tab, 3)
            complete = read_pds4(label)
            self.assertEqual(records, 7)
            self.assertEqual(sample.source_record_index.tolist(), [0,3,6])
            for name in complete:
                self.assertEqual(sample[name].tolist(), complete[name].iloc[[0,3,6]].tolist())

    def test_primary_sample_is_bounded_and_not_duplicate_records(self):
        with tempfile.TemporaryDirectory() as d:
            label, tab = primary_fixture(d)
            sample, records = primary_sample(label, tab, 100)
            self.assertEqual(len(sample), records)
            self.assertFalse(sample.source_record_index.duplicated().any())

    def test_wrong_label_identity_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            label, tab = primary_fixture(d)
            other = Path(d)/"other.TAB"; other.write_bytes(tab.read_bytes())
            with self.assertRaisesRegex(ValueError, "identity"):
                primary_sample(label, other)

    def test_truncation_is_not_missing_data_fallback(self):
        with tempfile.TemporaryDirectory() as d:
            label, tab = primary_fixture(d); tab.write_bytes(tab.read_bytes()[:-1])
            with self.assertRaisesRegex(ValueError, "size/count"):
                primary_sample(label, tab)

    def test_changed_let_units_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            label, tab = primary_fixture(d)
            label.write_text(label.read_text().replace("keV/micron", "unqualified"))
            with self.assertRaisesRegex(ValueError, "units"):
                primary_sample(label, tab)

    def test_platforms_versions_and_directions_remain_distinct(self):
        rows = []
        for platform, version, date in [("16","a","2024-01-01"),("19","a","2024-01-01"),("19","b","2024-01-02")]:
            for sensor in [0,1]:
                rows.append(dict(platform=platform,version=version,date=date,sensor=sensor,channel=0,
                    lower_energy_keV=1,upper_energy_keV=2,recorded_bins=288,qualified_bins=10,qualified_max_flux=2))
        summary = platform_summary(pd.DataFrame(rows))
        self.assertEqual(len(summary), 6)
        self.assertEqual(summary.recorded_bins.sum(), 6*288)
        self.assertTrue(summary.complete_qualified_channel_days.eq(0).all())

    def test_duplicate_platform_day_versions_are_not_silently_summed(self):
        row = dict(platform="19",version="a",date="2024-01-01",sensor=0,channel=0,
                   lower_energy_keV=1,upper_energy_keV=2,recorded_bins=288,qualified_bins=0,qualified_max_flux=np.nan)
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            platform_summary(pd.DataFrame([row, dict(row, version="b")]))


if __name__ == "__main__":
    unittest.main()
