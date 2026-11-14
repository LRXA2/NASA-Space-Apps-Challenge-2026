"""Retained-PDF source/page cases and historical resource duration/rate decomposition."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import sys
import unicodedata
from urllib.parse import unquote

sys.path[:0]=[str(Path(__file__).resolve().parents[2]/'shared'),str(Path(__file__).resolve().parents[3]),str(Path(__file__).resolve().parents[4])]
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import stage3_acquired_eda as acquired
from decision_eda import accepted_input
from environment_workflow import LocalRun
from stage3_mission_eda import LOCAL,ROOT,save_figure,resource_changes

CONFIG=Path(__file__).with_name('stage3_operations_config.json')
NOTEBOOK='Moon/Stage3_Requirements/Dar_055_operations_habitat_source_evidence.ipynb'


def normalized(text):return re.sub('[^a-z0-9]','',unicodedata.normalize('NFKC',text).casefold())


def duration_rate_decomposition(primary):
    f=resource_changes(primary)
    for field in ['actual_duration_min','planned_duration_min']:
        if not np.isfinite(f[field]).all() or not f[field].gt(0).all():raise ValueError('Positive sourced durations required')
    f['duration_ratio_actual_to_planned']=f.actual_duration_min/f.planned_duration_min
    f['actual_mean_consumed_per_min']=f.actual_consumed/f.actual_duration_min
    f['planned_mean_consumed_per_min']=f.predicted_consumed/f.planned_duration_min
    f['mean_rate_ratio']=f.actual_mean_consumed_per_min/f.planned_mean_consumed_per_min.where(f.planned_mean_consumed_per_min.gt(0))
    f['decomposition_supported']=f.planned_mean_consumed_per_min.gt(0)&np.isfinite(f.mean_rate_ratio)
    f['ratio_identity_residual']=f.consumption_ratio_actual_to_predicted-f.duration_ratio_actual_to_planned*f.mean_rate_ratio
    f['constant_planned_mean_duration_only_consumed']=f.predicted_consumed*f.duration_ratio_actual_to_planned
    f['actual_minus_duration_only_consumed']=f.actual_consumed-f.constant_planned_mean_duration_only_consumed
    f['decomposition_scope']='historical arithmetic sensitivity using rounded totals/mean rates, NOT constant true activity demand, modern reserve multiplier or hardware response model'
    return f


def case_rows(cases,extracted,source_hashes):
    docs={d['file']:d for d in extracted['documents']};rows=[]
    for case in cases:
        doc=docs[case['file']]
        if source_hashes[case['file']]!=doc['source_sha256']:raise ValueError('PDF/version differs from page extraction')
        pages={p['pdf_page']:p for p in doc['pages']}
        for page in case['pages']:
            p=pages[page]
            if hashlib.sha256(p['text'].encode()).hexdigest()!=p['text_sha256']:raise ValueError('Cached page text hash changed')
            if p['text_characters']<80:raise ValueError('Case page requires image/OCR review before this text claim')
        text=' '.join(pages[p]['text'] for p in case['pages'])
        if not all(normalized(term) in normalized(text) for term in case['check_terms']):raise ValueError('Reviewed case/page anchor changed: '+case['id'])
        rows.append({**{k:v for k,v in case.items() if k not in ['pages','check_terms']},
            'pdf_pages_1_based':','.join(map(str,case['pages'])),'source_pdf_sha256':doc['source_sha256'],
            'page_text_sha256':';'.join(pages[p]['text_sha256'] for p in case['pages']),
            'review_basis':'targeted text case reviewed by analyst; anchor checks are not automatic scientific verification',
            'independent_event_count':False,'numeric_limit_adopted':False,'operational_status':'Unknown'})
    return pd.DataFrame(rows)


def library_table(run,root,case_names,sample):
    indexed={}
    for name in ['PDF_Relevance_Index.md','Apollo_Journal_PDF_Review.md']:
        path=acquired.external_metadata(run,root,root/name)
        for line in path.read_text(encoding='utf-8-sig').splitlines():
            m=re.search(r'\]\((keep/.+?\.pdf)\)',line)
            if not m:continue
            file=Path(unquote(m[1])).name;cells=[s.strip() for s in line.strip().strip('|').split('|')]
            first_batch=len(cells)>6 and cells[1]=='keep'
            indexed[file]={'index_source':name,'relevance':cells[2] if first_batch else cells[1],
                'categories':cells[4] if first_batch else cells[3],'index_scope_and_limits':cells[5] if first_batch else cells[4]}
    actual={p.name:p for p in (root/'keep').glob('*.pdf')};rows=[]
    for file in sorted(set(indexed)|set(actual)):
        p=actual.get(file);entry=indexed.get(file,{})
        if p:
            with p.open('rb') as f:header=b'%PDF-' in f.read(1024)
        else:header=False
        hashed=p is not None and (not sample or file in case_names)
        sha=None
        if hashed:
            acquired.external_metadata(run,root,p);sha=run.record['inputs']['external_data/'+p.relative_to(root).as_posix()]['sha256']
        rows.append({'file':file,**entry,'present':p is not None,'bytes':p.stat().st_size if p else np.nan,'pdf_header_found':header,
            'source_sha256':sha,'hash_verified':hashed,'targeted_case_pages_reviewed':file in case_names,
            'retained_review_hold':entry.get('relevance','Unknown')=='Unknown','index_membership_known':file in indexed,
            'scope':'retained-library index/header/hash audit; not an independent full-text/image review of every PDF'})
    return pd.DataFrame(rows)


def proposals():
    definitions=[
        ('OP-G01','evidence_guard','Source identity, revision, evidence type and OCR limits','actual document/mission/phase, source/page/hash, primary versus plan/secondary/editorial and extraction support','E01 E06','Do not infer mission from filename, treat plans as outcomes, count related accounts as independent events or turn unreviewed scans into negative evidence'),
        ('OP-H01','conditional_hard_constraint','Essential crewed habitat/life-support capability','declared crew/activity/duration, atmosphere/pressure/air quality/water/waste/thermal services, coupled capacities and applicable requirements','E06 E09','Only applicable to a declared crewed scope; Failed if qualified essential capability is insufficient, Passed only with sufficient applicable evidence, otherwise Unknown'),
        ('OP-H02','conditional_hard_constraint','Applicable contingency return and reserve capability','actual configuration, credible required contingency/recovery scenarios, resource/time response and adopted reserves','E06 E13','Failed if qualified mandatory recovery/reserve capability is insufficient; Passed only with sufficient evidence; missing mission requirements remain Unknown, not an assumed Apollo reserve'),
        ('OP-S01','conditional_soft_preference','Lower qualified maintenance/scheduling/resource burden','mandatory conditions Passed, comparable mission and validated response-based consumable/maintenance/schedule burden','E06 E13','Use supported operational flexibility/cost, not a fixed historical consumption multiplier or raw environmental minimum'),
        ('OP-G02','evidence_guard','Conditional rules and apparent source conflicts retain scope','detailed operating condition, exceptions, revision and precedence/adoption authority','E06','Different normal/moving-traverse communication provisions cannot become one universal outage cutoff; unresolved applicability/precedence stays Unknown'),
        ('OP-G03','evidence_guard','Separate duration, activity/rate and deployment effects','sourced actual/planned durations, rounded stocks/consumption, activity/maintenance and failure attribution','E06 E14','Mean-rate arithmetic is descriptive; overprediction/underprediction is not itself a modern safety outcome or a validated demand model'),
        ('OP-G04','evidence_guard','Hardware/test environment and quantity are not interchangeable','flight versus trainer/laboratory hardware, chemistry, gravity/environment, charge/energy units and response','E01 E06 E13','Earth trainer/laboratory capacities do not qualify Moon hardware; Ah is charge, not Wh without supported voltage/response'),
        ('OP-G05','evidence_guard','Coupled operations and observation duty cycle','thermal/dust/power/contamination/crew activity dependencies, monitoring and actual observation windows','E02 E04 E06 E13','A deployment/thermal restriction or unobserved interval is not zero hazard; do not double-count related evidence or assume independent system margins')]
    return pd.DataFrame([{'id':id,'classification':kind,'title':title,'required_inputs':inputs,'existing_rule_crosswalk':old,
        'decision_logic':logic,'quantity':'mission-specific essential service/resource/recovery demand; source-quality and historical arithmetic context',
        'unit':'source-specific lb/Ah/min/% and response-specific units; no automatic charge-to-energy or historical-to-modern conversion',
        'applicability':'historical source configuration only; selected mission/equipment remain optional and are not fabricated',
        'source':'page-linked operational_cases.csv and accepted primary Apollo 17 Table 9-II, PDF p144, plus retained-library scope audit',
        'evidence':'operational_cases.csv; library_scope.csv; duration_rate_decomposition.csv; conditional_source_comparison.csv; crosscheck_existing_resources.csv',
        'limit_value':np.nan,'limit_state':'not_adopted','preference_weight':np.nan,'current_outcome':'Unknown',
        'status':'Stage 4 proposal only; not consumed by pipeline'} for id,kind,title,inputs,old,logic in definitions])


def execute(sample=False):
    config=json.loads(CONFIG.read_text());case_path=CONFIG.with_name(config['cases_config']);selection=json.loads(case_path.read_text())
    if config['schema']!=1 or config['body']!='Moon':raise ValueError('Moon operations schema required')
    with LocalRun(ROOT,'analysis/subject_operations'+('_sample' if sample else ''),config,NOTEBOOK) as run:
        pages_path=LOCAL/config['pdf_pages']
        for p in [CONFIG,case_path,Path(__file__),pages_path,Path(acquired.__file__),LOCAL/'EDA/shared/operational_pdf_extract.py']:
            run.input(p)
        extracted=json.loads(pages_path.read_text(encoding='utf-8'))
        if extracted['sample'] or extracted['case_config_sha256']!=hashlib.sha256(case_path.read_bytes()).hexdigest():raise ValueError('Full matching case-page extraction required')
        cases=selection['cases']
        if sample:cases=[c for c in cases if c['id'] in ['OPC01','OPC09','OPC14']]
        library=library_table(run,Path(selection['external_root']),{c['file'] for c in cases},sample)
        hashes=library.set_index('file').source_sha256.to_dict();coded=case_rows(cases,extracted,hashes)
        evidence=LOCAL/'data/processed/analysis'/selection['evidence_run']
        primary=pd.read_csv(accepted_input(run,evidence,'apollo17_emu_resources.csv'))
        prior=pd.read_csv(accepted_input(run,LOCAL/'data/processed/analysis'/config['resource_analysis_run'],'primary_resource_changes.csv'))
        if sample:primary=primary.head(6)
        rates=duration_rate_decomposition(primary)
        if rates.ratio_identity_residual.fillna(0).abs().max()>1e-12:raise ValueError('Duration/rate multiplicative identity changed')
        checked=rates.merge(prior,on=['mission','eva','crew_role','resource'],suffixes=('_new','_prior'),validate='one_to_one')
        checked['consumption_ratio_absolute_difference']=(checked.consumption_ratio_actual_to_predicted_new-checked.consumption_ratio_actual_to_predicted_prior).abs()
        checked['headroom_absolute_difference']=(checked.historical_remaining_minus_source_redline_new-checked.historical_remaining_minus_source_redline_prior).abs()
        if len(checked)!=len(rates) or checked[['consumption_ratio_absolute_difference','headroom_absolute_difference']].max().max()>1e-12:raise ValueError('Existing resource arithmetic changed')
        comparison=pd.DataFrame([
            {'topic':'communication loss','source':'a17_final-flight-mission-rules_19720068065.pdf','pdf_pages':'33;51','different_conditions':'normal two-crew/MSFN provision vs moving traverse with contact at next stop','historical_values':'5 min; approximately 30 min','resolution':'retain conditions; no universal cutoff or new authority/precedence adopted'},
            {'topic':'battery reference','source':'LRV Historical Full Handbook Transcripts.pdf','pdf_pages':'8','different_conditions':'flight silver-zinc vs one-g Earth trainer nickel-cadmium','historical_values':'115 Ah per flight battery vs 24 Ah per trainer battery','resolution':'different configurations/environments; neither is a default for selected Moon equipment'},
            {'topic':'nominal duration versus outcome','source':'a17_final-flight-mission-rules_19720068065.pdf; Apollo 17 Table 9-II','pdf_pages':'33;144','different_conditions':'nominal preflight EVA duration versus actual operational execution','historical_values':'7 h nominal rule; actual sourced durations retained in resource table','resolution':'do not declare an unqualified historical rule violation or copy the duration as a modern limit'}])
        category=coded.assign(category=coded.category.str.split('/')).explode('category').groupby(['category','source_type'],as_index=False).agg(coded_cases=('id','nunique'),documents=('file','nunique'))
        category['scope']='coded evidence coverage, not independent event frequencies or risk weights'
        tables={'library_scope':library,'operational_cases':coded,'case_category_coverage':category,
            'duration_rate_decomposition':rates,'conditional_source_comparison':comparison,'crosscheck_existing_resources':checked,
            'stage4_operations_proposals':proposals()}
        for name,frame in tables.items():frame.to_csv(run.path(name+'.csv'),index=False)
        fig,axes=plt.subplots(1,3,figsize=(13,4),layout='constrained')
        for ax,(resource,g) in zip(axes,rates.groupby('resource')):
            ax.scatter(g.duration_ratio_actual_to_planned,g.mean_rate_ratio)
            ax.axhline(1,color='gray');ax.axvline(1,color='gray');ax.set(title=resource,xlabel='Actual/planned duration',ylabel='Actual/planned mean consumption rate')
        fig.suptitle('Historical duration and rate effects; rounded totals, not a future demand model');save_figure(run,fig,'historical_duration_rate_decomposition')
        findings={'subject':'operations_habitat','sample':sample,'retained_library_files':int(library.present.sum()),'library_review_holds':int(library.retained_review_hold.sum()),
            'coded_cases':len(coded),'case_documents':coded.file.nunique(),'reviewed_case_pages':sum(len(d['pages']) for d in extracted['documents']) if not sample else None,
            'primary_resource_rows':len(rates),'consumption_exceeds_prediction_rows':int(rates.consumed_minus_predicted.gt(0).sum()),
            'above_planned_mean_rate_rows':int(rates.mean_rate_ratio.gt(1).sum()),'tables':{name:len(f) for name,f in tables.items()},
            'base_conclusion':'Historical NASA evidence supports coupled capability, calibration, contingency, maintenance and condition-specific decisions. Added rate/duration decomposition and source-condition checks do not establish modern mission capacity, local suitability or universal limits.',
            'time_applicability':'historical mission/EVA duration and source phases; no invented monthly climate chronology or selected modern mission period',
            'inferred_strategy_not_NASA_algorithm':'monitor qualified quantities; preserve source/operating condition; maintain essential capability and contingency return; adapt tasks/duty cycle/maintenance before optional preferences',
            'pipeline_changed':False,'adopted_limits':False,'operational_status':'Unknown',
            'remaining':['Unreviewed/image-dependent library material remains scoped, not negative evidence','Applicable configuration, requirements, response and adoption authority','Integrated Stage 4/source-field and cross-subject synthesis']}
        run.path('findings.json').write_text(json.dumps(findings,indent=2));folder=run.directory
    print(json.dumps(findings,indent=2),flush=True);return folder,findings


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--sample',action='store_true')
    print(execute(parser.parse_args().sample)[0])
