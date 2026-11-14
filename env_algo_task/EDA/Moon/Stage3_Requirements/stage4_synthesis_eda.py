"""Compile a traceable Stage 4 specification from completed studies; never evaluate/rank missions."""
from pathlib import Path
import argparse
import json
import re
import sys

sys.path[:0]=[str(Path(__file__).resolve().parents[2]/'shared'),str(Path(__file__).resolve().parents[3]),str(Path(__file__).resolve().parents[4])]
import numpy as np
import pandas as pd

from decision_eda import accepted_input
from environment_workflow import LocalRun
from stage3_mission_eda import LOCAL,ROOT

CONFIG=Path(__file__).with_name('stage4_synthesis_config.json')
NOTEBOOK='Moon/Stage3_Requirements/Dar_056_stage4_evidence_rule_synthesis.ipynb'
ROLES={'evidence_guard','conditional_hard_constraint','conditional_soft_preference'}
HARD_CROSSWALK={'UV-H01':'H_RAD E07 E13','PL-H01':'H_CHARGING E07 E16','HF-H01':'H_THERMAL E02 E07',
    'DU-H01':'H_DUST H_THERMAL E07','RA-H01':'H_RAD E04 E07','PT-H01':'H_THERMAL E02 E07',
    'EX-H01':'B_MOON H_LIFE E07 E13','NE-H01':'H_RAD E04 E07','NE-H02':'H_RESOURCE E07 E09',
    'SE-H01':'H_EVENTS E07 E08','TE-H01':'H_POWER E05 E07','TE-H02':'H_COMM E05 E07',
    'TE-H03':'H_GROUND E07 E09','OP-H01':'H_LIFE B_MOON E07','OP-H02':'H_RETURN R_APOLLO E07'}
FACTOR_SUBJECTS=[['polar_thermal','hfe'],['operations'],['exosphere','operations'],['polar_thermal','hfe','operations'],
    ['operations'],['operations'],['terrain_time'],['terrain_time'],['terrain_time'],['terrain_time'],['dust','terrain_time','operations'],
    ['terrain_time'],['radiation'],['radiation'],['radiation'],['dust','operations'],['seismic'],['neutrons','polar_thermal','uv'],
    ['neutrons','polar_thermal','operations'],['terrain_time','operations'],['terrain_time','hfe','operations'],['terrain_time','hfe','operations'],
    ['operations'],['exosphere','operations'],['terrain_time'],['operations'],['operations']]
UNRESOLVED_DIMENSIONS={
    'uv':'Subdaily flare peaks, mission-local incident spectrum and action/response models; LAMP remains a historical cumulative map',
    'plasma':'Full particle-distribution/current-balance and local material/geometry charging response are not solved from these moments',
    'hfe':'Deployment-disturbance attribution, soil conductivity and polar transfer are not established by historical thermometer/gradient records',
    'dust':'Event-classification/efficiency, qualified live-time/pointing, transport and local deposition/degradation are not established',
    'radiation':'Capped primary-file gaps and sparse primary-event scope remain; accepted daily counters/flux are not a complete event census or shielded local dose',
    'polar_thermal':'No chronological equipment history, validated full candidate footprint or resource detection/extraction follows from the static model',
    'exosphere':'Background/state attribution and local surface transfer unresolved; historical mission cannot supply year-plus climate or repeatable seasons',
    'neutrons':'Detector activity/background/dead-time/response/energy calibration and footprint unresolved; native SCALT unit hold remains',
    'seismic':'Qualified timing/event attribution/local recurrence unresolved; inverse-response experiments cover declared gap-free windows, not every waveform peak',
    'terrain_time':'Finite sampled horizons miss possible blockers; actual footprints, solar disk/panel/storage/link and soil/load response are not qualified',
    'operations':'Targeted pages, not full independent text/image review of all 95 PDFs; 14 review holds and unreviewed sections remain; modern applicability not adopted'}


