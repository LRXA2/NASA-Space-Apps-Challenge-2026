"""Dedicated UV study: all SEE spectra, native-pixel LAMP quality and explicit UTC bins."""
from pathlib import Path
from contextlib import ExitStack
import argparse
import json
import re
import sys

sys.path[:0] = [str(Path(__file__).resolve().parents[2]/'shared'),
               str(Path(__file__).resolve().parents[3]),str(Path(__file__).resolve().parents[4])]
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import netCDF4
import numpy as np
import pandas as pd
import rasterio
from rasterio.windows import Window
from pyproj import Transformer

import stage3_acquired_eda as acquired
from decision_eda import accepted_input
from environment_workflow import LocalRun
from environment_time import calendar_summary, fixed_month_comparison
from stage3_mission_eda import LOCAL, ROOT, save_figure
from research_p1_readers import pds3_number
from notebooks.shared.processing import MOON_CRS, MOON_GEOGRAPHIC

CONFIG = Path(__file__).with_name('stage3_subject_config.json')
NOTEBOOK = 'Moon/Stage3_Requirements/Dar_045_uv_spectral_spatial_time.ipynb'


def model_assisted_bins(wave):
    """Conservative product-description partition; not a per-record provenance flag."""
    w = np.asarray(wave,float)
    return (w<27)|((w>=114.5)&(w<=120.5))|((w>=122.5)&(w<=128.5))


def band_metrics(wave,flux,error,low,high):
    value,bound,n = acquired.see_band(wave,flux,error,low,high)
    w,x,e = [np.ma.filled(np.ma.asarray(a),np.nan).ravel().astype(float) for a in [wave,flux,error]]
    select = (w>=low)&(w<high)
    supported = np.isfinite(value)
    model = model_assisted_bins(w)&select
    return {'integral_W_m2':value,'absolute_error_sum_bound_W_m2':bound,
        'rss_error_if_independent_W_m2':float(np.sqrt(np.sum((x[select]*e[select])**2))) if supported else np.nan,
        'model_assisted_energy_fraction':float(x[model].sum()/value) if supported else np.nan,
        'valid_bins':n,'expected_bins':high-low,'complete_positive_band':bool(supported),
        'uncertainty_note':'sum is a conservative fully-correlated bound; RSS is conditional on independence, not established uncertainty'}


