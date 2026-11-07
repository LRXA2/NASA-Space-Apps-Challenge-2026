from pathlib import Path
import sys
import unittest

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / 'darrel stuff/EDA'), str(ROOT)]
from environmental_selection_eda import (lattice, components, select_component_candidates, associate_points,
    candidate_thermal_profiles, center_phase_spans, benefit_values, pareto_dominance, preference_scenarios,
    diagnostic_gate, gate_scenarios, requirement_readiness)


def grid():
    cells, meta = lattice([0, 0, 180, 180], 60, 30)
    cells['solar_visibility'] = .8
    cells['earth_visibility'] = .8
    cells['slope_deg'] = 5.
    return cells, meta


def pool():
    return pd.DataFrame({'unit_id': ['a', 'b', 'c', 'd'], 'region': ['R'] * 4, 'pool': ['test'] * 4,
                         'solar_fraction': [.8, .2, .8, np.nan], 'earth_fraction': [.8, .2, .8, .8],
                         'slope_deg': [5., 20., 5., 5.]})


class EnvironmentalSelectionTests(unittest.TestCase):
    def test_full_cells_remain_inside_bounds(self):
        cells, m = lattice([3, 7, 202, 202], 60)
        self.assertTrue((cells.x_m - 30 >= 3).all())
        self.assertTrue((cells.y_m + 30 <= 202).all())
        self.assertEqual(len(cells), m['width'] * m['height'])
        with self.assertRaises(ValueError):
            lattice([0, 0, 1, 1], 60)

    def test_connectivity_and_nominal_area(self):
        cells, m = grid()
        cells.loc[~cells.index.isin([0, 4, 8]), 'solar_visibility'] = 0
        _, table4, a = components(cells, m, connectivity=4)
        _, table8, b = components(cells, m, connectivity=8)
        self.assertEqual(a['component_count'], 3)
        self.assertEqual(b['component_count'], 1)
        self.assertEqual(table4.nominal_projected_area_m2.sum(), 3 * 60**2)
        self.assertEqual(table8.cells.iloc[0], 3)
        self.assertTrue(table4.lattice_interior_diameter_proxy_m.eq(60).all())

    def test_missing_and_empty_masks_not_invented_area(self):
        cells, m = grid()
        cells.solar_visibility = np.nan
        _, table, summary = components(cells, m)
        self.assertTrue(table.empty)
        self.assertEqual(summary['unknown_joint_cells'], 9)
        self.assertTrue(np.isnan(summary['joint_sample_fraction']))
        self.assertEqual(summary['largest_component_cells'], 0)

    def test_whole_mask_boundary_padding_and_grid_validation(self):
        cells, m = grid()
        labels, table, summary = components(cells, m)
        self.assertEqual(summary['lattice_interior_diameter_proxy_m'], 180)
        self.assertTrue(table.touches_analysis_boundary.iloc[0])
        with self.assertRaises(ValueError):
            components(cells.iloc[:-1], m)
        with self.assertRaises(ValueError):
            components(cells, m, connectivity=6)

    def test_monotonic_tighter_conditions(self):
        cells, m = grid()
        cells.solar_visibility = np.linspace(0, 1, len(cells))
        a = components(cells, m, (.25, .5, 10))[2]
        b = components(cells, m, (.75, .5, 10))[2]
        self.assertGreaterEqual(a['joint_cells'], b['joint_cells'])

    def test_sweep_summary_matches_detailed_components(self):
        cells, meta = grid()
        cells.loc[[1, 3, 5, 7], 'solar_visibility'] = 0
        a, _, detailed = components(cells, meta)
        b, empty, summary = components(cells, meta, detail=False)
        np.testing.assert_array_equal(a, b)
        self.assertTrue(empty.empty)
        self.assertEqual(detailed, summary)

    def test_component_selection_preserves_cell_identity_when_shuffled(self):
        cells, m = grid()
        cells.loc[cells.index > 0, 'solar_visibility'] = 0
        labels, table, _ = components(cells, m)
        result, selected = select_component_candidates(cells.iloc[::-1], labels, table, 'R')
        self.assertEqual(result.loc[result.candidate_id.notna(), 'row'].tolist(), [0])
        self.assertEqual(result.loc[result.candidate_id.notna(), 'col'].tolist(), [0])
        self.assertEqual(len(selected), 1)

    def test_point_association_bounds_not_thermal_footprint(self):
        cells, m = grid()
        labels, table, _ = components(cells, m)
        cells, _ = select_component_candidates(cells, labels, table, 'R')
        points = pd.DataFrame({'x_m': [0., 179.9, 180., -1.], 'y_m': [180., .1, 100., 100.]})
        assigned = associate_points(points, cells, m)
        self.assertTrue(assigned.iloc[:2].notna().all())
        self.assertTrue(assigned.iloc[2:].isna().all())

    def test_thermal_empty_products_and_cohorts_retained(self):
        obs = pd.DataFrame({'source_product': ['p1'], 'clon': [1.], 'clat': [-85.], 'tbol': [100.],
            'usable': [True], 'complete_common_cohort': [False], 'candidate_id': ['a']})
        table = candidate_thermal_profiles(obs, ['a', 'b'], ['p1', 'p2'])
        self.assertEqual(len(table), 8)
        self.assertEqual(table.usable_centers.sum(), 1)
        self.assertTrue(table.loc[table.usable_centers.eq(0), 'tbol_median_K'].isna().all())
        with self.assertRaises(ValueError):
            candidate_thermal_profiles(pd.concat([obs, obs]), ['a'], ['p1'])

    def test_single_phase_has_no_variation_estimate(self):
        obs = pd.DataFrame({'source_product': ['p1'], 'clon': [1.], 'clat': [-85.], 'tbol': [100.],
            'usable': [True], 'candidate_id': ['a']})
        result = center_phase_spans(obs, ['p1', 'p2'])
        self.assertTrue(np.isnan(result.phase_average_span_K.iloc[0]))
        self.assertFalse(result.all_common_products_observed.iloc[0])

    def test_domain_benefits_and_missingness(self):
        result = benefit_values(pool(), 'physical_domain')
        self.assertAlmostEqual(result.slope_deg.iloc[0], 1 - 5 / 90)
        self.assertTrue(result.iloc[3].isna().all())
        bad = pool(); bad.loc[0, 'solar_fraction'] = 2
        with self.assertRaises(ValueError):
            benefit_values(bad, 'physical_domain')

    def test_pareto_ties_and_unknowns(self):
        result = pareto_dominance(pool())
        self.assertEqual(result.pareto_status.tolist(), ['nondominated', 'dominated', 'nondominated', 'Unknown'])
        self.assertEqual(result.dominated_by_units.iloc[1], 2)

    def test_weight_grid_and_missing_scores_not_renormalized(self):
        result = preference_scenarios(pool())
        self.assertEqual(result.scenario_id.nunique(), 30)
        self.assertTrue(result.loc[result.unit_id.eq('d'), 'diagnostic_preference_score'].isna().all())
        self.assertTrue(result.operational_status.eq('Unknown').all())
        self.assertFalse(result.policy_adopted.any())
        weights = result[['solar_weight', 'earth_weight', 'slope_weight']].sum(axis=1)
        np.testing.assert_allclose(weights, 1)

    def test_gate_known_violation_and_missing_unknown(self):
        p = pool(); p.loc[3, 'earth_fraction'] = .1
        self.assertEqual(diagnostic_gate(p, (.5, .5, 10)).tolist(),
                         ['DiagnosticMet', 'DiagnosticNotMet', 'DiagnosticMet', 'DiagnosticNotMet'])
        p.loc[3, 'earth_fraction'] = .8
        self.assertEqual(diagnostic_gate(p, (.5, .5, 10)).iloc[3], 'Unknown')
        p.loc[3, 'solar_fraction'] = np.inf
        self.assertEqual(diagnostic_gate(p, (.5, .5, 10)).iloc[3], 'Unknown')

    def test_no_eligible_candidates_never_fake_top_five(self):
        p = pool(); p.solar_fraction = 0
        result, detail = gate_scenarios(p, preference_scenarios(p))
        self.assertTrue(result.diagnostic_met.eq(0).all())
        self.assertTrue(result.gate_first_top5_count.eq(0).all())
        self.assertTrue(detail.empty)

    def test_late_filter_can_hide_qualifying_candidates(self):
        p = pd.DataFrame({'unit_id': list('abcdef'), 'region': ['R'] * 6, 'pool': ['test'] * 6,
            'solar_fraction': [.1] * 5 + [.3], 'earth_fraction': [1.] * 5 + [.3], 'slope_deg': [0.] * 5 + [10.]})
        result, _ = gate_scenarios(p, preference_scenarios(p))
        row = result.loc[result.solar_min.eq(.25) & result.earth_min.eq(.25) & result.slope_q90_max_deg.eq(10)].iloc[0]
        self.assertEqual(row.eligible_hidden_by_late_top5_filter, 1)

    def test_actual_requirements_stay_unknown(self):
        result = requirement_readiness(['R1', 'R2'])
        self.assertEqual(len(result), 10)
        self.assertTrue(result.status.eq('Unknown').all())
        self.assertTrue(result.operational_score.isna().all())


if __name__ == '__main__':
    unittest.main()
