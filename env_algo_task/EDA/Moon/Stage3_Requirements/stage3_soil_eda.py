"""Standalone lunar-soil EDA; no site scoring, engineering model or adopted limits.

The handbook text extractor can run in a separate Python with pypdf installed.
All analysis uses the existing project environment and provenance helpers.
"""
from pathlib import Path
import argparse
import hashlib
import io
import json
import re
import shutil
import subprocess
import sys


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def extract_pdf(source, destination):
    from pypdf import PdfReader, __version__
    sha = digest(source)
    reader = PdfReader(source)
    pages = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        pages.append({'pdf_page': i + 1, 'text': text,
                      'text_sha256': hashlib.sha256(text.encode()).hexdigest()})
    if digest(source) != sha:
        raise ValueError('PDF changed during extraction')
    Path(destination).write_text(json.dumps({'source': str(source), 'source_sha256': sha,
        'extractor': 'pypdf ' + __version__, 'pages': pages}, ensure_ascii=False), encoding='utf-8')


if __name__ == '__main__' and '--extract-pdf' in sys.argv:
    parser = argparse.ArgumentParser()
    parser.add_argument('--extract-pdf', type=Path, required=True)
    parser.add_argument('--destination', type=Path, required=True)
    args = parser.parse_args()
    extract_pdf(args.extract_pdf, args.destination)
    raise SystemExit(0)

import numpy as np
import pandas as pd
from scipy import stats
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

LOCAL = Path(__file__).resolve().parents[3]
ROOT = LOCAL.parent
sys.path[:0] = [str(LOCAL / 'EDA/shared'), str(LOCAL), str(ROOT)]
from environment_workflow import LocalRun
from reference_eda import soil_table
from research_p1_readers import pin_source

NOTEBOOK = 'Moon/Stage3_Requirements/Dar_057_lunar_soil_properties.ipynb'
OXIDES = ['SiO2', 'TiO2', 'Al2O3', 'Cr2O3', 'FeO', 'MnO', 'MgO', 'CaO', 'Na2O', 'K2O', 'P2O5']
PROPERTIES = ['Is_FeO', 'Mz_um', 'Md_um', 'agglutinates_percent'] + OXIDES
ALIASES = {'Al203': 'Al2O3', 'Cr203': 'Cr2O3', 'Na20': 'Na2O', 'P205': 'P2O5'}
NUMBER = r'(?:\d+(?:\.\d*)?|\.\d+)'
SCIENTIFIC_SCOPE = ('Historical sample-level descriptive associations, not independent site trials, '
                    'causal effects, south-pole predictions or environmental-operability outcomes.')


def mission_for(sample):
    return {'10': 11, '12': 12, '14': 14, '15': 15}.get(sample[:2],
        {'6': 16, '7': 17}.get(sample[0]))