def spectral_study(run,config,sources,subject,sample):
    entries = acquired.bounded(acquired.science(sources,'D09_SEE'),sample)
    rows,fluxes,errors,dates,metadata = [],[],[],[],[]
    reference = None
    for entry in entries:
        path = acquired.pin(run,config,entry)
        with netCDF4.Dataset(path) as f:
            w,x,e = [np.ma.filled(f[name][:],np.nan).ravel().astype(float) for name in ['SP.WAVE','SP.FLUX','SP.ERR_TOT']]
            if f['SP.WAVE'].Units!='nm' or f['SP.FLUX'].Units!='W / m^2 / nm' or f['SP.ERR_TOT'].Units!='Fractional':
                raise ValueError('Changed SEE spectral/uncertainty units')
            if reference is not None and not np.array_equal(w,reference):
                raise ValueError('Changed SEE spectral grid; do not stack incompatible bins')
            reference = w
            date = pd.to_datetime(str(int(f['DATE'][:].item())),format='%Y%j',utc=True)
            product = f.Data_product_version
            for band,(low,high) in subject['uv_bands_nm'].items():
                rows.append({'file':path.name,'date':date,'band':band,'series_id':f'SEE_v{product}_{band}',
                    'revision':f.Data_product_revision,**band_metrics(w,x,e,low,high),
                    'scope':'native model-assisted daily mean at 1 AU, flare-removed; not surface dose or subdaily peak'})
            fluxes.append(x);errors.append(e);dates.append(date)
            if len(metadata)<1:
                metadata.append({'file':path.name,'global':f.__dict__,
                    'spectral_variables':{n:f[n].__dict__ for n in ['SP.WAVE','SP.FLUX','SP.ERR_TOT']}})
    frame = pd.DataFrame(rows)
    if frame.duplicated(['series_id','date']).any():raise ValueError('Repeated SEE dates or revisions')
    raw,err = np.array(fluxes),np.array(errors)
    positive = np.isfinite(raw)&(raw>0)&np.isfinite(err)&(err>=0)
    support = pd.DataFrame({'wavelength_nm':reference,'recorded_days':len(dates),
        'positive_supported_days':positive.sum(axis=0),'zero_flux_days':(raw==0).sum(axis=0),
        'negative_flux_days':(raw<0).sum(axis=0),'nonfinite_flux_days':(~np.isfinite(raw)).sum(axis=0),
        'model_assisted_partition':model_assisted_bins(reference),
        'inside_documented_0_190nm':(reference>=0)&(reference<190)})
    spectra = pd.DataFrame(np.where(positive,raw,np.nan),index=pd.DatetimeIndex(dates),columns=reference)
    relative_error = pd.DataFrame(np.where(positive,err,np.nan),index=spectra.index,columns=reference)
    support['median_positive_flux_W_m2_nm'] = spectra.median().to_numpy()
    support['median_fractional_error'] = relative_error.median().to_numpy()
    monthly = spectra.groupby(spectra.index.strftime('%Y-%m')).median().stack(dropna=False).rename('median_positive_daily_flux_W_m2_nm').reset_index()
    monthly.columns = ['year_month','wavelength_nm','median_positive_daily_flux_W_m2_nm']
    valid = spectra.notna().groupby(spectra.index.strftime('%Y-%m')).sum().stack().rename('valid_days').reset_index()
    valid.columns = ['year_month','wavelength_nm','valid_days']
    monthly = monthly.merge(valid,on=['year_month','wavelength_nm'],validate='one_to_one')
    run.path('see_source_metadata.json').write_text(json.dumps(metadata,indent=2,default=str))
    return frame,support,monthly,spectra,relative_error


def hist_state(edges):
    return {'edges':np.asarray(edges,float),'hist':np.zeros(len(edges)-1,dtype='int64'),
            'count':0,'sum':0.,'sum2':0.,'minimum':np.inf,'maximum':-np.inf,'under':0,'over':0}


def hist_add(state,values):
    x = np.asarray(values,float);x = x[np.isfinite(x)]
    if not len(x):return
    state['count']+=len(x);state['sum']+=float(x.sum());state['sum2']+=float(np.sum(x*x))
    state['minimum']=min(state['minimum'],float(x.min()));state['maximum']=max(state['maximum'],float(x.max()))
    state['under']+=int((x<state['edges'][0]).sum());state['over']+=int((x>state['edges'][-1]).sum())
    state['hist']+=np.histogram(x,bins=state['edges'])[0]


def quantile_bounds(state,q):
    if not 0<=q<=1:raise ValueError('Quantile outside 0..1')
    if not state['count']:return np.nan,np.nan
    target = int(np.floor(q*(state['count']-1)))
    if target<state['under']:return state['minimum'],state['edges'][0]
    if target>=state['under']+int(state['hist'].sum()):return state['edges'][-1],state['maximum']
    index = int(np.searchsorted(np.cumsum(state['hist']),target-state['under'],side='right'))
    return state['edges'][index],state['edges'][index+1]


def hist_row(state):
    n=state['count'];lo,hi=quantile_bounds(state,.5);p95lo,p95hi=quantile_bounds(state,.95)
    mean = state['sum']/n if n else np.nan
    return {'finite_pixels':n,'mean':mean,'standard_deviation':float(np.sqrt(max(0.,state['sum2']/n-mean**2))) if n else np.nan,
        'minimum':state['minimum'] if n else np.nan,'maximum':state['maximum'] if n else np.nan,
        'p50_hist_lower':lo,'p50_hist_upper':hi,'p95_hist_lower':p95lo,'p95_hist_upper':p95hi,
        'below_histogram_range':state['under'],'above_histogram_range':state['over'],
        'quantile_semantics':'histogram intervals, not exact pixel quantiles; tails retained explicitly'}


