"""Soil-only cross-mission comparisons and evidence-qualified metric candidates.

Reads pinned local source archives. No downloads, scoring policy, site mapping,
operational-response models or active env_pipeline imports/changes.
"""
from pathlib import Path
import argparse
import json
import re
import sys
import zipfile
import xml.etree.ElementTree as ET

import numpy as np
import pandas as pd
from bs4 import BeautifulSoup
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from stage3_soil_eda import LOCAL, ROOT, digest, mission_for
from environment_workflow import LocalRun
from decision_eda import accepted_input

CONFIG = Path(__file__).with_name('stage3_soil_comparison_config.json')
NOTEBOOK = 'Moon/Stage3_Requirements/Dar_058_soil_cross_mission_metrics.ipynb'
CHEM = ['FeO', 'TiO2', 'Al2O3', 'SiO2', 'CaO', 'MgO']
CORE = ['FeO', 'TiO2', 'Al2O3']
NASA_CODES = ['11', '12', '14', '15', '16', '17']


def sourcebook_profiles(text):
    """Parse only complete, named oxide rows; retain regional means separately."""
    lines = text.splitlines()
    header = next(line.split() for line in lines if line.split()[:3] == ['11', '12', '14'])
    expected = ['11','12','14','15a','15b','15c','15','16a','16b','16c','16',
                '17a','17b','17c','17d','17','L16','L20','L24']
    if header != expected:
        raise ValueError('Unreviewed sourcebook column identities/order')
    rows = {}
    for line in lines:
        tokens = line.split()
        if tokens and tokens[0] in CHEM:
            if len(tokens) != len(header)+1:
                raise ValueError('Incomplete selected sourcebook row: ' + tokens[0])
            if tokens[0] in rows:
                raise ValueError('Repeated selected sourcebook row')
            rows[tokens[0]] = [float(v) for v in tokens[1:]]
    if set(rows) != set(CHEM):
        raise ValueError('Missing selected chemical row')
    frame = pd.DataFrame(rows, index=header).rename_axis('profile_id').reset_index()
    if not np.isfinite(frame[CHEM]).all().all() or not ((frame[CHEM]>0)&(frame[CHEM]<=100)).all().all():
        raise ValueError('Invalid selected oxide values')
    frame['mission'] = frame.profile_id.map(lambda s: 'Luna '+s[1:] if s.startswith('L') else 'Apollo '+re.match(r'\d+',s)[0])
    frame['agency_group'] = np.where(frame.profile_id.str.startswith('L'), 'non_NASA', 'NASA')
    frame['aggregation'] = np.where(frame.profile_id.isin(NASA_CODES+['L16','L20','L24']),
                                    'published_mission_reference', 'published_regional_reference')
    frame['source_table'] = 'Lunar Sourcebook Table 7.15, USGS archived ASCII'
    frame['unit'] = 'wt_percent'
    return frame


def html_chemical_profiles(html, mission):
    soup = BeautifulSoup(html, 'html.parser')
    candidates = []
    for table in soup.find_all('table'):
        rows = [[c.get_text('', strip=True) for c in tr.find_all(['td','th'], recursive=False)]
                for tr in table.find_all('tr')]
        if any('FeO' in row and 'Al2O3' in row for row in rows):
            candidates.append(rows)
    if len(candidates) != 1:
        raise ValueError('Expected one bulk chemistry table: ' + mission)
    rows = candidates[0]
    index = next(i for i,r in enumerate(rows) if 'FeO' in r and 'Al2O3' in r)
    header = rows[index]
    positions = {f:header.index(f) for f in CHEM}
    records = []
    if mission == 'CE5':
        values = rows[index+1]
        uncertainty = rows[index+2]
        if values[0] != 'wt%' or not uncertainty[0].startswith('Uncertainty'):
            raise ValueError('Unreviewed CE5 chemistry units/rows')
        records.append({'profile_id':'CE5C0800YJFM002_XRF_mean',
            **{f:float(values[i]) for f,i in positions.items()},
            **{f+'_reported_uncertainty_k2':float(uncertainty[i]) for f,i in positions.items()},
            'source_table':'nwab188 Table 1 XRF; technical measurements not independent samples'})
    elif mission == 'CE6':
        # Later rows use trace-element units and repeat sample IDs; never pool them.
        for row in rows[index+1:]:
            if row[0].startswith('Element'):
                break
            if '(soil)' in row[0]:
                records.append({'profile_id':row[0].split()[0],
                    **{f:float(row[i]) for f,i in positions.items()},
                    'source_table':'nwae328 Table 2 soil rows only; basalt fragment excluded'})
        if len(records) != 2:
            raise ValueError('Expected two CE6 soil aliquots, not basalt/trace rows')
    else:
        raise ValueError('Unknown mission')
    frame = pd.DataFrame(records)
    frame['mission'] = "Chang'e-5" if mission=='CE5' else "Chang'e-6"
    frame['agency_group'] = 'non_NASA'
    frame['aggregation'] = 'published_soil_laboratory_profile'
    frame['unit'] = 'wt_percent'
    return frame


