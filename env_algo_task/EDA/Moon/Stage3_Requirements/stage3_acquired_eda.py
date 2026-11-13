"""Receipt-verified new lunar/environmental cohorts; Step 3 only, no engine changes."""
from pathlib import Path
import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET

sys.path[:0] = [str(Path(__file__).resolve().parents[2]/'shared'),
               str(Path(__file__).resolve().parents[3]), str(Path(__file__).resolve().parents[4])]
import cdflib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import netCDF4
import numpy as np
import pandas as pd
import rasterio
from obspy import read, read_inventory
from pyproj import Transformer

from data_maintenance import checked_path
from decision_eda import accepted_input
from environment_workflow import LocalRun
from notebooks.shared.processing import MOON_CRS, MOON_GEOGRAPHIC, sha256
from research_p1_readers import pds4_chunks, pds4_definition, pds3_number, pin_source
from stage3_mission_eda import ROOT, LOCAL, external_input, save_figure
from stage3_temporal_eda import cdf_values, period_summary, position_groups, support_table

CONFIG = Path(__file__).with_name('stage3_acquired_config.json')
NOTEBOOK = 'Moon/Stage3_Requirements/Dar_044_acquired_environment.ipynb'


def external_metadata(run, root, path):
    """Register provider-plan metadata (not a science receipt)."""
    path = checked_path(root, path)
    key = 'external_data/'+path.relative_to(root).as_posix()
    if key not in run.record['inputs']:
        run.record['inputs'][key] = {'path':str(path), 'bytes':path.stat().st_size, 'sha256':sha256(path)}
    return path


def catalog(run, config):
    root, result = Path(config['external_root']), {}
    for id in config['plans']:
        path = external_metadata(run, root, root/f'manifests/addons/plans/{id}.json')
        plan = json.loads(path.read_text())
        if plan['id'] != id or plan.get('gaps'):
            raise ValueError('Pinned source plan identity/gap changed')
        for job in plan['jobs']:
            for entry in job['entries']:
                result.setdefault(job['key'], []).append({**entry, 'key':job['key'], 'job':job['id']})
    return result


def pin(run, config, entry):
    """Reuse existing external verification and local baseline receipt contracts."""
    root = Path(config['external_root'])
    path = checked_path(root, entry['relative_path'])
    if not path.is_file():
        checkpoint = external_metadata(run, root, root/f"manifests/addons/jobs/{entry['job']}/inventory.json")
        record = json.loads(checkpoint.read_text())
        item = next(i for i in record['files'] if i['url'] == entry['url'])
        if not item.get('reference'):
            raise FileNotFoundError(path)
        path = Path(item['reference']['path'])
        if not path.resolve().is_relative_to((LOCAL/'data').resolve()):
            raise ValueError('Unexpected baseline root; explicit review required')
    local = path.resolve().is_relative_to(ROOT.resolve())
    key = str(path.resolve().relative_to(ROOT.resolve())) if local else 'external_data/'+path.relative_to(root).as_posix()
    if not entry.get('metadata'):
        run.record.setdefault('science_cohort',{})[entry['url']]={'dataset':entry['key'],'path':str(path)}
    if key in run.record['inputs']:
        return path
    receipt = path.with_name(path.name+'.json')
    saved = json.loads(receipt.read_text())
    if saved['source']['url'] != entry['url']:
        raise ValueError('Pinned URL/receipt mismatch: '+str(path))
    if local:
        return pin_source(run, path)
    item = {**saved['source'], 'sha256':saved['sha256'],
            'relative_path':path.relative_to(root).as_posix(), 'receipt':receipt.relative_to(root).as_posix()}
    return external_input(run, config, item)


def paired_path(run, config, sources, entry, suffix='.xml'):
    url = entry['url'].rsplit('.', 1)[0]+suffix
    return pin(run, config, next(e for e in sources[entry['key']] if e['url'] == url))


def science(sources, key):
    return sorted((e for e in sources[key] if not e.get('metadata')), key=lambda e:e['url'])


def monthly_edges(entries, species=False):
    """Selection depends on filenames/dates only, never observed values."""
    groups = {}
    for e in entries:
        name = Path(e['relative_path']).name
        date = re.search(r'(20\d{6})', name)
        if date is None:
            raise ValueError('No dated filename: '+name)
        key = (date[1][:6], name.split('_')[1] if species else '')
        groups.setdefault(key, []).append(e)
    ordered=[sorted(g,key=lambda e:(re.search(r'(20\d{6})',Path(e['relative_path']).name)[1],e['url'])) for g in groups.values()]
    return list({e['url']:e for group in ordered for e in [group[0], group[-1]]}.values())


def bounded(entries, sample):
    return list({e['url']:e for e in [entries[0], entries[-1]]}.values()) if sample and entries else entries


def describe(values):
    x = np.asarray(values, dtype=float)
    x = x[np.isfinite(x)]
    return {'valid':len(x), 'min':float(x.min()) if len(x) else np.nan,
            'median':float(np.median(x)) if len(x) else np.nan,
            'p95':float(np.quantile(x,.95)) if len(x) else np.nan,
            'max':float(x.max()) if len(x) else np.nan}


