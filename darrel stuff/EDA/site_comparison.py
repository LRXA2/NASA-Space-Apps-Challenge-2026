"""Support-aware lunar site comparisons; diagnostic subsets are not suitability rules."""
from itertools import product

import numpy as np
import pandas as pd

COHORTS = ('available', 'positive_spots', 'fixed_common')
JOINT_FIELDS = ['solar_visibility', 'earth_visibility', 'slope_deg']


def cohort_rows(frame, cohort):
    if cohort == 'available':
        return frame
    if cohort == 'positive_spots':
        return frame.loc[frame.spot_count.gt(0)]
    if cohort == 'fixed_common':
        if frame.complete_common_cohort.dtype != bool:
            raise ValueError('Expected explicit boolean common-cohort membership')
        return frame.loc[frame.complete_common_cohort]
    raise ValueError('Unreviewed comparison cohort')


def static_profiles(centers, variables):
    if centers.duplicated(['region', 'clon', 'clat']).any():
        raise ValueError('Repeated centers would reweight static profiles')
    rows = []
    for region, part in centers.groupby('region', sort=True):
        for cohort in COHORTS:
            chosen = cohort_rows(part, cohort)
            for variable, unit in variables.items():
                values = chosen[variable].replace([np.inf, -np.inf], np.nan).dropna()
                q = values.quantile([.1, .5, .9])
                rows.append({'region': region, 'cohort': cohort, 'variable': variable, 'unit': unit,
                             'cohort_centers': len(chosen), 'finite_centers': len(values),
                             'mean': values.mean(), 'q10': q.loc[.1], 'median': q.loc[.5], 'q90': q.loc[.9],
                             'evidence_status': 'observed_context' if len(values) else 'no_finite_cohort'})
    return pd.DataFrame(rows)


def thermal_profiles(regional):
    rows = []
    for region, frame in regional.groupby('region', sort=True):
        common = frame.loc[frame.common_product]
        for cohort, value, count in [('available', 'tbol_median_K', 'usable_rows'),
                                     ('fixed_common', 'fixed_common_tbol_median_K', 'fixed_common_rows')]:
            supported = common.loc[common[count].gt(0) & common[value].notna()]
            values = supported[value]
            rows.append({'region': region, 'cohort': cohort, 'common_products': len(common),
                         'supported_common_products': len(supported),
                         'median_of_product_medians_K': values.median(),
                         'minimum_product_median_K': values.min(), 'maximum_product_median_K': values.max(),
                         'span_of_product_medians_K': values.max()-values.min(),
                         'minimum_centers_per_supported_product': supported[count].min(),
                         'maximum_centers_per_supported_product': supported[count].max(),
                         'aggregation': 'equal product weight; phase-average summaries, not mission extrema',
                         'evidence_status': 'supported' if len(supported) else 'no_complete_common_cohort'})
    return pd.DataFrame(rows)


def joint_state(frame, solar, earth, slope):
    if not (np.isfinite([solar, earth, slope]).all() and 0 <= solar <= 1 and 0 <= earth <= 1 and 0 <= slope <= 90):
        raise ValueError('Diagnostic fractions/slope out of domain')
    valid = np.isfinite(frame[JOINT_FIELDS].to_numpy()).all(axis=1)
    state = pd.Series(pd.array([pd.NA] * len(frame), dtype='boolean'), index=frame.index)
    condition = frame.solar_visibility.ge(solar) & frame.earth_visibility.ge(earth) & frame.slope_deg.le(slope)
    state.loc[valid] = condition.loc[valid]
    return state