def parse_handbook(pages):
    """Conservative scalar extraction; blanks, mixed fractions and conflicts stay missing.

    No coordinates or collection-location comments are exported. Sample IDs, mission,
    source page/line and sieve support are necessary to avoid pooling unlike records.
    """
    observations, samples, holds, page_audit = [], {}, [], []
    previous = None
    for page in pages:
        text = page['text']
        header = re.search(r'^\s*SOIL\s*:\s*(\d{5})\b', text, re.M | re.I)
        footer = re.search(r'Apollo\s+(11|12|14|15|16|17)\s+Samples?\s+Data\s+Sheets?', text, re.I)
        is_sheet = footer is not None
        sample = header[1] if header else None
        if header and (not is_sheet or mission_for(sample) != int(footer[1])):
            holds.append({'pdf_page': page['pdf_page'], 'sample_id': sample,
                          'feature': 'identity', 'reason': 'Sample ID and mission footer conflict; no silent ID repair',
                          'raw_text': header[0].strip()})
            previous = None
            page_audit.append({'pdf_page': page['pdf_page'], 'classification': 'identity_hold'})
            continue
        if header:
            previous = (sample, page['pdf_page'])
            if sample in samples:
                raise ValueError('Repeated soil-sheet identity requires explicit review: ' + sample)
            samples[sample] = {'sample_id': sample, 'mission': int(footer[1]),
                'header_pdf_page': page['pdf_page'],
                'fraction_basis': 'less_than_1_mm_handbook_default_unless_feature_override',
                'source': 'JSC19069 Handbook of Lunar Soils', 'unit_scope': SCIENTIFIC_SCOPE}
        elif (is_sheet and previous and page['pdf_page'] == previous[1] + 1
              and 'MAJOR ELEMENTS' in text.upper()):
            sample = previous[0]
        else:
            previous = None
            page_audit.append({'pdf_page': page['pdf_page'], 'classification': 'not_scalar_soil_sheet'})
            continue
        page_audit.append({'pdf_page': page['pdf_page'], 'classification': 'soil_sheet', 'sample_id': sample})
        lines = text.splitlines()
        major = False
        for line_no, raw in enumerate(lines, 1):
            line = re.sub(r'\s+', ' ', raw).strip()
            if 'MAJOR ELEMENTS' in line.upper():
                major = True
            feature, remainder, unit = None, None, None
            maturity = re.match(r'^1\.?\s*I\s*[sS]\s*/\s*Fe[O0]\s*:?\s*(.*)', line)
            grain = re.match(r'^[12]\.?\s*M\s*([zd])\s*:?\s*(.*)', line, re.I)
            agglut = re.match(r'^2\.?\s*Agglutinates\s*:?\s*(.*)', line, re.I)
            oxide = re.match(r'^(' + '|'.join(OXIDES + list(ALIASES)) + r')\s+(.+)', line) if major else None
            if maturity:
                feature, remainder, unit = 'Is_FeO', maturity[1], 'reported_Is_FeO_index'
            elif grain:
                feature, remainder, unit = 'M' + grain[1].lower() + '_um', grain[2], 'micrometre'
            elif agglut:
                feature, remainder, unit = 'agglutinates_percent', agglut[1], 'reported_percent'
            elif oxide:
                feature, remainder, unit = ALIASES.get(oxide[1], oxide[1]), oxide[2], 'reported_major_oxide_percent'
            if feature is None:
                continue
            fraction_basis = 'less_than_1_mm_handbook_default'
            explicit_fine = None
            grain_segment = ''
            if grain:
                grain_segment = '\n'.join(lines[line_no-1:])
                # Preserve wrapped left-column values but stop at the next descriptor.
                grain_segment = re.split(r'\n\s*2\.?\s*M\s*d\s*:?|MAJOR ELEMENTS',
                    grain_segment, maxsplit=1, flags=re.I)[0] if feature == 'Mz_um' else grain_segment.split('MAJOR ELEMENTS')[0]
                fine = re.findall('(' + NUMBER + r')\s*[µμ�u]m\s*\(\s*<\s*1\s*mm\s*\)', grain_segment, re.I)
                if len(set(fine)) == 1:
                    explicit_fine = float(fine[0])
                    fraction_basis = 'explicit_less_than_1_mm'
                elif len(set(fine)) > 1:
                    holds.append({'sample_id': sample, 'feature': feature, 'pdf_page': page['pdf_page'],
                        'reason': 'Conflicting explicit fine-fraction grain values', 'raw_text': grain_segment[:500]})
                    continue
            match = re.match(r'^(' + NUMBER + r')(.*)', remainder)
            if not match and explicit_fine is None:
                continue  # Empty cell or text in an adjacent petrography/trace column, never zero.
            value = explicit_fine if explicit_fine is not None else float(match[1])
            tail = match[2].strip() if match else ''
            reason = None
            if explicit_fine is None and re.match(r'^[,;]?\s*(?:' + NUMBER + r'|[-–±/])', tail):
                reason = 'Multiple values/range/uncertainty or ambiguous numeric tail; scalar withheld'
            if feature in ['Mz_um', 'Md_um'] and explicit_fine is None:
                # Units must be explicit; the right-hand petrography column is not a grain value.
                grain_text = text.split('GRAIN SIZE PARAMETERS')[-1].split('MAJOR ELEMENTS')[0]
                if not re.match(r'^(?:[µμ�u]m|micron)', tail, re.I):
                    reason = 'Grain unit not explicit on value line'
                mixed_text = grain_text if feature == 'Md_um' else grain_segment
                if re.search(r'<\s*1\s*cm|whole\s+(?:soil|sample)|bulk\s+sample', mixed_text, re.I):
                    reason = 'Grain block has nonstandard/mixed sieve support; excluded from common-fraction comparison'
            if feature in OXIDES + ['agglutinates_percent'] and not 0 <= value <= 100:
                reason = 'Reported percent outside 0..100; source/OCR review required'
            if feature in ['Mz_um', 'Md_um'] and value <= 0:
                reason = 'Nonpositive grain size'
            entry = {'sample_id': sample, 'mission': samples[sample]['mission'],
                     'feature': feature, 'value': value, 'unit': unit, 'pdf_page': page['pdf_page'],
                     'source_line': line_no, 'raw_text': re.sub(r'\s+', ' ', grain_segment[:500]) if explicit_fine is not None else line,
                     'fraction_basis': fraction_basis,
                     'extraction_status': 'held' if reason else 'accepted'}
            if reason:
                holds.append({**entry, 'reason': reason})
            else:
                observations.append(entry)
    if not samples:
        raise ValueError('No supported soil identities extracted')
    obs = pd.DataFrame(observations)
    frame = pd.DataFrame(samples.values()).set_index('sample_id')
    for feature in PROPERTIES:
        frame[feature] = np.nan
    if not obs.empty:
        for (sample, feature), group in obs.groupby(['sample_id', 'feature']):
            values = group.value.unique()
            if len(values) == 1:
                frame.loc[sample, feature] = values[0]
            else:
                holds.append({'sample_id': sample, 'feature': feature,
                    'pdf_page': ','.join(map(str, group.pdf_page)),
                    'reason': 'Conflicting observations; no analyst/version averaging',
                    'raw_text': ' | '.join(group.raw_text)})
    # A held alternative must not be silently replaced by an accepted scalar elsewhere.
    for hold in holds:
        if hold.get('sample_id') in frame.index and hold.get('feature') in PROPERTIES:
            frame.loc[hold['sample_id'], hold['feature']] = np.nan
    return frame.reset_index(), obs, pd.DataFrame(holds), pd.DataFrame(page_audit)


