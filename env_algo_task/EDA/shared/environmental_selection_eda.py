"""Spatial and rule-influence diagnostics, not adopted mission requirements."""
from itertools import product

import numpy as np
import pandas as pd
from scipy import ndimage

from moon_p1_analysis import documented_illumination, sample_containing_pixels
from site_comparison import joint_state

METRICS = ['solar_fraction', 'earth_fraction', 'slope_deg']
VARIABLES = {'solar_visibility': 'fraction', 'earth_visibility': 'fraction',
             'permanent_shadow': 'binary', 'sky_view_sr': 'steradian',
             'elevation_m': 'm; radius reference 1737400 m', 'slope_deg': 'degree',
             'elevation_error_m': 'm', 'effective_resolution_m': 'm', 'spot_count': 'count'}


def source_layers(data_root):
    layers = documented_illumination(data_root)
    names = {'elevation_m': 'LDEM_80S_40MPP_ADJ.TIF', 'slope_deg': 'LDSM_80S_40MPP_ADJ.TIF',
             'elevation_error_m': 'LDEM_80S_40MPP_ADJ_ERR.TIF',
             'effective_resolution_m': 'LDEM_80S_40MPP_ADJ_EFFRES.TIF', 'spot_count': 'LDEC_80S_40MPP_ADJ.TIF'}
    for key, name in names.items():
        layers[key] = {'path': data_root / 'moon/lola_product90/large_area_dem' / name, 'unit': VARIABLES[key]}
    return layers


def lattice(bounds, spacing, shift=0.):
    """Globally anchored square analysis cells wholly inside the projected ROI."""
    west, south, east, north = bounds
    if not np.isfinite([*bounds, spacing, shift]).all() or spacing <= 0 or west >= east or south >= north:
        raise ValueError('Invalid bounds/grid')
    def axis(lo, hi):
        first = int(np.ceil((lo + spacing / 2 - shift) / spacing))
        last = int(np.floor((hi - spacing / 2 - shift) / spacing))
        return np.arange(first, last + 1) * spacing + shift
    xs, ys = axis(west, east), axis(south, north)[::-1]
    if not len(xs) or not len(ys):
        raise ValueError('No complete analysis cells in ROI')
    x, y = np.meshgrid(xs, ys)
    frame = pd.DataFrame({'row': np.repeat(np.arange(len(ys)), len(xs)),
                          'col': np.tile(np.arange(len(xs)), len(ys)), 'x_m': x.ravel(), 'y_m': y.ravel()})
    meta = {'spacing_m': float(spacing), 'shift_m': float(shift), 'height': len(ys), 'width': len(xs),
            'left_m': float(xs[0] - spacing / 2), 'top_m': float(ys[0] + spacing / 2),
            'right_m': float(xs[-1] + spacing / 2), 'bottom_m': float(ys[-1] - spacing / 2),
            'roi_bounds_m': list(bounds), 'area_kind': 'nominal projected analysis-cell area, not geodesic/buildable area'}
    return frame, meta


def sample_layers(layers, cells, bounds):
    result = cells.copy()
    native = []
    for name, definition in layers.items():
        values, _, resolution = sample_containing_pixels(definition['path'], cells, bounds)
        result[name] = values
        native.append({'variable': name, 'unit': definition['unit'], 'resolution_x_m': resolution[0],
                       'resolution_y_m': resolution[1], 'finite_cells': int(np.isfinite(values).sum()),
                       'sampled_cells': len(values), 'method': 'containing native pixel; scale decoded once'})
    for name in ['solar_visibility', 'earth_visibility']:
        finite = result[name].dropna()
        if not finite.between(0, 1).all():
            raise ValueError('Visibility outside documented domain')
    if not result.slope_deg.dropna().between(0, 90).all():
        raise ValueError('Slope outside degree domain')
    return result, pd.DataFrame(native)


