"""Full selected LADEE NMS species/geometry/time study and sparse-cohort sensitivity."""
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
NOTEBOOK='Moon/Stage3_Requirements/Dar_051_exosphere_species_geometry_time.ipynb'


def native_dates(f):
    """Conservative canonical-component clock; noncanonical/unknown values are held, not corrected."""
    date=pd.to_datetime(f[['Year','Month','Day']].rename(columns={'Year':'year','Month':'month','Day':'day'}),utc=True,errors='coerce')
    valid=f.Hours.ge(0)&f.Hours.lt(24)&f.Minutes.ge(0)&f.Minutes.lt(60)&f.Seconds.ge(0)&f.Seconds.lt(60)
    seconds=(f.Hours*3600+f.Minutes*60+f.Seconds).where(valid)
    return pd.DatetimeIndex(date+pd.to_timedelta(seconds,unit='s'))


def original_archive_dates(f):
    """Exact earlier arithmetic decoder, for old-cohort replay only; not the new clock-qualification policy."""
    date=pd.to_datetime(f[['Year','Month','Day']].rename(columns={'Year':'year','Month':'month','Day':'day'}),utc=True)
    return pd.DatetimeIndex(date+pd.to_timedelta(f.Hours*3600+f.Minutes*60+f.Seconds,unit='s'))


def abundance_support(f,clock):
    return np.isfinite(f.value)&np.isfinite(f['std'])&f['std'].ge(0)&clock


def geometry_bins(f):
    g=f.copy()
    g['altitude_bin_km']=pd.cut(g.altitude.where(g.altitude.ge(0)),[0,25,50,100,200,np.inf],right=False)
    local=g.local_hour.where(g.local_hour.between(0,24)).mod(24)
    g['local_solar_hour_bin']=pd.cut(local,np.arange(0,25,3),right=False)
    g['latitude_bin_deg']=pd.cut(g.latitude.where(g.latitude.between(-90,90)),[-90,-60,-30,0,30,60,90],include_lowest=True)
    return g


def stratum_summary(f,keys):
    rows=[]
    for labels,g in f.groupby(keys,observed=True,dropna=False):
        labels=labels if isinstance(labels,tuple) else (labels,)
        supported=g.value.where(g.supported)
        rows.append({**dict(zip(keys,map(str,labels))),'recorded':len(g),'supported':int(g.supported.sum()),
            'negative_supported_estimates':int((g.supported&g.value.lt(0)).sum()),'recorded_utc_dates':g.date.dt.floor('D').nunique(),
            'median_reported_std':g.loc[g.supported,'std'].median(),**acquired.describe(supported),
            'scope':'record-weighted orbital historical context; geometry bins are descriptive, not safety limits; NaN bin is missing geometry'})
    return pd.DataFrame(rows)


def proposals():
    definitions=[
        ('EX-G01','evidence_guard','Preserve species, uncertainty and orbital geometry','species/units, reported Std, unique dated records, altitude, lunar coordinates and local solar time','E01 E13 E14','Retain negative estimates and invalid/missing support explicitly; no mixing species or orbital sampling as a surface concentration'),
        ('EX-G02','evidence_guard','Control sparse-cohort and time/geometry confounding','full versus preselected orbit cohort, actual calendar support and conditional geometry coverage','E14 E15','Changed full-day medians from more orbit coverage are cohort sensitivity, not a contradiction or causal seasonal change'),
        ('EX-H01','conditional_hard_constraint','Applicable external-vacuum and contamination compatibility','mission-local gas/contamination demand, operations/outgassing, pressure/material response and essential capability','E06 E09 E13','Failed if qualified applicable demand exceeds an essential capability/limit; Passed only with sufficient evidence; otherwise Unknown'),
        ('EX-S01','conditional_soft_preference','Lower qualified contamination-control burden','all mandatory conditions Passed, comparable mission/activity, background and response-based maintenance/energy burden','E13','Do not prefer universally smaller raw abundance or classify the lunar exosphere as breathable atmosphere'),
        ('EX-G03','evidence_guard','Natural exosphere versus instrument/mission background','background/calibration and spacecraft activity/outgassing evidence','E01 E06','A measured signal/negative estimate alone does not resolve contamination; historical Apollo cases guide checks, not numerical LADEE corrections')]
    return pd.DataFrame([{'id':id,'classification':kind,'title':title,'required_inputs':inputs,'existing_rule_crosswalk':old,
        'decision_logic':logic,'quantity':'species abundance and reported standard deviation; local vacuum/contamination response if qualified',
        'unit':'native P/Cc = particles/cm3; geometry km/degree/hour; operational response-specific',
        'applicability':'historical LADEE orbit/epoch; surface footprint and mission activity must be established',
        'source':'D35 PDS4 NMS field labels; accepted Dar044 cohort; Apollo 17 outgassing/background PDF evidence remains contextual',
        'evidence':'file_support.csv; geometry_strata.csv; calendar_context.csv; crosscheck_old_cohort.csv; full_vs_sparse_daily.csv',
        'limit_value':np.nan,'limit_state':'not_adopted','preference_weight':np.nan,'current_outcome':'Unknown',
        'status':'Stage 4 proposal only; not consumed by pipeline'} for id,kind,title,inputs,old,logic in definitions])