def daily_rows(sid, dates, values):
    f = pd.DataFrame({'date':pd.DatetimeIndex(pd.to_datetime(dates, utc=True)).floor('D'), 'value':np.asarray(values,float)})
    if f.date.isna().any():
        raise ValueError('Missing source dates')
    g = f.groupby('date').value
    out = g.agg(daily_median='median', daily_max='max', recorded_samples='size', valid_samples='count')
    out['daily_p95'], out['series_id'], out['valid_seconds'] = g.quantile(.95), sid, np.nan
    return out.reset_index()


def series(sid, environment, instrument, channel, unit, basis, scope):
    return {'series_id':sid,'environment':environment,'instrument':instrument,'channel':channel,
            'unit':unit,'version':'source-specific; see file diagnostics','position_group':scope,
            'daily_statistic':'record-weighted median, not time-weighted','validity_basis':basis,
            'spatial_scope':scope}


def see_band(wave, flux, errors, low=115, high=180):
    """Complete positive native 1-nm bins only; zeros in padded bins are not quiet Sun."""
    w, x, e = [np.ma.filled(np.ma.asarray(a),np.nan).ravel().astype(float) for a in [wave,flux,errors]]
    selected = (w >= low) & (w < high)
    if not np.array_equal(w[selected], np.arange(low+.5,high,1)):
        raise ValueError('Incomplete/changed SEE wavelength grid')
    good = np.isfinite(x[selected]) & (x[selected]>0) & np.isfinite(e[selected]) & (e[selected]>=0)
    return (float(x[selected].sum()) if good.all() else np.nan,
            float((x[selected]*e[selected]).sum()) if good.all() else np.nan, int(good.sum()))


def see(run, config, sources, sample):
    rows, diagnostics, cats = [], [], []
    selected = bounded(science(sources,'D09_SEE'),sample)
    bands = {'FUV_115_180':(115,180),'EUV_27_115':(27,115)}
    for e in selected:
        path = pin(run,config,e)
        with netCDF4.Dataset(path) as f:
            date = pd.to_datetime(str(int(f['DATE'][:].item())), format='%Y%j', utc=True)
            if f['SP.WAVE'].getncattr('Units')!='nm' or f['SP.FLUX'].getncattr('Units')!='W / m^2 / nm':
                raise ValueError('Changed SEE units')
            product = f.getncattr('Data_product_version');revision=f.getncattr('Data_product_revision')
            for band,(low,high) in bands.items():
                value,error,n = see_band(f['SP.WAVE'][:],f['SP.FLUX'][:],f['SP.ERR_TOT'][:],low,high)
                sid = f'SEE_v{product}_{band}'
                rows.append({'series_id':sid,'date':date,'daily_median':value,'daily_max':value,
                    'daily_p95':np.nan,'recorded_samples':high-low,'valid_samples':n,'valid_seconds':np.nan})
                diagnostics.append({'file':path.name,'date':date,'band':band,'revision':revision,
                    'integral_W_m2':value,'sum_absolute_bin_error_W_m2':error,'complete_positive_bins':n==high-low})
                cats.append(series(sid,'UV','TIMED_SEE',band,'W/m2 at 1 AU',
                    'complete positive bins and finite nonnegative fractional uncertainty; model-filled bands remain model-assisted',
                    'solar reference, not local lunar exposure; daily flare-removed spectrum'))
    return pd.DataFrame(rows),pd.DataFrame(cats).drop_duplicates(),pd.DataFrame(diagnostics)


def p2(run, config, sources, sample):
    rows,cats,diagnostics = [],[],[]
    for e in bounded(science(sources,'D11_P2'),sample):
        path=pin(run,config,e);f=cdflib.CDF(str(path))
        times=pd.DatetimeIndex(pd.to_datetime(cdflib.cdfepoch.to_datetime(f.varget('Epoch')),utc=True))
        if times.hasnans or times.has_duplicates or not times.is_monotonic_increasing:
            raise ValueError('Invalid P2 timestamps')
        xyz,attrs=cdf_values(f,'XYZ_SSE')
        if attrs['UNITS']!='Rm':raise ValueError('Changed P2 positions')
        strata,radius=position_groups(xyz)
        for name in ['thc_peif_densityQ','thc_peif_vthermalQ','thc_peif_vflowspeedQ','thc_fgs_btotal']:
            value,attrs=cdf_values(f,name)
            if attrs['DEPEND_0']!='Epoch' or len(value)!=len(times):raise ValueError('P2 time alignment')
            for group in ['all_positions',*sorted(set(strata))] if 'density' in name else ['all_positions']:
                keep=np.ones(len(times),bool) if group=='all_positions' else strata==group
                sid=f'P2_{path.stem.rsplit("_",1)[1]}_{name}_{group}'
                if keep.any():rows.append(daily_rows(sid,times[keep],value[keep]))
                cats.append(series(sid,'plasma','ARTEMIS_P2',name,attrs['UNITS'],
                    'published Q plasma + fill/valid range; FGM range only','spacecraft '+group+', not surface charging'))
        diagnostics.append({'file':path.name,'records':len(times),'first':times.min(),'last':times.max(),
            'median_spacing_s':np.median(np.diff(times.asi8)/1e9),'unknown_position_records':int((strata=='unknown_position').sum()),
            'minimum_radius_Rm':np.nanmin(radius),'maximum_radius_Rm':np.nanmax(radius)})
    return pd.concat(rows,ignore_index=True),pd.DataFrame(cats).drop_duplicates(),pd.DataFrame(diagnostics)


