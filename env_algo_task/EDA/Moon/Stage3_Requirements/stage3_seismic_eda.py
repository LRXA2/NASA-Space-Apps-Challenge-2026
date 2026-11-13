"""All selected Apollo S12 motion axes, mode/clock support and bounded response experiments."""
from pathlib import Path
import argparse
import datetime
import json
import re
import sys

sys.path[:0]=[str(Path(__file__).resolve().parents[2]/'shared'),str(Path(__file__).resolve().parents[3]),str(Path(__file__).resolve().parents[4])]
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from obspy import read,read_inventory
from scipy.signal import welch

import stage3_acquired_eda as acquired
from decision_eda import accepted_input
from environment_workflow import LocalRun
from environment_time import calendar_summary,fixed_month_comparison
from stage3_mission_eda import LOCAL,ROOT,save_figure

CONFIG=Path(__file__).with_name('stage3_subject_config.json')
NOTEBOOK='Moon/Stage3_Requirements/Dar_053_seismic_axes_response_time.ipynb'
PREFILTERS={'wider_diagnostic_band':[.02,.03,1.,1.5],'narrower_diagnostic_band':[.05,.08,.6,1.]}
WINDOW=8192


def archive_day(name):
    m=re.search(r'\.(197[34])\.(\d{3})\.',name)
    if m is None:raise ValueError('Expected selected 1973/1974 archive date')
    return pd.Timestamp(datetime.datetime.strptime(m[1]+m[2],'%Y%j'),tz='UTC')


def raw_statistics(values):
    v=np.asarray(values,float);good=np.isfinite(v)&(v!=-1);x=v[good]
    center=float(np.median(x)) if len(x) else np.nan;dev=x-center
    return {'samples':len(v),'valid_samples':int(good.sum()),'raw_median':center,
        'raw_min':float(x.min()) if len(x) else np.nan,'raw_max':float(x.max()) if len(x) else np.nan,
        'demeaned_rms_counts':float(np.sqrt(np.mean(dev**2))) if len(x) else np.nan,
        'p95_absolute_deviation_counts':float(np.quantile(np.abs(dev),.95)) if len(x) else np.nan,
        'maximum_absolute_deviation_counts':float(np.abs(dev).max()) if len(x) else np.nan}


def first_valid_window(values,length=WINDOW):
    """First full native gap-free segment; no interpolation, gap joining or event selection."""
    v=np.asarray(values,float)
    if length<2:raise ValueError('Window length must be at least two')
    bad=np.flatnonzero(~np.isfinite(v)|(v==-1));boundaries=np.r_[-1,bad,len(v)]
    spans=np.diff(boundaries)-1;eligible=np.flatnonzero(spans>=length)
    return int(boundaries[eligible[0]]+1) if len(eligible) else None


def response_cohort(entries):
    groups={}
    for e in entries:
        name=Path(e['relative_path']).name;parts=name.split('.')
        key=(parts[2],parts[3],archive_day(name).strftime('%Y-%m'))
        groups.setdefault(key,[]).append(e)
    return {e['url'] for es in groups.values() for e in [sorted(es,key=lambda x:x['url'])[0],sorted(es,key=lambda x:x['url'])[-1]]}


def channel_metadata(inv,trace):
    def channels(time):
        selected=inv.select(network=trace.stats.network,station=trace.stats.station,
            location=trace.stats.location,channel=trace.stats.channel,time=time)
        return [c for net in selected for sta in net for c in sta]
    first,last=channels(trace.stats.starttime),channels(trace.stats.endtime)
    if len(first)!=1 or len(last)!=1:return {'response_status':'Unknown_missing_or_ambiguous_metadata'}
    a,b=first[0],last[0]
    if a.response is None or b.response is None or a.response.instrument_sensitivity is None or b.response.instrument_sensitivity is None:
        return {'response_status':'Unknown_missing_sensitivity'}
    same=a.start_date==b.start_date and a.end_date==b.end_date
    sensitivity=a.response.instrument_sensitivity
    return {'response_status':'Available_same_epoch' if same else 'Unknown_epoch_crossing',
        'response_at_both_ends':True,'response_input_unit':sensitivity.input_units,'response_output_unit':sensitivity.output_units,
        'sensitivity_counts_per_input_unit':sensitivity.value,'sensitivity_frequency_Hz':sensitivity.frequency,
        'azimuth_deg':a.azimuth,'dip_deg':a.dip,'metadata_sampling_rate_Hz':a.sample_rate,
        'metadata_clock_drift_s_per_sample':a.clock_drift_in_seconds_per_sample,
        'response_epoch_start':str(a.start_date),'response_epoch_stop':str(a.end_date),
        'mode_comment':'; '.join(c.value for c in a.comments)}


