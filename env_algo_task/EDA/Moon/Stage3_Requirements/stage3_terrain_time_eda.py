"""Two full years of sampled reference-point Sun/Earth geometry and terrain/source consistency."""
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
import spiceypy as spice

import stage3_expanded_eda as horizon
from decision_eda import accepted_input
from environment_workflow import LocalRun
from environment_time import calendar_summary,bucket_bounds
from research_p1_readers import pilot_files,pin_source
from stage3_mission_eda import LOCAL,ROOT,save_figure

CONFIG=Path(__file__).with_name('stage3_terrain_time_config.json')
NOTEBOOK='Moon/Stage3_Requirements/Dar_054_terrain_illumination_multiyear.ipynb'


def read_context(run,folder,name,**kwargs):
    return pd.read_csv(accepted_input(run,LOCAL/'data/processed/analysis'/folder,name),**kwargs)


def period_geometry(frame,kinds,cadence_minutes,anchor=2000):
    """Native sample fractions and observed run spans, recomputed for every calendar window."""
    times=pd.DatetimeIndex(frame.utc);step=pd.Timedelta(minutes=cadence_minutes)
    if len(times)<2 or times.hasnans or times.has_duplicates or not times.is_monotonic_increasing or not np.all(np.diff(times.asi8)==step.value):
        raise ValueError('Require a regular known UTC model-sampling grid')
    if frame.center_blocked_by_sampled_terrain.isna().any():raise ValueError('Unknown numerical geometry cannot become clear')
    rows=[];first,last=times[0],times[-1]+step
    for kind in kinds:
        start,_,_=bucket_bounds(first,kind,anchor)
        while start<last:
            start,stop,label=bucket_bounds(start,kind,anchor)
            part=frame.loc[frame.utc.ge(start)&frame.utc.lt(stop)]
            runs=horizon.sampled_runs(part.utc,part.center_blocked_by_sampled_terrain) if len(part)>=2 else []
            if len(part)==1 and bool(part.center_blocked_by_sampled_terrain.iloc[0]):
                runs=[{'sample_span_hours':0.,'left_censored':True,'right_censored':True}]
            rows.append({'period_kind':kind,'period':label,'period_start_utc':start,'period_stop_exclusive_utc':stop,
                'expected_calendar_samples':int((stop-start)/step),'recorded_samples':len(part),
                'partial_source_span_period':start<first or stop>last,
                'blocked_samples':int(part.center_blocked_by_sampled_terrain.sum()),
                'sampled_blocked_fraction':part.center_blocked_by_sampled_terrain.mean(),
                'minimum_sampled_clearance_deg':part.clearance_deg.min(),'maximum_sampled_clearance_deg':part.clearance_deg.max(),
                'observed_blocked_run_count':len(runs),'longest_observed_blocked_sample_span_hours':max((r['sample_span_hours'] for r in runs),default=0.) if len(part) else np.nan,
                'left_censored_runs':sum(r['left_censored'] for r in runs),'right_censored_runs':sum(r['right_censored'] for r in runs),
                'meaning':'calendar sample context; observed first-to-last blocked-sample span, NOT guaranteed continuous darkness, power endurance or working-link outage'})
            start=stop
    return pd.DataFrame(rows)


