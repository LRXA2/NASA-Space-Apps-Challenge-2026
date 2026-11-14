"""Apollo HFE: sensor/depth, signed corrected differences, clocks and calendar support."""
from pathlib import Path
import argparse
import json
import re
import sys

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
from research_p1_readers import pds4_chunks
from stage3_mission_eda import LOCAL,ROOT,save_figure

CONFIG=Path(__file__).with_name('stage3_subject_config.json')
NOTEBOOK='Moon/Stage3_Requirements/Dar_047_subsurface_thermal_depth_time.ipynb'
BITS={1:'missing data',2:'ambiguous bitflip',4:'outlier dT',8:'outlier T',16:'HTR placeholder',
      32:'TREF outlier',64:'TC1 outlier',128:'TC2 outlier',256:'TC3 outlier',512:'TC4 outlier',
      1024:'time discrepancy',2048:'cycle-change spike',4096:'sensitivity error',8192:'bit-flipped eclipse'}


def depths_from_document(text):
    result={}
    sections=re.split(r'### Apollo (15|17) probe ([12])\s*\n',text)
    for i in range(1,len(sections),3):
        mission,probe,body=sections[i:i+3]
        body=body.split('\n## ')[0]
        # Provider table uses TC11/TG11 even in probe-2 sections: section identifies probe.
        for name,value in re.findall(r'^\* (TC\d\d|T[GR]\d\d[AB]):\s*([^\n]+)',body,re.M):
            numeric=re.match(r'(-?\d+(?:\.\d+)?)',value)
            depth=float(numeric[1]) if numeric else 0. if value.strip()=='on surface' else np.nan
            result[(f'a{mission}',f'p{probe}',name)]={'depth_cm':depth,'position_text':value.strip()}
    if len(result)!=48:raise ValueError('Provider HFE depth table changed')
    return result


def bridge_values(mean,delta):
    """Lamont/clean convention: lower minus upper, not the opposite recovered-source convention."""
    return mean-delta/2,mean+delta/2


def flag_counts(flags):
    f=np.asarray(flags,float)
    good=np.isfinite(f)&(f>=0)&(f==np.floor(f))
    integer=f[good].astype('int64')
    out=[{'bit':bit,'meaning':meaning,'records':int(((integer&bit)!=0).sum())} for bit,meaning in BITS.items()]
    out.extend([{'bit':0,'meaning':'strict zero flags','records':int((integer==0).sum())},
                {'bit':-1,'meaning':'invalid/missing flag','records':int((~good).sum())},
                {'bit':-2,'meaning':'unknown flag bits','records':int(((integer&~sum(BITS))!=0).sum())}])
    return out


def proposals():
    definitions=[
        ('HF-G01','evidence_guard','Keep deployment, sensor depth and acquisition lineage','mission/probe/sensor position, epoch, recovered vs downsampled archival lineage','E01 E02 E06','Do not assign equatorial Apollo temperatures or depth positions to a polar footprint; changed sampling is not climate change'),
        ('HF-G02','evidence_guard','Signed corrected differences and clock/flag support','native missing constants, bitmask, corrected field and sign convention, unique dated samples','E01 E02','Negative dT is meaningful; use documented corrected dT where supplied; mangled heater state cannot establish heater performance'),
        ('HF-H01','conditional_hard_constraint','Applicable buried-system thermal envelope','mission-local depth-dependent thermal history, soil/contact response, component limits and duration','E02 E06','Failed if a qualified applicable component envelope is exceeded; Passed only with sufficient applicable evidence; otherwise Unknown'),
        ('HF-S01','conditional_soft_preference','Reduced qualified thermal-control burden','mandatory conditions Passed, comparable local response, excavation/installation/power costs','E02 E13','A deeper, quieter thermometer is not automatically a better or feasible base; prefer only qualified total operational burden'),
        ('HF-G03','evidence_guard','No heat flux without applicable conductivity and geometry','paired temperatures, separation, local thermal properties, disturbance/uncertainty model','E02 E13','dT and dT/separation are difference/gradient context, not measured heat flux or insulation performance')]
    return pd.DataFrame([{'id':id,'classification':role,'title':title,'required_inputs':inputs,'existing_rule_crosswalk':prior,
        'decision_logic':logic,'quantity':'temperature K; difference K; gradient K/m, as applicable','unit':'quantity-specific',
        'applicability':'historical Apollo deployment only until local mission applicability is established',
        'source':'D28 PDS clean labels and bundle documentation sections Thermometer Positions, Bitmask, Data contents',
        'evidence':'sensor_metadata.csv; daily_context.csv; native_field_statistics.csv; flags_by_file.csv; crosscheck_Dar044.csv',
        'limit_value':np.nan,'limit_state':'not_adopted','preference_weight':np.nan,'current_outcome':'Unknown',
        'status':'Stage 4 proposal only; not consumed by pipeline'} for id,role,title,inputs,prior,logic in definitions])