def compile_proposals(frames,active_ids):
    result=pd.concat(frames,ignore_index=True)
    required={'id','classification','title','required_inputs','decision_logic','existing_rule_crosswalk','current_outcome','limit_value','limit_state','preference_weight','subject','source_run','proposal_table'}
    if required-set(result):raise ValueError('Missing proposal contract fields: '+str(required-set(result)))
    if result.id.isna().any() or result.id.duplicated().any() or not set(result.classification)<=ROLES:raise ValueError('Ambiguous proposal identity/role')
    if result.limit_value.notna().any() or result.preference_weight.notna().any() or not result.current_outcome.eq('Unknown').all() or not result.limit_state.eq('not_adopted').all():raise ValueError('This proposal cannot adopt limits/weights or assert actual operational outcomes')
    rows=[]
    for row in result.to_dict('records'):
        original=str(row['existing_rule_crosswalk']);reviewed=set(original.split())
        reviewed.update(HARD_CROSSWALK.get(row['id'],'E01 E07 E13').split())
        if row['subject']=='seismic':reviewed.add('E08')
        if row['subject']=='operations':reviewed.update(['E06','R_APOLLO','B_MOON'])
        if reviewed-set(active_ids):raise ValueError('Unknown existing rule reference: '+str(reviewed-set(active_ids)))
        role=row['classification'];hard=role=='conditional_hard_constraint';guard=role=='evidence_guard'
        gaps=[k for k in ['quantity','unit','applicability','source'] if pd.isna(row.get(k))]
        row.update({'original_existing_rule_crosswalk':original,'reviewed_existing_rule_crosswalk':' '.join(sorted(reviewed)),
            'crosswalk_review':'topic/quantity review adds relevant existing H_/B_/R_ conditions; preliminary evidence references are retained, not claimed to be exact replacements',
            'evidence_origin':row['source_run']+'/'+row['proposal_table']+'#'+row['id'],
            'quantity':row.get('quantity') if pd.notna(row.get('quantity')) else None,
            'unit':row.get('unit') if pd.notna(row.get('unit')) else None,
            'applicability':row.get('applicability') if pd.notna(row.get('applicability')) else None,
            'source':row.get('source') if pd.notna(row.get('source')) else None,
            'preliminary_metadata_gaps':';'.join(gaps),
            'passed_semantics':'All applicable source-use checks met; not an operational pass' if guard else
                'Applicable mandatory demand/capability/limit relation is met with sufficient qualified footprint/period/uncertainty evidence' if hard else
                'A declared desirable criterion is supported; does not compensate for mandatory Failed/Unknown',
            'failed_semantics':'Attempted source use violates its declared quantity/units/support/applicability; this alone is NOT a site failure' if guard else
                'Qualified evidence shows an applicable mandatory criterion/capability is not met' if hard else
                'A supported desirable criterion is not met; this alone does not fail the mission',
            'unknown_semantics':'A required source/applicability check cannot be established' if guard else
                'Applicability, local demand/response, capability, adopted limit, period/footprint or uncertainty is missing/insufficient',
            'applicability_policy':'Do not select inapplicable requirements; unknown applicability is not Passed. Optional mission/equipment profiles remain absent unless supplied.',
            'preference_eligibility':'Only after all selected mandatory conditions are Passed; do not zero-fill missing preferences, double-count shared inputs or assume a monotonic unsupported direction',
            'limit_authority_state':'No mission-applicable numerical limit or adoption authority selected',
            'operational_quantity_binding':'Local response/requirement quantity and units must be explicitly bound before evaluation; context units are not a conversion model',
            'uncertainty_policy':'Preserve quality/missingness, scope, sampling, model/measurement basis and source-specific holds; no invented fallback or hazard-zero assumption',
            'readiness':'context/proposal ready; not qualified operational evaluation','adoption_state':'proposed_unadopted','loaded_by_pipeline':False})
        rows.append(row)
    return pd.DataFrame(rows)