def bh_adjust(values):
    values = np.asarray(values, dtype=float)
    order = np.argsort(values)
    result = np.empty(len(values))
    result[order] = np.minimum.accumulate((values[order] * len(values) / np.arange(1, len(values)+1))[::-1])[::-1].clip(0, 1)
    return result


def correlation_tables(frame):
    rows, within, leave_out = [], [], []
    for i, x in enumerate(PROPERTIES):
        for y in PROPERTIES[i+1:]:
            pair = frame[['sample_id', 'mission', x, y]].dropna()
            if len(pair) < 10 or pair[x].nunique() < 3 or pair[y].nunique() < 3:
                continue
            rho, p = stats.spearmanr(pair[x], pair[y])
            ranks = pair[[x, y]].rank()
            centred = ranks - ranks.groupby(pair.mission).transform('mean')
            adjusted = centred[x].corr(centred[y])
            # Identical paired profiles are a sensitivity cohort, not proven independent samples.
            unique = pair.drop_duplicates([x, y])
            unique_rho = stats.spearmanr(unique[x], unique[y]).statistic if len(unique) >= 10 else np.nan
            rows.append({'x': x, 'y': y, 'n_samples': len(pair), 'n_missions': pair.mission.nunique(),
                'spearman_rho': rho, 'nominal_p_value': p,
                'mission_adjusted_rank_association': adjusted,
                'distinct_pair_profiles': len(unique), 'distinct_profile_rho': unique_rho,
                'interpretation': 'exploratory association; dependent samples and compositional closure limit inference'})
            for mission, group in pair.groupby('mission'):
                if len(group) >= 8 and group[x].nunique() >= 3 and group[y].nunique() >= 3:
                    within.append({'x': x, 'y': y, 'mission': mission, 'n_samples': len(group),
                                   'spearman_rho': stats.spearmanr(group[x], group[y]).statistic})
                remainder = pair[pair.mission != mission]
                if len(remainder) >= 10 and remainder[x].nunique() >= 3 and remainder[y].nunique() >= 3:
                    leave_out.append({'x': x, 'y': y, 'excluded_mission': mission, 'n_samples': len(remainder),
                                      'spearman_rho': stats.spearmanr(remainder[x], remainder[y]).statistic})
    pooled = pd.DataFrame(rows)
    if not pooled.empty:
        pooled['bh_q_value'] = bh_adjust(pooled.nominal_p_value)
    return pooled, pd.DataFrame(within), pd.DataFrame(leave_out)


