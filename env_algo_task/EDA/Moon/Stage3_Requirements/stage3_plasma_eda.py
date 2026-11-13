"""Full ESA subject EDA, mode/quality/cadence analysis and existing-context cross-checks."""
from pathlib import Path
import argparse
import json
import sys

sys.path[:0]=[str(Path(__file__).resolve().parents[2]/'shared'),str(Path(__file__).resolve().parents[3]),str(Path(__file__).resolve().parents[4])]
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import stage3_acquired_eda as acquired
from environment_time import calendar_summary, fixed_month_comparison
from environment_workflow import LocalRun
from decision_eda import accepted_input
from stage3_mission_eda import LOCAL,ROOT,save_figure

CONFIG=Path(__file__).with_name('stage3_subject_config.json')
NOTEBOOK='Moon/Stage3_Requirements/Dar_046_plasma_modes_charging_time.ipynb'


def read_context(run,folder,name):
    return pd.read_csv(accepted_input(run,LOCAL/'data/processed/analysis'/folder,name))


def quality_tables(diagnostics):
    d=diagnostics.copy()
    d['date']=pd.to_datetime(d.file.str.extract(r'(20\d{6})')[0],format='%Y%m%d',utc=True)
    d['year']=d.date.dt.year
    d['quality_zero_fraction']=d.quality_zero/d.recorded.replace(0,np.nan)
    rows=[]
    for row in d.to_dict('records'):
        value=row.get('quality_flag_counts_in_nominal_day')
        if not isinstance(value,str):continue
        for flag,count in json.loads(value).items():
            rows.append({'file':row['file'],'date':row['date'],'mode':row['mode'],'flag_value':flag,'records':count,
                'meaning':'0=publisher good; nonzero/fill are not silently accepted','basis':'records inside nominal UTC file day, before ambiguous-clock screening'})
    per_year=d.groupby(['mode','year'],as_index=False).agg(files=('file','nunique'),recorded=('recorded','sum'),
        quality_zero=('quality_zero','sum'),median_daily_good_fraction=('quality_zero_fraction','median'),
        ambiguous_clock_records=('ambiguous_or_missing_clock_records','sum'),outside_nominal_day=('outside_nominal_day','sum'),
        median_file_spacing_s=('median_spacing_s','median'))
    per_year['pooled_record_good_fraction']=per_year.quality_zero/per_year.recorded.replace(0,np.nan)
    per_year['interpretation']='record fractions, not elapsed valid-time coverage; native full/reduced/burst and species differ'
    return d,pd.DataFrame(rows),per_year


def paired_daily(daily,left,right,name):
    f=daily.loc[daily.series_id.eq(left),['date','daily_median','valid_samples']].rename(columns={'daily_median':'left_value','valid_samples':'left_valid_samples'})
    g=daily.loc[daily.series_id.eq(right),['date','daily_median','valid_samples']].rename(columns={'daily_median':'right_value','valid_samples':'right_valid_samples'})
    pair=f.merge(g,on='date',validate='one_to_one').dropna(subset=['left_value','right_value'])
    pair['comparison']=name
    positive=(pair.left_value>0)&(pair.right_value>0)
    pair['positive_value_ratio']=pair.left_value.where(positive)/pair.right_value.where(positive)
    pair['limitation']='same UTC daily summaries, not coincident sample times, co-location, quasi-neutrality proof or a charging model'
    n=len(pair)
    rho=pair.left_value.corr(pair.right_value,method='spearman') if n>=30 and pair.left_value.nunique()>1 and pair.right_value.nunique()>1 else np.nan
    return pair,{'comparison':name,'left_series':left,'right_series':right,'paired_valid_dates':n,
        'spearman_descriptive':rho,'median_positive_daily_ratio':pair.positive_value_ratio.median() if positive.any() else np.nan,
        'interpretation':'descriptive common-day association; no causality, event-rate or safety claim'}


def screening_crosscheck(new,old):
    original=old.loc[old.series_id.str.startswith('ESA_')].copy()
    original['date']=pd.to_datetime(original.date,utc=True)
    keys=['series_id','date']
    cols=['daily_median','daily_max','daily_p95','recorded_samples','valid_samples']
    joined=original[keys+cols].merge(new[keys+cols],on=keys,how='left',suffixes=('_old','_new'),indicator=True,validate='one_to_one')
    rows=[]
    for column in cols:
        a,b=joined[column+'_old'],joined[column+'_new']
        valid=a.notna()&b.notna()
        rows.append({'quantity':column,'previous_daily_rows':len(original),'matched_rows':int(joined._merge.eq('both').sum()),
            'support_changed_rows':int((a.isna()!=b.isna()).sum()),
            'maximum_absolute_difference':float((a[valid]-b[valid]).abs().max()) if valid.any() else np.nan,
            'conclusion':'full-file cohort expansion must preserve identical native-day/mode results on the screening subset'})
    return pd.DataFrame(rows)