def esa(run, config, sources, sample, *, all_files=False, flag_diagnostics=False):
    rows,cats,diagnostics = [],[],[]
    entries=science(sources,'D11_ESA')
    selected=entries if all_files else monthly_edges(entries)
    for e in bounded(selected,sample):
        path=pin(run,config,e);f=cdflib.CDF(str(path))
        for mode in ['peif','peef','peir','peer','peib','peeb']:
            prefix='thb_'+mode
            if f.varinq(prefix+'_time').Last_Rec<0:
                diagnostics.append({'file':path.name,'mode':mode,'recorded':0,'quality_zero':0,'status':'empty_native_mode'})
                continue
            seconds,ta=cdf_values(f,prefix+'_time')
            if ta['UNITS']!='sec':raise ValueError('Changed ESA time units')
            times=pd.DatetimeIndex(pd.to_datetime(seconds,unit='s',utc=True))
            keep=nominal_day(times,path.name)
            clock_good=unique_clock(times)
            quality,qa=cdf_values(f,prefix+'_data_quality')
            if len(quality)!=len(times) or '0: Good data' not in qa['CATDESC']:
                raise ValueError('Changed ESA quality meaning/alignment')
            for variable in ['density','avgtemp','sc_pot']:
                name=prefix+'_'+variable
                value,attrs=cdf_values(f,name)
                if attrs.get('DEPEND_TIME')!=prefix+'_time' or len(value)!=len(times):
                    raise ValueError('ESA native value/time alignment changed')
                # Q variables are virtual with zero stored records: apply the published 0-good flag explicitly.
                value=np.where((quality==0)&clock_good,value,np.nan)
                sid='ESA_'+path.stem.rsplit('_',1)[1]+'_'+name
                if keep.any():rows.append(daily_rows(sid,times[keep],value[keep]))
                cats.append(series(sid,'plasma','ARTEMIS_P1_ESA',name,attrs['UNITS'],
                    'native numeric fields + quality==0 + fill/valid bounds + finite unique timestamps; no virtual-Q substitution',
                    ('spacecraft; all downloaded day files; potential is NOT regolith voltage' if all_files else
                     'spacecraft; sampled first/last available day per month; potential is NOT regolith voltage')))
            diagnostics.append({'file':path.name,'mode':mode,'recorded':len(times),'quality_zero':int((quality==0).sum()),
                'outside_nominal_day':int((~keep).sum()),'in_day_quality_zero':int(((quality==0)&keep).sum()),
                'ambiguous_or_missing_clock_records':int((~clock_good).sum()),'backward_clock_steps':int((np.diff(seconds)<0).sum()),
                'status':'native_quality_screened; file-boundary context outside nominal UTC day excluded explicitly',
                'median_spacing_s':np.median(np.diff(seconds)) if len(seconds)>1 else np.nan})
            if flag_diagnostics:
                flags,counts=np.unique(quality[keep & np.isfinite(quality)],return_counts=True)
                frequencies={str(int(flag)):int(count) for flag,count in zip(flags,counts)}
                frequencies['fill_or_out_of_range']=int((keep & ~np.isfinite(quality)).sum())
                diagnostics[-1].update({'nominal_day_records':int(keep.sum()),
                    'nominal_day_clock_supported_records':int((keep&clock_good).sum()),
                    'quality_flag_counts_in_nominal_day':json.dumps(frequencies,sort_keys=True)})
    return pd.concat(rows,ignore_index=True),pd.DataFrame(cats).drop_duplicates(),pd.DataFrame(diagnostics)


def nominal_day(times,filename):
    day=re.search(r'(20\d{6})',filename)
    if day is None:raise ValueError('No nominal UTC date')
    expected=pd.to_datetime(day[1],format='%Y%m%d',utc=True)
    return (times>=expected)&(times<expected+pd.Timedelta(days=1))


def unique_clock(times):
    """Retain chronology diagnostics; withhold ambiguous samples rather than double-weight them."""
    times=pd.DatetimeIndex(times)
    return ~times.isna() & ~times.duplicated(keep=False)


