"""Scalar extraction and association guards for the standalone soil study."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'Moon/Stage3_Requirements'))
from stage3_soil_eda import parse_handbook, bh_adjust, mission_for, correlation_tables, PROPERTIES


def sheet(body, sample='10010', mission=11, page=12):
    return {'pdf_page': page, 'text': f'SOIL: {sample}\n{body}\nApollo {mission} Samples Data Sheet'}


class SoilExtractionTests(unittest.TestCase):
    def test_scalar_missing_and_adjacent_columns(self):
        frame, observations, holds, _ = parse_handbook([sheet(
            '1. IS/FeO 75.0 mature\n2. Agglutinates\n1. Mz 52 µm\n'
            '2. Md Feldspar 60\nMAJOR ELEMENTS TRACE ELEMENTS\n'
            'SiO2 42.16 Sc 60.2 La 15.8\nFeO Ba 170 Eu 1.60\nAl203 13.60 Co 28')])
        row = frame.iloc[0]
        self.assertEqual(row.Is_FeO, 75)
        self.assertEqual(row.Mz_um, 52)
        self.assertEqual(row.SiO2, 42.16)
        self.assertEqual(row.Al2O3, 13.60)
        self.assertTrue(row[['Md_um', 'FeO', 'agglutinates_percent']].isna().all())
        self.assertEqual(len(holds), 0)

    def test_explicit_fine_fraction_selected_without_guessing_other_fraction(self):
        frame, _, holds, _ = parse_handbook([sheet(
            'GRAIN SIZE PARAMETERS\n1. Mz 129 µm (<1 cm): 99\nµm (<1 mm)\n'
            '2. Md 139 µm\nMAJOR ELEMENTS\nFeO 10.4 Ba 100')])
        self.assertEqual(frame.iloc[0].Mz_um, 99)
        self.assertTrue(frame.Md_um.isna().all())
        self.assertEqual(len(holds), 1)

    def test_conflicting_values_and_multiple_columns_are_held(self):
        frame, _, holds, _ = parse_handbook([sheet(
            'MAJOR ELEMENTS\nFeO 15.0 Ba 100\nFeO 16.0 Ba 100\nTiO2 4.5 5.2 V 40')])
        self.assertTrue(frame[['FeO', 'TiO2']].isna().all().all())
        self.assertEqual(len(holds), 2)

    def test_only_immediate_data_continuation_is_joined(self):
        pages = [sheet('1. IS/FeO 75'),
                 {'pdf_page': 13, 'text': 'MAJOR ELEMENTS\nFeO 15.3 Ba 100\nApollo 11 Samples Data Sheet'},
                 {'pdf_page': 14, 'text': 'BIBLIOGRAPHY\nFeO 20.0'},
                 {'pdf_page': 15, 'text': 'MAJOR ELEMENTS\nFeO 90.0\nApollo 11 Samples Data Sheet'}]
        frame, _, _, _ = parse_handbook(pages)
        self.assertEqual(frame.iloc[0].FeO, 15.3)

    def test_mission_identity_conflict_is_not_repaired(self):
        pages = [sheet('1. IS/FeO 57', '21003', 12, 79), sheet('1. IS/FeO 75')]
        frame, _, holds, _ = parse_handbook(pages)
        self.assertEqual(list(frame.sample_id), ['10010'])
        self.assertEqual(holds.iloc[0].feature, 'identity')
        self.assertEqual(mission_for('15013'), 15)
        self.assertEqual(mission_for('60050'), 16)

    def test_bh_adjustment_preserves_original_order(self):
        self.assertTrue(all(abs(a-b)<1e-12 for a,b in zip(bh_adjust([.04, .001, .03]), [.04, .003, .04])))

    def test_unqualified_grain_unit_is_withheld(self):
        frame, _, holds, _ = parse_handbook([sheet('1. Mz 52\n2. Md 6 cm\n')])
        self.assertTrue(frame[['Mz_um', 'Md_um']].isna().all().all())
        self.assertEqual(len(holds), 2)

    def test_mission_adjustment_exposes_pooled_confounding(self):
        import pandas as pd
        import numpy as np
        rows = []
        for mission, offset in [(11, 0), (12, 100)]:
            for i in range(12):
                row = dict.fromkeys(PROPERTIES, np.nan)
                row.update(sample_id=f'{mission}_{i}', mission=mission,
                           Is_FeO=offset+i, FeO=offset+12-i)
                rows.append(row)
        pooled, within, _ = correlation_tables(pd.DataFrame(rows))
        self.assertGreater(pooled.iloc[0].spearman_rho, 0)
        self.assertAlmostEqual(pooled.iloc[0].mission_adjusted_rank_association, -1)
        self.assertTrue((within.spearman_rho < -.99).all())


if __name__ == '__main__':
    unittest.main()
