"""Support/source sensitivity and descriptive conditional terrain relationships."""
import re
import xml.etree.ElementTree as ET

import numpy as np
import pandas as pd
import rasterio
from rasterio.crs import CRS

from decision_eda import accepted_input
from moon_p1_analysis import sample_containing_pixels
from notebooks.shared.processing import MOON_CRS


def support_policy_checks(elevation, fraction, features, threshold=.99):
    """Port notebook 12's exact mask/neighbourhood controls, not a new policy."""
    from scipy.ndimage import minimum_filter
    if elevation.shape != fraction.shape or elevation.ndim != 2:
        raise ValueError('Aligned two-dimensional elevation/support required')
    if not np.isfinite(threshold) or not 0 < threshold <= 1:
        raise ValueError('Invalid declared support policy')
    inside = np.isfinite(fraction)
    if not ((fraction[inside] >= 0) & (fraction[inside] <= 1)).all():
        raise ValueError('Image-support fractions outside [0,1]')
    finite = np.isfinite(elevation)
    mismatch = int(np.count_nonzero((inside & ~finite) ^ (inside & (fraction < threshold))))
    if np.any(finite & ~inside): raise ValueError('Finite elevation outside declared support ROI')
    results = {'elevation_policy_mismatches': mismatch}
    for name, width in [('slope_deg', 3), ('laplacian_per_m', 3), ('local_elevation_std_m', 11)]:
        if name not in features or features[name].shape != elevation.shape:
            raise ValueError('Missing/unaligned derived feature: ' + name)
        expected = minimum_filter(finite.astype('uint8'), size=width, mode='constant', cval=0).astype(bool)
        results[name + '_neighbourhood_mismatches'] = int(np.count_nonzero(np.isfinite(features[name]) ^ expected))
    if any(results.values()): raise ValueError('Accepted terrain policy inconsistency: ' + str(results))
    return inside, results


def source_crop_check(source, crop, samples_per_axis=8):
    """Port notebook 25 source/crop coordinate checks, decoding source only once."""
    if type(samples_per_axis) is not int or samples_per_axis < 1:
        raise ValueError('Positive integer sampling count required')
    with rasterio.open(source) as src, rasterio.open(crop) as dst:
        if src.crs != dst.crs or src.res != dst.res or dst.scales != (1.,) or dst.offsets != (0.,):
            raise ValueError('Crop grid or decoded-value contract differs')
        rows = np.unique(np.linspace(0, dst.height - 1, samples_per_axis, dtype=int))
        cols = np.unique(np.linspace(0, dst.width - 1, samples_per_axis, dtype=int))
        rr, cc = np.meshgrid(rows, cols, indexing='ij')
        xy = list(zip(*rasterio.transform.xy(dst.transform, rr.ravel(), cc.ravel())))
        expected = np.ma.vstack(list(src.sample(xy, masked=True))).astype(float).filled(np.nan).ravel()
        expected = expected * src.scales[0] + src.offsets[0]
        actual = np.ma.vstack(list(dst.sample(xy, masked=True))).astype(float).filled(np.nan).ravel()
        if not np.array_equal(np.isfinite(expected), np.isfinite(actual)):
            raise ValueError('Crop/source sample missingness disagrees')
        finite = np.isfinite(expected)
        delta = float(np.max(np.abs(expected[finite] - actual[finite]))) if finite.any() else np.nan
        if finite.any() and delta > 1e-6: raise ValueError('Source/crop coordinate/scale mismatch')
        return {'sample_positions': len(actual), 'finite_pairs': int(finite.sum()),
                'maximum_absolute_difference': delta, 'native_resolution_m': src.res[0]}