def hfe(run,config,sources,sample):
    rows,cats,diagnostics=[],[],[]
    for e in bounded(science(sources,'D28'),sample):
        path=pin(run,config,e);label=paired_path(run,config,sources,e)
        f=pd.concat(pds4_chunks(label,chunk_rows=20000),ignore_index=True)
        mission=re.match(r'(a\d+)(?:_\d{4})?(p\df\d)',path.stem)
        if mission is None:raise ValueError('Unknown HFE thermometer identity')
        epoch=pd.Timestamp('1970-12-31' if mission[1]=='a15' else '1971-12-31',tz='UTC')
        dates=pd.DatetimeIndex(epoch+pd.to_timedelta(f.Time,unit='ms'))
        dated=~dates.isna()
        good=f['flags'].eq(0)&dated
        for col in [n for n in f if n in ['T','TREF','TC1','TC2','TC3','TC4']]:
            values=f[col].where(good & f[col].gt(0) & np.isfinite(f[col]))
            sid='HFE_'+mission[1]+'_'+mission[2]+'_'+col
            rows.append(daily_rows(sid,dates[dated],values.loc[dated]))
            cats.append(series(sid,'thermal','Apollo_HFE',mission[1]+'_'+mission[2]+'_'+col,'K',
                'strict flags==0, finite positive temperature; other flags retained in diagnostics',
                'historical deployed thermometer, not polar or component temperature'))
        for flag,n in f['flags'].value_counts(dropna=False).items():
            flag_rows=f['flags'].eq(flag) if pd.notna(flag) else f['flags'].isna()
            diagnostics.append({'file':path.name,'first':dates.min(),'last':dates.max(),'flag':flag,'records':n,
                'undated_records':int((flag_rows&~dated).sum()),'note':'undated records retained here, not assigned invented calendar dates'})
    return pd.concat(rows,ignore_index=True),pd.DataFrame(cats).drop_duplicates(),pd.DataFrame(diagnostics)


def pds_table(run,config,sources,entry):
    path=pin(run,config,entry);label=paired_path(run,config,sources,entry)
    return path,pd.concat(pds4_chunks(label,chunk_rows=20000),ignore_index=True)


def ladee(run,config,sources,sample):
    rows,cats,diagnostics,current,nms=[],[],[],[],{}
    for e in bounded(science(sources,'D10'),sample):
        path,f=pds_table(run,config,sources,e)
        dates=pd.to_datetime(f.TIME,format='%Y-%jT%H:%M:%S.%f',utc=True)
        if path.name.startswith('current'):
            frame=f[['CURRENT','SIGNAL','BACKGROUND']].copy();frame['date']=dates
            current.append(frame)
        else:
            for (q,saturation),g in f.groupby(['QUALITY','SATURATED'],dropna=False):
                for col in ['MASS','MASS_THRESHOLD']:
                    diagnostics.append({'file':path.name,'kind':'mass','quality':q,'saturation':saturation,
                        'field':col,'unit':'kg',**describe(g[col]),'qualification':'quality classes not adopted as science-good without event-classification documentation'})
    if current:
        frame=pd.concat(current,ignore_index=True)
        # Weekly source files can share a UTC date. Aggregate native rows, never medians of partial-day medians.
        clock=unique_clock(frame.date)
        diagnostics.append({'kind':'LDEX_current_clock','ambiguous_or_missing_clock_records':int((~clock).sum()),'records':len(frame)})
        for col in ['CURRENT','SIGNAL','BACKGROUND']:
            sid='LDEX_'+col
            rows.append(daily_rows(sid,frame.date,frame[col].where(clock)))
            cats.append(series(sid,'dust','LADEE_LDEX',col,'elementary charges/s',
                'native calibrated currents + unique timestamps; signed/background-subtracted values retained','2013-2014 orbital context, not surface dust loading'))
    for e in bounded(monthly_edges(science(sources,'D35'),species=True),sample):
        path,f=pds_table(run,config,sources,e)
        dates=pd.to_datetime(f[['Year','Month','Day']].rename(columns={'Year':'year','Month':'month','Day':'day'}),utc=True)
        dates=pd.DatetimeIndex(dates+pd.to_timedelta(f.Hours*3600+f.Minutes*60+f.Seconds,unit='s'))
        col=next(n for n in f if n.endswith('_ABUNDANCE'))
        sid='NMS_'+col
        values=f[col].where(np.isfinite(f[col]) & f.Std.ge(0) & np.isfinite(f.Std))
        nms.setdefault(sid,[]).append(pd.DataFrame({'date':dates,'value':np.asarray(values)}))
        cats.append(series(sid,'exosphere','LADEE_NMS',col,'particles/cm3',
            'finite abundance and finite nonnegative reported Std; negative estimates retained explicitly',
            'first/last orbit per species/month; orbital historical, not surface or atmosphere safety'))
        diagnostics.append({'file':path.name,'kind':'NMS','field':col,'records':len(f),'negative_estimates':int((f[col]<0).sum()),
            'altitude_min_km':f.Altitude.min(),'altitude_max_km':f.Altitude.max(),'latitude_min':f.Latitude.min(),
            'latitude_max':f.Latitude.max(),'local_hour_min':f.Lmst.min(),'local_hour_max':f.Lmst.max()})
    for sid,frames in nms.items():
        frame=pd.concat(frames,ignore_index=True);clock=unique_clock(frame.date)
        diagnostics.append({'kind':'NMS_clock','field':sid,'records':len(frame),'ambiguous_or_missing_clock_records':int((~clock).sum())})
        rows.append(daily_rows(sid,frame.date,frame.value.where(clock)))
    return pd.concat(rows,ignore_index=True),pd.DataFrame(cats).drop_duplicates(),pd.DataFrame(diagnostics)