def execute(sample=False):
    subject=json.loads(CONFIG.read_text());config=json.loads(CONFIG.with_name(subject['acquisition_config']).read_text())
    with LocalRun(ROOT,'analysis/subject_hfe'+('_sample' if sample else ''),subject,NOTEBOOK) as run:
        for p in [CONFIG,Path(__file__),acquired.CONFIG,Path(acquired.__file__),LOCAL/'EDA/shared/environment_time.py']:
            run.input(p)
        sources=acquired.catalog(run,config)
        entry=next(e for e in sources['D28'] if e['url'].endswith('/bundle_documentation.md'))
        document=acquired.pin(run,config,entry);depths=depths_from_document(document.read_text())
        fields,metadata,stats,flags,clocks,corrections=[],{},[],[],[],[]
        selected=acquired.bounded(acquired.science(sources,'D28'),sample)
        for e in selected:
            path=acquired.pin(run,config,e);label=acquired.paired_path(run,config,sources,e)
            f=pd.concat(pds4_chunks(label,chunk_rows=20000),ignore_index=True)
            match=re.fullmatch(r'(a\d+)(?:_(\d{4}))?(p[12])f([1-5])',path.stem)
            if match is None:raise ValueError('Unrecognised HFE identity')
            mission,recovered,probe,number=match.groups()
            epoch=pd.Timestamp('1970-12-31' if mission=='a15' else '1971-12-31',tz='UTC')
            date=pd.DatetimeIndex(epoch+pd.to_timedelta(f.Time,unit='ms'))
            strict=f['flags'].eq(0)&~date.isna()
            clock=acquired.unique_clock(date)
            clocks.append({'file':path.name,'mission':mission,'probe':probe,'file_number':number,'records':len(f),
                'undated_records':int(date.isna().sum()),'ambiguous_or_missing_clock_records':int((~clock).sum()),
                'nonpositive_adjacent_time_steps':int((np.diff(date[~date.isna()].asi8)<=0).sum()),
                'median_positive_spacing_s':float(np.median(np.diff(date[~date.isna()].asi8)[np.diff(date[~date.isna()].asi8)>0]/1e9)),
                'lineage':'recovered '+recovered if recovered else 'Lamont-NSSDC 1971-1974; archive downsampled',
                'first_utc':date.min(),'last_utc':date.max(),'clock_contract':'provider mission epoch without leap seconds; no fabricated precision'})
            for row in flag_counts(f['flags']):flags.append({'file':path.name,**row})
            values={name:(f[name],name,np.nan,'not a single deployed sensor depth') for name in f if name in ['T','TREF','TC1','TC2','TC3','TC4']}
            if number=='3':
                for name in ['TC1','TC2','TC3','TC4']:
                    info=depths[(mission,probe,'TC1'+name[-1])]
                    values[name]=(f[name],name,info['depth_cm'],info['position_text'])
            else:
                delta=f['dT_corr'] if 'dT_corr' in f else f['dT']
                convention='provider dT_corr' if 'dT_corr' in f else 'provider clean dT (no correction field declared)'
                family='TG' if number in ['1','2'] else 'TR';bridge='1' if number in ['1','4'] else '2'
                a,b=[depths[(mission,probe,family+'1'+bridge+suffix)] for suffix in ['A','B']]
                upper,lower=bridge_values(f['T'],delta)
                values.update({'dT_selected':(delta,convention,np.nan,'lower minus upper'),
                    'upper_A':(upper,convention,a['depth_cm'],a['position_text']),
                    'lower_B':(lower,convention,b['depth_cm'],b['position_text']),
                    'gradient':(delta/((b['depth_cm']-a['depth_cm'])/100),convention,np.nan,'bridge separation only; not heat flux')})
                diff=delta-f.dT
                corrections.append({'file':path.name,'selected_field':convention,'strict_dated_records':int(strict.sum()),
                    'strict_corrected_different_records':int((strict&np.isfinite(diff)&diff.ne(0)).sum()),
                    'maximum_absolute_correction_K':float(diff.loc[strict].abs().max()),
                    'strict_negative_selected_difference_records':int((strict&delta.lt(0)).sum())})
            for name,(value,basis,depth,position) in values.items():
                sid=f'HFE_{mission}_{probe}f{number}_{name}'
                positive=name not in ['dT_selected','gradient']
                valid=strict&np.isfinite(value)
                if positive:valid&=value.gt(0)
                # Preserve the earlier T/TC/TREF daily contract for exact cross-checking.
                # New derived fields additionally require unambiguous native time.
                derived=name in ['dT_selected','gradient','upper_A','lower_B']
                if derived:valid&=clock
                masked=value.where(valid)
                fields.append(pd.DataFrame({'series_id':sid,'date':date,'value':np.asarray(masked),'derived':derived}))
                unit='K/m' if name=='gradient' else 'K'
                metadata[sid]={'series_id':sid,'mission':mission,'probe':probe,'file_number':number,'field':name,
                    'depth_cm':depth,'position':position,'unit':unit,'difference_basis':basis,
                    'quality':'strict flags==0, dated, finite; absolute temperature >0; new derived fields require unique clock',
                    'scope':'historical deployed Apollo sensor; not polar-site or modern equipment temperature'}
                stats.append({'file':path.name,'series_id':sid,'records':len(f),'strict_supported':int(valid.sum()),
                    'unit':unit,**acquired.describe(masked)})
        native=pd.concat(fields,ignore_index=True)
        daily=[];merged_clocks=[]
        for sid,g in native.groupby('series_id'):
            dated=g.date.notna();clock=acquired.unique_clock(g.date)
            merged_clocks.append({'series_id':sid,'undated_records':int((~dated).sum()),'ambiguous_or_missing_clock_records':int((~clock).sum())})
            if g.derived.any():g=g.assign(value=g.value.where(clock))
            daily.append(acquired.daily_rows(sid,g.loc[dated,'date'],g.loc[dated,'value']))
        daily=pd.concat(daily,ignore_index=True)
        calendar=calendar_summary(daily,subject['time_bins'],subject['two_year_anchor'])
        old=pd.read_csv(accepted_input(run,LOCAL/'data/processed/analysis'/subject['screening_run'],'daily_context.csv'))
        old=old.loc[old.series_id.str.startswith('HFE_')].copy();old['date']=pd.to_datetime(old.date,utc=True)
        checks=old[['series_id','date','daily_median','valid_samples']].merge(daily[['series_id','date','daily_median','valid_samples']],on=['series_id','date'],how='inner',suffixes=('_old','_new'),validate='one_to_one')
        checks['absolute_difference_K']=(checks.daily_median_old-checks.daily_median_new).abs()
        checks['support_changed']=(checks.daily_median_old.isna()!=checks.daily_median_new.isna())|(checks.valid_samples_old!=checks.valid_samples_new)
        if not sample and (len(checks)!=len(old) or checks.support_changed.any() or checks.absolute_difference_K.fillna(0).max()>1e-10):
            raise ValueError('HFE accepted daily support/values changed')
        pairs=[]
        for mission in ['a15','a17']:
            for probe in ['p1','p2']:
                left=f'HFE_{mission}_{probe}f1_upper_A';right=f'HFE_{mission}_{probe}f2_lower_B'
                a=daily.loc[daily.series_id.eq(left),['date','daily_median']];b=daily.loc[daily.series_id.eq(right),['date','daily_median']]
                pair=a.merge(b,on='date',suffixes=('_upper','_lower'),validate='one_to_one').dropna()
                for year,g in pair.groupby(pair.date.dt.year):
                    pairs.append({'mission':mission,'probe':probe,'year':year,'matched_valid_days':len(g),
                        'upper_depth_cm':metadata[left]['depth_cm'],'lower_depth_cm':metadata[right]['depth_cm'],
                        'upper_p95_p05_span_K':g.daily_median_upper.quantile(.95)-g.daily_median_upper.quantile(.05),
                        'lower_p95_p05_span_K':g.daily_median_lower.quantile(.95)-g.daily_median_lower.quantile(.05),
                        'median_lower_minus_upper_daily_K':(g.daily_median_lower-g.daily_median_upper).median(),
                        'interpretation':'same valid UTC dates but different sensor times; percentile span, not a qualified lunar-cycle amplitude or causal insulation coefficient'})
        tables={'daily_context':daily,'sensor_metadata':pd.DataFrame(metadata.values()),'native_field_statistics':pd.DataFrame(stats),
            'flags_by_file':pd.DataFrame(flags),'file_clock_lineage':pd.DataFrame(clocks),'merged_clock_support':pd.DataFrame(merged_clocks),
            'difference_corrections':pd.DataFrame(corrections),'calendar_context':calendar,
            'matched_January_December_years':fixed_month_comparison(daily),'matched_depth_years':pd.DataFrame(pairs),
            'crosscheck_Dar044':checks,'stage4_hfe_proposals':proposals()}
        for name,frame in tables.items():frame.to_csv(run.path(name+'.csv'),index=False)
        meta=tables['sensor_metadata'].set_index('series_id')
        for mission in ['a15','a17']:
            for probe in ['p1','p2']:
                fig,axes=plt.subplots(2,1,figsize=(12,6),sharex=True,layout='constrained')
                subset=calendar.loc[calendar.period_kind.eq('month')&calendar.series_id.str.startswith(f'HFE_{mission}_{probe}')&calendar.series_id.str.endswith(('upper_A','lower_B'))]
                for sid,g in subset.groupby('series_id'):
                    axes[0].plot(pd.to_datetime(g.period_start_utc),g.median_of_daily_values,label=f'{sid.split(probe)[-1]} {meta.loc[sid,"depth_cm"]:g} cm')
                    axes[1].plot(pd.to_datetime(g.period_start_utc),g.valid_day_fraction)
                axes[0].set(ylabel='Monthly median of daily K',title=f'{mission} {probe}: historical bridge elements; depths relative to deployed surface');axes[0].legend(ncol=4,fontsize=7)
                axes[1].set(ylabel='Valid-day fraction',ylim=(-.02,1.02));save_figure(run,fig,f'{mission}_{probe}_depth_months')
        fig,ax=plt.subplots(figsize=(11,5),layout='constrained')
        for sid,g in calendar.loc[calendar.period_kind.eq('month')&calendar.series_id.str.endswith('f1_dT_selected')].groupby('series_id'):
            ax.plot(pd.to_datetime(g.period_start_utc),g.median_of_daily_values,label=sid)
        ax.axhline(0,color='gray');ax.set(ylabel='Lower minus upper K',title='Signed selected/corrected differences; negative is not missing');ax.legend(fontsize=8)
        save_figure(run,fig,'signed_bridge_differences')
        findings={'subject':'subsurface_thermal','sample':sample,'analysed_files':len(selected),'native_table_records':int(tables['file_clock_lineage'].records.sum()),
            'undated_native_records':int(tables['file_clock_lineage'].undated_records.sum()),'series':daily.series_id.nunique(),
            'first_utc':str(daily.date.min()),'last_utc':str(daily.date.max()),'tables':{n:len(f) for n,f in tables.items()},
            'base_conclusion':'Depth, deployment, signed differences, archive sampling and missing/flagged periods matter. These historical nonpolar sensors cannot establish polar equipment temperature, heat flux, excavation benefit or a safe season.',
            'time_contract':subject['time_contract'],'pipeline_changed':False,'adopted_limits':False,'operational_status':'Unknown',
            'remaining':['Local polar depth-dependent response and thermal properties','Qualified component/installation demand and applicable envelope','Deployment-disturbance attribution, not inferred from calendar association','Other subjects and integrated Stage 4 synthesis']}
        run.path('findings.json').write_text(json.dumps(findings,indent=2));folder=run.directory
    print(json.dumps(findings,indent=2),flush=True);return folder,findings


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--sample',action='store_true')
    print(execute(parser.parse_args().sample)[0])