def association_uncertainty(frame, pairs, repetitions=2000, seed=5701):
    """Within-mission bootstrap and permutation sensitivity; not independent-site CIs."""
    rng = np.random.default_rng(seed)
    rows = []
    for x, y in pairs:
        pair = frame[['mission', x, y]].dropna().reset_index(drop=True)
        if len(pair) < 10 or pair[x].nunique() < 3 or pair[y].nunique() < 3:
            continue
        groups = [g.index.to_numpy() for _, g in pair.groupby('mission')]
        boot_indices = np.concatenate([rng.choice(g, (repetitions, len(g)), replace=True) for g in groups], axis=1)
        a = stats.rankdata(pair[x].to_numpy()[boot_indices], axis=1)
        b = stats.rankdata(pair[y].to_numpy()[boot_indices], axis=1)
        a -= a.mean(axis=1, keepdims=True); b -= b.mean(axis=1, keepdims=True)
        denominator = np.sqrt((a*a).sum(axis=1) * (b*b).sum(axis=1))
        correlations = np.divide((a*b).sum(axis=1), denominator, out=np.full(repetitions, np.nan), where=denominator>0)
        ranks = pair[[x, y]].rank()
        residuals = ranks - ranks.groupby(pair.mission).transform('mean')
        ra, rb = residuals[x].to_numpy(), residuals[y].to_numpy()
        norm = np.linalg.norm(ra)*np.linalg.norm(rb)
        adjusted = np.dot(ra, rb)/norm if norm else np.nan
        exceed = 0
        if norm:
            for _ in range(repetitions):
                permuted = rb.copy()
                for g in groups:
                    permuted[g] = rng.permutation(rb[g])
                exceed += abs(np.dot(ra, permuted)/norm) >= abs(adjusted)
        low, high = np.nanquantile(correlations, [.025, .975])
        rows.append({'x': x, 'y': y, 'n_samples': len(pair), 'bootstrap_rho_low': low,
            'bootstrap_rho_high': high, 'finite_bootstrap_replicates': int(np.isfinite(correlations).sum()),
            'mission_adjusted_rank_association': adjusted,
            'within_mission_permutation_p': (exceed+1)/(repetitions+1) if norm else np.nan,
            'scope': 'conditional sample-resampling sensitivity, NOT population/site confidence or causation'})
    result = pd.DataFrame(rows)
    if not result.empty:
        known = result.within_mission_permutation_p.notna()
        result.loc[known, 'permutation_bh_q'] = bh_adjust(result.loc[known, 'within_mission_permutation_p'])
    return result


def soil_mechanics(run):
    frames = []
    base = LOCAL / 'data/reference/apollo15_soil'
    for label in sorted(base.rglob('a15_smss_*.xml')):
        for path in [label, label.with_suffix('.tab')]:
            pin_source(run, path)
        frame, _ = soil_table(label)
        # No coordinates/context labels are necessary in this standalone comparison.
        frame = frame.drop(columns=['location_context'])
        frames.append(frame)
    if len(frames) != 6:
        raise ValueError('Expected the six existing Apollo 15 penetrometer tables')
    raw = pd.concat(frames, ignore_index=True)
    summary = []
    for number, group in raw.groupby('run'):
        valid = group[['PENETRATION_DEPTH', 'stress_kPa']].dropna()
        valid = valid[(valid.PENETRATION_DEPTH >= 0) & (valid.stress_kPa >= 0)]
        summary.append({'run': number, 'mission': 15, 'geometry': group.geometry.iloc[0],
            'records': len(group), 'numeric_depth_stress_records': len(valid),
            'reported_depth_min_cm': valid.PENETRATION_DEPTH.min(),
            'reported_depth_max_cm': valid.PENETRATION_DEPTH.max(),
            'reported_stress_max_kPa': valid.stress_kPa.max(),
            'depth_stress_rank_association': stats.spearmanr(valid.PENETRATION_DEPTH, valid.stress_kPa).statistic
                if len(valid)>2 and valid.PENETRATION_DEPTH.nunique()>1 else np.nan,
            'documented_depth_limitation': bool(group.documented_depth_limitation.iloc[0]),
            'documented_trench_collapse': bool(group.documented_trench_collapse.iloc[0]),
            'interpretation': 'within-run loading path, NOT independent soil trials or a soil-type coefficient'})
    return raw, pd.DataFrame(summary)


