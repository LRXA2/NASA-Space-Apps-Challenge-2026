"""Full selected LEND native spectra, state/geometry/time support and resource-inference limits."""
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
from environment_time import calendar_summary,fixed_month_comparison,longest_true
from stage3_mission_eda import LOCAL,ROOT,save_figure

CONFIG=Path(__file__).with_name('stage3_subject_config.json')
NOTEBOOK='Moon/Stage3_Requirements/Dar_052_neutron_spectra_state_time.ipynb'


def raw_rate(counts,collection_seconds,supported):
    c,t=np.asarray(counts,float),np.asarray(collection_seconds,float)
    good=np.asarray(supported,bool)&np.isfinite(c)&np.isfinite(t)&(t>0)
    return np.divide(c,t,out=np.full(c.shape,np.nan),where=good)


def daily_record(sid,day,values,recorded):
    x=np.asarray(values,float);valid=np.isfinite(x);x=x[valid]
    return {'series_id':sid,'date':day,'daily_median':float(np.median(x)) if len(x) else np.nan,
        'daily_max':float(x.max()) if len(x) else np.nan,'daily_p95':float(np.quantile(x,.95)) if len(x) else np.nan,
        'recorded_samples':recorded,'valid_samples':len(x),'valid_seconds':np.nan}


def zero_state_summary(daily):
    rows=[]
    for sid,g in daily.groupby('series_id'):
        g=g.sort_values('date');dates=pd.date_range(g.date.min(),g.date.max(),freq='D')
        # A zero maximum means every supported native rate was zero, not merely median==0.
        zeros=g.daily_max.eq(0)&g.valid_samples.gt(0)
        mask=dates.isin(g.loc[zeros,'date'])
        rows.append({'series_id':sid,'recorded_dates':len(g),'supported_dates':int(g.daily_max.notna().sum()),
            'all_supported_values_zero_dates':int(zeros.sum()),'longest_consecutive_observed_zero_dates':longest_true(mask),
            'interpretation':'raw channel state diagnostic; missing dates break runs; zero is not absence of neutrons, safe dose or detected ice',
            'science_response_qualified':False})
    return pd.DataFrame(rows)


def proposals():
    definitions=[
        ('NE-G01','evidence_guard','Native spectra/state are not calibrated flux or resources','detector/channel, instrument activity, background/dead-time/response and geometry','E01 E04 E13','All-zero raw channels and spectral-bin sums do not establish no neutrons, safe radiation or water abundance'),
        ('NE-G02','evidence_guard','Preserve raw collection-register and time support','native collection seconds, unique nominal-day clocks, geometry/parameter flags and gaps','E01 E14','Counts per reported collection second are raw diagnostics, not qualified flux/dose or elapsed science-good exposure'),
        ('NE-G03','evidence_guard','Units and detector footprint before altitude/site inference','validated field units, detector response footprint and actual site association','E01 E13','Do not silently interpret the XML SCALT unit 8 as km; ground-track south-of-80 selection is not candidate localization'),
        ('NE-H01','conditional_hard_constraint','Applicable neutron-radiation protection','local neutron field/transport, shielding, exposure duration, qualified response and adopted applicable limit','E04 E10 E13','Failed if qualified applicable demand exceeds a mandatory envelope; Passed only with sufficient evidence; otherwise Unknown'),
        ('NE-H02','conditional_hard_constraint','Resource capacity when the mission actually depends on extraction','corroborated abundance/accessibility, extraction yield/power/consumables and required mission supply','E06 E13','Only mandatory for a declared resource-dependent mission; stability or raw neutron deficit alone cannot pass supply adequacy; otherwise this requirement is not assumed applicable'),
        ('NE-S01','conditional_soft_preference','Lower qualified resource/protection operational burden','mandatory conditions Passed, applicable extraction/protection response and comparable mission','E04 E13','Do not reward raw low neutron counts or model stability depth as recoverable water or globally safer terrain')]
    return pd.DataFrame([{'id':id,'classification':kind,'title':title,'required_inputs':inputs,'existing_rule_crosswalk':old,
        'decision_logic':logic,'quantity':'raw detector spectra/rates; qualified local radiation or resource response if established',
        'unit':'counts/collection; counts per reported collection second; response-specific dose/yield units',
        'applicability':'LRO orbital history and broad ground-track selection; no validated candidate footprint',
        'source':'D29 PDS4 binary fields; PDS3 archive identity; accepted Dar044 raw-spectrum cohort and E04/E13 boundaries',
        'evidence':'daily_context.csv; file_geometry_state.csv; zero_channel_summary.csv; monthly_spectral_bins.csv; unit_holds.csv; crosscheck_Dar044.csv',
        'limit_value':np.nan,'limit_state':'not_adopted','preference_weight':np.nan,'current_outcome':'Unknown',
        'status':'Stage 4 proposal only; not consumed by pipeline'} for id,kind,title,inputs,old,logic in definitions])