def components(cells, meta, thresholds=(.5, .5, 10.), connectivity=4, detail=True):
    if connectivity not in [4, 8]:
        raise ValueError('Connectivity must be 4 or 8')
    if len(cells) != meta['height'] * meta['width'] or cells.duplicated(['row', 'col']).any():
        raise ValueError('Require a complete unique rectangular analysis grid')
    ordered = cells.sort_values(['row', 'col'])
    state = joint_state(ordered, *thresholds)
    mask = state.fillna(False).to_numpy(dtype=bool).reshape(meta['height'], meta['width'])
    labels, count = ndimage.label(mask, structure=ndimage.generate_binary_structure(2, 1 if connectivity == 4 else 2))
    sizes = np.bincount(labels.ravel())[1:]
    spacing = meta['spacing_m']
    # Padding ensures unknown/outside ROI is not treated as a continuation.
    distance = ndimage.distance_transform_edt(np.pad(mask, 1), sampling=spacing)[1:-1, 1:-1]
    diameter_proxy = 2 * np.maximum(distance - spacing / 2, 0)
    widths = ndimage.maximum(diameter_proxy, labels, index=np.arange(1, count + 1)) if count else np.array([])
    rows = []
    for component_id, slices in enumerate(ndimage.find_objects(labels) if detail else [], start=1):
        if slices is None:
            continue
        local = labels[slices] == component_id
        r, c = slices
        rows.append({'component_label': component_id, 'cells': int(sizes[component_id - 1]),
                     'nominal_projected_area_m2': float(sizes[component_id - 1] * spacing**2),
                     'left_m': meta['left_m'] + c.start * spacing, 'right_m': meta['left_m'] + c.stop * spacing,
                     'top_m': meta['top_m'] - r.start * spacing, 'bottom_m': meta['top_m'] - r.stop * spacing,
                     'lattice_interior_diameter_proxy_m': float(diameter_proxy[slices][local].max()),
                     'touches_analysis_boundary': bool(r.start == 0 or c.start == 0 or r.stop == mask.shape[0] or c.stop == mask.shape[1])})
    table = pd.DataFrame(rows, columns=['component_label', 'cells', 'nominal_projected_area_m2', 'left_m',
                                      'right_m', 'top_m', 'bottom_m', 'lattice_interior_diameter_proxy_m', 'touches_analysis_boundary'])
    finite = int(state.notna().sum())
    summary = {'analysis_cells': len(cells), 'finite_joint_cells': finite, 'unknown_joint_cells': int(state.isna().sum()),
               'joint_cells': int(mask.sum()), 'joint_sample_fraction': float(mask.sum() / finite) if finite else np.nan,
               'component_count': int(count), 'largest_component_cells': int(sizes.max()) if count else 0,
               'largest_nominal_projected_area_m2': float(sizes.max() * spacing**2) if count else 0.,
               'largest_component_share_of_joint': float(sizes.max() / mask.sum()) if count else np.nan,
               'singleton_components': int((sizes == 1).sum()),
               'lattice_interior_diameter_proxy_m': float(diameter_proxy.max()) if count else 0.,
               'connectivity': connectivity, 'solar_min': thresholds[0], 'earth_min': thresholds[1],
               'slope_max_deg': thresholds[2], 'diagnostic_only': True}
    for width in [120, 240, 480]:
        summary[f'components_with_diameter_proxy_ge_{width}m'] = int((widths >= width).sum())
    return labels, table, summary


def select_component_candidates(cells, labels, table, region, maximum=3):
    """Purposive size-ordered examples under a declared diagnostic, not best bases."""
    if not isinstance(maximum, int) or maximum < 1:
        raise ValueError('Positive candidate example limit required')
    selected = table.sort_values(['cells', 'component_label'], ascending=[False, True]).head(maximum).copy()
    selected['region'] = region
    selected['candidate_id'] = [f'{region}:diagnostic_component_{int(i):05d}' for i in selected.component_label]
    mapping = selected.set_index('component_label').candidate_id.to_dict()
    result = cells.copy()
    result['component_label'] = labels[result.row.to_numpy(dtype=int), result.col.to_numpy(dtype=int)]
    result['candidate_id'] = result.component_label.map(mapping)
    return result, selected


def associate_points(points, cells, meta):
    """Point-containing diagnostic cell, NOT thermal-footprint containment."""
    if not np.isfinite(points[['x_m', 'y_m']]).all().all():
        raise ValueError('Unknown point coordinates')
    r = np.floor((meta['top_m'] - points.y_m.to_numpy()) / meta['spacing_m']).astype(int)
    c = np.floor((points.x_m.to_numpy() - meta['left_m']) / meta['spacing_m']).astype(int)
    valid = (r >= 0) & (c >= 0) & (r < meta['height']) & (c < meta['width'])
    lookup = cells.set_index(['row', 'col']).candidate_id
    if not lookup.index.is_unique:
        raise ValueError('Duplicate cell identity')
    index = pd.MultiIndex.from_arrays([r, c])
    assigned = lookup.reindex(index).to_numpy()
    assigned[~valid] = np.nan
    return pd.Series(assigned, index=points.index, name='candidate_id')


def candidate_static_profiles(cells):
    rows = []
    selected = cells.loc[cells.candidate_id.notna()]
    for candidate, frame in selected.groupby('candidate_id'):
        for variable, unit in VARIABLES.items():
            values = frame[variable].replace([np.inf, -np.inf], np.nan).dropna()
            q = values.quantile([.1, .5, .9])
            rows.append({'candidate_id': candidate, 'region': frame.region.iloc[0], 'variable': variable, 'unit': unit,
                         'cells': len(frame), 'finite_cells': len(values), 'mean': values.mean(), 'minimum': values.min(),
                         'q10': q.loc[.1], 'median': q.loc[.5], 'q90': q.loc[.9], 'maximum': values.max()})
    return pd.DataFrame(rows)