def binary_layout(label):
    """Decode direct fields and single-field repeated spectral groups from PDS4 byte positions."""
    root=ET.parse(label).getroot();t=root.find('.//{*}Table_Binary')
    if t is None:raise ValueError('Expected PDS4 binary table')
    record=t.find('{*}Record_Binary');length=int(record.findtext('{*}record_length'))
    types={'UnsignedByte':'u1','UnsignedMSB2':'>u2','UnsignedMSB4':'>u4','UnsignedMSB8':'>u8','IEEE754MSBDouble':'>f8'}
    names,formats,offsets=[],[],[]
    for field in record:
        kind=field.tag.split('}')[-1]
        if kind not in ['Field_Binary','Group_Field_Binary']:continue
        if kind=='Group_Field_Binary':
            children=field.findall('{*}Field_Binary')
            if len(children)!=1 or int(field.findtext('{*}groups'))!=0:raise ValueError('Unsupported binary group')
            child=children[0];offset=int(field.findtext('{*}group_location'))-1
            n=int(field.findtext('{*}repetitions'))
        else:child=field;offset=0;n=None
        name=child.findtext('{*}name');ty=child.findtext('{*}data_type');width=int(child.findtext('{*}field_length'))
        dt='S'+str(width) if ty=='ASCII_String' else types[ty]
        names.append(name);formats.append((dt,(n,)) if n else dt);offsets.append(offset+int(child.findtext('{*}field_location'))-1)
    return np.dtype({'names':names,'formats':formats,'offsets':offsets,'itemsize':length}),int(t.findtext('{*}offset')),int(t.findtext('{*}records'))


def lend(run,config,sources,sample):
    rows=[]
    for e in bounded(monthly_edges(science(sources,'D29')),sample):
        path=pin(run,config,e);label=paired_path(run,config,sources,e)
        dt,offset,n=binary_layout(label)
        if path.stat().st_size!=offset+n*dt.itemsize:raise ValueError('LEND binary byte count')
        f=np.memmap(path,mode='r',dtype=dt,offset=offset,shape=(n,))
        good=(f['POINTING']==1)&(f['INTERSECTING']==1)&(f['DATA_COLLECTION_TIME']>0)&(f['PARAMETERS_CHANGED']==0)
        good &= np.isfinite(f['LATITUDE']) & (np.abs(f['LATITUDE'])<=90) & np.isfinite(f['LONGITUDE'])
        for region,mask in [('all_track',good),('south_of_80S',good&(f['LATITUDE']<=-80))]:
            for name in ['SETN_SPECTRUM','CSETN1_SPECTRUM','CSETN2_SPECTRUM','CSETN3_SPECTRUM','CSETN4_SPECTRUM']:
                counts=np.asarray(f[name],float).sum(axis=1)
                rows.append({'file':path.name,'region':region,'channel':name,'records':n,'geometry_parameter_supported':int(mask.sum()),
                    **describe(counts[mask]),'unit':'sum of 16 raw spectral channels, counts/collection',
                    'nonzero_supported_records':int((counts[mask]>0).sum()),'science_response_qualified':False,
                    'scope':'first/last date per month; no background/deadtime/response correction or water abundance; all-zero channel is not absence of neutrons'})
        del f
    return pd.DataFrame(rows)


def regional_masks(lon,lat,bounds):
    tr=Transformer.from_crs(MOON_GEOGRAPHIC,MOON_CRS,always_xy=True)
    x,y=tr.transform(np.asarray(lon),np.asarray(lat))
    return {key:(x>=b[0])&(x<=b[2])&(y>=b[1])&(y<=b[3]) for key,b in bounds.items()}


def prp(run,config,sources,sample):
    e=science(sources,'D20_PRP')[0];pin(run,config,e);label=paired_path(run,config,sources,e)
    sums={};points=[];records=0
    for i,f in enumerate(pds4_chunks(label,columns=['tri_clon','tri_clat','temp_avg','temp_max','ice_depth'],chunk_rows=40000)):
        masks={'whole_south_product':np.ones(len(f),bool),**regional_masks(f.tri_clon,f.tri_clat,config['region_bounds_m'])}
        for key,mask in masks.items():
            g=f.loc[mask];s=sums.setdefault(key,{'records':0,'avg_sum':0.,'max_sum':0.,'valid_avg':0,'valid_max':0,'max_surface_K':-np.inf,'stable_surface_model':0,'excluded_ice_depth':0})
            a=g.temp_avg.where(g.temp_avg>0);b=g.temp_max.where(g.temp_max>0)
            s['records']+=len(g);s['avg_sum']+=a.sum();s['max_sum']+=b.sum();s['valid_avg']+=a.count();s['valid_max']+=b.count()
            if b.notna().any():s['max_surface_K']=max(s['max_surface_K'],float(b.max()))
            s['stable_surface_model']+=int(g.ice_depth.eq(0).sum());s['excluded_ice_depth']+=int((g.ice_depth.eq(-999)|g.ice_depth.isna()).sum())
        points.append(f.iloc[::200].copy());records+=len(f)
        if sample:break
    rows=[]
    for key,s in sums.items():
        if not s['valid_max']:s['max_surface_K']=np.nan
        rows.append({'region':key,**s,'mean_annual_2cm_K':s['avg_sum']/s['valid_avg'] if s['valid_avg'] else np.nan,
            'mean_model_surface_max_K':s['max_sum']/s['valid_max'] if s['valid_max'] else np.nan,
            'scope':'triangle centre inclusion, not full candidate footprint; two depths/statistics, NOT a temperature-cycle amplitude; model stability not detected ice'})
    return pd.DataFrame(rows),pd.concat(points,ignore_index=True),records