def execute(sample=False):
    subject=json.loads(CONFIG.read_text());config=json.loads(CONFIG.with_name(subject['acquisition_config']).read_text())
    with LocalRun(ROOT,'analysis/subject_neutrons'+('_sample' if sample else ''),subject,NOTEBOOK) as run:
        for p in [CONFIG,Path(__file__),acquired.CONFIG,Path(acquired.__file__),LOCAL/'EDA/shared/environment_time.py']:run.input(p)
        sources=acquired.catalog(run,config);entries=acquired.bounded(acquired.science(sources,'D29'),sample)
        old_urls={e['url'] for e in acquired.monthly_edges(acquired.science(sources,'D29'))}
        old_channels=['SETN_SPECTRUM','CSETN1_SPECTRUM','CSETN2_SPECTRUM','CSETN3_SPECTRUM','CSETN4_SPECTRUM']
        daily=[];diagnostics=[];raw_summaries=[];old_replay=[];hist={};metadata=[];unit_holds=[];geometry=[];total_records=0
        for index,e in enumerate(entries):
            path=acquired.pin(run,config,e);label=acquired.paired_path(run,config,sources,e)
            # Keep the paired original archive identity too; its external FMT is not silently substituted.
            acquired.paired_path(run,config,sources,e,'.lbl')
            xml=ET.parse(label).getroot();fields=xml.findall('.//{*}Field_Binary');units={f.findtext('{*}name'):f.findtext('{*}unit') for f in fields}
            if units['LATITUDE']!='degree' or units['LONGITUDE']!='degree' or units['DATA_COLLECTION_TIME']!='s':raise ValueError('LEND geometry/time units changed')
            if units['SCALT'] not in ['km','kilometer','Kilometers']:
                unit_holds.append({'file':path.name,'field':'SCALT','native_unit':units['SCALT'],
                    'hold':'unresolved unit; not used as km or silently corrected; position-vector radius is separately named if reported'})
            for axis in ['X','Y','Z']:
                if units['SCPOS_MOON_'+axis]!='km':raise ValueError('LEND native position units changed')
            if index==0:
                metadata=[{'field':f.findtext('{*}name'),'unit':f.findtext('{*}unit'),'description':' '.join((f.findtext('{*}description') or '').split())} for f in fields]
            dt,offset,n=acquired.binary_layout(label)
            if path.stat().st_size!=offset+n*dt.itemsize:raise ValueError('LEND binary byte count changed')
            f=np.memmap(path,mode='r',dtype=dt,offset=offset,shape=(n,))
            text=np.char.strip(np.char.decode(f['UTC'],'ascii'))
            dates=pd.DatetimeIndex(pd.to_datetime(text,utc=True,errors='coerce'))
            keep=acquired.nominal_day(dates,path.name);clock=acquired.unique_clock(dates)
            geometry_good=(f['POINTING']==1)&(f['INTERSECTING']==1)&(f['DATA_COLLECTION_TIME']>0)&(f['PARAMETERS_CHANGED']==0)
            geometry_good&=np.isfinite(f['LATITUDE'])&(np.abs(f['LATITUDE'])<=90)&np.isfinite(f['LONGITUDE'])
            supported=geometry_good&keep&clock
            collection=np.asarray(f['DATA_COLLECTION_TIME'],float)
            day=pd.to_datetime(path.stem.rsplit('_',1)[1],format='%Y%m%d',utc=True)
            regions={'all_track':np.ones(n,bool),'south_of_80S':f['LATITUDE']<=-80}
            radius=np.sqrt(sum(np.asarray(f['SCPOS_MOON_'+axis],float)**2 for axis in ['X','Y','Z']))
            diagnostics.append({'file':path.name,'date':day,'records':n,'nominal_dated_records':int(keep.sum()),
                'geometry_parameter_supported':int(geometry_good.sum()),'clock_geometry_nominal_supported':int(supported.sum()),
                'ambiguous_or_missing_clock_records':int((~clock).sum()),'outside_or_missing_nominal_clock_records':int((~keep).sum()),
                'pointing_missing':int((f['POINTING']!=1).sum()),'not_intersecting':int((f['INTERSECTING']!=1).sum()),
                'parameter_changed_records':int((f['PARAMETERS_CHANGED']!=0).sum()),'nonpositive_collection_records':int((collection<=0).sum()),
                'maximum_native_collection_seconds':collection.max(),'supported_collection_register_seconds_sum':collection[supported].sum(),
                'scope':'reported register/time/geometry support, NOT detector-response qualification or guaranteed nonoverlapping live exposure'})
            channels=[name for name in dt.names if name.endswith('_SPECTRUM')]
            if len(channels)!=11:raise ValueError('LEND channel set changed')
            for region,within in regions.items():
                mask=supported&within;oldmask=geometry_good&within
                geometry.append({'file':path.name,'date':day,'region':region,'recorded_region_frames':int(within.sum()),'supported_region_frames':int(mask.sum()),
                    'median_lunar_fixed_position_radius_km':float(np.median(radius[mask])) if mask.any() else np.nan,
                    'latitude_min_deg':float(f['LATITUDE'][mask].min()) if mask.any() else np.nan,
                    'latitude_max_deg':float(f['LATITUDE'][mask].max()) if mask.any() else np.nan,
                    'source_collection_seconds_sum':collection[mask].sum(),'note':'radius is not SCALT; south ground-track selection is not detector footprint or candidate localization'})
                for name in channels:
                    if units[name]!='counts':raise ValueError('LEND native spectral unit changed')
                    spectrum=f[name];counts=np.asarray(spectrum,dtype='uint64').sum(axis=1)
                    if spectrum.dtype!=np.dtype('>u2'):raise ValueError('LEND spectral word size changed; revisit ceiling diagnostic')
                    rate=raw_rate(counts,collection,mask)
                    sid='LEND_raw_rate_'+region+'_'+name
                    daily.append(daily_record(sid,day,rate[within],int(within.sum())))
                    raw_summaries.append({'file':path.name,'date':day,'region':region,'channel':name,'records':n,
                        'supported_frames':int(mask.sum()),'raw_counts_sum':int(counts[mask].sum()),
                        'nonzero_supported_frames':int((counts[mask]>0).sum()),'u16_ceiling_bin_values':int((spectrum[mask]==65535).sum()),
                        'source_collection_seconds_sum':collection[mask].sum(),**acquired.describe(counts[mask]),
                        'unit':'sum native spectral-bin counts per collection; no background/dead-time/response correction'})
                    key=(day.strftime('%Y-%m'),region,name)
                    sums=np.asarray(spectrum[mask],dtype='uint64').sum(axis=0)
                    if key in hist:hist[key]+=sums
                    else:hist[key]=sums
                    if e['url'] in old_urls and name in old_channels:
                        old_replay.append({'file':path.name,'region':region,'channel':name,
                            'geometry_parameter_supported':int(oldmask.sum()),**acquired.describe(counts[oldmask]),
                            'nonzero_supported_records':int((counts[oldmask]>0).sum())})
            total_records+=n
            del f
            if index%100==0:print('LEND files read:',index+1,'native frames:',total_records,flush=True)
        daily=pd.DataFrame(daily)
        if daily.duplicated(['series_id','date']).any():raise ValueError('More than one LEND file per series/day; native reconciliation required')
        calendar=calendar_summary(daily,subject['time_bins'],subject['two_year_anchor'])
        old=pd.read_csv(accepted_input(run,LOCAL/'data/processed/analysis'/subject['screening_run'],'lend_sampled_spectra.csv'))
        replay=pd.DataFrame(old_replay)
        compare=old.merge(replay,on=['file','region','channel'],suffixes=('_old','_replayed'),how='inner',validate='one_to_one')
        check_rows=[]
        for col in ['geometry_parameter_supported','valid','min','median','p95','max','nonzero_supported_records']:
            a,b=compare[col+'_old'],compare[col+'_replayed'];valid=a.notna()&b.notna()
            check_rows.append({'quantity':col,'previous_rows':len(old),'matched_rows':len(compare),
                'support_changed_rows':int((a.isna()!=b.isna()).sum()),'maximum_absolute_difference':float((a[valid]-b[valid]).abs().max()) if valid.any() else np.nan,
                'scope':'sample only' if sample else 'original 74-file/five-channel geometry-only contract replayed; new clock screening and six extra channels are separately named'})
        checks=pd.DataFrame(check_rows)
        if not sample and (len(compare)!=len(old) or checks.support_changed_rows.gt(0).any() or checks.maximum_absolute_difference.fillna(0).max()>1e-10):raise ValueError('LEND old sparse spectral summaries changed')
        spectral_rows=[{'month':month,'region':region,'channel':name,'native_bin_index':i,'raw_bin_counts_sum':int(value),
            'scope':'native bin index only; no calibrated energy/efficiency or ice abundance'} for (month,region,name),values in hist.items() for i,value in enumerate(values)]
        tables={'daily_context':daily,'file_geometry_state':pd.DataFrame(diagnostics),'track_geometry':pd.DataFrame(geometry),
            'raw_channel_statistics':pd.DataFrame(raw_summaries),'monthly_spectral_bins':pd.DataFrame(spectral_rows),
            'zero_channel_summary':zero_state_summary(daily),'calendar_context':calendar,
            'matched_June_October_years':fixed_month_comparison(daily,6,10),'unit_holds':pd.DataFrame(unit_holds,columns=['file','field','native_unit','hold']),
            'field_metadata':pd.DataFrame(metadata),'crosscheck_Dar044':checks,'stage4_neutron_proposals':proposals()}
        for name,frame in tables.items():frame.to_csv(run.path(name+'.csv'),index=False)
        for region in regions:
            fig,axes=plt.subplots(2,1,figsize=(12,7),sharex=True,layout='constrained')
            g=calendar.loc[calendar.period_kind.eq('month')&calendar.series_id.str.startswith('LEND_raw_rate_'+region+'_')]
            for sid,part in g.groupby('series_id'):
                axes[0].plot(pd.to_datetime(part.period_start_utc),part.median_of_daily_values,label=sid.split(region+'_')[1])
                axes[1].plot(pd.to_datetime(part.period_start_utc),part.valid_day_fraction)
            axes[0].set(ylabel='Counts/reported collection second',yscale='symlog',title=region+': raw channel diagnostics, NOT neutron flux/dose/water');axes[0].legend(ncol=4,fontsize=6)
            axes[1].set(ylabel='Supported-day fraction',ylim=(-.02,1.02));save_figure(run,fig,region+'_channel_context')
        findings={'subject':'neutrons_resources','sample':sample,'analysed_files':len(entries),'native_frames':total_records,
            'channels':channels,'daily_rows':len(daily),'first_utc':str(daily.date.min()),'last_utc':str(daily.date.max()),
            'tables':{n:len(f) for n,f in tables.items()},'time_contract':subject['time_contract'],
            'base_conclusion':'Full native channel/time coverage resolves raw spectral, zero-state and geometry/clock support, not calibrated flux, local dose or recoverable resources. The SCALT unit hold is explicit and not silently corrected.',
            'full_source_scope':'all selected LEND days and all 11 spectral channels' if not sample else 'first/last selected LEND days, all channels',
            'pipeline_changed':False,'adopted_limits':False,'operational_status':'Unknown',
            'remaining':['Detector activity/background/dead-time/response and calibrated footprint','SCALT unit authority and geometry applicability','Local neutron transport/protection or corroborated extraction response','Other subjects and integrated Stage 4 synthesis']}
        run.path('findings.json').write_text(json.dumps(findings,indent=2));folder=run.directory
    print(json.dumps(findings,indent=2),flush=True);return folder,findings


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--sample',action='store_true')
    print(execute(parser.parse_args().sample)[0])