def response_experiment(trace,inv,metadata):
    if metadata['response_status']!='Available_same_epoch':return [{'experiment_status':metadata['response_status'],'window_samples':WINDOW}],[]
    if metadata['response_input_unit']!='M' or metadata['response_output_unit']!='COUNTS':raise ValueError('Displacement/count response contract changed')
    if not np.isclose(trace.stats.sampling_rate,metadata['metadata_sampling_rate_Hz']):raise ValueError('Native/response sample rate mismatch')
    start=first_valid_window(trace.data)
    if start is None:return [{'experiment_status':'Unknown_no_gap_free_window','window_samples':WINDOW}],[]
    segment=trace.copy();segment.data=np.asarray(trace.data[start:start+WINDOW],float)
    segment.stats.starttime=trace.stats.starttime+start/trace.stats.sampling_rate
    f,p=welch(segment.data,fs=segment.stats.sampling_rate,nperseg=2048,detrend='constant')
    psd=[{'frequency_Hz':freq,'raw_counts_squared_per_Hz':power} for freq,power in zip(f,p)]
    rows=[]
    for name,prefilt in PREFILTERS.items():
        if not 0<prefilt[0]<prefilt[1]<prefilt[2]<prefilt[3]<segment.stats.sampling_rate/2:raise ValueError('Invalid exploratory prefilter/Nyquist contract')
        corrected=segment.copy();corrected.remove_response(inventory=inv,output='DISP',pre_filt=prefilt,water_level=60,
            zero_mean=True,taper=True,taper_fraction=.05)
        x=np.asarray(corrected.data,float)
        if len(x)!=WINDOW or not np.isfinite(x).all():raise ValueError('Response correction produced unsupported values')
        rows.append({'experiment_status':'Available_exploratory_only','filter_choice':name,'prefilter_Hz':json.dumps(prefilt),
            'water_level_dB':60,'taper_fraction':.05,'window_samples':WINDOW,'window_first_native_index':start,
            'window_start_nominal_utc':str(segment.stats.starttime),'window_stop_nominal_utc':str(segment.stats.endtime),
            'displacement_rms_m':float(np.sqrt(np.mean(x**2))),'maximum_absolute_displacement_m':float(np.max(np.abs(x))),
            'interpretation':'band-limited metadata-based displacement experiment; nominal archive clock, first gap-free window, NOT qualified ground-motion peak, event detection or structural demand'})
    return rows,psd


def proposals():
    definitions=[
        ('SE-G01','evidence_guard','Preserve axes, mode, response epoch and clocks','station/location/channel, response metadata, native missing code, ATT timing and gap support','E01 E07 E14','Raw counts are not acceleration; metadata availability or an inverse-response experiment alone does not qualify motion timing/response'),
        ('SE-G02','evidence_guard','Spectral/response experiments are bounded and selection-specific','actual gap-free window, response units, prefilter/taper/water level and nominal cadence','E01 E07 E13','First/last archive days and first gap-free segments are not event peaks/censuses; filter sensitivity is not a validated structural response'),
        ('SE-H01','conditional_hard_constraint','Applicable structural/vibration/impact tolerance','local design hazard, event attribution/uncertainty, ground-to-structure response, mission duration and qualified tolerance','E07 E13','Failed if qualified applicable demand exceeds mandatory capability; Passed only with sufficient evidence; otherwise Unknown'),
        ('SE-S01','conditional_soft_preference','Lower qualified vibration/isolation operating burden','all mandatory conditions Passed, comparable local mission/activity and validated isolation/operations cost','E07 E13','No lowest raw RMS, quiet archive window or sparse event count is a universal safest-site preference'),
        ('SE-G03','evidence_guard','Natural versus operational events and geographic transfer','catalog provenance, independent event identity, crew/rover/deliberate-source context and location/recurrence model','E07 E14','Related catalogs are not independent populations; S12 historical motion is not south-polar recurrence or absence of natural hazards')]
    return pd.DataFrame([{'id':id,'classification':kind,'title':title,'required_inputs':inputs,'existing_rule_crosswalk':old,
        'decision_logic':logic,'quantity':'raw motion counts; exploratory band-limited displacement; qualified local structural response if available',
        'unit':'counts; counts2/Hz; m; response-specific tolerance units','applicability':'historical S12 1973-1974, actual axis/mode; not a selected south-polar footprint',
        'source':'D14 PDS waveform/StationXML metadata; accepted Dar007 catalog and Dar044 timing/raw checks; Apollo 16 operation-source evidence',
        'evidence':'raw_trace_support.csv; response_metadata.csv; response_experiments.csv; archived_ATT_context.csv; calendar_context.csv; crosscheck_Dar044.csv',
        'limit_value':np.nan,'limit_state':'not_adopted','preference_weight':np.nan,'current_outcome':'Unknown',
        'status':'Stage 4 proposal only; not consumed by pipeline'} for id,kind,title,inputs,old,logic in definitions])


