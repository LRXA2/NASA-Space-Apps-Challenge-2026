from pathlib import Path
import io
import sys
import tempfile
import unittest
import zipfile

import numpy as np
import pandas as pd
from scipy.io import savemat

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / 'darrel stuff/EDA'), str(ROOT)]
from reference_eda import (checked_member, iter_battery_cells, trace_summary, battery_record_summary,
                           relative_capacity, matlab_start, soil_table, impedance_estimate)


class ReferenceEDATests(unittest.TestCase):
    def setUp(self):
        base = ROOT / 'darrel stuff/data/verification'
        base.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix='.reference-eda-test-', dir=base)
        self.folder = Path(self.temp.name).resolve()
        self.assertTrue(self.folder.is_relative_to(base.resolve()))
        self.addCleanup(self.temp.cleanup)

    def trace(self):
        return {'Time': [0, 1800, 3600], 'Voltage_measured': [3., 3., 3.],
                'Current_measured': [-2., -2., -2.], 'Temperature_measured': [20., 21., 22.]}

    def test_current_sign_and_time_units_in_trace_integral(self):
        result = trace_summary(self.trace())
        self.assertEqual(result['observed_discharge_Ah'], 2.)
        self.assertEqual(result['observed_discharge_Wh'], 6.)
        self.assertEqual(result['integration_status'], 'all_intervals')
        self.assertEqual(result['temperature_max_C'], 22.)

    def test_missing_endpoint_does_not_bridge_two_intervals(self):
        data = {'Time': [0., 1., 2., 3.], 'Voltage_measured': [3.] * 4,
                'Current_measured': [-1., np.nan, -1., -1.], 'Temperature_measured': [20.] * 4}
        result = trace_summary(data)
        self.assertAlmostEqual(result['observed_discharge_Ah'], 1/3600)
        self.assertAlmostEqual(result['finite_interval_fraction'], 1/3)
        self.assertEqual(result['integration_status'], 'partial_observed_intervals')

    def test_missing_vectors_produce_nan_not_fake_zero_energy(self):
        result = trace_summary({'Time': [0, 1]})
        self.assertTrue(np.isnan(result['observed_discharge_Wh']))
        self.assertEqual(result['integration_status'], 'missing_or_mismatched_vectors')

    def test_time_not_sorted_or_duplicated_silently(self):
        data = self.trace(); data['Time'] = [0, 0, 3600]
        result = trace_summary(data)
        self.assertEqual(result['nonpositive_time_steps'], 1)
        self.assertEqual(result['integration_status'], 'partial_observed_intervals')
        self.assertEqual(data['Time'], [0, 0, 3600])

    def nested(self, value=2.):
        raw = io.BytesIO()
        record = {'type': 'discharge', 'ambient_temperature': 24,
                  'time': [2008, 4, 2, 15, 25, 41.593], 'data': {**self.trace(), 'Capacity': value}}
        savemat(raw, {'B0005': {'cycle': record}})
        package = io.BytesIO()
        with zipfile.ZipFile(package, 'w') as inner:
            inner.writestr('README.txt', 'Data Description: fixture only.\nFiles:\nB0005.mat\n')
            inner.writestr('B0005.mat', raw.getvalue())
        return package.getvalue()

    def test_identical_nested_histories_are_counted_once_with_aliases(self):
        payload = self.nested()
        path = self.folder / 'outer.zip'
        with zipfile.ZipFile(path, 'w') as outer:
            outer.writestr('first.zip', payload)
            outer.writestr('second.zip', payload)
        inventory, documents = [], {}
        results = list(iter_battery_cells(path, inventory, documents))
        self.assertEqual(len(results), 1)
        self.assertEqual([r['duplicate_history'] for r in inventory], [False, True])
        result = battery_record_summary(*results[0])
        self.assertEqual(result.reported_capacity_Ah.iloc[0], 2.)
        self.assertEqual(result.discharge_index.iloc[0], 1)

    def test_conflicting_cell_identity_fails_instead_of_merging(self):
        path = self.folder / 'conflict.zip'
        with zipfile.ZipFile(path, 'w') as outer:
            outer.writestr('first.zip', self.nested(2.))
            outer.writestr('second.zip', self.nested(1.))
        with self.assertRaisesRegex(ValueError, 'Different histories'):
            list(iter_battery_cells(path, [], {}))

    def test_member_paths_and_size_are_bounded_without_extraction(self):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as package:
            package.writestr('../escape.txt', b'x')
            package.writestr('normal.txt', b'123')
        with zipfile.ZipFile(buffer) as package:
            for name, limit in [('../escape.txt', 100), ('normal.txt', 2)]:
                with self.subTest(name=name), self.assertRaises(ValueError):
                    checked_member(package, package.getinfo(name), limit)

    def test_relative_capacity_uses_per_cell_first_positive_value_not_a_universal_rating(self):
        f = pd.DataFrame({'cell_id': ['A','A','B','B'], 'record_index': [1,2,1,2],
                          'reported_capacity_Ah': [np.nan, 1.5, 1., .5]})
        out = relative_capacity(f)
        self.assertTrue(np.isnan(out.relative_reported_capacity.iloc[0]))
        np.testing.assert_allclose(out.relative_reported_capacity.iloc[1:], [1., 1., .5])
        self.assertNotIn('relative_reported_capacity', f)

    def test_matlab_date_preserves_fractional_seconds_without_inventing_utc(self):
        self.assertEqual(matlab_start([2008,4,2,15,25,41.593]), '2008-04-02T15:25:41.593000')

    def test_complex_fit_estimate_is_retained_but_not_used_as_real_resistance(self):
        result = impedance_estimate(.05-.03j, 'Re')
        self.assertEqual(result['Re_source_real_ohm'], .05)
        self.assertEqual(result['Re_source_imag_ohm'], -.03)
        self.assertEqual(result['Re_estimate_status'], 'complex_estimate')
        self.assertTrue(np.isnan(result['Re_ohm']))
        self.assertEqual(impedance_estimate(.05, 'Re')['Re_ohm'], .05)

    def soil_fixture(self, suffix=11, stress_unit='Newton/cm^2'):
        names = ['LOAD','STRESS','PENETRATION_DEPTH','CORRECTION'] if suffix == 11 else ['LOAD','STRESS','PENETRATION_DEPTH']
        units = ['Newton',stress_unit,'Centimeter','Centimeter']
        rows = [[0.,-9.99,0.,3.75],[4.9,1.52,2.84,6.59]]
        length = len(names) * 6 + 2
        label = self.folder / f'a15_smss_71_m016935_{suffix:03d}.xml'
        payload = b''.join((''.join(f'{v:6.2f}' for v in row[:len(names)])+'\r\n').encode() for row in rows)
        label.with_suffix('.tab').write_bytes(payload)
        fields = ''.join(f'<Field_Character><name>{name}</name><field_location>{i*6+1}</field_location><field_length>6</field_length><data_type>ASCII_Real</data_type><unit>{units[i]}</unit>'
                         + ('<Special_Constants><not_applicable_constant>-9.99</not_applicable_constant></Special_Constants>' if name=='STRESS' else '')
                         + '</Field_Character>' for i,name in enumerate(names))
        label.write_text(f'<Product_Observational xmlns="http://pds.nasa.gov/pds4/pds/v1"><File_Area_Observational><File><file_name>{label.with_suffix(".tab").name}</file_name></File><Table_Character><offset>0</offset><records>2</records><Record_Character><record_length>{length}</record_length>{fields}</Record_Character></Table_Character></File_Area_Observational></Product_Observational>')
        return label, payload

    def test_soil_label_constants_units_and_correction_are_preserved(self):
        label, payload = self.soil_fixture()
        frame, metadata = soil_table(label)
        self.assertTrue(np.isnan(frame.STRESS.iloc[0]))
        self.assertEqual(frame.stress_kPa.iloc[1], 15.2)
        np.testing.assert_allclose(frame.cone_depth_correction_cm, 3.75)
        self.assertEqual(frame.source_row.tolist(), [1,2])
        self.assertEqual(label.with_suffix('.tab').read_bytes(), payload)

    def test_plate_is_not_given_a_cone_correction_or_polar_site_label(self):
        label, payload = self.soil_fixture(15)
        frame, _ = soil_table(label)
        self.assertTrue(frame.cone_depth_correction_cm.isna().all())
        self.assertTrue(frame.geometry.eq('plate').all())
        self.assertTrue(frame.documented_depth_limitation.all())

    def test_unreviewed_soil_units_fail(self):
        label, _ = self.soil_fixture(stress_unit='pascal')
        with self.assertRaisesRegex(ValueError, 'units'):
            soil_table(label)

    def test_supplemental_header_is_not_mistaken_for_the_table_stream(self):
        label, payload = self.soil_fixture()
        header = label.with_suffix('.txt'); header.write_text('Separate descriptive header')
        text = label.read_text().replace('</Product_Observational>',
            f'<File_Area_Observational_Supplemental><File><file_name>{header.name}</file_name></File></File_Area_Observational_Supplemental></Product_Observational>')
        label.write_text(text)
        frame, _ = soil_table(label)
        self.assertEqual(len(frame), 2)
        self.assertEqual(frame.LOAD.iloc[1], 4.9)


if __name__ == '__main__':
    unittest.main()