def proposals():
    definitions=[
        ('TE-G01','evidence_guard','Footprint, terrain uncertainty and reference configuration','actual footprint, native DEM/resolution/error, observer height, horizon radius/sampling and source support','E01 E05 E13','ROI-center geometry and un-clipped region summaries cannot replace component footprints or certify a clear horizon'),
        ('TE-G02','evidence_guard','Visibility means do not determine uninterrupted supply','chronological forcing, cadence/gaps, solar disk/orientation, actual generation/loads/storage or contact requirements','E05 E14','Keep observed run spans/censoring; equal mean sunlight can coexist with different blocking spans; no inferred continuous power from averages'),
        ('TE-H01','conditional_hard_constraint','Essential power and storage across the mission period','applicable generation, loads, usable storage/efficiency/reserves, duration and qualified local forcing','E05 E06','Failed if qualified available power/energy/reserves cannot meet a mandatory demand; Passed only with sufficient applicable evidence; otherwise Unknown'),
        ('TE-H02','conditional_hard_constraint','Required communication service and outages','mission contact schedule, Earth/relay/station geometry, antenna/link budget and required outage limit','E05 E06','Failed if qualified contact/service fails applicable mandatory requirements; Passed only with sufficient evidence; otherwise Unknown'),
        ('TE-H03','conditional_hard_constraint','Applicable mobility/foundation/load envelope','actual activity/vehicle/foundation, local footprint/soil/terrain uncertainty and qualified capability','E01 E13','Only applicable for declared operations; slope/imagery alone cannot pass strength or mobility; applicable capability exceedance is Failed, missing response/limits Unknown'),
        ('TE-S01','conditional_soft_preference','Lower qualified power/storage or communications operating burden','mandatory conditions Passed, comparable mission, validated response-based energy/storage/contact burden','E05 E13','Do not substitute a lowest blocking fraction or shortest sampled span for a qualified operational margin'),
        ('TE-G03','evidence_guard','Remote imagery/radar and static maps retain their meanings','native scale/offset/pixel classes, resolution, acquisition epoch and physical quantity','E01 E13','Missing imagery is not permanent shadow; signed radar samples are not invalid merely for being negative; brightness/backscatter is not ice abundance or bearing strength'),
        ('TE-G04','evidence_guard','Calendar and cadence are not physical seasonal forecasts','actual UTC window, model/kernel identities, native cadence, source periods and temporal convergence','E05 E14 E15','Two historical model years do not validate repeating lunar seasons or future safe arrival windows; retain sub-cadence/unmodelled-blocker limits')]
    return pd.DataFrame([{'id':id,'classification':kind,'title':title,'required_inputs':inputs,'existing_rule_crosswalk':old,
        'decision_logic':logic,'quantity':'sampled Sun/Earth-center geometry; native terrain/image support; qualified mission response if established',
        'unit':'degree; fraction; observed sample-span hours; source-specific terrain/image units; response-specific W/Wh/link/load units',
        'applicability':'existing seven reference points, heights/radii and historical 2020-2021 model windows, not candidate operating footprints',
        'source':'accepted Dar020/026/027/032/036/042 source/model contracts; pinned DE421/MOON_ME kernels',
        'evidence':'geometry_periods.csv; observed_blocked_runs.csv; cadence_sensitivity.csv; crosscheck_Dar036.csv; static_vs_point_context.csv; source_support_context.csv',
        'limit_value':np.nan,'limit_state':'not_adopted','preference_weight':np.nan,'current_outcome':'Unknown',
        'status':'Stage 4 proposal only; not consumed by pipeline'} for id,kind,title,inputs,old,logic in definitions])