def lamp_native(run,config,sources,subject,sample):
    categories=['ALBEDO','BRIGHTNESS','DATA_QUALITY','ERROR','EXPOSURE']
    edges={'ALBEDO':np.linspace(0,1,1001),'BRIGHTNESS':np.r_[0.,np.logspace(0,8,801)],
           'ERROR':np.r_[0.,np.logspace(-2,4,601)],'EXPOSURE':np.r_[0.,np.logspace(-2,9,1101)]}
    rows,quality_rows,histograms,images,time_rows=[],[],[],[],[]
    window_size=subject['lamp_window_pixels']
    for band in (['long'] if sample else ['long','lya','off','on']):
        states={};coverage={};flags={}
        wavelength=None
        with ExitStack() as stack:
            readers={};shape=None;transform=None;crs=None
            for category in categories:
                entry=next(e for e in acquired.science(sources,'D32') if '/'+category+'/' in e['url'] and '_'+band+'_' in e['url'])
                acquired.pin(run,config,entry);label=acquired.paired_path(run,config,sources,entry,'.lbl');text=label.read_text()
                if category=='ERROR' and 'signal-to-noise' not in text:raise ValueError('LAMP ERROR is no longer SNR')
                if category=='DATA_QUALITY' and '0 = good data' not in text:raise ValueError('Changed LAMP quality flags')
                if pds3_number(text,'A_AXIS_RADIUS')!=1737.4:raise ValueError('Nonlunar LAMP radius')
                if pds3_number(text,'SCALING_FACTOR')!=1 or pds3_number(text,'OFFSET')!=0:
                    raise ValueError('Nonidentity LAMP scaling needs explicit decoding review')
                r=stack.enter_context(rasterio.open(label));readers[category]=r
                if shape is not None and (r.shape!=shape or r.transform!=transform or r.crs!=crs):
                    raise ValueError('Unaligned LAMP map family')
                shape,transform,crs=r.shape,r.transform,r.crs
                wavelength=(pds3_number(text,'MINIMUM_WAVELENGTH'),pds3_number(text,'MAXIMUM_WAVELENGTH'))
                start=re.search(r'^START_TIME\s*=\s*([^\s]+)',text,re.M)
                stop=re.search(r'^STOP_TIME\s*=\s*([^\s]+)',text,re.M)
                if start is None or stop is None:raise ValueError('LAMP acquisition interval missing')
                time_rows.append({'dataset':'LAMP_'+band+'_'+category,'time_basis':'historical cumulative map',
                    'label_start_time_utc':start[1],'label_stop_time_utc':stop[1],
                    'calendar_binning_applicable':False,'reason':'label acquisition interval is not a pixel-level chronology'})
            project=Transformer.from_crs(crs,MOON_GEOGRAPHIC,always_xy=True)
            for r0 in range(0,shape[0],window_size):
                for c0 in range(0,shape[1],window_size):
                    h,w=min(window_size,shape[0]-r0),min(window_size,shape[1]-c0)
                    win=Window(c0,r0,w,h)
                    values={cat:np.ma.filled(r.read(1,window=win,masked=True),np.nan).astype(float) for cat,r in readers.items()}
                    rr,cc=np.meshgrid(np.arange(r0,r0+h),np.arange(c0,c0+w),indexing='ij')
                    x=transform.c+(cc+.5)*transform.a+(rr+.5)*transform.b
                    y=transform.f+(cc+.5)*transform.d+(rr+.5)*transform.e
                    _,lat=project.transform(x,y);domain=lat<=-80
                    supported=domain&(values['DATA_QUALITY']==0)&(values['EXPOSURE']>0)&(values['ERROR']>=3)
                    masks={'south_polar_domain':domain}
                    masks.update({key:domain&(x>=b[0])&(x<=b[2])&(y>=b[1])&(y<=b[3]) for key,b in config['region_bounds_m'].items()})
                    qvalues=values['DATA_QUALITY'][domain]
                    for q in np.unique(qvalues[np.isfinite(qvalues)]):flags[str(q)]=flags.get(str(q),0)+int((qvalues==q).sum())
                    flags['nonfinite_or_masked']=flags.get('nonfinite_or_masked',0)+int((~np.isfinite(qvalues)).sum())
                    for region,mask in masks.items():
                        cov=coverage.setdefault(region,{'domain_pixels':0,'quality_zero_pixels':0,'positive_exposure_pixels':0,'snr_ge3_pixels':0,'joint_support_pixels':0})
                        cov['domain_pixels']+=int(mask.sum());cov['quality_zero_pixels']+=int((mask&(values['DATA_QUALITY']==0)).sum())
                        cov['positive_exposure_pixels']+=int((mask&(values['EXPOSURE']>0)).sum())
                        cov['snr_ge3_pixels']+=int((mask&(values['ERROR']>=3)).sum());cov['joint_support_pixels']+=int((mask&supported).sum())
                        for category in edges:
                            for cohort,keep in [('finite_before_quality',mask),('joint_quality_supported',mask&supported)]:
                                key=(region,category,cohort)
                                hist_add(states.setdefault(key,hist_state(edges[category])),values[category][keep])
                if sample:break  # Explicit first native row of windows, not a complete polar map.
            for (region,category,cohort),state in states.items():
                rows.append({'band':band,'region':region,'quantity':category,'cohort':cohort,**hist_row(state),
                    'unit':{'ALBEDO':'dimensionless','BRIGHTNESS':'photons/(cm2 s sr)','ERROR':'SNR ratio','EXPOSURE':'s'}[category],
                    'wavelength_min_nm':wavelength[0],'wavelength_max_nm':wavelength[1],
                    'pixel_weighting':'equal projected native pixel, not exact surface area','spatial_support':'bounding-box pixel centres, not certified candidate footprints'})
                if category=='ALBEDO' and cohort=='joint_quality_supported':
                    histograms.extend({'band':band,'region':region,'lower':a,'upper':b,'pixels':int(n)} for a,b,n in zip(state['edges'][:-1],state['edges'][1:],state['hist']))
            for region,cov in coverage.items():
                quality_rows.append({'band':band,'region':region,**cov,
                    'supported_fraction':cov['joint_support_pixels']/cov['domain_pixels'] if cov['domain_pixels'] else np.nan,
                    'sample':sample,'scope':'native pixel counts; quality masks are not environmental safety gates'})
            for flag,count in flags.items():quality_rows.append({'band':band,'region':'quality_flag_counts','quality_flag':flag,'flag_pixels':count,'sample':sample})
            target=(int(np.ceil(shape[0]/subject['lamp_display_stride'])),int(np.ceil(shape[1]/subject['lamp_display_stride'])))
            small={cat:np.ma.filled(readers[cat].read(1,out_shape=target,masked=True),np.nan) for cat in categories}
            mask=(small['DATA_QUALITY']==0)&(small['EXPOSURE']>0)&(small['ERROR']>=3)
            images.append((band,np.where(mask,small['ALBEDO'],np.nan)))
        print('Native LAMP complete:',band,flush=True)
    return pd.DataFrame(rows),pd.DataFrame(quality_rows),pd.DataFrame(histograms),images,pd.DataFrame(time_rows)