def native_environment_port(run, root, region_limit=None):
    """Adapt root notebooks 11/12/25 to existing local products, one region at a time."""
    import json
    from pathlib import Path
    from notebooks.shared.processing import Grid, warp
    from rasterio.enums import Resampling
    local = root / 'darrel stuff'
    data = local / 'data'
    folder = data / 'processed/lunar_terrain_environment/20261106T180253772848Z_40d3f3'
    metadata = json.loads((folder / 'provenance.json').read_text(encoding='utf-8'))
    if metadata['status'] != 'complete' or metadata['config']['minimum_image_support_fraction'] != .99:
        raise ValueError('Expected accepted 30 m image-support preparation/policy')
    policy_path = data / 'reference/environment-readiness-20261028/native_layer_units.json'
    run.input(policy_path)
    policy = pd.read_json(policy_path)
    for source in ['preprocessing/11_inspect_environment_and_actions.ipynb',
                   'preprocessing/12_investigate_lunar_shadow_gaps.ipynb',
                   'exploration/25_environment_native_support_eda.ipynb', 'shared/processing.py']:
        run.input(root / 'notebooks' / source)
    run.input(Path(__file__))
    regions = sorted(metadata['config']['regions'])
    if region_limit is not None:
        if type(region_limit) is not int or not 1 <= region_limit <= len(regions): raise ValueError('Invalid region limit')
        regions = regions[:region_limit]
    checks, groups, crops = [], [], []
    names = {'solar_visibility': ('AVGVISIB_85S_060M_201608.TIF', 'fraction'),
             'earth_visibility': ('AVGVISIB_85S_060M_201608_EARTH.TIF', 'fraction'),
             'permanent_shadow': ('LPSR_85S_060M_201608.TIF', 'binary'),
             'sky_view_sr': ('SKYV_65S_240M.TIF', 'sr')}
    for region in regions:
        prefix = 'moon/' + region + '/'
        values = {}
        grid = None
        for name in ['elevation_m', 'image_support_fraction', 'slope_deg', 'laplacian_per_m', 'local_elevation_std_m']:
            path = accepted_input(run, folder, prefix + 'grid_30m/' + name + '.tif')
            with rasterio.open(path) as src:
                current = (src.crs, src.transform, src.width, src.height)
                if grid is not None and current != grid: raise ValueError('Feature grid mismatch')
                grid = current
                values[name] = src.read(1, masked=True).astype(float).filled(np.nan)
        inside, result = support_policy_checks(values['elevation_m'], values['image_support_fraction'], values)
        checks.append({'region': region, 'analysis_cells': int(inside.sum()), **result})
        aligned = {}
        for variable, (name, unit) in names.items():
            path = accepted_input(run, folder, prefix + 'native/illumination/' + name)
            evidence = policy.loc[policy.region.eq(region) & policy.file.eq(name)]
            if len(evidence) != 1 or evidence.iloc[0]['status'] != 'documented':
                raise ValueError('Unconfirmed native unit: ' + name)
            expected_unit = evidence.iloc[0]['unit']
            if expected_unit != unit: raise ValueError('Documented unit mismatch: ' + name)
            originals = list((data / 'moon/illumination_2016/geotiff/south').rglob(name))
            if len(originals) != 1: raise FileNotFoundError('Missing/ambiguous original map: ' + name)
            run.input(originals[0])
            crops.append({'region': region, 'variable': variable, 'unit': unit,
                          **source_crop_check(originals[0], path)})
            aligned[variable] = warp(path, Grid(*grid), resampling=Resampling.nearest)
        valid_psr = inside & np.isfinite(aligned['permanent_shadow'])
        if not np.isin(aligned['permanent_shadow'][valid_psr], [0, 1]).all(): raise ValueError('Invalid PSR encoding')
        for label, selected in [('all_roi', inside), ('excluded_elevation', inside & ~np.isfinite(values['elevation_m'])),
                                ('retained_elevation', inside & np.isfinite(values['elevation_m']))]:
            row = {'region': region, 'cohort': label, 'analysis_grid_cells': int(selected.sum()),
                   'known_psr_cells': int((selected & valid_psr).sum()),
                   'psr_cells': int((selected & valid_psr & (aligned['permanent_shadow'] == 1)).sum()),
                   'scope': '30 m analysis grid; 60/240 m source maps, not independent finer observations or time histories'}
            for variable in ['solar_visibility', 'earth_visibility', 'sky_view_sr']:
                finite = aligned[variable][selected & np.isfinite(aligned[variable])]
                row[variable + '_valid_cells'] = len(finite)
                row[variable + '_median'] = float(np.median(finite)) if len(finite) else np.nan
            groups.append(row)
        print('Native/static support checks passed:', region, flush=True)
    pd.DataFrame(checks).to_csv(run.path('terrain_policy_consistency.csv'), index=False)
    pd.DataFrame(crops).to_csv(run.path('native_source_crop_checks.csv'), index=False)
    pd.DataFrame(groups).to_csv(run.path('terrain_environment_support.csv'), index=False)
    return {'regions': len(regions), 'source_crop_checks': len(crops),
            'native_coordinate_samples': sum(c['sample_positions'] for c in crops),
            'terrain_policy_mismatches': sum(sum(v for k, v in r.items() if k.endswith('mismatches')) for r in checks),
            'dated_terrain_aware_history_found': False,
            'limits': ['Static mean maps and PSR are terrain-aware spatial context, not dated mission histories',
                       '201608 is a product identifier/date, not a per-interval timestamp',
                       'Image-support exclusion is not equivalent to permanent shadow',
                       'No full raw/orthomosaic gallery or original CNN model replay claimed']}