def lamp(run,config,sources,sample):
    rows=[];stride=config['lamp_stride'];maps=[]
    for band in (['long'] if sample else ['long','lya','off','on']):
        data={};transform=None;shape=None
        for category in ['ALBEDO','BRIGHTNESS','DATA_QUALITY','ERROR','EXPOSURE']:
            e=next(e for e in science(sources,'D32') if '/'+category+'/' in e['url'] and '_'+band+'_' in e['url'])
            pin(run,config,e);label=paired_path(run,config,sources,e,'.lbl');text=label.read_text()
            if category=='ERROR' and 'signal-to-noise' not in text:raise ValueError('LAMP ERROR is no longer SNR')
            if category=='DATA_QUALITY' and '0 = good data' not in text:raise ValueError('Changed LAMP quality definition')
            with rasterio.open(label) as r:
                if not np.isclose(r.crs.ellipsoid.semi_major_metre if hasattr(r.crs,'ellipsoid') else pds3_number(text,'A_AXIS_RADIUS')*1000,1737400):raise ValueError('Nonlunar LAMP CRS')
                if transform is not None and (r.transform!=transform or r.shape!=shape):raise ValueError('Unaligned LAMP map family')
                shape,transform=r.shape,r.transform
                raw=r.read(1,masked=True)[::stride,::stride]
                data[category]=np.ma.filled(raw,np.nan).astype(float)
        rr,cc=np.meshgrid(np.arange(0,shape[0],stride),np.arange(0,shape[1],stride),indexing='ij')
        x=transform.c+(cc+.5)*transform.a;y=transform.f+(rr+.5)*transform.e
        lon,lat=Transformer.from_crs(MOON_CRS,MOON_GEOGRAPHIC,always_xy=True).transform(x,y)
        domain=lat<=-80
        good=(data['DATA_QUALITY']==0)&(data['EXPOSURE']>0)&(data['ERROR']>=3)&domain
        masks={'south_polar_domain':domain}
        for key,b in config['region_bounds_m'].items():masks[key]=(x>=b[0])&(x<=b[2])&(y>=b[1])&(y<=b[3])&domain
        for key,mask in masks.items():
            valid=mask&good
            for category in ['ALBEDO','BRIGHTNESS','ERROR','EXPOSURE']:
                rows.append({'band':band,'region':key,'quantity':category,'sampled_domain_pixels':int(mask.sum()),
                    'quality_supported_pixels':int(valid.sum()),**describe(data[category][valid]),'stride':stride,
                    'scope':'historical cumulative, 240 m native pixel; ERROR=SNR, not error bar; not local UV irradiance'})
        maps.append((band,data['ALBEDO'],good))
    return pd.DataFrame(rows),maps


def seismic(run,config,sources,sample):
    entries=[e for e in science(sources,'D14_PSE') if '.mhz.' in e['url'] or '.att.' in e['url']]
    if sample:
        dates=sorted({re.search(r'\.(197[34]\.\d{3})\.',e['url'])[1] for e in entries})
        entries=[e for e in entries if any('.'+d+'.' in e['url'] for d in [dates[0],dates[-1]])]
    response=pin(run,config,next(e for e in sources['D14_PSE'] if e['url'].endswith('.sxml')))
    inv=read_inventory(str(response),format='STATIONXML');rows=[]
    for e in entries:
        path=pin(run,config,e);paired_path(run,config,sources,e)
        for t in read(str(path),format='MSEED'):
            v=np.asarray(t.data,dtype=float);good=np.isfinite(v)&(v!=-1)
            row={'file':path.name,'trace_id':t.id,'start':str(t.stats.starttime),'stop':str(t.stats.endtime),
                'samples':len(v),'valid_samples':int(good.sum()),'sampling_rate_Hz':t.stats.sampling_rate,'missing_code':-1,
                'scope':'nominal archive timing; no event detection or hazard rate; raw counts not ground acceleration'}
            if t.stats.channel=='ATT':
                delta=np.diff(v);pairs=good[:-1]&good[1:];positive=delta[pairs&(delta>0)]
                row.update({'quantity':'timing','nonpositive_steps':int((delta[pairs]<=0).sum()),
                    'median_positive_step_s':float(np.median(positive)) if len(positive) else np.nan,
                    'maximum_positive_step_s':float(positive.max()) if len(positive) else np.nan})
            else:
                x=v[good];centre=float(np.median(x)) if len(x) else np.nan
                try:
                    a=inv.get_response(t.id,t.stats.starttime);b=inv.get_response(t.id,t.stats.endtime)
                    response_ok=a.instrument_sensitivity is not None and b.instrument_sensitivity is not None
                except ValueError:
                    response_ok=False
                row.update({'quantity':'MHZ_raw','response_at_both_ends':response_ok,'raw_median':centre,
                    'demeaned_rms_counts':float(np.sqrt(np.mean((x-centre)**2))) if len(x) else np.nan,
                    'p95_absolute_deviation_counts':float(np.quantile(np.abs(x-centre),.95)) if len(x) else np.nan})
            rows.append(row)
    return pd.DataFrame(rows)