def source_scope(frame):
    rows = []
    for mission, group in frame.groupby('mission'):
        rows.append({'source_family': 'Handbook Apollo ' + str(mission), 'records': len(group),
                     'use': 'sample-level composition/grain/maturity comparison',
                     'limit': 'non-core returned samples, uneven missingness, related subsamples; no environmental outcome variable'})
    rows += [
        {'source_family': 'Surveyor 5/6/7', 'records': 0,
         'use': 'external qualitative comparison: mare/highland chemistry contrast',
         'published_comparison': 'Surveyor 7 highland material has less Fe than the previously analysed mare material; qualitative agreement with the iron/aluminium contrast in the Apollo sample comparison, not a matched experiment',
         'limit': 'not covered by this handbook; no harmonized local numerical sample table; atomic-element results not pooled with Apollo oxide percentages',
         'source_url': 'https://www.usgs.gov/publications/implications-surveyor-7-results'},
        {'source_family': 'D37 unified geology', 'records': 0, 'use': 'future geological-context grouping',
         'limit': 'regional geological units, not direct soil properties; no requested site/location join'},
        {'source_family': 'D34 M3 L1B', 'records': 0, 'use': 'future composition reconstruction after correction/coverage assessment',
         'limit': 'radiance cubes not ready-made comparable mineral fractions; no fabricated spectral/sample pairing'},
        {'source_family': 'D30 Mini-RF CPR', 'records': 0, 'use': 'future scattering-context comparison',
         'limit': 'not direct soil type or strength; no matched soil specimens'},
        {'source_family': 'D28 historical HFE / D10 LDEX', 'records': 0,
         'use': 'not joined in this standalone study',
         'limit': 'no specimen-matched soil/thermal/dust outcomes; mission labels alone do not support a correlation'}]
    return pd.DataFrame(rows)


def pipeline_candidates():
    return pd.DataFrame([
        {'feature': 'soil_composition_vector', 'fields': 'FeO, TiO2, Al2O3 and remaining reported oxides',
         'potential_use': 'condition/regime context, not a scalar good/bad soil label',
         'guard': 'compositional dependence; calibration and prospective-source compatibility required'},
        {'feature': 'soil_grain_size', 'fields': 'Mz_um, Md_um, sieve support',
         'potential_use': 'candidate continuous descriptors after measurement/protocol matching',
         'guard': 'Mz/Md correlated; mean size is NOT respirable fraction, dust flux or strength'},
        {'feature': 'soil_maturity', 'fields': 'Is_FeO; agglutinates with declared fraction',
         'potential_use': 'maturity/context descriptor, NOT higher-is-safer/lower-is-safer',
         'guard': 'no outcome-calibrated direction, threshold or weight; do not double-count related indices'},
        {'feature': 'soil_mechanical_response', 'fields': 'load/stress/depth with geometry and limitation flags',
         'potential_use': 'reference evidence only in this standalone analysis',
         'guard': 'different geometries and measurement limitations; no universal bearing-strength gate'}
    ]).assign(adoption_status='research_only_not_adopted', environmental_effect_identified=False,
              scoring_direction='unresolved', threshold='not_established', weight='not_established')