SDEM_VARIABLES = {'sdem_elevation_m': 'elevation_m.tif', 'sdem_slope_deg': 'slope_deg.tif',
                  'sdem_local_std_m': 'local_elevation_std_m.tif',
                  'sdem_image_fraction': 'image_support_fraction.tif'}
PAIR_COHORTS = ['finite_slope_pair', 'complete_sdem_features', 'complete_positive_lola']


def sample_sdem_products(run, folder, region, points, bounds):
    """Read accepted 30 m image-supported products, never rebuild/extract the terrain."""
    if set(SDEM_VARIABLES) & set(points.columns):
        raise ValueError('Would overwrite existing SDEM fields')
    result = points.copy()
    grid = None
    for variable, filename in SDEM_VARIABLES.items():
        path = accepted_input(run, folder, 'moon/' + region + '/grid_30m/' + filename)
        with rasterio.open(path) as src:
            if src.crs != CRS.from_user_input(MOON_CRS) or src.res != (30., 30.):
                raise ValueError('Unexpected SDEM product CRS/resolution')
            current = (src.transform, src.shape)
            if grid is not None and grid != current:
                raise ValueError('SDEM feature grids disagree')
            grid = current
            if variable == 'sdem_elevation_m' and src.tags().get('vertical_reference') != 'radius 1737400 m':
                raise ValueError('Unconfirmed SDEM elevation reference')
        values, _, _ = sample_containing_pixels(path, points, bounds)
        result[variable] = values
    return result


def pair_cohort(frame, cohort):
    finite_slope = np.isfinite(frame[['slope_deg', 'sdem_slope_deg']]).all(axis=1)
    if cohort == 'finite_slope_pair':
        return frame.loc[finite_slope]
    complete = finite_slope & np.isfinite(frame[list(SDEM_VARIABLES)]).all(axis=1) & frame.sdem_image_fraction.ge(.99)
    if cohort == 'complete_sdem_features':
        return frame.loc[complete]
    if cohort == 'complete_positive_lola':
        return frame.loc[complete & frame.spot_count.gt(0)]
    raise ValueError('Unknown source-support cohort')


def terrain_source_statistics(frame):
    records = []
    for cohort in PAIR_COHORTS:
        chosen = pair_cohort(frame, cohort)
        for variable, left, right, unit in [('slope', 'slope_deg', 'sdem_slope_deg', 'degree'),
                                             ('elevation', 'elevation_m', 'sdem_elevation_m', 'm')]:
            pairs = chosen[[left, right]].replace([np.inf, -np.inf], np.nan).dropna()
            delta = pairs[right] - pairs[left]
            q = delta.quantile([.1, .5, .9])
            rho = pairs[left].corr(pairs[right], method='spearman') if len(pairs) >= 3 and pairs.nunique().min() > 1 else np.nan
            records.append({'cohort': cohort, 'variable': variable, 'unit': unit, 'pair_count': len(pairs),
                            'sdem_minus_lola_mean': delta.mean(), 'difference_q10': q.loc[.1],
                            'difference_median': q.loc[.5], 'difference_q90': q.loc[.9],
                            'rms_source_difference': np.sqrt(np.mean(delta**2)) if len(delta) else np.nan,
                            'spearman_rho': rho, 'interpretation': 'source/processing difference; neither is ground truth'})
    return pd.DataFrame(records)