def screening_checks(run,subject,bands,quality):
    folder=LOCAL/'data/processed/analysis'/subject['screening_run']
    old=pd.read_csv(accepted_input(run,folder,'see_file_diagnostics.csv'))
    joined=bands.merge(old[['file','band','integral_W_m2']],on=['file','band'],suffixes=('_subject','_screen'),validate='one_to_one')
    rows=[]
    for band,g in joined.groupby('band'):
        numeric=g.integral_W_m2_subject.notna()&g.integral_W_m2_screen.notna()
        rows.append({'check':'Dar044_same_band_integrals','subject':band,'paired_files':len(g),
            'different_support_rows':int((g.integral_W_m2_subject.isna()!=g.integral_W_m2_screen.isna()).sum()),
            'maximum_absolute_difference':float(np.max(np.abs(g.loc[numeric,'integral_W_m2_subject']-g.loc[numeric,'integral_W_m2_screen']))) if numeric.any() else np.nan,
            'conclusion':'same raw band/screening semantics; new subbands do not replace unsupported wider bands'})
    lamp=pd.read_csv(accepted_input(run,folder,'lamp_supported_maps.csv'))
    lamp=lamp.loc[lamp.quantity.eq('ALBEDO')].copy();lamp['stride4_support_fraction']=lamp.quality_supported_pixels/lamp.sampled_domain_pixels
    diff=quality.loc[quality.region.ne('quality_flag_counts')].merge(lamp[['band','region','stride4_support_fraction']],on=['band','region'],validate='one_to_one')
    diff['native_minus_stride4_percentage_points']=100*(diff.supported_fraction-diff.stride4_support_fraction)
    return pd.DataFrame(rows),diff