def candidate_thermal_profiles(observations, candidates, products):
    if observations.duplicated(['source_product', 'clon', 'clat']).any():
        raise ValueError('Repeated native thermal center/product')
    if observations.usable.dtype != bool or observations.complete_common_cohort.dtype != bool:
        raise ValueError('Explicit source boolean flags required')
    valid = observations.loc[observations.usable & observations.source_product.isin(products)]
    if not np.isfinite(valid.tbol).all() or not valid.tbol.gt(0).all():
        raise ValueError('Invalid usable temperatures')
    rows = []
    for candidate in candidates:
        part = valid.loc[valid.candidate_id.eq(candidate)]
        for cohort, chosen in [('available', part), ('fixed_common', part.loc[part.complete_common_cohort])]:
            for source in products:
                values = chosen.loc[chosen.source_product.eq(source), 'tbol']
                q = values.quantile([.1, .5, .9])
                rows.append({'candidate_id': candidate, 'cohort': cohort, 'source_product': source,
                             'usable_centers': len(values), 'tbol_q10_K': q.loc[.1], 'tbol_median_K': q.loc[.5],
                             'tbol_q90_K': q.loc[.9], 'status': 'observed_point_association' if len(values) else 'no_observations'})
    return pd.DataFrame(rows)


def center_phase_spans(observations, products):
    chosen = observations.loc[observations.usable & observations.source_product.isin(products) & observations.candidate_id.notna()]
    if chosen.duplicated(['source_product', 'clon', 'clat']).any():
        raise ValueError('Repeated phase observation')
    grouped = chosen.groupby(['candidate_id', 'clon', 'clat']).tbol.agg(['count', 'min', 'median', 'max']).reset_index()
    grouped['phase_average_span_K'] = grouped['max'] - grouped['min']
    grouped.loc[grouped['count'] < 2, 'phase_average_span_K'] = np.nan
    grouped['all_common_products_observed'] = grouped['count'].eq(len(products))
    return grouped


def comparison_pool(blocks, centers):
    """Retain empty blocks; these are context samples, not engineered footprints."""
    keys = ['region', 'block_x', 'block_y']
    statics = centers.groupby(keys).agg(solar_fraction=('solar_visibility', 'median'),
        earth_fraction=('earth_visibility', 'median'), slope_deg=('slope_deg', lambda x: x.quantile(.9)),
        sampled_centers=('clon', 'size')).reset_index()
    result = blocks[keys + ['left_m', 'right_m', 'bottom_m', 'top_m']].merge(statics, on=keys, how='left', validate='one_to_one')
    result['sampled_centers'] = result.sampled_centers.fillna(0).astype(int)
    result['unit_id'] = result.region + ':' + result.block_x.astype(str) + ':' + result.block_y.astype(str)
    result['pool'] = 'regional_1.2km_analysis_blocks'
    return result


def benefit_values(pool, normalization):
    raw = pool[METRICS].astype(float)
    finite = np.isfinite(raw).all(axis=1)
    if not raw.loc[finite, ['solar_fraction', 'earth_fraction']].ge(0).all().all() or not raw.loc[finite, ['solar_fraction', 'earth_fraction']].le(1).all().all():
        raise ValueError('Fraction metric outside [0,1]')
    if not raw.loc[finite, 'slope_deg'].between(0, 90).all():
        raise ValueError('Slope metric outside [0,90]')
    result = pd.DataFrame(np.nan, index=pool.index, columns=METRICS)
    values = raw.loc[finite].copy()
    if normalization == 'physical_domain':
        values.slope_deg = 1 - values.slope_deg / 90
    elif normalization == 'within_pool_percentile':
        values = values.rank(pct=True, ascending=True)
        values.slope_deg = raw.loc[finite, 'slope_deg'].rank(pct=True, ascending=False)
    else:
        raise ValueError('Unknown diagnostic normalization')
    result.loc[finite] = values
    return result


def pareto_dominance(pool):
    values = benefit_values(pool, 'physical_domain').to_numpy()
    valid = np.isfinite(values).all(axis=1)
    complete = values[valid]
    counts = np.full(len(pool), np.nan)
    for position in np.where(valid)[0]:
        counts[position] = ((complete >= values[position]).all(axis=1) & (complete > values[position]).any(axis=1)).sum()
    result = pool[['unit_id', 'region', 'pool']].copy()
    result['dominated_by_units'] = counts
    result['pareto_status'] = np.where(~valid, 'Unknown', np.where(counts == 0, 'nondominated', 'dominated'))
    return result