def execute(sample=False):
    subject=json.loads(CONFIG.read_text());config=json.loads(CONFIG.with_name(subject['acquisition_config']).read_text())
    with LocalRun(ROOT,'analysis/subject_exosphere'+('_sample' if sample else ''),subject,NOTEBOOK) as run:
        for p in [CONFIG,Path(__file__),acquired.CONFIG,Path(acquired.__file__),LOCAL/'EDA/shared/environment_time.py']:run.input(p)
        sources=acquired.catalog(run,config);all_entries=acquired.science(sources,'D35')
        old_urls={e['url'] for e in acquired.monthly_edges(all_entries,species=True)}
        entries=all_entries
        if sample:
            groups={}
            for e in entries:groups.setdefault(Path(e['relative_path']).name.split('_')[1],[]).append(e)
            edges=[e for es in groups.values() for e in acquired.bounded(es,True)]
            known_clock_cases=['nms_he_36499_20140131_211317.csv','nms_ar_36721_20140228_211518.csv']
            entries=list({e['url']:e for e in [*edges,*[e for e in entries if Path(e['relative_path']).name in known_clock_cases]]}.values())
        frames={};diagnostics=[];metadata=[];seen=set()
        for index,e in enumerate(entries):
            path,f=acquired.pds_table(run,config,sources,e);label=acquired.paired_path(run,config,sources,e)
            column=next(c for c in f if c.endswith('_ABUNDANCE'));species=column.split('_')[0]
            fields=ET.parse(label).getroot();defs=fields.findall('.//{*}Field_Character')+fields.findall('.//{*}Field_Delimited')
            units={d.findtext('{*}name'):d.findtext('{*}unit') for d in defs}
            if units[column]!='P/Cc' or units['Std']!='P/Cc' or units['Altitude']!='Kilometers' or units['Lmst']!='Hours':raise ValueError('NMS field units changed')
            if species not in seen:
                metadata.extend({'species':species,'file':path.name,'field':d.findtext('{*}name'),'unit':d.findtext('{*}unit'),
                    'description':' '.join((d.findtext('{*}description') or '').split())} for d in defs);seen.add(species)
            date=native_dates(f)
            old_cohort=e['url'] in old_urls
            original_date=original_archive_dates(f) if old_cohort else pd.NaT
            frame=pd.DataFrame({'date':date,'original_date':original_date,'value':f[column].to_numpy(),'std':f.Std.to_numpy(),
                'altitude':f.Altitude.to_numpy(),'latitude':f.Latitude.to_numpy(),'longitude':f.Longitude.to_numpy(),
                'local_hour':f.Lmst.to_numpy(),'old_cohort':old_cohort})
            frames.setdefault(species,[]).append(frame)
            diagnostics.append({'file':path.name,'species':species,'records':len(f),'first':date.min(),'last':date.max(),
                'withheld_noncanonical_or_missing_clock_records':int(date.isna().sum()),
                'native_seconds_equal_60_records':int(f.Seconds.eq(60).sum()),'negative_estimates':int(f[column].lt(0).sum()),
                'invalid_std_records':int((~np.isfinite(f.Std)|f.Std.lt(0)).sum()),'old_sparse_cohort':e['url'] in old_urls,
                'altitude_min_km':f.Altitude.min(),'altitude_max_km':f.Altitude.max(),'local_solar_hour_min':f.Lmst.min(),'local_solar_hour_max':f.Lmst.max()})
            if index%300==0:print('NMS files read:',index+1,flush=True)
        daily=[];old_daily=[];strict_old_daily=[];strata=[];display=[];clock_rows=[]
        for species,parts in frames.items():
            f=pd.concat(parts,ignore_index=True);clock=acquired.unique_clock(f.date);dated=f.date.notna()
            f['species']=species;f['supported']=abundance_support(f,clock)
            clock_rows.append({'species':species,'records':len(f),'undated_records':int((~dated).sum()),
                'ambiguous_or_missing_clock_records':int((~clock).sum()),'numerically_supported':int(f.supported.sum()),
                'meaning':'finite abundance, finite nonnegative Std, unique dated records; not total uncertainty or response qualification'})
            sid='NMS_'+species+'_ABUNDANCE'
            for name,value in [(sid,f.value.where(f.supported)),('NMS_Std_'+species,f['std'].where(f.supported))]:
                daily.append(acquired.daily_rows(name,f.loc[dated,'date'],value.loc[dated]))
            old=f.loc[f.old_cohort].copy();valid=abundance_support(old,acquired.unique_clock(old.date));d=old.date.notna()
            strict_old_daily.append(acquired.daily_rows(sid,old.loc[d,'date'],old.value.where(valid).loc[d]))
            original=pd.to_datetime(old.original_date,utc=True);clock=acquired.unique_clock(original)
            valid=abundance_support(old,clock);d=original.notna()
            old_daily.append(acquired.daily_rows(sid,original.loc[d],old.value.where(valid).loc[d]))
            binned=geometry_bins(f)
            for dims in [['species','altitude_bin_km'],['species','local_solar_hour_bin'],['species','latitude_bin_deg'],
                         ['species','altitude_bin_km','local_solar_hour_bin','latitude_bin_deg']]:
                summary=stratum_summary(binned,dims);summary['dimensions']=';'.join(dims[1:]);strata.append(summary)
            step=max(1,int(np.ceil(len(f)/5000)));display.append(f.iloc[::step].assign(display_stride=step,
                scope='systematic display sample only; statistics/calendar use all selected records'))
        daily=pd.concat(daily,ignore_index=True);old_daily=pd.concat(old_daily,ignore_index=True)
        strict_old_daily=pd.concat(strict_old_daily,ignore_index=True)
        previous=pd.read_csv(accepted_input(run,LOCAL/'data/processed/analysis'/subject['screening_run'],'daily_context.csv'))
        previous=previous.loc[previous.series_id.str.startswith('NMS_')].copy();previous['date']=pd.to_datetime(previous.date,utc=True)
        cols=['series_id','date','daily_median','valid_samples']
        check=previous[cols].merge(old_daily[cols],on=['series_id','date'],how='inner',suffixes=('_old','_replayed'),validate='one_to_one')
        check['absolute_difference']=(check.daily_median_old-check.daily_median_replayed).abs()
        check['support_changed']=(check.daily_median_old.isna()!=check.daily_median_replayed.isna())|(check.valid_samples_old!=check.valid_samples_replayed)
        if not sample and (len(check)!=len(previous) or check.support_changed.any() or check.absolute_difference.fillna(0).max()>1e-8):raise ValueError('Replayed NMS original cohort changed')
        contrast=previous[cols].merge(daily[cols],on=['series_id','date'],how='inner',suffixes=('_sparse','_full'),validate='one_to_one')
        contrast['full_minus_sparse_daily_median']=contrast.daily_median_full-contrast.daily_median_sparse
        contrast['interpretation']='combined additional orbit/geometry coverage and stricter canonical-component clocks; isolate the two effects in the separate controlled comparisons'
        clock_effect=old_daily[cols].merge(strict_old_daily[cols],on=['series_id','date'],how='outer',suffixes=('_original_clock','_canonical_clock'),validate='one_to_one')
        clock_effect['canonical_minus_original_daily_median']=clock_effect.daily_median_canonical_clock-clock_effect.daily_median_original_clock
        clock_effect['interpretation']='fixed original files: conservative noncanonical-clock hold, not orbit-cohort change; native second=60 meaning/rounding unresolved'
        cohort_effect=strict_old_daily[cols].merge(daily[cols],on=['series_id','date'],how='inner',suffixes=('_sparse','_full'),validate='one_to_one')
        cohort_effect['full_minus_sparse_daily_median']=cohort_effect.daily_median_full-cohort_effect.daily_median_sparse
        cohort_effect['interpretation']='same conservative canonical-component policy: additional orbit/geometry coverage, not a seasonal causal effect'
        calendar=calendar_summary(daily,subject['time_bins'],subject['two_year_anchor'])
        tables={'daily_context':daily,'file_support':pd.DataFrame(diagnostics),'species_clock_support':pd.DataFrame(clock_rows),
            'field_metadata':pd.DataFrame(metadata),'geometry_strata':pd.concat(strata,ignore_index=True),
            'calendar_context':calendar,'matched_January_December_years':fixed_month_comparison(daily),
            'crosscheck_old_cohort':check,'full_vs_sparse_daily':contrast,'clock_filter_effect_old_cohort':clock_effect,
            'cohort_effect_fixed_clock':cohort_effect,'display_sample':pd.concat(display,ignore_index=True),
            'stage4_exosphere_proposals':proposals()}
        for name,frame in tables.items():frame.to_csv(run.path(name+'.csv'),index=False)
        for species,g in tables['display_sample'].groupby('species'):
            g=g.loc[g.supported]
            fig,axes=plt.subplots(1,3,figsize=(14,4),layout='constrained')
            for ax,col,label in zip(axes,['altitude','local_hour','latitude'],['Altitude km','Local solar hour','Latitude degree']):
                ax.scatter(g[col],g.value,s=2,alpha=.25);ax.set(xlabel=label,ylabel=species+' particles/cm3')
                ax.set_yscale('symlog',linthresh=1)
            fig.suptitle(species+' orbital geometry: display sample, not a causal/surface model');save_figure(run,fig,'geometry_'+species)
            fig,axes=plt.subplots(2,1,figsize=(12,6),sharex=True,layout='constrained')
            d=daily.loc[daily.series_id.eq('NMS_'+species+'_ABUNDANCE')]
            axes[0].plot(d.date,d.daily_median,label='all selected orbit files')
            o=previous.loc[previous.series_id.eq('NMS_'+species+'_ABUNDANCE')];axes[0].scatter(o.date,o.daily_median,s=15,label='old sparse orbit cohort')
            axes[0].set(ylabel='Particles/cm3',yscale='symlog',title=species+' historical daily abundance; signed estimates retained');axes[0].legend()
            axes[1].plot(d.date,d.valid_samples/d.recorded_samples);axes[1].set(ylabel='Numerical/clock-supported record fraction',ylim=(-.02,1.02));save_figure(run,fig,'daily_'+species)
        findings={'subject':'exosphere','sample':sample,'analysed_files':len(entries),'native_records':int(tables['file_support'].records.sum()),
            'species':sorted(frames),'daily_rows':len(daily),'first_utc':str(daily.date.min()),'last_utc':str(daily.date.max()),
            'tables':{n:len(f) for n,f in tables.items()},'time_contract':subject['time_contract'],
            'base_conclusion':'Full native orbit/species coverage improves abundance, uncertainty and geometry context and exposes sparse-cohort sensitivity. Historical orbital abundances and calendar associations do not establish local surface contamination, breathable air or hardware compatibility.',
            'full_source_scope':'all selected NMS files' if not sample else 'first/last file per species plus two known noncanonical-clock cases',
            'withheld_noncanonical_or_missing_clock_records':int(tables['file_support'].withheld_noncanonical_or_missing_clock_records.sum()),
            'native_seconds_equal_60_records':int(tables['file_support'].native_seconds_equal_60_records.sum()),
            'pipeline_changed':False,'adopted_limits':False,'operational_status':'Unknown',
            'remaining':['Instrument/background and activity attribution','Local surface/contamination response and applicable capability','No year-plus or repeatable season inference from the historical mission span','Other subjects and integrated Stage 4 synthesis']}
        run.path('findings.json').write_text(json.dumps(findings,indent=2));folder=run.directory
    print(json.dumps(findings,indent=2),flush=True);return folder,findings


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--sample',action='store_true')
    print(execute(parser.parse_args().sample)[0])