def pdf_cases(run,config):
    path=Path(config['pdf_review_pages']);run.input(path)
    reviewed=json.loads(path.read_text());rows=[]
    cases=[('a08-biomed_eval.pdf','radiation',[74,77],'calibration and instrument cross-checks','low/zero reading cannot certify zero exposure'),
        ('A16_MissionReport.pdf','thermal/dust',[28,30],'shroud/dust effects and heat-flow cable failure','failed deployment is not a temperature observation'),
        ('Apollo_17_Postflight_Mission_Report_19730015117.pdf','thermal/exosphere',[40,41],'outgassing, background and thermally restricted operations','operational gaps and contaminated signals need explicit context'),
        ('A16_MissionReport.pdf','seismic',[28,29],'crew/rover and deliberate-source signals','waveforms without event attribution do not establish natural-event rates'),
        ('as10-day4-pt13.pdf','terrain/illumination',[7],'lighting-dependent orbital visibility','visual appearance is not local irradiance or a surface darkness history'),
        ('a10-mission-rules-19690415.pdf','requirements',[276],'historical confirmed-event/measurement decision structure','historical dose values are not current limits'),
        ('as10-day6-pt25.pdf','equipment',[47],'journal account of fuel-cell cooling failure','secondary diagnosis needs primary corroboration; no modern hardware default')]
    for name,category,pages,observation,limit in cases:
        record=next(x for x in reviewed if x['file']==name)
        if not set(pages)<={p['pdf_page'] for p in record['pages']}:raise ValueError('Unreviewed PDF page')
        external_metadata(run,Path(config['external_root']),Path(config['external_root'])/'keep'/name)
        rows.append({'pdf':name,'category':category,'pdf_pages_1_based':','.join(map(str,pages)),
            'observed_or_documented_case':observation,'eda_implication_not_implemented_gate':limit,
            'basis':'targeted reviewed text, not a new quantitative response model','candidate_safety_status':'Unknown'})
    return pd.DataFrame(rows)