def execute(pdf, pdf_python='python', page_cache=None, sample=False):
    config = {'schema': 1, 'source_pdf': str(pdf.resolve()), 'source_sha256': digest(pdf),
              'sample': sample, 'properties': PROPERTIES, 'minimum_pair_n': 10,
              'bootstrap_permutation_repetitions': 2000, 'seed': 5701,
              'pipeline_changed': False, 'scope': SCIENTIFIC_SCOPE}
    with LocalRun(ROOT, 'analysis/subject_soil', config, NOTEBOOK) as run:
        run.input(Path(__file__))
        run.input(LOCAL / 'EDA/shared/reference_eda.py')
        run.input(LOCAL / 'EDA/shared/research_p1_readers.py')
        run.record['inputs']['external_data/soils_hb.pdf'] = {
            'path': str(pdf.resolve()), 'bytes': pdf.stat().st_size, 'sha256': digest(pdf)}
        cache = run.path('handbook_page_text.json')
        if page_cache:
            cached = json.loads(page_cache.read_text(encoding='utf-8'))
            if cached.get('source_sha256') != config['source_sha256']:
                raise ValueError('Page cache does not match source PDF')
            shutil.copyfile(page_cache, cache)
        else:
            subprocess.run([pdf_python, str(Path(__file__).resolve()), '--extract-pdf', str(pdf),
                            '--destination', str(cache)], check=True)
        payload = json.loads(cache.read_text(encoding='utf-8'))
        pages = payload['pages']
        for page in pages:
            if hashlib.sha256(page['text'].encode()).hexdigest() != page['text_sha256']:
                raise ValueError('Extracted page hash mismatch')
        if sample:
            # Predeclared short/complex examples, covering all six Apollo missions.
            selected = {11, 12, 14, 15, 77, 78, 79, 240, 241, 364, 365, 584, 585, 867, 868}
            pages = [p for p in pages if p['pdf_page'] in selected]
        frame, observations, holds, audit = parse_handbook(pages)
        # Complete-case only: no missing-value imputation, oxide closure, or arbitrary normalization.
        complete = frame.dropna(subset=OXIDES).copy()
        complete['reported_oxide_sum_percent'] = complete[OXIDES].sum(axis=1)
        complete['closure_diagnostic_only'] = True
        long = frame.melt(id_vars=['sample_id', 'mission'], value_vars=PROPERTIES,
                          var_name='feature', value_name='value')
        summary = long.groupby(['mission', 'feature']).value.agg(
            samples='size', supported='count', median='median', minimum='min', maximum='max',
            q25=lambda s: s.quantile(.25), q75=lambda s: s.quantile(.75)).reset_index()
        summary['missing_fraction'] = 1-summary.supported/summary.samples
        pooled, within, leave = correlation_tables(frame)
        pairs = [('Is_FeO', 'Mz_um'), ('Is_FeO', 'agglutinates_percent'), ('Mz_um', 'Md_um'),
                 ('FeO', 'Al2O3'), ('FeO', 'TiO2')]
        uncertainty = association_uncertainty(frame, pairs, repetitions=100 if sample else 2000)
        groups = []
        for feature in PROPERTIES:
            values = [g[feature].dropna().to_numpy() for _, g in frame.groupby('mission') if g[feature].notna().sum() >= 3]
            if len(values) >= 2 and len(np.unique(np.concatenate(values))) >= 2:
                h, p = stats.kruskal(*values)
                groups.append({'feature': feature, 'groups': len(values), 'n_samples': sum(map(len, values)),
                    'kruskal_H': h, 'nominal_p_value': p, 'scope': SCIENTIFIC_SCOPE})
        differences = pd.DataFrame(groups)
        if not differences.empty:
            differences['bh_q_value'] = bh_adjust(differences.nominal_p_value)
        raw_mechanics, mechanics = soil_mechanics(run)
        tables = {'soil_samples': frame, 'extracted_observations': observations, 'extraction_holds': holds,
                  'page_scope': audit, 'mission_property_summary': summary, 'pooled_associations': pooled,
                  'within_mission_associations': within, 'leave_one_mission_out': leave,
                  'association_uncertainty': uncertainty, 'mission_group_comparisons': differences,
                  'complete_oxide_closure': complete, 'penetrometer_records': raw_mechanics,
                  'penetrometer_run_summary': mechanics, 'source_scope': source_scope(frame),
                  'pipeline_research_candidates': pipeline_candidates()}
        for name, table in tables.items():
            table.to_csv(run.path(name+'.csv'), index=False)
        fig, axes = plt.subplots(2, 2, figsize=(11, 8))
        for ax, feature in zip(axes.flat, ['FeO', 'Al2O3', 'TiO2', 'Mz_um']):
            values = [(m, g[feature].dropna()) for m, g in frame.groupby('mission') if g[feature].notna().any()]
            if values:
                ax.boxplot([v for _, v in values], tick_labels=[str(m) for m, _ in values], showfliers=True)
            ax.set(title=feature, xlabel='Apollo mission', ylabel='micrometre' if feature.endswith('_um') else 'reported oxide %')
        fig.suptitle('Historical soil samples: uneven sample counts; not site-safety rankings')
        fig.savefig(run.path('mission_distributions.png'), dpi=150, bbox_inches='tight'); plt.close(fig)
        fig, axes = plt.subplots(1, 2, figsize=(11, 4))
        for mission, group in frame.groupby('mission'):
            axes[0].scatter(group.Is_FeO, group.Mz_um, label=str(mission), alpha=.7)
            axes[1].scatter(group.FeO, group.Al2O3, label=str(mission), alpha=.7)
        axes[0].set(xlabel='Reported Is/FeO maturity index', ylabel='Mz (micrometre)')
        axes[1].set(xlabel='FeO (reported %)', ylabel='Al2O3 (reported %)')
        axes[1].legend(title='Apollo');fig.suptitle('Sample associations; not environmental effects')
        fig.savefig(run.path('property_associations.png'), dpi=150, bbox_inches='tight');plt.close(fig)
        fig, ax = plt.subplots(figsize=(6, 5))
        for number, group in raw_mechanics.groupby('run'):
            good = group.PENETRATION_DEPTH.ge(0) & group.stress_kPa.ge(0)
            ax.plot(group.loc[good, 'PENETRATION_DEPTH'], group.loc[good, 'stress_kPa'], marker='.', label=str(number))
        ax.set(xlabel='Reported penetration depth (cm)', ylabel='Reported stress (kPa)',
               title='Apollo 15 loading paths: geometry/limitations differ');ax.legend(title='Run')
        fig.savefig(run.path('penetrometer_loading_paths.png'), dpi=150, bbox_inches='tight');plt.close(fig)
        findings = {'subject': 'standalone_soil', 'sample': sample, 'pages_in_analysis': len(pages),
            'soil_sheet_pages': int(audit.classification.eq('soil_sheet').sum()), 'unique_sample_ids': len(frame),
            'mission_sample_counts': {str(m):len(g) for m,g in frame.groupby('mission')},
            'supported_property_counts': {f:int(frame[f].notna().sum()) for f in PROPERTIES},
            'extraction_holds': len(holds), 'complete_oxide_profiles': len(complete),
            'soil_mechanics_runs': len(mechanics), 'associations': uncertainty.to_dict('records'),
            'base_conclusion': 'Soil properties can describe distinct historical sample regimes and interrelated features. '
                'These data do not identify an effect on mission/base environmental operability or an optimum soil type.',
            'pipeline_changed': False, 'adopted_thresholds_or_weights': False,
            'limits': ['Related samples are not independent site trials; sample counts are not independent missions.',
                'Pairs use pairwise complete cases with different support; missingness may be selective.',
                'Oxide percentages share compositional closure; Is/FeO itself contains an FeO denominator.',
                'Distinct-pair-profile sensitivity is not a pedigree-aware correction for related samples.',
                'Reported maturity agglutinates differ from petrographic counts in other grain fractions.',
                'No specimen-matched thermal/dust/mission outcome response; success is not a negative/positive soil label.',
                'Surveyor retained as qualitative external evidence, not mixed-unit pseudo-samples.',
                'Selected scalar extraction, not a complete transcription of every value in the handbook.']}
        run.path('findings.json').write_text(json.dumps(findings, indent=2, allow_nan=False), encoding='utf-8')
        folder = run.directory
    print(json.dumps({'output': str(folder), 'samples': len(frame), 'support': findings['supported_property_counts']}, indent=2))
    return folder, findings


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pdf', type=Path, default=Path('D:/projects/NASA Dataset/soils_hb.pdf'))
    parser.add_argument('--pdf-python', default='python', help='Python executable containing pypdf')
    parser.add_argument('--page-cache', type=Path, help='Optional source-hash-matched page-text cache')
    parser.add_argument('--sample', action='store_true')
    args = parser.parse_args()
    execute(args.pdf, args.pdf_python, args.page_cache, args.sample)