def uv_proposals():
    rows=[
        ('UV-G01','evidence_guard','Complete band, units and uncertainty support','daily spectrum and native support/quality metadata','Unknown for local exposure; Failed only if an unsupported inference is attempted','E01 E04 E13','No zero-filled or partial spectral sum may stand in for a supported complete band'),
        ('UV-H01','conditional_hard_constraint','Applicable crew/material UV exposure limit','local incident spectrum, duration/activity, protection and qualified action/response model, adopted applicable limit','Unknown','E04 E13','If applicable evaluated demand exceeds an adopted limit, Failed; if sufficient evidence proves within limit, Passed; missing applicability/response/limit is Unknown'),
        ('UV-S01','conditional_soft_preference','Lower supported operational UV burden where desired','mandatory conditions Passed, equivalent mission/activity, comparable local response-based UV burden','Unknown','E13','Preference only after all mandatory conditions pass; do not double-weight sunlight opportunity or assume less sunlight is globally better'),
        ('UV-G02','evidence_guard','LAMP albedo/brightness is not incident UV dose','quantity/units, historical acquisition support, geometry, irradiance and response model','Unknown for dose','E01 E04 E13','Native reflectance/SNR/exposure context may be used as such, not substituted for surface irradiance, absorbed dose or ice detection'),
        ('UV-G03','evidence_guard','Explicit calendar windows and peak limitations','UTC source dates, coverage, instrument cadence, relevant event/mission period','Unknown for forecast or flare peak','E14 E15','DJF labels are not lunar climate seasons; daily flare-removed means do not establish intraday peaks or future safe arrival months'),
        ('UV-G04','evidence_guard','Keep solar products and epochs distinct','instrument/version/model-assisted partition and matched qualified timestamps','Unknown for unsupported cross-product substitution','E15 E16','New contemporary SEE overlap does not change historical SOLSTICE non-overlap or validate a surface-charging model')]
    return pd.DataFrame([{'id':id,'classification':role,'title':title,'required_inputs':inputs,'current_outcome':'Unknown',
        'outcome_scope_note':outcome,
        'existing_rule_crosswalk':old,'decision_logic':logic,'quantity':'spectral/local response-specific; see requirements',
        'unit':'quantity-specific','applicability':'Moon mission/activity and local footprint/period must be established',
        'limit_value':np.nan,'limit_state':'not_adopted','preference_weight':np.nan,'status':'Stage 4 proposal only; not loaded by pipeline',
        'evidence':'band_daily_context.csv; spectral_support.csv; calendar_context.csv; lamp_native_quality.csv; crosscheck_screening.csv',
        'source':'provider SEE/LAMP labels and README; accepted Dar042/043/044 context; project evidence-use contract'}
        for id,role,title,inputs,outcome,old,logic in rows])