def execute(sample=False):
    config=json.loads(CONFIG.read_text());subject=json.loads(CONFIG.with_name(config['subject_config']).read_text())
    if config['body']!='Moon' or config['schema']!=1:raise ValueError('Moon scenario schema required')
    with LocalRun(ROOT,'analysis/subject_terrain_time'+('_sample' if sample else ''),config,NOTEBOOK) as run:
        for p in [CONFIG,Path(__file__),CONFIG.with_name(config['subject_config']),Path(horizon.__file__),LOCAL/'EDA/shared/environment_time.py']:run.input(p)
        folder=LOCAL/'data/processed/analysis'/config['terrain_source_run']
        provenance=json.loads(accepted_input(run,folder,'findings.json').with_name('provenance.json').read_text())
        source_config=provenance['config'];profiles=read_context(run,config['terrain_source_run'],'sampled_horizon_profiles.csv')
        observers=read_context(run,config['terrain_source_run'],'reference_observers.csv')
        previous=read_context(run,config['terrain_source_run'],'terrain_target_center_geometry.csv.gz');previous['utc']=pd.to_datetime(previous.utc,utc=True)
        native=read_context(run,config['native_support_run'],'terrain_policy_consistency.csv')
        mismatch=[c for c in native if c.endswith('mismatches')]
        if native[mismatch].to_numpy().sum()!=0:raise ValueError('Existing native terrain policy/crop disagreement needs review')
        support=[]
        for family,key in [('native_terrain','native_support_run'),('ShadowCam','shadowcam_run'),('MiniRF','minirf_run')]:
            name='terrain_environment_support.csv' if family=='native_terrain' else 'regional_source_support.csv'
            f=read_context(run,config[key],name);f['source_family']=family
            f['scope']='accepted static/image context; not dated power/contact, ice detection or soil capacity';support.append(f)
        science=read_context(run,subject['science_profile_run'],'candidate_science_profiles.csv')
        start=pd.Timestamp(config['start_utc']);stop=pd.Timestamp(config['stop_exclusive_utc'])
        if sample:
            start=pd.Timestamp('2020-06-01T00:00:00Z');stop=start+pd.Timedelta(days=4)
            regions=[config['sensitivity_region'],'A3CLR22_2_Haworth']
            observers=observers.loc[observers.region.isin(regions)];profiles=profiles.loc[profiles.region.isin(regions)]
        step=pd.Timedelta(minutes=config['cadence_minutes']);times=pd.date_range(start,stop,freq=step,inclusive='left')
        kernels=[p for suffix in ['.tls','.tpc','.bsp','.bpc','.tf'] for p in pilot_files(LOCAL/'data','D19',suffix)]
        if not kernels:raise FileNotFoundError('No pinned local ephemeris kernels')
        for p in kernels:pin_source(run,p);run.input(p.with_name(p.name+'.json'))
        periods=[];intervals=[];daily=[];cross=[];cadence=[];comparisons=[];geometry_file=run.path('target_center_geometry.csv.gz');header=True;tracks=0
        spice.kclear()
        try:
            for p in kernels:spice.furnsh(str(p))
            positions={target:np.array([spice.spkpos(target,spice.str2et(t.strftime('%Y-%m-%dT%H:%M:%S')),'MOON_ME','NONE','MOON')[0] for t in times])*1000 for target in ['SUN','EARTH']}
            for obs in observers.to_dict('records'):
                region=obs['region'];basis=horizon.local_basis(obs['longitude_deg'],obs['latitude_deg'])
                for (height,radius),profile in profiles.loc[profiles.region.eq(region)].groupby(['height_m','radius_m']):
                    observer=horizon.cartesian(obs['longitude_deg'],obs['latitude_deg'],source_config['radius_m']+obs['surface_elevation_m']+height)
                    for target,pos in positions.items():
                        identity={'region':region,'height_m':height,'radius_m':radius,'target':target}
                        az,alt=horizon.angles(pos-observer,basis);skyline=horizon.lookup_horizon(profile,az)
                        if not np.isfinite(skyline).all() or not np.isfinite(alt).all():raise ValueError('Unknown numerical skyline/target geometry')
                        f=pd.DataFrame({'utc':times,'azimuth_deg':az,'target_center_elevation_deg':alt,'sampled_horizon_deg':skyline,
                            'center_blocked_by_sampled_terrain':alt<=skyline,'clearance_deg':alt-skyline})
                        f.assign(**identity).to_csv(geometry_file,index=False,mode='wt' if header else 'at',header=header,compression='gzip');header=False
                        period=period_geometry(f,subject['time_bins'],config['cadence_minutes'],subject['two_year_anchor']);periods.append(period.assign(**identity))
                        runs=horizon.sampled_runs(times,f.center_blocked_by_sampled_terrain)
                        intervals.extend({**identity,**r} for r in runs)
                        sid=f'TERRAIN_{region}_{height:g}m_{radius:g}m_{target}_blocked_fraction'
                        part=f.assign(date=f.utc.dt.floor('D')).groupby('date').center_blocked_by_sampled_terrain.agg(['mean','size']).reset_index()
                        part=part.assign(series_id=sid,daily_median=part['mean'],daily_max=part['mean'],recorded_samples=part['size'],valid_samples=part['size'],valid_seconds=np.nan,
                            daily_value_meaning='daily fraction of blocked model samples; not a native median, irradiance, energy or service coverage')
                        daily.append(part[['series_id','date','daily_median','daily_max','recorded_samples','valid_samples','valid_seconds','daily_value_meaning']])
                        prior=previous.loc[previous.region.eq(region)&previous.height_m.eq(height)&previous.radius_m.eq(radius)&previous.target.eq(target)]
                        shared=prior.merge(f,on='utc',suffixes=('_old','_new'),validate='one_to_one')
                        cross.append({**identity,'previous_rows':len(prior),'shared_rows':len(shared),
                            'maximum_absolute_elevation_difference_deg':float((shared.target_center_elevation_deg_old-shared.target_center_elevation_deg_new).abs().max()) if len(shared) else np.nan,
                            'maximum_absolute_horizon_difference_deg':float((shared.sampled_horizon_deg_old-shared.sampled_horizon_deg_new).abs().max()) if len(shared) else np.nan,
                            'blocking_classification_changes':int((shared.center_blocked_by_sampled_terrain_old!=shared.center_blocked_by_sampled_terrain_new).sum()),
                            'scope':'partial sample overlap' if sample else 'all prior two-window samples must match'})
                        if height==config['sensitivity_height_m'] and radius==config['sensitivity_radius_m']:
                            comparisons.append({**identity,'recorded_samples':len(f),'sampled_clear_fraction':float((~f.center_blocked_by_sampled_terrain).mean()),
                                'longest_observed_blocked_sample_span_hours':max((r['sample_span_hours'] for r in runs),default=0.),
                                'candidate_solar_proxy_min':science.loc[science.region.eq(region),'solar_opportunity_fraction_median'].min() if target=='SUN' else np.nan,
                                'candidate_solar_proxy_max':science.loc[science.region.eq(region),'solar_opportunity_fraction_median'].max() if target=='SUN' else np.nan,
                                'substitutable_for_static_candidate_profile':False,
                                'scope':'reference point vs candidate components; different footprint/time/configuration, so differing values are not contradictions or interchangeable inputs'})
                        if region==config['sensitivity_region'] and height==config['sensitivity_height_m'] and radius==config['sensitivity_radius_m']:
                            fine_step=pd.Timedelta(minutes=config['sensitivity_cadence_minutes']);fine_times=pd.date_range(start,stop,freq=fine_step,inclusive='left')
                            fine_pos=np.array([spice.spkpos(target,spice.str2et(t.strftime('%Y-%m-%dT%H:%M:%S')),'MOON_ME','NONE','MOON')[0] for t in fine_times])*1000
                            faz,falt=horizon.angles(fine_pos-observer,basis);blocked=falt<=horizon.lookup_horizon(profile,faz);fine_runs=horizon.sampled_runs(fine_times,blocked)
                            cadence.append({**identity,'base_cadence_minutes':config['cadence_minutes'],'fine_cadence_minutes':config['sensitivity_cadence_minutes'],
                                'base_blocked_fraction':f.center_blocked_by_sampled_terrain.mean(),'fine_blocked_fraction':blocked.mean(),
                                'base_longest_observed_sample_span_hours':max((r['sample_span_hours'] for r in runs),default=0.),
                                'fine_longest_observed_sample_span_hours':max((r['sample_span_hours'] for r in fine_runs),default=0.),
                                'scope':'same sampled skyline, temporal cadence only; not terrain convergence or guaranteed continuous intervals'})
                        tracks+=1
                print('Two-year geometry completed:',region,flush=True)
        finally:spice.kclear()
        cross=pd.DataFrame(cross)
        if not sample and (not cross.shared_rows.eq(cross.previous_rows).all() or cross.blocking_classification_changes.gt(0).any() or cross[['maximum_absolute_elevation_difference_deg','maximum_absolute_horizon_difference_deg']].max().max()>1e-9):raise ValueError('Prior reference geometry changed')
        daily=pd.concat(daily,ignore_index=True);calendar=calendar_summary(daily,subject['time_bins'],subject['two_year_anchor'])
        tables={'geometry_periods':pd.concat(periods,ignore_index=True),'observed_blocked_runs':pd.DataFrame(intervals,columns=['region','height_m','radius_m','target','first_blocked_sample','last_blocked_sample','blocked_samples','sample_span_hours','left_censored','right_censored']),
            'daily_context':daily,'calendar_daily_fraction_context':calendar,'cadence_sensitivity':pd.DataFrame(cadence),
            'crosscheck_Dar036':cross,'static_vs_point_context':pd.DataFrame(comparisons),'source_support_context':pd.concat(support,ignore_index=True),
            'native_policy_consistency':native,'stage4_terrain_proposals':proposals()}
        for name,frame in tables.items():frame.to_csv(run.path(name+'.csv'),index=False)
        fig,axes=plt.subplots(2,1,figsize=(12,7),sharex=True,layout='constrained')
        for region,g in tables['geometry_periods'].loc[lambda d:d.period_kind.eq('month')&d.target.eq('SUN')&d.height_m.eq(2)&d.radius_m.eq(20000)].groupby('region'):
            axes[0].plot(pd.to_datetime(g.period_start_utc),1-g.sampled_blocked_fraction,label=region)
            axes[1].plot(pd.to_datetime(g.period_start_utc),g.longest_observed_blocked_sample_span_hours)
        axes[0].set(ylabel='Sampled clear-center fraction',title='2 m / 20 km reference-point scenario; NOT power or mission darkness');axes[0].legend(fontsize=5,ncol=2)
        axes[1].set(ylabel='Longest observed blocked-sample span h');save_figure(run,fig,'solar_fraction_and_observed_spans')
        fig,ax=plt.subplots(figsize=(9,5),layout='constrained');g=tables['static_vs_point_context'].loc[lambda d:d.target.eq('SUN')]
        for row in g.to_dict('records'):
            ax.scatter(row['sampled_clear_fraction'],row['longest_observed_blocked_sample_span_hours'],label=row['region'])
        ax.set(xlabel='Two-year clear solar-center sample fraction',ylabel='Longest observed blocked-sample span h',title='Mean visibility and persistence are different; no qualified energy/storage demand');ax.legend(fontsize=5)
        save_figure(run,fig,'mean_visibility_vs_blocked_persistence')
        findings={'subject':'terrain_illumination','sample':sample,'reference_points':len(observers),'scenario_target_tracks':tracks,
            'native_geometry_samples':tracks*len(times),'start_utc':str(start),'stop_exclusive_utc':str(stop),'cadence_minutes':config['cadence_minutes'],
            'tables':{name:len(f) for name,f in tables.items()},'time_contract':subject['time_contract'],
            'base_conclusion':'Two historical model years show sampled blocking persistence as well as mean visibility. Existing terrain/image support remains consistent, but reference-point geometry cannot establish component power, working links, buildable soil or qualified continuous darkness.',
            'pipeline_changed':False,'adopted_limits':False,'operational_status':'Unknown',
            'remaining':['Validated mission footprints and unmodelled terrain/blockers','Solar-disk/orientation/generation/load/storage and contact/link response','Applicable mobility/foundation and mission operating requirements','Operational/PDF evidence and integrated Stage 4 synthesis']}
        run.path('findings.json').write_text(json.dumps(findings,indent=2));result=run.directory
    print(json.dumps(findings,indent=2),flush=True);return result,findings


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--sample',action='store_true')
    print(execute(parser.parse_args().sample)[0])