def specification_examples():
    # These are specification examples, NOT a decision engine, mission inputs or candidate results.
    return pd.DataFrame([
        ('qualified_mandatory_exceedance','Applicable qualified demand exceeds mandatory limit/capability','Failed',False,'A high preference cannot compensate'),
        ('qualified_mandatory_satisfaction','Applicable qualified demand meets mandatory capability with sufficient evidence','Passed',True,'Eligibility only; no score or weight is adopted'),
        ('missing_local_response','Raw orbital/reference quantity available but required local response absent','Unknown',False,'Not Passed and not a zero hazard'),
        ('missing_limit_authority','Demand exists but applicable limit/adoption is absent','Unknown',False,'No quantile/historical redline substitutes for an adopted limit'),
        ('unknown_applicability','Mission/activity/configuration applicability unresolved','Unknown',False,'Optional profile is not invented'),
        ('invalid_evidence_use','Required evidence guard rejects the only supplied quantity/footprint substitution','Failed',False,'Guard failure; underlying operational assessment remains Unknown, not automatic site failure'),
        ('unselected_inapplicable_requirement','Scope establishes this requirement is not applicable',None,None,'Not selected for evaluation; no fourth constraint status and not counted as Passed'),
        ('all_mandatory_pass_soft_missing','All selected mandatory conditions Passed; some preferences unavailable','Unknown',True,'Soft Unknown is not zero and does not become a mandatory failure'),
        ('mandatory_unknown_soft_favourable','Mandatory condition Unknown despite favourable soft context','Unknown',False,'No operational preference ranking over unresolved mandatory qualification')],
        columns=['example_id','hypothetical_condition','specified_check_state','preference_comparison_eligible','interpretation'])


def native_catalog(subject,table,frame,run_path):
    rows=[]
    name=next((c for c in ['field','channel','quantity','resource'] if c in frame),None)
    if name and 'unit' in frame:
        keys=[c for c in ['series_id','species','band',name,'unit'] if c in frame]
        for row in frame.drop_duplicates(keys).to_dict('records'):
            meaning=next((str(row[k]) for k in ['description','meaning','scope','validity_basis','position','spatial_scope'] if k in row and pd.notna(row[k])), 'see source/table contract')
            rows.append({'subject':subject,'source_run':run_path,'artifact':table,'field':row[name],'unit':row['unit'],
                'series_or_species':row.get('series_id',row.get('species',row.get('band',row.get('resource','')))),
                'meaning':meaning,'available_role':'native/derived context as labelled, not automatic operational demand','operational_status':'Unknown'})
    return rows


