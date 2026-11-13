"""LADEE LDEX current uncertainty and impact-catalog threshold/class/time study."""
from pathlib import Path
import argparse
import json
import sys
import xml.etree.ElementTree as ET

sys.path[:0]=[str(Path(__file__).resolve().parents[2]/'shared'),str(Path(__file__).resolve().parents[3]),str(Path(__file__).resolve().parents[4])]
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import stage3_acquired_eda as acquired
from decision_eda import accepted_input
from environment_workflow import LocalRun
from environment_time import calendar_summary,fixed_month_comparison
from stage3_mission_eda import LOCAL,ROOT,save_figure

CONFIG=Path(__file__).with_name('stage3_subject_config.json')
NOTEBOOK='Moon/Stage3_Requirements/Dar_048_dust_threshold_quality_time.ipynb'


def numerical_mass_support(frame):
    """Numerical support only, never an adopted reliable-event class or detection efficiency."""
    return (np.isfinite(frame.MASS)&frame.MASS.gt(0)&np.isfinite(frame.MASS_THRESHOLD)&frame.MASS_THRESHOLD.gt(0)
            &np.isfinite(frame.MASS_SIG)&frame.MASS_SIG.ge(0))


def class_counts(frame):
    return frame.groupby(['QUALITY','SATURATED'],dropna=False).size().rename('catalog_records').reset_index()


def proposals():
    definitions=[
        ('DU-G01','evidence_guard','Impact classes, thresholds and saturation remain explicit','quality-event classification, saturation, mass uncertainty/threshold and observing efficiency','E01 E13','No lowest/highest quality-number assumption; no equal detectability across thresholds or saturated states'),
        ('DU-G02','evidence_guard','Counts and current are not flux or surface loading','instrument live time/area/pointing/efficiency, orbital geometry and surface-transfer model','E01 E13 E14','Event-catalog record counts are not occurrence rates; current is not deposited dust mass or cabin concentration'),
        ('DU-H01','conditional_hard_constraint','Essential cooling, sealing and filtration remain adequate','local operational dust demand, activity/transport, qualified degradation response and applicable capability','E06 E13','Failed if qualified applicable demand exceeds essential capability; Passed only with sufficient evidence; otherwise Unknown'),
        ('DU-S01','conditional_soft_preference','Lower qualified dust-maintenance burden','all mandatory conditions Passed, comparable activity, response-based maintenance/energy/consumables burden','E13','Prefer supported total operational burden, not arbitrary low orbital current or few detected impacts'),
        ('DU-G03','evidence_guard','Real historical duration and background uncertainty','native timestamps, background/current uncertainty and gaps, valid calendar support','E14 E15','Keep the 2013-2014 mission span; no fabricated year-plus history, lunar seasons or future quiet-month forecast')]
    return pd.DataFrame([{'id':id,'classification':kind,'title':title,'required_inputs':inputs,'existing_rule_crosswalk':old,
        'decision_logic':logic,'quantity':'instrument current; catalog mass/threshold; local operational burden as applicable','unit':'elementary charges/s; kg; response-specific',
        'applicability':'LADEE orbital historical context; local mission/activity must be established',
        'source':'D10 PDS LDEX current/mass labels; quality classification reference [8] remains an explicit hold',
        'evidence':'current_daily_context.csv; current_uncertainty_by_file.csv; event_class_summary.csv; mass_threshold_summary.csv; calendar_context.csv',
        'limit_value':np.nan,'limit_state':'not_adopted','preference_weight':np.nan,'current_outcome':'Unknown',
        'status':'Stage 4 proposal only; not consumed by pipeline'} for id,kind,title,inputs,old,logic in definitions])