def docx_tables(path):
    ns = {'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    with zipfile.ZipFile(path) as package:
        info = package.getinfo('word/document.xml')
        if info.file_size > 20*1024**2:
            raise ValueError('Unexpected oversized source XML')
        root = ET.fromstring(package.read(info))
    tables = []
    for table in root.findall('.//w:tbl', ns):
        tables.append([[''.join(e.text or '' for e in cell.iter() if e.tag.endswith('}t'))
                        for cell in row.findall('w:tc', ns)] for row in table.findall('w:tr', ns)])
    return tables


def grain_catalog(tables):
    candidates = [t for t in tables if t[0][:2]==['Sample Number','Maturity']]
    if len(candidates) != 1:
        raise ValueError('Missing/unreviewed grain table')
    records = []
    for number, row in enumerate(candidates[0][1:], 2):
        if len(row)!=6 or not re.fullmatch(r'\d{5},\d+',row[0]):
            raise ValueError('Unreviewed grain record identity')
        parent = row[0].split(',')[0]
        mission = mission_for(parent)
        if mission is None or row[1] not in ['immature','submature','mature']:
            raise ValueError('Unsupported mission/category in grain table')
        values = list(map(float,row[2:]))
        if not np.isfinite(values).all() or values[3] <= 0:
            raise ValueError('Invalid grain statistics')
        records.append({'analysis_id':row[0], 'parent_sample_id':parent, 'mission':'Apollo '+str(mission),
            'agency_group':'NASA', 'reported_maturity':row[1],
            **dict(zip(['mean_phi','median_phi','mode_phi','sorting_phi'],values)),
            'fraction':'less_than_1_mm', 'source_table':'nwab188 Supplementary Table 8', 'source_row':number})
    frame = pd.DataFrame(records)
    if frame.analysis_id.duplicated().any():
        raise ValueError('Repeated grain analysis identity')
    for name in ['mean','median','mode']:
        frame[name+'_equivalent_um'] = 1000 * 2.0**(-frame[name+'_phi'])
    return frame


def maturity_category(value):
    """Noble NASA reference convention: a classification, never a suitability order."""
    if value is None or not np.isfinite(value) or value < 0:
        return 'Unknown'
    if value < 30:
        return 'immature'
    if value <= 60:
        return 'submature'
    return 'mature'


def clr(values):
    values = np.asarray(values, dtype=float)
    if not np.isfinite(values).all() or (values<=0).any():
        raise ValueError('Log-ratio chemistry requires positive, complete selected oxides')
    log = np.log(values)
    return log-log.mean(axis=-1, keepdims=True)


def range_audit(samples, mission_profiles):
    nasa = mission_profiles[mission_profiles.agency_group.eq('NASA')]
    external = mission_profiles[mission_profiles.agency_group.eq('non_NASA')]
    rows = []
    for feature in CHEM:
        known = samples[feature].dropna()
        references = [('Apollo_sample_minmax',known.min(),known.max(),len(known)),
            ('Apollo_sample_p05_p95',known.quantile(.05),known.quantile(.95),len(known)),
            ('Apollo_mission_reference_minmax',nasa[feature].min(),nasa[feature].max(),len(nasa))]
        for name,low,high,count in references:
            for _,row in external.iterrows():
                x = row[feature]
                rows.append({'mission':row.mission,'feature':feature,'value_wt_percent':x,
                    'reference':name,'lower':low,'upper':high,'reference_records':count,
                    'position':'below' if x<low else 'above' if x>high else 'inside',
                    'is_safety_limit':False,'gate_adopted':False,
                    'comparison_support':'Nominal soil oxide percentages; historical sieve/analytical methods not fully harmonized'})
    return pd.DataFrame(rows)


def comparisons(profiles, samples, regions, grain, physical):
    audit = range_audit(samples, profiles)
    groups = profiles.melt(id_vars=['mission','agency_group'],value_vars=CHEM,var_name='feature',value_name='value')
    summary = groups.groupby(['agency_group','feature']).value.agg(
        reference_profiles='size',minimum='min',median='median',maximum='max').reset_index()
    summary['interpretation'] = 'Convenience reference profiles, not random site samples or independent agency effects'
    nasa = profiles[profiles.agency_group.eq('NASA')]
    reference = clr(nasa[CORE].to_numpy())
    nearest = []
    for _,row in profiles[profiles.agency_group.eq('non_NASA')].iterrows():
        distances = np.linalg.norm(reference-clr(row[CORE].to_numpy(float)),axis=1)
        ix = int(np.argmin(distances))
        nearest.append({'mission':row.mission,'nearest_Apollo_reference':nasa.iloc[ix].mission,
            'selected_oxides':','.join(CORE),'clr_distance':float(distances[ix]),
            'meaning':'Compositional resemblance only; NOT suitability, familiarity benefit or a NASA selection criterion'})
    regional = []
    for mission, group in regions[regions.aggregation.eq('published_regional_reference')].groupby('mission'):
        for feature in CORE:
            regional.append({'mission':mission,'feature':feature,'regional_references':len(group),
                'minimum':group[feature].min(),'maximum':group[feature].max(),
                'span':group[feature].max()-group[feature].min()})
    parents = grain.groupby(['parent_sample_id','mission'])[['mean_phi','median_phi','sorting_phi']].median().reset_index()
    grain_compare = []
    for ext in physical['missions']:
        for cohort_name, reference_frame in [('reported_analysis_rows',grain),('parent_median_sensitivity',parents)]:
            grain_compare.append({'mission':ext['mission'],'reference':cohort_name,'reference_n':len(reference_frame),
                'reference_missions':reference_frame.mission.nunique(),
                'external_reported_mean_phi':ext['mass_mean_phi'],
                'external_reported_mass_median_um':ext['mass_median_um'],
                'reference_coarser_mean_count':int(reference_frame.mean_phi.lt(ext['mass_mean_phi']).sum()),
                'reference_coarser_mean_fraction':float(reference_frame.mean_phi.lt(ext['mass_mean_phi']).mean()),
                'mean_phi_inside_observed_range':bool(reference_frame.mean_phi.min()<=ext['mass_mean_phi']<=reference_frame.mean_phi.max()),
                'mass_median_inside_observed_range':bool(reference_frame.median_phi.min()<=ext['mass_median_phi']<=reference_frame.median_phi.max()),
                'is_independent_site_test':False,
                'limit':'Phi definitions align but optical model-mass versus legacy grain methods and depths differ; parent medians are a sensitivity, not pooled physical samples'})
    return {'mission_group_comparison':summary, 'reference_range_audit':audit,
        'nearest_composition_reference':pd.DataFrame(nearest), 'within_Apollo_regional_spread':pd.DataFrame(regional),
        'grain_parent_sensitivity':parents, 'grain_external_comparison':pd.DataFrame(grain_compare)}


def execute(config_path=CONFIG):
    config = json.loads(Path(config_path).read_text(encoding='utf-8'))
    if config['schema']!=1:
        raise ValueError('Unknown soil comparison schema')
    with LocalRun(ROOT,'analysis/soil_cross_mission',config,NOTEBOOK) as run:
        for path in [Path(__file__),Path(config_path),Path(__file__).with_name('stage3_soil_eda.py')]:
            run.input(path)
        sources = {}
        for name,item in config['sources'].items():
            path = (LOCAL/'data'/item['relative_path']).resolve()
            if not path.is_relative_to((LOCAL/'data/reference').resolve()):
                raise ValueError('Source path must remain in the local reference archive')
            if path.stat().st_size!=item['bytes'] or digest(path)!=item['sha256']:
                raise ValueError('Source differs from reviewed version: '+name)
            run.input(path); sources[name]=path
        base = LOCAL/'data/processed/analysis/subject_soil'/config['apollo_baseline_run']
        samples = pd.read_csv(accepted_input(run,base,'soil_samples.csv'))
        if len(samples)!=168:
            raise ValueError('Apollo reference cohort changed; explicitly review before comparison')
        regions = sourcebook_profiles(sources['sourcebook'].read_text(encoding='ascii'))
        historic = regions[regions.aggregation.eq('published_mission_reference')]
        ce5 = html_chemical_profiles(sources['ce5_article'].read_text(encoding='utf-8'),'CE5')
        ce6 = html_chemical_profiles(sources['ce6_article'].read_text(encoding='utf-8'),'CE6')
        # CE6 soil aliquots represent one mission, not two independent landing areas.
        modern = pd.concat([ce5,ce6],ignore_index=True)
        averaged = modern.groupby(['mission','agency_group'])[CHEM].mean().reset_index()
        averaged['aggregation']='laboratory_profiles_averaged_once_per_mission'
        averaged['unit']='wt_percent'
        averaged['profile_id']=averaged.mission+'_laboratory_reference'
        averaged['source_table']='nwab188 Table 1 / nwae328 Table 2; soil only'
        profiles = pd.concat([historic,averaged],ignore_index=True)
        if len(historic)!=9 or len(profiles)!=11:
            raise ValueError('Expected six Apollo, three Luna and two Chang\'e mission profiles')
        tables = docx_tables(sources['ce5_supplement'])
        grain = grain_catalog(tables)
        if len(grain)!=80 or grain.parent_sample_id.nunique()!=23:
            raise ValueError('Review changed grain cohort/parent identities')
        physical = json.loads(sources['physical_context'].read_text(encoding='utf-8'))
        for record in physical['missions']:
            text = BeautifulSoup(sources[record['article_source']].read_text(encoding='utf-8'),'html.parser').get_text(' ',strip=True)
            if any(str(v) not in text for v in record['article_numeric_anchors']):
                raise ValueError('Published physical-context anchor missing')
        results = comparisons(profiles,samples,regions,grain,physical)
        rules = json.loads(sources['metric_evidence'].read_text(encoding='utf-8'))
        output = {'sourcebook_regions':regions,'mission_reference_profiles':profiles,
            'change_chemical_laboratory_profiles':modern,'Apollo_grain_catalog':grain,
            'published_physical_context':pd.DataFrame(physical['missions']),
            'metric_candidate_evidence':pd.DataFrame(rules['metrics']), **results}
        # Do not join this categorical reference to unlike paper-inferred maturity labels.
        maturity = samples[['sample_id','mission','Is_FeO']].copy()
        maturity['reference_category']=maturity.Is_FeO.map(maturity_category)
        maturity['classification_only_not_suitability']=True
        maturity['fraction_guard']='Is/FeO has method-specific reference fractions; original citations must be checked before transferring measurements'
        output['Apollo_maturity_categories']=maturity
        output['grain_reported_maturity_counts']=grain.groupby(['mission','reported_maturity']).size().rename('analysis_rows').reset_index()
        output['source_quality_holds']=pd.DataFrame([
            {'source':'Sourcebook 7.15','field':'Na2O, Apollo 11','hold':'ASCII prints 47; not used or silently decimal-corrected'},
            {'source':'Sourcebook 7.15','field':'P2O3','hold':'Archive row label ambiguous for the intended oxide; not mapped to P2O5'},
            {'source':'nwab188 narrative versus Supplementary Table 8','field':'Apollo/Luna attribution',
             'hold':'All 80 table identities are Apollo, five missions, 23 parents; no Luna analyses in this numeric cohort'},
            {'source':'Lunar whole-surface population','field':'general Moon control group',
             'hold':'No representative whole-Moon soil sample survey. Broader mission collection is NOT a random global or unvisited-site control.'},
            {'source':'Surveyor chemical analyses','field':'units/instrument','hold':'Atomic/group-element summaries not harmonized to oxide wt%; qualitative context only'},
            {'source':'Chang\'e-5/-6 physical results','field':'mass and density','hold':'Model-mass particle statistics and returned-sample packing are not in-situ particle counts or density profiles'},
        ])
        for name,frame in output.items():
            frame.to_csv(run.path(name+'.csv'),index=False)
        fig,axes=plt.subplots(1,2,figsize=(11,4))
        colors={'NASA':'tab:blue','non_NASA':'tab:orange'}
        for _,row in profiles.iterrows():
            for ax,y in zip(axes,['Al2O3','TiO2']):
                ax.scatter(row.FeO,row[y],color=colors[row.agency_group]);ax.annotate(row.mission,(row.FeO,row[y]),fontsize=7)
        axes[0].set(xlabel='FeO (wt%)',ylabel='Al2O3 (wt%)')
        axes[1].set(xlabel='FeO (wt%)',ylabel='TiO2 (wt%)')
        fig.suptitle('Mission-reference chemistry: blue Apollo; orange Luna/Chang\'e; no suitability ranking')
        fig.savefig(run.path('cross_mission_chemistry.png'),dpi=160,bbox_inches='tight');plt.close(fig)
        fig,ax=plt.subplots(figsize=(8,4))
        ax.hist(grain.mean_equivalent_um,bins=16,alpha=.6,label='80 Apollo analysis records (23 parents)')
        for ext in physical['missions']:
            ax.axvline(1000*2**(-ext['mass_mean_phi']),label=ext['mission']+' reported mean-phi equivalent')
        ax.set(xlabel='Equivalent diameter from reported mean phi (micrometre)',ylabel='Analysis records',
               title='Historical grain support, not a preferred range');ax.legend(fontsize=8)
        fig.savefig(run.path('grain_reference_comparison.png'),dpi=160,bbox_inches='tight');plt.close(fig)
        findings={'subject':'soil_only_cross_mission','sample':False,'agency_counts':profiles.agency_group.value_counts().to_dict(),
            'mission_profiles':len(profiles),'grain_analysis_rows':len(grain),'grain_parent_samples':grain.parent_sample_id.nunique(),
            'grain_missions':grain.mission.nunique(),'chemistry_features':CHEM,
            'reference_diagnostics':results['reference_range_audit'].to_dict('records'),
            'grain_comparison':results['grain_external_comparison'].to_dict('records'),
            'base_conclusion':'Real cross-mission soil differences exist, but agency membership is not a validated soil-quality label. '
                'Geological mixtures, sampled depths, preparation, analytical methods and aggregation level explain or confound differences. '
                'Observed reference intervals cannot be adopted as preferred or forbidden chemistry ranges.',
            'usable_now':'Measured descriptors and explicitly named maturity categories; optional composition-distance diagnostics, NOT suitability scores.',
            'hard_gates_supported':False,'preferred_ranges_supported':False,'weights_supported':False,
            'pipeline_changed':False,'tables':{name:len(f) for name,f in output.items()}}
        run.path('findings.json').write_text(json.dumps(findings,indent=2,allow_nan=False),encoding='utf-8')
        folder=run.directory
    print(json.dumps({'output':str(folder),'mission_profiles':len(profiles),'grain_analysis_rows':len(grain)},indent=2))
    return folder,findings


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,default=CONFIG)
    args=parser.parse_args()
    execute(args.config)