def execute(sample=False):
    config=json.loads(CONFIG.read_text())
    if config['schema']!=1 or config['body']!='Moon':raise ValueError('Moon synthesis schema required')
    with LocalRun(ROOT,'analysis/stage4_environment_proposal'+('_sample' if sample else ''),config,NOTEBOOK) as run:
        for p in [CONFIG,Path(__file__),LOCAL/config['outline_crosswalk'],LOCAL/config['active_register']]:run.input(p)
        active=json.loads((LOCAL/config['active_register']).read_text());active_ids={r['id'] for r in active['rules']}
        sources=config['sources'][:2] if sample else config['sources'];proposals=[];scope=[];artifacts=[];fields=[];data={}
        for item in sources:
            folder=LOCAL/'data/processed/analysis'/item['run']
            finding=json.loads(accepted_input(run,folder,'findings.json').read_text())
            if finding['sample'] or finding.get('pipeline_changed') is not False:raise ValueError('Complete isolated subject evidence required')
            f=pd.read_csv(accepted_input(run,folder,item['proposal_table']))
            f=f.assign(subject=item['subject'],source_run=item['run'],proposal_table=item['proposal_table']);proposals.append(f)
            limitations=finding.get('remaining',[])
            creation_notes=[s for s in limitations if re.search(r'other subjects|integrated stage 4|stage 4 synthesis',s,re.I)]
            current_limits=[s for s in limitations if s not in creation_notes]
            scope.append({'subject':item['subject'],'datasets':item['datasets'],'source_run':item['run'],'basis':item['kind'],
                'declared_scope':finding.get('full_source_scope',finding.get('time_applicability',finding['base_conclusion'])),
                'base_conclusion':finding['base_conclusion'],'analysis_status':'completed_scoped','operational_status':'Unknown',
                'remaining_evidence_or_operational_limits':'; '.join(current_limits),
                'source_creation_followup_notes_not_current_status':'; '.join(creation_notes),
                'unanalysed_or_unqualified_dimensions':UNRESOLVED_DIMENSIONS[item['subject']],
                'temporal_support':finding.get('first_utc',finding.get('start_utc','see native time/acquisition contract'))+' | '+finding.get('last_utc',finding.get('stop_exclusive_utc','not a fabricated dated history')),
                'numeric_limits_adopted':False,'pipeline_integrated':False})
            for name in item['tables']:
                path=accepted_input(run,folder,name);d=pd.read_csv(path);data[item['subject'],name]=d
                for column in d:
                    artifacts.append({'subject':item['subject'],'datasets':item['datasets'],'source_run':item['run'],'artifact':name,'field':column,
                        'basis':item['kind'],'scope':'analysis column; native/derived units and source meaning in catalog/table contract',
                        'permitted_use':'declared context and requirement proposal only','qualified_operational_input':False})
                fields.extend(native_catalog(item['subject'],name,d,item['run']))
            if item['subject']=='plasma':
                # The earlier plasma proposal omitted these columns. Bind source-context metadata
                # from its verified catalog, not guessed units or a local charging model.
                catalog=data['plasma','esa_series_catalog.csv']
                f['quantity']='native ion/electron density, temperature and spacecraft-potential context; local charging demand remains unbound'
                f['unit']='; '.join(sorted(catalog.unit.dropna().unique()))+' (native source context, not local response units)'
                f['applicability']=f['scope']
                f['source']=item['run']+'/esa_series_catalog.csv; native ESA metadata/quality, not surface-voltage qualification'
            if item['subject']=='uv':
                meta=json.loads(accepted_input(run,folder,'see_source_metadata.json').read_text())
                for source in meta:
                    for field,attrs in source['spectral_variables'].items():
                        fields.append({'subject':'uv','source_run':item['run'],'artifact':'see_source_metadata.json','field':field,'unit':attrs['Units'],
                            'series_or_species':source['file'],'meaning':attrs['Description'],'available_role':'native solar-reference context','operational_status':'Unknown'})
                lamp=pd.read_csv(accepted_input(run,folder,'lamp_native_statistics.csv'))
                fields.extend(native_catalog('uv','lamp_native_statistics.csv',lamp,item['run']))
            contracts={
                'uv':[('band_daily_context.csv','complete_daily_band_integral','W/m2 at 1 AU','complete supported 1-nm-bin integral of daily solar-reference spectrum, not local dose')],
                'seismic':[('raw_trace_support.csv','demeaned_rms_counts','counts','whole-file median-centred raw RMS, axis/mode-specific'),
                    ('response_experiments.csv','displacement_rms_m','m','exploratory band-limited inverse response on selected nominal-clock windows, not qualified peak motion'),
                    ('archived_ATT_context.csv','median_positive_step_s','s','native archive timing diagnostic, not a corrected motion clock')],
                'terrain_time':[('geometry_periods.csv','target_center_elevation_and_clearance','degree','sampled model target-center/skyline geometry'),
                    ('geometry_periods.csv','sampled_blocked_fraction','fraction','fraction of native model samples, not generated energy or contact service'),
                    ('observed_blocked_runs.csv','sample_span_hours','h','first-to-last observed blocked-sample span, not guaranteed continuous darkness/outage')],
                'operations':[('duration_rate_decomposition.csv','actual_and_planned_duration','min','historical sourced EVA duration, not a modern profile')]
            }
            for table,field,unit,meaning in contracts.get(item['subject'],[]):
                fields.append({'subject':item['subject'],'source_run':item['run'],'artifact':table,'field':field,'unit':unit,
                    'meaning':meaning,'available_role':'explicit derived/historical analysis contract','operational_status':'Unknown'})
        combined=compile_proposals(proposals,active_ids)
        if not sample and len(set(combined.subject))!=11:raise ValueError('All subject areas required')
        outline=pd.read_csv(LOCAL/config['outline_crosswalk'])
        if len(outline)!=len(FACTOR_SUBJECTS):raise ValueError('Outline factors changed; explicit coverage review required')
        outline_rows=[]
        for index,row in outline.iterrows():
            subjects=FACTOR_SUBJECTS[index];selected=combined.loc[combined.subject.isin(subjects)]
            outline_rows.append({**row.to_dict(),'new_subjects':';'.join(subjects),'proposed_rule_ids':';'.join(selected.id),
                'new_evidence_state':'lunar baseline/internal-system applicability, not Earth-style exterior weather' if index in [1,2,4,5,22,23,25,26] else 'scoped context available; local operational response/limits unresolved',
                'operational_status':'Unknown','coverage_note':'existing outline boundary retained; no missing dataset/response is silently treated as supplied'})
        cross=[];dependencies=[]
        if not sample:
            geom=data['terrain_time','static_vs_point_context.csv'];solar=geom.loc[geom.target.eq('SUN')].copy()
            # A transparent closest-mean pair, not selected by suitability or a NASA threshold.
            candidates=[]
            rows=solar.to_dict('records')
            for i,a in enumerate(rows):
                for b in rows[i+1:]:
                    candidates.append((abs(a['sampled_clear_fraction']-b['sampled_clear_fraction']),a,b))
            _,a,b=min(candidates,key=lambda x:x[0])
            cross.append({'finding':'Similar mean visibility does not determine persistence','subjects':'terrain_time;operations',
                'evidence':f"{a['region']}: clear fraction {a['sampled_clear_fraction']:.6f}, span {a['longest_observed_blocked_sample_span_hours']:g} h; {b['region']}: {b['sampled_clear_fraction']:.6f}, {b['longest_observed_blocked_sample_span_hours']:g} h",
                'conclusion':'Reference-point sampled means/spans differ; local generation/load/storage/link response is still required',
                'source_pointer':'terrain_time/static_vs_point_context.csv; operations/operational_cases.csv'})
            rad=data['radiation','solar_associations.csv'];crater=rad.loc[rad.series_id.eq('RAD_CRATER_SEC_selected_state')&rad.comparison_window.eq('all_common_dates')].iloc[0]
            cross.append({'finding':'Solar/counter level association is not a robust dose model','subjects':'uv;radiation',
                'evidence':f"Pooled Spearman {crater.spearman_daily_levels:.6f}; consecutive-day differences {crater.spearman_daily_first_differences:.6f}",
                'conclusion':'Within-year/difference checks weaken a simple pooled relationship; no causal/dose or safe-month inference',
                'source_pointer':'radiation/solar_associations.csv'})
            for finding,subjects,evidence,conclusion,pointer in [
                ('No universal darker/colder/lower-density preference','uv;plasma;polar_thermal;operations','UV/Sun input sharing; plasma source boundary; historical Sun/off camera thermal management','Charging, thermal control and power compete; qualified mission response and mandatory conditions precede preferences','UV-G/PL-G/PT-G/OPC11'),
                ('Instrument zeros and missing observations are not absence of hazards','radiation;neutrons;dust;operations','Native zero channels, sparse/event selections and thermally restricted duty cycle','Keep state/background/exposure and event attribution; do not certify zero dose, impacts or contamination','NE-G01/DU-G02/RA-G02/OPC07'),
                ('Model stability and remote indicators do not prove usable resources','polar_thermal;neutrons;uv;terrain_time','PRP stability, LEND spectra and LAMP/radar/image source boundaries','No corroborated abundance, accessibility, extraction yield or qualified local dose follows','PT-G03/NE-H02/UV-G02/TE-G03'),
                ('Deployment and maintenance couple thermal/dust/crew/resources','dust;hfe;operations','Shroud/dust/cable cases and source ECS dependencies','Ambient conditions alone cannot establish functioning deployment, cooling or life support','OPC03/04/12/14'),
                ('Historical timing and geometry control transfer','seismic;hfe;exosphere;terrain_time','S12 clocks/modes, Apollo depth positions, NMS orbit/clock sensitivity and finite horizons','Different footprints, time support and responses cannot become a single local mission history','SE-G01/HF-G01/EX-G02/TE-G01'),
                ('Optional mission/equipment inputs are not invented','operations;all','Historical capacities, lab/trainer references and conditional source rules','Absent profiles keep operational applicability/capacity Unknown without blocking context EDA','OP-H01/02/OP-G04')]:
                cross.append({'finding':finding,'subjects':subjects,'evidence':evidence,'conclusion':conclusion,'source_pointer':pointer})
            dependencies=[
                {'family':'solar_visibility','related_quantities':'Sun opportunity; UV opportunity; photoemission opportunity; complement shadow opportunity','policy':'same input or complement, not independent evidence/weights; no dose/voltage conversion'},
                {'family':'related_Apollo_accounts','related_quantities':'primary resource totals; retrospective percentage tables; journal/report accounts','policy':'related historical evidence, not independent mission/event counts'},
                {'family':'orbital_particle_context','related_quantities':'GOES/CRaTER/LEND counters or flux; solar irradiance; spacecraft plasma','policy':'distinct quantities/platforms/responses; neither merge as dose nor infer Moon surface charging from a pooled correlation'},
                {'family':'terrain_model_footprint','related_quantities':'regional boxes; reference observers; candidate components; native image/model pixels','policy':'different spatial/time support; no unvalidated point/box-to-candidate substitution'}]
        tables={'proposed_requirement_register':combined,'subject_scope_and_conclusions':pd.DataFrame(scope),
            'analysis_artifact_field_crosswalk':pd.DataFrame(artifacts),'native_derived_field_catalog':pd.DataFrame(fields),
            'outline_factor_crosswalk':pd.DataFrame(outline_rows),'cross_subject_findings':pd.DataFrame(cross),
            'shared_evidence_dependencies':pd.DataFrame(dependencies),'passed_failed_unknown_specification_examples':specification_examples()}
        for name,frame in tables.items():frame.to_csv(run.path(name+'.csv'),index=False)
        manifest={'schema':1,'body':'Moon','adoption_state':'proposed_unadopted','engine_integration':False,
            'mission_equipment_optional':True,'numeric_limits_adopted':False,'preference_weights_adopted':False,
            'requirements':json.loads(combined.where(pd.notna(combined),None).to_json(orient='records'))}
        run.path('proposed_requirement_register.json').write_text(json.dumps(manifest,indent=2))
        findings={'sample':sample,'subject_areas':len(sources),'proposals':len(combined),'roles':combined.classification.value_counts().to_dict(),
            'outline_factors':len(outline_rows),'analysis_field_crosswalk_rows':len(artifacts),'native_derived_field_catalog_rows':len(fields),
            'cross_subject_findings':len(cross),'tables':{name:len(f) for name,f in tables.items()},
            'base_conclusion':'Existing Moon/source evidence supports environmental context, source-quality guards and conditional requirements. Actual operational suitability remains Unknown until applicable mission-local demand, qualified responses/capabilities and requirements are supplied.',
            'scope':'Stage 4 specification/proposal, NOT a mission evaluator, adopted requirement set or NASA certification',
            'pipeline_changed':False,'operational_status':'Unknown','required_followup_for_operational_use':'separate Stage 5 design/adoption and mission-specific engineering validation; not part of this Stage 3-4 deliverable'}
        run.path('findings.json').write_text(json.dumps(findings,indent=2));result=run.directory
    print(json.dumps(findings,indent=2),flush=True);return result,findings


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--sample',action='store_true');print(execute(p.parse_args().sample)[0])