def execute(sample=False):
    subject=json.loads(CONFIG.read_text());config=json.loads(CONFIG.with_name(subject['acquisition_config']).read_text())
    with LocalRun(ROOT,'analysis/subject_dust'+('_sample' if sample else ''),subject,NOTEBOOK) as run:
        for p in [CONFIG,Path(__file__),acquired.CONFIG,Path(acquired.__file__),LOCAL/'EDA/shared/environment_time.py']:
            run.input(p)
        sources=acquired.catalog(run,config);entries=acquired.science(sources,'D10')
        if sample:
            entries=[e for prefix in ['current','mass'] for e in acquired.bounded([e for e in entries if Path(e['relative_path']).name.startswith(prefix)],True)]
        current,mass,diagnostics,label_rows=[],[],[],[]
        for e in entries:
            path,f=acquired.pds_table(run,config,sources,e);label=acquired.paired_path(run,config,sources,e)
            for field in ET.parse(label).getroot().findall('.//{*}Field_Character'):
                label_rows.append({'file':path.name,'field':field.findtext('{*}name'),'unit':field.findtext('{*}unit'),
                    'description':' '.join((field.findtext('{*}description') or '').split())})
            f['date']=pd.to_datetime(f.TIME,format='%Y-%jT%H:%M:%S.%f',utc=True);f['source_file']=path.name
            if path.name.startswith('current'):
                current.append(f)
                residual=f.CURRENT-(f.SIGNAL-f.BACKGROUND)
                for name,uncertainty in [('CURRENT','STD_CURRENT'),('SIGNAL','STD_SIGNAL'),('BACKGROUND','STD_BACKGROUND')]:
                    supported=np.isfinite(f[name])&np.isfinite(f[uncertainty])&f[uncertainty].ge(0)
                    diagnostics.append({'file':path.name,'quantity':name,'records':len(f),'finite_value_records':int(np.isfinite(f[name]).sum()),
                        'nonnegative_uncertainty_supported':int(supported.sum()),'negative_value_records':int(f[name].lt(0).sum()),
                        'zero_uncertainty_records':int(f[uncertainty].eq(0).sum()),'median_std':f.loc[supported,uncertainty].median(),
                        'maximum_current_minus_signal_background_residual':residual.abs().max(),
                        'interpretation':'reported standard deviation, not automatically standard error/CI; signed background-subtracted values retained'})
            else:mass.append(f)
        current=pd.concat(current,ignore_index=True);mass=pd.concat(mass,ignore_index=True)
        current_clock=acquired.unique_clock(current.date);mass_clock=acquired.unique_clock(mass.date)
        daily=[]
        for name,std in [('CURRENT','STD_CURRENT'),('SIGNAL','STD_SIGNAL'),('BACKGROUND','STD_BACKGROUND')]:
            # Retain Dar044's original numerical current contract; uncertainty support is additional and separately named.
            daily.append(acquired.daily_rows('LDEX_'+name,current.date,current[name].where(current_clock)))
            supported=current_clock&np.isfinite(current[std])&current[std].ge(0)
            daily.append(acquired.daily_rows('LDEX_uncertainty_supported_'+name,current.date,current[name].where(supported)))
            positive=current_clock&np.isfinite(current[name])&np.isfinite(current[std])&current[std].gt(0)
            daily.append(acquired.daily_rows('LDEX_value_over_reported_std_'+name,current.date,(current[name]/current[std].where(positive)).where(positive)))
        current_daily=pd.concat(daily,ignore_index=True)
        numerical=numerical_mass_support(mass);mass['numerical_support']=numerical;mass['unique_clock']=mass_clock
        mass['mass_to_threshold']=mass.MASS.where(numerical)/mass.MASS_THRESHOLD.where(numerical)
        mass['relative_reported_uncertainty']=mass.MASS_SIG.where(numerical)/mass.MASS.where(numerical)
        mass['utc_day']=mass.date.dt.floor('D')
        event_daily=mass.groupby(['utc_day','QUALITY','SATURATED'],dropna=False).agg(
            catalog_records=('MASS','size'),numerically_supported_mass_records=('numerical_support','sum'),
            unique_clock_records=('unique_clock','sum'),median_mass_kg=('MASS','median'),
            median_mass_to_threshold=('mass_to_threshold','median'),median_relative_reported_uncertainty=('relative_reported_uncertainty','median')).reset_index()
        event_daily['interpretation']='catalog detections on recorded dates, not observing exposure or a surface-event rate; quality classes not adopted'
        summaries=[]
        for (quality,saturated),g in mass.groupby(['QUALITY','SATURATED'],dropna=False):
            good=g.numerical_support&g.unique_clock
            for col in ['MASS','MASS_THRESHOLD','MASS_SIG','mass_to_threshold','relative_reported_uncertainty','VELOCITY']:
                summaries.append({'quality':quality,'saturated':saturated,'field':col,'catalog_records':len(g),
                    'below_native_mass_threshold':int((g.mass_to_threshold<1).sum()),
                    'numerically_supported_unique_clock_records':int(good.sum()),**acquired.describe(g.loc[good,col]),
                    'scope':'numerical/class-specific context, not event-classification or science-response qualification'})
            sid=f'LDEX_catalog_Q{quality:g}_S{saturated:g}_MASS'
            daily.append(acquired.daily_rows(sid,g.date,g.MASS.where(good)))
            daily.append(acquired.daily_rows(sid+'_threshold',g.date,g.MASS_THRESHOLD.where(good)))
        combined=pd.concat(daily,ignore_index=True)
        calendar=calendar_summary(combined,subject['time_bins'],subject['two_year_anchor'])
        old=pd.read_csv(accepted_input(run,LOCAL/'data/processed/analysis'/subject['screening_run'],'daily_context.csv'))
        old=old.loc[old.series_id.str.startswith('LDEX_')].copy();old['date']=pd.to_datetime(old.date,utc=True)
        checks=old[['series_id','date','daily_median','valid_samples']].merge(current_daily[['series_id','date','daily_median','valid_samples']],on=['series_id','date'],how='inner',suffixes=('_old','_new'),validate='one_to_one')
        checks['absolute_difference']=(checks.daily_median_old-checks.daily_median_new).abs()
        checks['support_changed']=(checks.daily_median_old.isna()!=checks.daily_median_new.isna())|(checks.valid_samples_old!=checks.valid_samples_new)
        if not sample and (len(checks)!=len(old) or checks.support_changed.any() or checks.absolute_difference.fillna(0).max()>1e-8):raise ValueError('LDEX accepted current contract changed')
        tables={'current_daily_context':current_daily,'current_uncertainty_by_file':pd.DataFrame(diagnostics),
            'event_class_summary':class_counts(mass),'event_class_daily_records':event_daily,'mass_threshold_summary':pd.DataFrame(summaries),
            'calendar_context':calendar,'matched_January_December_years':fixed_month_comparison(combined),
            'field_metadata':pd.DataFrame(label_rows),'crosscheck_Dar044':checks,'stage4_dust_proposals':proposals()}
        for name,frame in tables.items():frame.to_csv(run.path(name+'.csv'),index=False)
        fig,axes=plt.subplots(2,1,figsize=(12,6),sharex=True,layout='constrained')
        for name in ['CURRENT','SIGNAL','BACKGROUND']:
            g=current_daily.loc[current_daily.series_id.eq('LDEX_'+name)]
            axes[0].plot(g.date,g.daily_median,label=name);axes[1].plot(g.date,g.valid_samples/g.recorded_samples,label=name)
        axes[0].set(ylabel='Elementary charges/s',title='Orbital LDEX signed daily current; not deposited mass');axes[0].legend()
        axes[1].set(ylabel='Numerically supported record fraction',ylim=(-.02,1.02));save_figure(run,fig,'signed_current_context')
        fig,axes=plt.subplots(2,1,figsize=(12,6),sharex=True,layout='constrained')
        for (q,s),g in mass.groupby(['QUALITY','SATURATED'],dropna=False):
            supported=g.numerical_support&g.unique_clock
            axes[0].scatter(g.loc[supported,'date'],g.loc[supported,'MASS'],s=2,label=f'Q{q:g} S{s:g}')
            axes[1].scatter(g.loc[supported,'date'],g.loc[supported,'mass_to_threshold'],s=2)
        axes[0].set(ylabel='Mass kg',yscale='log',title='Impact-catalog classes remain separate; numerical support is not event qualification');axes[0].legend(ncol=5,fontsize=7)
        axes[1].set(ylabel='Mass/native threshold',yscale='log');save_figure(run,fig,'mass_threshold_classes')
        fig,ax=plt.subplots(figsize=(12,4),layout='constrained')
        for (q,s),g in event_daily.groupby(['QUALITY','SATURATED'],dropna=False):
            ax.scatter(g.utc_day,g.catalog_records,s=6,label=f'Q{q:g} S{s:g}')
        ax.set(ylabel='Recorded catalog entries/day',title='Observed catalog counts, NOT flux or an exposure-corrected occurrence rate');ax.legend(ncol=5,fontsize=7)
        save_figure(run,fig,'catalog_records_not_rates')
        findings={'subject':'dust','sample':sample,'analysed_files':len(entries),'current_records':len(current),'mass_catalog_records':len(mass),
            'current_recorded_dates':current.date.dt.floor('D').nunique(),'mass_recorded_dates':mass.utc_day.nunique(),
            'ambiguous_current_clock_records':int((~current_clock).sum()),'ambiguous_mass_clock_records':int((~mass_clock).sum()),
            'numerically_supported_mass_records':int(numerical.sum()),'numerical_mass_below_native_threshold':int(mass.mass_to_threshold.lt(1).sum()),
            'time_start':str(min(current.date.min(),mass.date.min())),'time_stop':str(max(current.date.max(),mass.date.max())),
            'tables':{n:len(f) for n,f in tables.items()},'time_contract':subject['time_contract'],
            'base_conclusion':'Background/uncertainty, class, saturation and mass threshold affect orbital dust evidence. Signed currents and detected catalog counts do not establish local surface contamination, health burden or hardware degradation.',
            'pipeline_changed':False,'adopted_limits':False,'operational_status':'Unknown',
            'remaining':['Event-classification/efficiency and live-time qualification','Orbital pointing/altitude and local activity/transport','Qualified cooling/seal/filter degradation and applicable capability','Other subjects and integrated Stage 4 synthesis']}
        run.path('findings.json').write_text(json.dumps(findings,indent=2));folder=run.directory
    print(json.dumps(findings,indent=2),flush=True);return folder,findings


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--sample',action='store_true')
    print(execute(parser.parse_args().sample)[0])