def proposals():
    rows=[
        ('PL-G01','evidence_guard','Native quality and clocks before mode comparisons','stored moments, Q-flag meaning, unique finite time, nominal-day support','E01 E14','Virtual Q arrays have no stored data; explicitly apply native flags and preserve missing/ambiguous records'),
        ('PL-G02','evidence_guard','Modes/species/cadence are not interchangeable','full/reduced/burst and electron/ion identity; units and actual sampling','E01 E14','No pooling as identical observations or converting record counts into qualified duration'),
        ('PL-G03','evidence_guard','Spacecraft geometry and potential are not surface conditions','position/altitude and frame, local surface/material response, solar geometry','E13 E16','Neither spacecraft-potential moments nor density/field alone supply candidate surface voltage or discharge rate'),
        ('PL-H01','conditional_hard_constraint','Essential-system charging/ESD capability','qualified local charging/discharge demand; hardware/material capability; applicable limit and operating period','E06 E16','Passed only when supported local demand meets applicable capability; Failed if an applicable mandatory limit/capability is exceeded; otherwise Unknown'),
        ('PL-S01','conditional_soft_preference','Reduced qualified charging-management burden','all mandatory conditions Passed; comparable activity and response-based management burden','E13 E16','Preference may use a validated operational burden, not an arbitrary lowest-density, lowest-voltage or darkest-site rule'),
        ('PL-G04','evidence_guard','Calendar associations are not causal or forecast safety models','matched valid dates, mode and geometry support, coverage and validation','E14 E15','Keep partial windows and sample-matching limits; different spacecraft/daily medians are not co-located instantaneous observations')]
    return pd.DataFrame([{'id':id,'classification':kind,'title':title,'required_inputs':inputs,'decision_logic':logic,
        'existing_rule_crosswalk':prior,'current_outcome':'Unknown','limit_value':np.nan,'limit_state':'not_adopted',
        'preference_weight':np.nan,'scope':'Moon mission/footprint, configuration and applicable period must be established',
        'evidence':'esa_daily_context.csv; native_quality_years.csv; quality_flag_frequencies.csv; calendar_context.csv; matched_daily_summary.csv',
        'status':'Stage 4 proposal only; not consumed by pipeline'} for id,kind,title,inputs,prior,logic in rows])