def execute(sample=False):
    subject=json.loads(CONFIG.read_text());config=json.loads(CONFIG.with_name(subject['acquisition_config']).read_text())
    if subject['schema']!=1 or subject['body']!='Moon':raise ValueError('Expected Moon subject schema')
    stage='analysis/subject_uv'+('_sample' if sample else '')
    with LocalRun(ROOT,stage,subject,NOTEBOOK) as run:
        for path in [CONFIG,Path(__file__),acquired.CONFIG,Path(acquired.__file__),LOCAL/'EDA/shared/environment_time.py']:
            run.input(path)
        sources=acquired.catalog(run,config)
        docs=[e for e in sources['D09_SEE'] if 'README' in e['url'] or 'ReleaseNotes' in e['url']]
        for e in docs:acquired.pin(run,config,e)
        print('Reading complete SEE spectra',flush=True)
        bands,support,monthly_spectrum,spectra,uncertainty=spectral_study(run,config,sources,subject,sample)
        daily=bands.rename(columns={'integral_W_m2':'daily_median','valid_bins':'valid_samples','expected_bins':'recorded_samples'}).copy()
        daily['daily_max']=daily.daily_median;daily['valid_seconds']=np.nan
        daily['daily_statistic']='complete band integral of native daily-mean spectrum; not median wavelength flux or a subdaily maximum'
        oldfolder=LOCAL/'data/processed/analysis'/subject['temporal_run']
        prior=pd.read_csv(accepted_input(run,oldfolder,'daily_context.csv'))
        prior=prior.loc[prior.series_id.str.startswith('UV_SOLSTICE_')].copy()
        if sample:prior=prior.groupby('series_id').head(20)
        compare=pd.concat([daily[['series_id','date','daily_median','daily_max','recorded_samples','valid_samples','valid_seconds']],
                           prior[['series_id','date','daily_median','daily_max','recorded_samples','valid_samples','valid_seconds']]],ignore_index=True)
        compare['date']=pd.to_datetime(compare.date,utc=True)
        calendar=calendar_summary(compare,subject['time_bins'],subject['two_year_anchor'])
        matched=fixed_month_comparison(compare,6,10)
        print('Scanning native LAMP pixels in bounded windows',flush=True)
        native,quality,hist,images,temporal=lamp_native(run,config,sources,subject,sample)
        checks,differences=screening_checks(run,subject,bands,quality)
        profile_folder=LOCAL/'data/processed/analysis'/subject['science_profile_run']
        profiles=pd.read_csv(accepted_input(run,profile_folder,'candidate_science_profiles.csv'))
        proxies=profiles[['candidate_id','region','solar_opportunity_fraction_median','uv_sun_visibility_opportunity_proxy']].copy()
        proxies['same_underlying_opportunity']=np.isclose(proxies.solar_opportunity_fraction_median,proxies.uv_sun_visibility_opportunity_proxy,equal_nan=True)
        proxies['independent_score_evidence']=False
        proxies['local_uv_dose_supplied']=False
        proxies['conclusion']='static geometric opportunity, not spectral/chronological exposure; do not double-weight the identical sunlight input'
        overlap=pd.DataFrame([{'left':'SOLSTICE','right':'SEE','simultaneous_overlap':False,
            'reason':'historical SOLSTICE ends 2020, SEE cohort begins June 2023; do not stitch as calibrated one-instrument trend'},
            {'left':'SEE','right':'LAMP','simultaneous_overlap':False,
             'reason':'LAMP maps aggregate 2009-2010 acquisition, not contemporary surface irradiance'}])
        tables={'band_daily_context':daily,'spectral_support':support,'monthly_spectral_profile':monthly_spectrum,
            'calendar_context':calendar,'matched_June_October_years':matched,'lamp_native_statistics':native,
            'lamp_native_quality':quality,'lamp_albedo_histograms':hist,'lamp_time_applicability':temporal,
            'crosscheck_screening':checks,'crosscheck_native_vs_stride4':differences,'cross_product_applicability':overlap,
            'crosscheck_existing_sunlight_uv_proxy':proxies,
            'stage4_uv_proposals':uv_proposals()}
        for name,frame in tables.items():frame.to_csv(run.path(name+'.csv'),index=False)
        fig,axes=plt.subplots(2,1,figsize=(12,7),layout='constrained')
        positive=spectra.where(spectra>0)
        axes[0].imshow(np.log10(positive.to_numpy()).T,aspect='auto',origin='lower',extent=[0,len(spectra),support.wavelength_nm.min(),support.wavelength_nm.max()])
        axes[0].set(title='Daily spectral support, log10 W/m2/nm; column index follows UTC dates',ylabel='Wavelength nm',xlabel='Recorded day index; gaps not filled')
        axes[1].plot(support.wavelength_nm,support.positive_supported_days/support.recorded_days)
        axes[1].set(xlabel='Wavelength nm',ylabel='Positive supported day fraction',ylim=(-.02,1.02))
        save_figure(run,fig,'spectral_support')
        for band,g in daily.groupby('band'):
            fig,axes=plt.subplots(2,1,figsize=(11,5),sharex=True,layout='constrained')
            axes[0].scatter(pd.to_datetime(g.date,utc=True),g.daily_median,s=2)
            axes[0].set(ylabel='W/m2 at 1 AU',title=band+'; model-assisted daily means, NOT local safety')
            axes[1].scatter(pd.to_datetime(g.date,utc=True),g.model_assisted_energy_fraction,s=2)
            axes[1].set(ylabel='Assisted-bin energy fraction',xlabel='UTC date')
            save_figure(run,fig,'daily_'+band)
        fuv=calendar.loc[calendar.series_id.str.contains('FUV_115_180')]
        fig,axes=plt.subplots(2,1,figsize=(12,6),sharex=True,layout='constrained')
        for kind,g in fuv.groupby('period_kind'):
            axes[0].plot(pd.to_datetime(g.period_start_utc),g.median_of_daily_values,marker='.',label=kind)
            axes[1].plot(pd.to_datetime(g.period_start_utc),g.valid_day_fraction,marker='.',label=kind)
        axes[0].set(ylabel='Median daily FUV, W/m2',title='Calendar aggregation changes appearance; no lunar-season/forecast inference');axes[0].legend(fontsize=7,ncol=4)
        axes[1].set(ylabel='Valid-day fraction',ylim=(-.02,1.02));save_figure(run,fig,'fuv_calendar_scales')
        for band,image in images:
            fig,ax=plt.subplots(figsize=(6,6),layout='constrained');im=ax.imshow(image)
            ax.set(title='LAMP '+band+' supported albedo; display only downsampled\nstatistics use native pixels; white is masked, not zero UV')
            fig.colorbar(im,ax=ax);save_figure(run,fig,'lamp_'+band+'_native_support')
        band_summary=bands.groupby('band').agg(recorded_days=('date','size'),supported_days=('complete_positive_band','sum'),
            median_supported_integral=('integral_W_m2','median'),median_assisted_fraction=('model_assisted_energy_fraction','median')).reset_index()
        band_summary.to_csv(run.path('band_support_summary.csv'),index=False)
        findings={'subject':'solar_uv','sample':sample,'tables':{k:len(v) for k,v in tables.items()},
            'bands':band_summary.to_dict('records'),'calendar_definitions':subject['time_contract'],
            'base_conclusion':'Solar spectral/temporal and native polar-map evidence improves context and support assessment, but does not supply mission-local UV dose, biological/material response or a safe arrival season.',
            'full_source_scope':'all SEE daily spectra; all pixels in all 20 selected LAMP maps' if not sample else 'first/last SEE files and first native window-row in long LAMP only',
            'pipeline_changed':False,'numeric_safety_limits_adopted':False,'operational_status':'Unknown',
            'remaining':['Subdaily flare peaks and local shadow/orientation histories','Qualified crew/material action/response models and applicable limits','Solar product cross-calibration and LAMP-to-incident-irradiance model','Other subjects and integrated Stage 4 synthesis remain active goal work']}
        run.path('findings.json').write_text(json.dumps(findings,indent=2,default=str));folder=run.directory
    print(json.dumps(findings,indent=2),flush=True)
    return folder,findings


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--sample',action='store_true')
    print(execute(parser.parse_args().sample)[0])