def joint_sweep(centers, solar_values, earth_values, slope_values):
    rows = []
    for region, frame in centers.groupby('region', sort=True):
        for cohort in COHORTS:
            part = cohort_rows(frame, cohort)
            valid = np.isfinite(part[JOINT_FIELDS].to_numpy()).all(axis=1)
            measured = part.loc[valid]
            for solar, earth, slope in product(solar_values, earth_values, slope_values):
                joint = joint_state(measured, solar, earth, slope)
                a, b, c = measured.solar_visibility.ge(solar), measured.earth_visibility.ge(earth), measured.slope_deg.le(slope)
                n = len(measured)
                marginal = [int(a.sum()), int(b.sum()), int(c.sum())]
                count = int(joint.sum())
                rows.append({'region': region, 'cohort': cohort, 'solar_min': solar, 'earth_min': earth,
                             'slope_max_deg': slope, 'cohort_centers': len(part), 'finite_joint_centers': n,
                             'unknown_context_centers': int((~valid).sum()),
                             'solar_condition_centers': marginal[0], 'earth_condition_centers': marginal[1],
                             'slope_condition_centers': marginal[2], 'solar_earth_centers': int((a & b).sum()),
                             'solar_slope_centers': int((a & c).sum()), 'earth_slope_centers': int((b & c).sum()),
                             'joint_centers': count, 'joint_observed_center_fraction': count/n if n else np.nan,
                             'marginal_min_fraction_upper_bound': min(marginal)/n if n else np.nan,
                             'marginals_exist_but_joint_absent': bool(min(marginal) > 0 and count == 0) if n else pd.NA,
                             'status': 'diagnostic_only' if n else 'no_finite_cohort'})
    return pd.DataFrame(rows)


def thermal_joint_summary(observations, centers, products, thresholds):
    """All products/cohorts/classes remain indexed, including absent groups."""
    if centers.duplicated(['clon', 'clat']).any() or centers.region.nunique() != 1:
        raise ValueError('Require unique native centers for one region')
    region = centers.region.iloc[0]
    context = centers[['clon', 'clat', 'spot_count']].copy()
    context['diagnostic_joint'] = joint_state(centers, *thresholds).to_numpy()
    context['context_found'] = True
    paired = observations.merge(context, on=['clon', 'clat'], how='left', validate='many_to_one')
    if paired.context_found.isna().any():
        raise ValueError('Thermal center is absent from the accepted context union')
    if paired.duplicated(['source_product', 'clon', 'clat']).any():
        raise ValueError('Repeated center within thermal product')
    paired = paired.loc[paired.usable & paired.source_product.isin(products)].copy()
    if not np.isfinite(paired.tbol).all() or not paired.tbol.gt(0).all():
        raise ValueError('Invalid temperature marked usable')
    paired['condition_class'] = 'unknown_context'
    known = paired.diagnostic_joint.notna()
    paired.loc[known & paired.diagnostic_joint.eq(True), 'condition_class'] = 'joint_subset'
    paired.loc[known & paired.diagnostic_joint.eq(False), 'condition_class'] = 'other_measured_context'
    rows = []
    for cohort in COHORTS:
        chosen = cohort_rows(paired, cohort)
        for product_id in products:
            product_rows = chosen.loc[chosen.source_product.eq(product_id)]
            for condition in ['joint_subset', 'other_measured_context', 'unknown_context']:
                values = product_rows.loc[product_rows.condition_class.eq(condition), 'tbol']
                q = values.quantile([.1, .5, .9])
                rows.append({'region': region, 'cohort': cohort, 'source_product': product_id,
                             'condition_class': condition, 'usable_rows': len(values),
                             'total_usable_product_rows': len(product_rows), 'tbol_q10_K': q.loc[.1],
                             'tbol_median_K': q.loc[.5], 'tbol_q90_K': q.loc[.9],
                             'status': 'observed' if len(values) else 'no_observations'})
    return pd.DataFrame(rows)


def rule_input_table(profiles):
    """Environmental values ready for configuration, not invented rule evaluations."""
    required = {'solar_visibility': ('solar_context', 'fraction'), 'earth_visibility': ('earth_visibility_context', 'fraction'),
                'slope_deg': ('terrain_context', 'degree')}
    records = []
    for variable, (criterion, unit) in required.items():
        for row in profiles.loc[profiles.cohort.eq('available') & profiles.variable.eq(variable)].itertuples():
            records.append({'region': row.region, 'criterion_input': criterion, 'metric': variable+'_median',
                            'value': row.median, 'unit': unit, 'finite_centers': row.finite_centers,
                            'spatial_support': 'observed regional thermal-center union; not area coverage',
                            'temporal_support': 'static modeled context; not mission-time history',
                            'evidence_role': 'region_associated_context', 'rule_classification': 'Unconfigured',
                            'requirement_status': 'Unknown', 'reason_code': 'MISSION_OR_POLICY_NOT_CONFIGURED',
                            'preference_score': np.nan})
    return pd.DataFrame(records)