def execute(sample=False):
    subject=json.loads(CONFIG.read_text());config=json.loads(CONFIG.with_name(subject['acquisition_config']).read_text())
    with LocalRun(ROOT,'analysis/subject_seismic'+('_sample' if sample else ''),subject,NOTEBOOK) as run:
        for p in [CONFIG,Path(__file__),acquired.CONFIG,Path(acquired.__file__),LOCAL/'EDA/shared/environment_time.py']:run.input(p)
        run.record['packages'].update({'obspy':sys.modules['obspy'].__version__,'scipy':sys.modules['scipy'].__version__})
        sources=acquired.catalog(run,config)
        entries=[e for e in acquired.science(sources,'D14_PSE') if any('.'+c+'.' in e['url'] for c in ['mh1','mh2','mhz'])]
        selected_response=response_cohort(entries)
        if sample:
            groups={}
            for e in entries:
                name=Path(e['relative_path']).name;parts=name.split('.');groups.setdefault((parts[2],parts[3]),[]).append(e)
            entries=[e for group in groups.values() for e in acquired.bounded(group,True)]
        response=acquired.pin(run,config,next(e for e in sources['D14_PSE'] if e['url'].endswith('.sxml')))
        inv=read_inventory(str(response),format='STATIONXML');raw=[];meta=[];experiments=[];psds=[];daily=[]
        for index,e in enumerate(entries):
            path=acquired.pin(run,config,e);acquired.paired_path(run,config,sources,e)
            for trace in read(str(path),format='MSEED'):
                if trace.stats.station!='S12' or trace.stats.channel not in ['MH1','MH2','MHZ']:raise ValueError('Unexpected station/axis')
                day=archive_day(path.name);stats=raw_statistics(trace.data);m=channel_metadata(inv,trace)
                identity={'file':path.name,'trace_id':trace.id,'date':day,'axis':trace.stats.channel,'location_mode_code':trace.stats.location}
                raw.append({**identity,'start':str(trace.stats.starttime),'stop':str(trace.stats.endtime),'sampling_rate_Hz':trace.stats.sampling_rate,
                    **stats,'response_at_both_ends':m.get('response_at_both_ends',False),
                    'scope':'all valid samples in dated archive file; nominal timing, no event attribution or qualified acceleration'})
                meta.append({**identity,**m})
                sid='PSE_'+trace.id.replace('.','_')+'_raw_daily_RMS'
                daily.append({'series_id':sid,'date':day,'daily_median':stats['demeaned_rms_counts'],
                    'daily_max':stats['maximum_absolute_deviation_counts'],'daily_p95':stats['p95_absolute_deviation_counts'],
                    'recorded_samples':stats['samples'],'valid_samples':stats['valid_samples'],'valid_seconds':np.nan,
                    'daily_value_meaning':'daily whole-file median-centred RMS counts; NOT a native median or physical displacement'})
                if e['url'] in selected_response:
                    rows,spectrum=response_experiment(trace,inv,m)
                    experiments.extend({**identity,**r} for r in rows);psds.extend({**identity,**r} for r in spectrum)
            if index%200==0:print('Motion files read:',index+1,flush=True)
        raw=pd.DataFrame(raw);daily=pd.DataFrame(daily)
        if daily.duplicated(['series_id','date']).any():raise ValueError('Repeated axis/mode/day requires native reconciliation')
        old=pd.read_csv(accepted_input(run,LOCAL/'data/processed/analysis'/subject['screening_run'],'seismic_daily_support.csv'))
        timing=old.loc[old.quantity.eq('timing')].copy()
        timing['date']=pd.to_datetime(timing.start,utc=True).dt.floor('D')
        timing_daily=timing.assign(series_id='PSE_ATT_native_record_support_fraction',daily_median=timing.valid_samples/timing.samples,
            daily_max=timing.valid_samples/timing.samples,recorded_samples=timing.samples,valid_seconds=np.nan)
        combined=pd.concat([daily,timing_daily[['series_id','date','daily_median','daily_max','recorded_samples','valid_samples','valid_seconds']]],ignore_index=True)
        calendar=calendar_summary(combined,subject['time_bins'],subject['two_year_anchor'])
        vertical=old.loc[old.quantity.eq('MHZ_raw')]
        checks=vertical.merge(raw,on=['file','trace_id','start','stop'],suffixes=('_old','_new'),validate='one_to_one',how='inner')
        check_rows=[]
        for col in ['samples','valid_samples','sampling_rate_Hz','raw_median','demeaned_rms_counts','p95_absolute_deviation_counts']:
            a,b=checks[col+'_old'],checks[col+'_new'];valid=a.notna()&b.notna()
            check_rows.append({'quantity':col,'old_rows':len(vertical),'matched_rows':len(checks),
                'support_changed_rows':int((a.isna()!=b.isna()).sum()),'maximum_absolute_difference':float((a[valid]-b[valid]).abs().max()) if valid.any() else np.nan,
                'scope':'sample' if sample else 'all prior vertical traces must replay identically; other axes/response experiments are additions'})
        cross=pd.DataFrame(check_rows)
        if not sample and (len(checks)!=len(vertical) or cross.support_changed_rows.gt(0).any() or cross.maximum_absolute_difference.fillna(0).max()>1e-9):raise ValueError('Vertical waveform baseline changed')
        tables={'raw_trace_support':raw,'response_metadata':pd.DataFrame(meta),'response_experiments':pd.DataFrame(experiments),
            'selected_window_raw_PSD':pd.DataFrame(psds),'daily_context':daily,'archived_ATT_context':timing,
            'calendar_context':calendar,'matched_January_December_years':fixed_month_comparison(combined),
            'crosscheck_Dar044':cross,'stage4_seismic_proposals':proposals()}
        for name,frame in tables.items():frame.to_csv(run.path(name+'.csv'),index=False)
        fig,axes=plt.subplots(2,1,figsize=(12,7),sharex=True,layout='constrained')
        for sid,g in calendar.loc[calendar.period_kind.eq('month')&calendar.series_id.str.endswith('_raw_daily_RMS')].groupby('series_id'):
            axes[0].plot(pd.to_datetime(g.period_start_utc),g.median_of_daily_values,label=sid)
            axes[1].plot(pd.to_datetime(g.period_start_utc),g.valid_day_fraction)
        axes[0].set(ylabel='Median daily RMS counts',title='Axes/modes separate; raw variation is not ground acceleration or event rate');axes[0].legend(fontsize=6)
        axes[1].set(ylabel='Supported-date fraction',ylim=(-.02,1.02));save_figure(run,fig,'raw_axes_calendar')
        exp=tables['response_experiments']
        fig,ax=plt.subplots(figsize=(12,5),layout='constrained')
        if 'filter_choice' in exp:
            for (axis,mode,choice),g in exp.loc[exp.experiment_status.eq('Available_exploratory_only')].groupby(['axis','location_mode_code','filter_choice']):
                ax.scatter(pd.to_datetime(g.date),g.displacement_rms_m,s=6,label=f'{axis}/{mode}/{choice}')
        else:ax.text(.5,.5,'No supported response experiment: Unknown',transform=ax.transAxes,ha='center')
        ax.set(ylabel='Exploratory band-limited RMS m',yscale='log',title='First gap-free segments, filter sensitivity and metadata response; NOT physical event peaks');ax.legend(fontsize=5,ncol=3)
        save_figure(run,fig,'bounded_response_experiments')
        findings={'subject':'seismic','sample':sample,'analysed_motion_files':len(entries),'motion_traces':len(raw),
            'native_motion_samples':int(raw.samples.sum()),'valid_native_motion_samples':int(raw.valid_samples.sum()),
            'motion_axes':sorted(raw.axis.unique()),'archived_ATT_traces_reused':len(timing),
            'response_experiment_rows':len(exp),'tables':{name:len(f) for name,f in tables.items()},'time_contract':subject['time_contract'],
            'base_conclusion':'Three-axis/mode/clock support and bounded inverse-response experiments improve historical waveform interpretation. They do not establish independent natural events, qualified local peak ground motion, south-polar recurrence or structural safety.',
            'full_source_scope':'all selected three-axis motion files; reused complete accepted ATT diagnostics; first/last archive day per mode/axis/month for exploratory 8192-sample response windows' if not sample else 'first/last files per axis/location mode; bounded response experiments',
            'pipeline_changed':False,'adopted_limits':False,'operational_status':'Unknown',
            'remaining':['ATT-based qualified timing/response and event attribution','Local hazard/recurrence and ground-to-structure model','Applicable mission configuration and tolerances','Other subjects and integrated Stage 4 synthesis']}
        run.path('findings.json').write_text(json.dumps(findings,indent=2));folder=run.directory
    print(json.dumps(findings,indent=2),flush=True);return folder,findings


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--sample',action='store_true')
    print(execute(parser.parse_args().sample)[0])
