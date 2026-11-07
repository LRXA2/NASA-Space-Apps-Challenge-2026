from pathlib import Path
import json
import sys
import tempfile
import unittest
import zipfile

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT), str(ROOT / "darrel stuff/EDA")]
from research_p1_readers import (read_pds4, pds4_image, dose_profiles, pds3_number,
                                 nsp1_wavelengths, published_crater_tables, pilot_files, INVENTORY)


class ResearchReaderTests(unittest.TestCase):
    def setUp(self):
        base = ROOT / "darrel stuff/data/verification"
        base.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=base)
        self.root = Path(self.temp.name).resolve()
        self.assertTrue(self.root.is_relative_to(base.resolve()))
        self.addCleanup(self.temp.cleanup)

    def label(self, table):
        path = self.root / "values.xml"
        path.write_text('<Product_Observational xmlns="http://pds.nasa.gov/pds4/pds/v1">'
                        '<File_Area_Observational><File><file_name>values.tab</file_name></File>'
                        + table + '</File_Area_Observational></Product_Observational>', encoding="utf-8")
        return path

    def character_label(self):
        return self.label('''<Table_Character><offset>2</offset><records>2</records>
          <Record_Character><record_length>10</record_length>
          <Field_Character><name>name</name><field_location>1</field_location><field_length>4</field_length><data_type>ASCII_String</data_type></Field_Character>
          <Field_Character><name>value</name><field_location>5</field_location><field_length>5</field_length><data_type>ASCII_Real</data_type>
          <Special_Constants><missing_constant>-9999</missing_constant></Special_Constants></Field_Character>
          </Record_Character></Table_Character>''')

    def test_fixed_width_offset_string_and_missing_constant(self):
        label = self.character_label()
        (self.root / "values.tab").write_bytes(b"H\nAB    123\nCD  -9999\n")
        frame = read_pds4(label, chunk_rows=1)
        self.assertEqual(frame.name.tolist(), ["AB", "CD"])
        self.assertEqual(frame.value.iloc[0], 123.)
        self.assertTrue(np.isnan(frame.value.iloc[1]))

    def test_wrong_byte_count_fails(self):
        label = self.character_label()
        (self.root / "values.tab").write_bytes(b"short")
        with self.assertRaisesRegex(ValueError, "byte count"):
            read_pds4(label)

    def test_zip_declared_filename_is_case_insensitive_without_extraction(self):
        label = self.character_label()
        archive = self.root / "values.zip"
        with zipfile.ZipFile(archive, "w") as z:
            z.writestr("VALUES.TAB", b"H\nAB    123\nCD  -9999\n")
        result = read_pds4(label, archive=archive, columns=["value"])
        self.assertEqual(result.columns.tolist(), ["value"])
        self.assertFalse((self.root / "VALUES.TAB").exists())

    def test_delimited_offset_and_numeric_types(self):
        label = self.label('''<Table_Delimited><offset>4</offset><records>2</records><field_delimiter>Comma</field_delimiter>
          <Record_Delimited><Field_Delimited><name>name</name><data_type>ASCII_String</data_type></Field_Delimited>
          <Field_Delimited><name>value</name><data_type>ASCII_Real</data_type></Field_Delimited></Record_Delimited></Table_Delimited>''')
        (self.root / "values.tab").write_bytes(b"x,y\na,1\nb,2\n")
        result = read_pds4(label)
        self.assertEqual(result.value.tolist(), [1, 2])
        self.assertEqual(result.name.tolist(), ["a", "b"])

    def test_image_specials_masked_before_one_scale_application(self):
        label = self.label('''<Array_2D_Image><offset>4</offset><Element_Array><data_type>SignedLSB2</data_type>
          <unit>Scaled I/F</unit><scaling_factor>0.5</scaling_factor><value_offset>1</value_offset></Element_Array>
          <Axis_Array><axis_name>Line</axis_name><elements>2</elements></Axis_Array>
          <Axis_Array><axis_name>Sample</axis_name><elements>2</elements></Axis_Array>
          <Special_Constants><missing_constant>-9999</missing_constant><valid_minimum>-10</valid_minimum></Special_Constants></Array_2D_Image>''')
        path = self.root / "image.img"
        path.write_bytes(b"HEAD" + np.array([[-9999, -2], [3, 4]], dtype="<i2").tobytes())
        values, meta = pds4_image(label, path, stride=1)
        np.testing.assert_allclose(values, [[np.nan, 0], [2.5, 3]], equal_nan=True)
        self.assertEqual(meta["valid_sampled_pixels"], 3)

    def test_dose_scenarios_and_unknown_headers(self):
        path = self.root / "dose.txt"
        path.write_text('Al thickness 1 g/cm2, Smax2015, particles all\n detpth, cm\tEffective dose, cSv/year\n0\t20\n1\t19\n')
        frame = dose_profiles(path)
        self.assertEqual(frame.al_g_cm2.tolist(), [1, 1])
        self.assertEqual(frame.effective_dose_cSv_year.tolist(), [20, 19])
        path.write_text('Unknown scenario\n0 20\n')
        with self.assertRaisesRegex(ValueError, "before scenario"):
            dose_profiles(path)

    def test_pds3_numeric_metadata_rejects_ambiguity(self):
        self.assertEqual(pds3_number(' MAP_SCALE = 0.0074 <km/pixel>\n', 'MAP_SCALE'), .0074)
        with self.assertRaisesRegex(ValueError, "ambiguous"):
            pds3_number('OFFSET = 0\nOFFSET = 1\n', 'OFFSET')

    def test_wavelength_mapping_keeps_pixel_with_padding_in_unused_coefficient(self):
        path = self.root / "calibration.txt"
        path.write_text('PDS header\nPixel\tWavelength(um)\tCoefficient\tSigma\n'
                        '0\t1.1693218\t7.4\t0.9\n1\t1.1829783\t22\t\t1.08\n')
        result = nsp1_wavelengths(path)
        self.assertEqual(result.Pixel.tolist(), [0, 1])
        np.testing.assert_allclose(result["Wavelength(um)"], [1.1693218, 1.1829783])
        path.write_text('No mapping here')
        with self.assertRaisesRegex(ValueError, "header"):
            nsp1_wavelengths(path)

    def test_observed_and_modeled_radiation_blocks_are_not_pooled(self):
        path = self.root / "study.txt"
        path.write_text('Time, year\tCRaTER monthly averaged, cGy/year\tCRaTER std, cGy/year\n'
                        '2009.5\t10.5\t0.8\n'
                        'Time, year\tGCR in Si detector, cGy/year\tp\tn\tgamma\te\n'
                        '2009.5\t11\t0\t0.1\t0.2\t0.3\n')
        observed, modeled = published_crater_tables(path)
        self.assertEqual(observed.shape, (1, 3))
        self.assertEqual(modeled.shape, (1, 6))
        self.assertEqual(observed.absorbed_rate_cGy_year.iloc[0], 10.5)
        self.assertEqual(modeled.GCR_in_Si_cGy_year.iloc[0], 11)

    def test_pilot_selection_enforces_local_root_size_and_source(self):
        path = self.root / "D07/one.tab"
        path.parent.mkdir()
        path.write_bytes(b"1")
        receipt = path.with_name(path.name + ".json")
        receipt.write_text(json.dumps({"source": {"url": "https://example.test/one.tab"}}))
        inventory = self.root / INVENTORY
        inventory.parent.mkdir(parents=True)
        item = {"dataset": "D07", "relative_path": "D07/one.tab", "size_bytes": 1,
                "url": "https://example.test/one.tab"}
        inventory.write_text(json.dumps({"files": [item]}))
        self.assertEqual(pilot_files(self.root, "D07", ".tab"), [path.resolve()])
        receipt.write_text(json.dumps({"source": {"url": "https://different.test/one.tab"}}))
        with self.assertRaisesRegex(ValueError, "size/source"):
            pilot_files(self.root, "D07", ".tab")
        item["relative_path"] = "../escape.tab"
        inventory.write_text(json.dumps({"files": [item]}))
        with self.assertRaisesRegex(ValueError, "escapes"):
            pilot_files(self.root, "D07", ".tab")


if __name__ == "__main__":
    unittest.main()