def preference_scenarios(pool):
    """Declared simplex grid: 15 weights, two transforms, never operational scores."""
    rows = []
    for normalization in ['physical_domain', 'within_pool_percentile']:
        benefits = benefit_values(pool, normalization)
        for solar, earth in product(range(5), repeat=2):
            slope = 4 - solar - earth
            if slope < 0:
                continue
            weights = np.array([solar, earth, slope]) / 4
            score = benefits.mul(weights, axis=1).sum(axis=1, min_count=3)
            result = pool[['unit_id', 'region', 'pool']].copy()
            result['normalization'] = normalization
            result['scenario_id'] = f'{normalization}:w{solar}{earth}{slope}'
            result['solar_weight'], result['earth_weight'], result['slope_weight'] = weights
            result['diagnostic_preference_score'] = score
            result['diagnostic_rank'] = score.rank(method='min', ascending=False)
            result['operational_status'] = 'Unknown'
            result['policy_adopted'] = False
            rows.append(result)
    return pd.concat(rows, ignore_index=True)


def diagnostic_gate(pool, thresholds):
    solar, earth, slope = thresholds
    proxy = pool.rename(columns={'solar_fraction': 'solar_visibility', 'earth_fraction': 'earth_visibility'}).replace([np.inf, -np.inf], np.nan)
    state = joint_state(proxy, solar, earth, slope)
    # Kleene conjunction: a known violation establishes NotMet even when another field is missing.
    known_failure = (proxy.solar_visibility.notna() & proxy.solar_visibility.lt(solar)) | (proxy.earth_visibility.notna() & proxy.earth_visibility.lt(earth)) | (proxy.slope_deg.notna() & proxy.slope_deg.gt(slope))
    result = pd.Series('Unknown', index=pool.index)
    result.loc[state.eq(True).fillna(False)] = 'DiagnosticMet'
    result.loc[known_failure] = 'DiagnosticNotMet'
    return result


def gate_scenarios(pool, preferences):
    """Contrast gate-before-ranking with the identical ungated candidate pool."""
    chosen = preferences.loc[preferences.scenario_id.eq('physical_domain:w112')].set_index('unit_id')
    base = pool.merge(chosen[['diagnostic_preference_score']], left_on='unit_id', right_index=True, validate='one_to_one')
    summaries, details = [], []
    for thresholds in product([.25, .5, .75], [.25, .5, .75], [5., 10., 15.]):
        state = diagnostic_gate(base, thresholds)
        eligible = base.loc[state.eq('DiagnosticMet')]
        ungated = base.loc[base.diagnostic_preference_score.notna()].sort_values(['diagnostic_preference_score', 'unit_id'], ascending=[False, True]).head(5)
        filtered = eligible.sort_values(['diagnostic_preference_score', 'unit_id'], ascending=[False, True]).head(5)
        late = ungated.loc[state.loc[ungated.index].eq('DiagnosticMet')]
        row = {'solar_min': thresholds[0], 'earth_min': thresholds[1], 'slope_q90_max_deg': thresholds[2],
               'pool_units': len(base), 'diagnostic_met': int(state.eq('DiagnosticMet').sum()),
               'diagnostic_not_met': int(state.eq('DiagnosticNotMet').sum()), 'unknown': int(state.eq('Unknown').sum()),
               'ungated_top5_met': len(late), 'gate_first_top5_count': len(filtered),
               'eligible_hidden_by_late_top5_filter': int(len(filtered) - len(late)),
               'policy_adopted': False, 'operational_status': 'Unknown'}
        summaries.append(row)
        for idx in filtered.index:
            details.append({**row, 'unit_id': base.loc[idx, 'unit_id'], 'region': base.loc[idx, 'region'],
                            'diagnostic_preference_score': base.loc[idx, 'diagnostic_preference_score']})
    return pd.DataFrame(summaries), pd.DataFrame(details)


def requirement_readiness(regions):
    checks = {'power_endurance': 'DATED_TERRAIN_ILLUMINATION_AND_HARDWARE_REQUIRED',
              'component_thermal_margin': 'APPLICABLE_COMPONENT_RESPONSE_AND_LIMITS_REQUIRED',
              'communications_continuity': 'DATED_GEOMETRY_ARCHITECTURE_AND_LINK_REQUIREMENTS_REQUIRED',
              'radiation_protection': 'APPLICABLE_SURFACE_FIELD_TRANSPORT_AND_LIMITS_REQUIRED',
              'base_footprint_requirement': 'LAYOUT_SIZE_TERRAIN_POLICY_AND_LOCAL_VALIDATION_REQUIRED'}
    return pd.DataFrame([{'region': region, 'requirement': key, 'status': 'Unknown', 'reason_code': reason,
                          'operational_score': np.nan} for region in regions for key, reason in checks.items()])