def execute(sample=False):
    config=json.loads(CONFIG.read_text());stage='analysis/stage3_acquired_environment'+('_sample' if sample else '')
    if config['schema']!=1:raise ValueError('Unknown acquired EDA schema')
    with LocalRun(ROOT,stage,config,NOTEBOOK) as run:
        run.record['packages'].update({'cdflib':cdflib.__version__,'netCDF4':netCDF4.__version__,
                                       'obspy':sys.modules['obspy'].__version__})
        for path in [CONFIG,Path(__file__),Path(__file__).with_name('stage3_temporal_eda.py'),LOCAL/'EDA/shared/research_p1_readers.py']:
            run.input(path)
        sources=catalog(run,config);tables={};parts=[];cats=[];counts=[]
        for name,reader in [('see',see),('p2',p2),('esa',esa),('hfe',hfe),('ladee',ladee)]:
            print('Reading',name,flush=True)
            run.path('progress.json').write_text(json.dumps({'phase':name,'sample':sample}))
            daily,cat,info=reader(run,config,sources,sample)
            parts.append(daily);cats.append(cat);tables[name+'_file_diagnostics']=info
            counts.append({'category':name,'daily_rows':len(daily),'series':len(cat)})
            run.save()
        daily=pd.concat(parts,ignore_index=True);daily['date']=pd.to_datetime(daily.date,utc=True)
        catalog_frame=pd.concat(cats,ignore_index=True).drop_duplicates()
        if daily.duplicated(['series_id','date']).any():raise ValueError('Overlapping source days; aggregation requires explicit review')
        # Some geometry strata have no rows in a bounded sample: do not invent observations.
        catalog_frame=catalog_frame.loc[catalog_frame.series_id.isin(daily.series_id)].copy()
        if catalog_frame.series_id.duplicated().any():raise ValueError('Series identity changed across inputs')
        tables.update({'daily_context':daily,'series_catalog':catalog_frame,
            'monthly_context':period_summary(daily,'M'),'quarterly_context':period_summary(daily,'Q'),
            'temporal_support':support_table(daily,catalog_frame)})
        old=LOCAL/'data/processed/analysis'/config['previous_temporal_run']
        prior=pd.read_csv(accepted_input(run,old,'daily_context.csv'))
        prior['date']=pd.to_datetime(prior.date,utc=True)
        compare=pd.concat([daily.loc[daily.series_id.str.startswith(('SEE_','P2_'))],prior.loc[prior.series_id.eq('RAD_CRATER_SEC_selected_state')]],ignore_index=True)
        pivot=compare.pivot(index='date',columns='series_id',values='daily_median');associations=[]
        uv=[c for c in pivot if c.startswith('SEE_')];context=[c for c in pivot if c=='RAD_CRATER_SEC_selected_state' or ('densityQ_all_positions' in c)]
        for a in uv:
            for b in context:
                pair=pivot[[a,b]].dropna();n=len(pair)
                associations.append({'solar_series':a,'context_series':b,'paired_valid_dates':n,
                    'spearman_descriptive':pair[a].corr(pair[b],method='spearman') if n>=30 and pair[a].nunique()>1 and pair[b].nunique()>1 else np.nan,
                    'interpretation':'matched UTC daily summaries, not co-location, causality, forecast or candidate safety; no significance claim'})
        tables['concurrent_daily_associations']=pd.DataFrame(associations)
        run.path('progress.json').write_text(json.dumps({'phase':'LEND_PRP_LAMP','sample':sample}))
        print('Reading LEND monthly edge dates',flush=True);tables['lend_sampled_spectra']=lend(run,config,sources,sample)
        print('Reading PRP triangles',flush=True);tables['prp_region_context'],points,n=prp(run,config,sources,sample)
        print('Reading LAMP support',flush=True);tables['lamp_supported_maps'],maps=lamp(run,config,sources,sample)
        run.path('progress.json').write_text(json.dumps({'phase':'seismic','sample':sample}))
        print('Reading MHZ and ATT',flush=True);tables['seismic_daily_support']=seismic(run,config,sources,sample)
        tables['pdf_operational_cases']=pdf_cases(run,config);tables['category_execution']=pd.DataFrame(counts)
        used=pd.DataFrame(run.record['science_cohort'].values())
        tables['cohort_coverage']=pd.DataFrame([{'dataset':key,'downloaded_science_files_in_pinned_plan':len(science(sources,key)),
            'analysed_science_files':int(used.dataset.eq(key).sum()),'selection':config['cohorts'][key],
            'sample_run':sample,'all_downloaded_files_analysed':int(used.dataset.eq(key).sum())==len(science(sources,key))}
            for key in config['cohorts']])
        for name,frame in tables.items():frame.to_csv(run.path(name+'.csv'),index=False)
        chosen=catalog_frame.loc[catalog_frame.series_id.str.contains('FUV|EUV|densityQ_all_positions|a15_p1f1_T|a17_p1f1_T')]
        for row in chosen.to_dict('records'):
            m=tables['monthly_context'].loc[tables['monthly_context'].series_id.eq(row['series_id'])]
            fig,axes=plt.subplots(2,1,figsize=(10,5),sharex=True,layout='constrained')
            dates=pd.to_datetime(m.period_start_utc,utc=True)
            axes[0].plot(dates,m.median_of_daily_medians,marker='.',label='Median of valid daily medians')
            axes[0].set(ylabel=row['unit'],title=row['series_id']+'; historical context, NOT safety')
            axes[1].bar(dates,m.valid_day_fraction,width=20);axes[1].set(ylabel='Valid-day fraction',ylim=(0,1.05))
            save_figure(run,fig,'monthly_'+row['series_id'])
        fig,ax=plt.subplots(figsize=(7,6),layout='constrained')
        im=ax.scatter(points.tri_clon,points.tri_clat,c=points.temp_max.where(points.temp_max>0),s=1)
        ax.set(xlabel='East longitude',ylabel='Latitude',title='Systematic triangle-centre display; model surface maximum K')
        fig.colorbar(im,ax=ax);save_figure(run,fig,'prp_model_overview')
        for band,albedo,good in maps:
            fig,ax=plt.subplots(figsize=(6,6),layout='constrained');im=ax.imshow(np.where(good,albedo,np.nan))
            ax.set(title='LAMP '+band+'; supported albedo, stride '+str(config['lamp_stride']));fig.colorbar(im,ax=ax)
            save_figure(run,fig,'lamp_'+band+'_supported')
        findings={'sample':sample,'scope':config['scope'],'cohorts':config['cohorts'],'tables':{k:len(v) for k,v in tables.items()},
            'series':len(catalog_frame),'prp_triangles_read':n,'candidate_operational_status':'Unknown',
            'new_safety_thresholds':False,'pipeline_source_pins_changed':False,
            'holds':['ESA/LEND/NMS are predefined sparse monthly cohorts, not full downloaded collections or event censuses',
                'SEE includes model-filled bins and flare removal; positive-bin bands are screening, not qualified local exposure',
                'Plasma moment modes and spacecraft positions are distinct; no density-to-safety or spacecraft-to-surface-voltage conversion',
                'HFE strict zero-flag selection is conservative; thermal depth and instrument histories differ',
                'PSE MHZ/ATT raw diagnostics are not response-corrected shaking, earthquake counts or local hazard probabilities',
                'PRP model stability and raw LEND spectra do not establish detected or recoverable water ice',
                'LAMP ERROR is SNR; quality/exposure masks do not make albedo surface UV dose',
                'LADEE orbital currents/mass/abundance and reviewed mission cases are historical context, not modern candidate observations']}
        run.path('findings.json').write_text(json.dumps(findings,indent=2))
        run.path('progress.json').write_text(json.dumps({'phase':'complete','sample':sample}))
        folder=run.directory
    print(json.dumps(findings,indent=2),flush=True)
    return folder,findings


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--sample',action='store_true')
    print(execute(parser.parse_args().sample)[0])