def execute(sample=False):
    subject=json.loads(CONFIG.read_text());config=json.loads(CONFIG.with_name(subject['acquisition_config']).read_text())
    if subject['schema']!=1 or subject['body']!='Moon':raise ValueError('Moon subject schema required')
    stage='analysis/subject_plasma'+('_sample' if sample else '')
    with LocalRun(ROOT,stage,subject,NOTEBOOK) as run:
        for p in [CONFIG,Path(__file__),Path(acquired.__file__),acquired.CONFIG,LOCAL/'EDA/shared/environment_time.py']:
            run.input(p)
        sources=acquired.catalog(run,config)
        print('Reading all selected ESA files (sample first/last only when requested)',flush=True)
        daily,catalog,diag=acquired.esa(run,config,sources,sample,all_files=True,flag_diagnostics=True)
        daily['date']=pd.to_datetime(daily.date,utc=True)
        if daily.duplicated(['series_id','date']).any():raise ValueError('Repeated mode/day')
        native,flags,years=quality_tables(diag)
        screening=read_context(run,subject['screening_run'],'daily_context.csv')
        screening['date']=pd.to_datetime(screening.date,utc=True)
        checks=screening_crosscheck(daily,screening)
        if sample:checks['scope']='sample can only overlap part of prior screening; unmatched rows are expected'
        else:
            if (checks.support_changed_rows>0).any() or (checks.matched_rows!=checks.previous_daily_rows).any():
                raise ValueError('Full cohort changed previously accepted screening support')
            if checks.maximum_absolute_difference.fillna(0).max()>1e-10:raise ValueError('Full cohort changed screening values')
        previous=read_context(run,subject['temporal_run'],'daily_context.csv')
        previous=previous.loc[previous.series_id.str.startswith('PLASMA_')].copy();previous['date']=pd.to_datetime(previous.date,utc=True)
        p2=screening.loc[screening.series_id.str.startswith('P2_')].copy()
        if sample:
            previous=previous.groupby('series_id').head(10);p2=p2.groupby('series_id').head(10)
        combined=pd.concat([daily,previous,p2],ignore_index=True)
        calendar=calendar_summary(combined,subject['time_bins'],subject['two_year_anchor'])
        same_months=fixed_month_comparison(combined,6,10)
        pairs,summaries=[],[]
        for mode in ['f','r','b']:
            left='ESA_v01_thb_pei'+mode+'_density';right='ESA_v01_thb_pee'+mode+'_density'
            pair,summary=paired_daily(daily,left,right,'P1_ion_vs_electron_'+mode)
            pairs.append(pair);summaries.append(summary)
        p1ids=[s for s in previous.series_id.unique() if 'thb_peif_densityQ_all_positions' in s]
        p2ids=[s for s in p2.series_id.unique() if 'thc_peif_densityQ_all_positions' in s]
        for left in p1ids:
            for right in p2ids:
                pair,summary=paired_daily(combined,left,right,'P1_vs_P2_full_mode_daily')
                pairs.append(pair);summaries.append(summary)
            pair,summary=paired_daily(combined,'ESA_v01_thb_peif_density',left,'P1_native_vs_merged_product')
            pair['limitation']='related products, not independent experiments; cadence/selection differ even with the same source spacecraft'
            pairs.append(pair);summaries.append(summary)
        tables={'esa_daily_context':daily,'esa_series_catalog':catalog,'native_file_quality':native,
            'quality_flag_frequencies':flags,'native_quality_years':years,'calendar_context':calendar,
            'matched_June_October_years':same_months,'matched_daily_values':pd.concat(pairs,ignore_index=True),
            'matched_daily_summary':pd.DataFrame(summaries),'crosscheck_Dar044':checks,'stage4_plasma_proposals':proposals()}
        for name,frame in tables.items():frame.to_csv(run.path(name+'.csv'),index=False)
        for variable,unit in [('density','cm^-3'),('avgtemp','eV'),('sc_pot','V, spacecraft support value')]:
            fig,axes=plt.subplots(2,1,figsize=(12,6),sharex=True,layout='constrained')
            subset=calendar.loc[calendar.period_kind.eq('month')&calendar.series_id.str.startswith('ESA_')&calendar.series_id.str.endswith('_'+variable)]
            for sid,g in subset.groupby('series_id'):
                date=pd.to_datetime(g.period_start_utc)
                axes[0].plot(date,g.median_of_daily_values,marker='.',label=sid.split('_thb_')[-1])
                axes[1].plot(date,g.valid_day_fraction,marker='.')
            axes[0].set(ylabel=unit,title='P1 ESA '+variable+' by native species/mode; not a charging/safety score');axes[0].legend(fontsize=7,ncol=3)
            axes[1].set(ylabel='Valid-day fraction',ylim=(-.02,1.02));save_figure(run,fig,'esa_monthly_'+variable)
        fig,axes=plt.subplots(2,1,figsize=(12,6),layout='constrained')
        for mode,g in native.groupby('mode'):
            axes[0].scatter(g.date,g.quality_zero_fraction,s=3,label=mode)
            axes[1].scatter(g.date,g.median_spacing_s,s=3,label=mode)
        axes[0].set(ylabel='Raw quality=0 fraction',ylim=(-.02,1.02),title='Record fractions and observed native cadence; neither is elapsed qualified exposure');axes[0].legend(ncol=6,fontsize=8)
        axes[1].set(ylabel='Median file spacing, s',yscale='log');save_figure(run,fig,'mode_quality_and_cadence')
        for name,g in tables['matched_daily_values'].groupby('comparison'):
            fig,ax=plt.subplots(figsize=(6,5),layout='constrained');ax.scatter(g.left_value,g.right_value,s=4,alpha=.4)
            ax.set(xlabel='Left daily density cm^-3',ylabel='Right daily density cm^-3',title=name+'\nUTC-day matching, not co-location or a response model')
            save_figure(run,fig,'matched_'+name)
        findings={'subject':'plasma_charging','sample':sample,'full_downloaded_ESA_files':not sample,
            'analysed_ESA_files':int(native.file.nunique()),'mode_file_rows':len(native),'daily_rows':len(daily),
            'quality_zero_records':int(native.quality_zero.sum()),'recorded_mode_records':int(native.recorded.sum()),
            'ambiguous_or_missing_clock_mode_records':int(native.ambiguous_or_missing_clock_records.sum()),
            'calendar_kinds':subject['time_bins'],'tables':{k:len(v) for k,v in tables.items()},
            'base_conclusion':'Full native ESA coverage improves mode-specific plasma/spacecraft-potential and quality/cadence context. It does not establish surface voltage, discharge/ESD risk, a monotonic safe-density ranking or a mission-operable site.',
            'crosscheck':'shared Dar044 days/modes preserved; merged products and spacecraft contrasts are separate, not extra independent observations',
            'pipeline_changed':False,'adopted_limits':False,'operational_status':'Unknown',
            'remaining':['Local charging/triboelectric/material/illumination response','Applicable system capability and limits','Position/epoch alignment for any local operational inference','Other subject studies and integrated Stage 4 synthesis']}
        run.path('findings.json').write_text(json.dumps(findings,indent=2));folder=run.directory
    print(json.dumps(findings,indent=2),flush=True);return folder,findings


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--sample',action='store_true')
    print(execute(parser.parse_args().sample)[0])