def slope_classification_comparison(frame, limits=(5., 10., 15.)):
    records = []
    for cohort in PAIR_COHORTS:
        chosen = pair_cohort(frame, cohort)
        for context in ['all_pairs', 'solar_earth_ge_0.5']:
            p = chosen if context == 'all_pairs' else chosen.loc[chosen.solar_visibility.ge(.5) & chosen.earth_visibility.ge(.5)]
            for limit in limits:
                a, b = p.slope_deg.le(limit), p.sdem_slope_deg.le(limit)
                records.append({'cohort': cohort, 'context': context, 'diagnostic_slope_limit_deg': limit,
                                'paired_cells': len(p), 'both_met': int((a & b).sum()),
                                'lola_only_met': int((a & ~b).sum()), 'sdem_only_met': int((~a & b).sum()),
                                'neither_met': int((~a & ~b).sum()),
                                'disagreement_fraction': float((a != b).mean()) if len(p) else np.nan,
                                'policy_adopted': False})
    return pd.DataFrame(records)


def candidate_source_support(frame, candidates, limit=10.):
    records = []
    for candidate in candidates:
        p = frame.loc[frame.candidate_id.eq(candidate)]
        slope = p.sdem_slope_deg.replace([np.inf, -np.inf], np.nan).dropna()
        complete = pair_cohort(p, 'complete_sdem_features')
        records.append({'candidate_id': candidate, 'analysis_cells': len(p), 'finite_sdem_slope_cells': len(slope),
                        'unknown_sdem_slope_cells': len(p) - len(slope), 'complete_sdem_feature_cells': len(complete),
                        'sdem_slope_median_deg': slope.median(), 'sdem_slope_q90_deg': slope.quantile(.9),
                        'sdem_slope_above_diagnostic_limit_cells': int(slope.gt(limit).sum()),
                        'sdem_slope_above_fraction_of_finite': float(slope.gt(limit).mean()) if len(slope) else np.nan,
                        'zero_lola_spot_cells': int(p.spot_count.eq(0).sum()), 'diagnostic_limit_deg': limit,
                        'interpretation': 'alternative-source diagnostic, not operational failure'})
    return pd.DataFrame(records)


def illumination_roughness(frame):
    records = []
    for cohort in PAIR_COHORTS:
        p = pair_cohort(frame, cohort)
        for low, high in zip([0., .25, .5, .75], [.25, .5, .75, 1.]):
            selected = p.loc[p.solar_visibility.ge(low) & (p.solar_visibility.le(high) if high == 1 else p.solar_visibility.lt(high))]
            values = selected.sdem_local_std_m.replace([np.inf, -np.inf], np.nan).dropna()
            records.append({'cohort': cohort, 'solar_bin_low': low, 'solar_bin_high': high,
                            'sampled_cells': len(selected), 'finite_local_std_cells': len(values),
                            'local_std_q10_m': values.quantile(.1), 'local_std_median_m': values.median(),
                            'local_std_q90_m': values.quantile(.9)})
    return pd.DataFrame(records)


def documented_nominal_bin_size(label):
    root = ET.parse(label).getroot()
    matches = []
    for element in root.iter():
        if element.tag.split('}')[-1] == 'description':
            matches.extend(re.findall(r'binned\s+at\s+(\d+(?:\.\d+)?)\s+m\s+resolution', ''.join(element.itertext()), re.I))
    if len(matches) != 1 or float(matches[0]) <= 0:
        raise ValueError('No unique documented nominal projected bin size')
    return float(matches[0])


def nominal_box_overlap(x, y, label, labels, known, meta, side_m):
    """Exact intersection with analysis squares, conditional on a declared nominal box.

    This does not reconstruct radiometer FOV, exact native grid affine, or physical registration.
    """
    if not np.isfinite([x, y, side_m]).all() or side_m <= 0 or label < 1:
        raise ValueError('Invalid point, component label or nominal support size')
    if labels.shape != known.shape or labels.shape != (meta['height'], meta['width']):
        raise ValueError('Grid masks disagree with metadata')
    if (labels[~known] > 0).any():
        raise ValueError('A component cannot include unknown context')
    spacing = meta['spacing_m']
    left, top = meta['left_m'], meta['top_m']
    west, east, south, north = x-side_m/2, x+side_m/2, y-side_m/2, y+side_m/2
    c0, c1 = int(np.floor((west-left)/spacing)), int(np.ceil((east-left)/spacing))
    r0, r1 = int(np.floor((top-north)/spacing)), int(np.ceil((top-south)/spacing))
    component_area = known_area = 0.
    for r in range(max(0, r0), min(meta['height'], r1)):
        dy = max(0., min(north, top-r*spacing)-max(south, top-(r+1)*spacing))
        for c in range(max(0, c0), min(meta['width'], c1)):
            dx = max(0., min(east, left+(c+1)*spacing)-max(west, left+c*spacing))
            area = dx*dy
            if known[r, c]:
                known_area += area
            if labels[r, c] == label:
                component_area += area
    fraction = component_area / side_m**2
    known_fraction = known_area / side_m**2
    if not (-1e-10 <= fraction <= known_fraction+1e-10 and known_fraction <= 1+1e-10):
        raise ValueError('Invalid intersection arithmetic')
    return {'component_overlap_fraction': float(np.clip(fraction, 0, 1)),
            'known_context_fraction': float(np.clip(known_fraction, 0, 1)),
            'unknown_or_outside_fraction': float(np.clip(1-known_fraction, 0, 1)),
            'full_nominal_box_in_component': bool(fraction >= 1-1e-10)}


def conditional_rank_relationship(frame, predictor, controls, minimum=20, raw_controls=()):
    """Rank-response/predictor residuals; optional raw cyclic control basis, no causal inference."""
    fields = ['tbol', predictor, *controls]
    if len(set(fields)) != len(fields):
        raise ValueError('Response/predictor/controls must be distinct')
    if not set(raw_controls).issubset(controls):
        raise ValueError('Unranked controls must be named controls')
    p = frame[fields].replace([np.inf, -np.inf], np.nan).dropna()
    result = {'complete_rows': len(p), 'unadjusted_rho_same_rows': np.nan, 'partial_rank_rho': np.nan,
              'design_rank': np.nan, 'design_columns': len(controls)+1, 'condition_number': np.nan,
              'status': 'insufficient_rows'}
    if len(p) < minimum or len(p) <= len(controls)+2:
        return result
    ranks = p.rank(method='average')
    basis = ranks.copy()
    for variable in raw_controls:
        basis[variable] = p[variable]
    std = basis.std(ddof=0)
    if std.iloc[:2].eq(0).any():
        result['status'] = 'constant_response_or_predictor'
        return result
    result['unadjusted_rho_same_rows'] = float(ranks.iloc[:, 0].corr(ranks.iloc[:, 1]))
    if std.iloc[2:].eq(0).any():
        result['status'] = 'constant_control'
        return result
    scaled = (basis-basis.mean())/std
    design = np.column_stack([np.ones(len(p)), scaled[controls].to_numpy()])
    rank = np.linalg.matrix_rank(design)
    condition = np.linalg.cond(design)
    result.update(design_rank=int(rank), condition_number=float(condition))
    if rank < design.shape[1] or condition > 1e10:
        result['status'] = 'rank_deficient_or_ill_conditioned'
        return result
    variables = scaled[['tbol', predictor]].to_numpy()
    residual = variables-design @ np.linalg.lstsq(design, variables, rcond=None)[0]
    if np.std(residual, axis=0).min() <= 1e-12:
        result['status'] = 'no_residual_variation'
        return result
    result['partial_rank_rho'] = float(np.corrcoef(residual.T)[0, 1])
    result['status'] = 'descriptive'
    return result
