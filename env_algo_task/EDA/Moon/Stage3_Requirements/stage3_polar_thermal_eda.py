"""Native PRP triangle area/support, thermal tails and model-resource applicability."""
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
from pyproj import Transformer

import stage3_acquired_eda as acquired
from decision_eda import accepted_input
from environment_workflow import LocalRun
from research_p1_readers import pds4_chunks
from notebooks.shared.processing import MOON_CRS,MOON_GEOGRAPHIC
from stage3_mission_eda import LOCAL,ROOT,save_figure

CONFIG=Path(__file__).with_name('stage3_subject_config.json')
NOTEBOOK='Moon/Stage3_Requirements/Dar_050_polar_thermal_model_support.ipynb'


def triangle_area(vertices):
    """Euclidean area of a native 3-D triangular facet, km^2 -> m^2; not geodesic ROI area."""
    v=np.asarray(vertices,float)
    if v.ndim!=3 or v.shape[1:]!=(3,3):raise ValueError('Need N x 3 vertices x 3 coordinates')
    return np.linalg.norm(np.cross(v[:,1]-v[:,0],v[:,2]-v[:,0]),axis=1)*.5e6


def histogram_state(edges):
    e=np.asarray(edges,float)
    if not np.isfinite(e).all() or not (np.diff(e)>0).all():raise ValueError('Ordered finite bin edges required')
    return {'edges':e,'counts':np.zeros(len(e)-1,dtype='int64'),'areas':np.zeros(len(e)-1),
        'count':0,'area':0.,'sum':0.,'weighted_sum':0.,'minimum':np.inf,'maximum':-np.inf,
        'under_count':0,'over_count':0,'under_area':0.,'over_area':0.}


def add_histogram(state,values,areas):
    x,w=np.asarray(values,float),np.asarray(areas,float)
    good=np.isfinite(x)&np.isfinite(w)&(w>0);x,w=x[good],w[good]
    if not len(x):return
    e=state['edges'];state['counts']+=np.histogram(x,e)[0];state['areas']+=np.histogram(x,e,weights=w)[0]
    state['count']+=len(x);state['area']+=w.sum();state['sum']+=x.sum();state['weighted_sum']+=np.dot(x,w)
    state['minimum']=min(state['minimum'],x.min());state['maximum']=max(state['maximum'],x.max())
    for name,mask in [('under',x<e[0]),('over',x>e[-1])]:
        state[name+'_count']+=int(mask.sum());state[name+'_area']+=w[mask].sum()


def quantile_interval(state,q,weighted=False):
    """Histogram interval only, preserving tails; no claim of exact within-bin quantile."""
    if not 0<=q<=1:raise ValueError('Quantile outside [0,1]')
    total=state['area'] if weighted else state['count']
    if total<=0:return np.nan,np.nan
    hist=state['areas'] if weighted else state['counts'];under=state['under_area'] if weighted else state['under_count']
    over=state['over_area'] if weighted else state['over_count'];e=state['edges'];target=q*total
    if under>0 and target<=under:return state['minimum'],e[0]
    if over>0 and target>total-over:return e[-1],state['maximum']
    i=int(np.flatnonzero(hist>0)[0]) if target==0 else min(np.searchsorted(np.cumsum(hist)+under,target,side='left'),len(hist)-1)
    return e[i],e[i+1]


def state_row(state):
    n,a=state['count'],state['area']
    result={'supported_triangles':n,'native_facet_area_m2':a,'triangle_weighted_mean':state['sum']/n if n else np.nan,
        'facet_area_weighted_mean':state['weighted_sum']/a if a else np.nan,
        'minimum':state['minimum'] if n else np.nan,'maximum':state['maximum'] if n else np.nan,
        'underflow_triangles':state['under_count'],'overflow_triangles':state['over_count']}
    for q in [.05,.5,.95,.99]:
        for weighted,label in [(False,'triangle'),(True,'facet_area')]:
            low,high=quantile_interval(state,q,weighted)
            result[f'{label}_p{int(q*100):02d}_lower']=low;result[f'{label}_p{int(q*100):02d}_upper']=high
    return result


def proposals():
    definitions=[
        ('PT-G01','evidence_guard','Keep thermal statistic, depth and model epoch distinct','annual mean at 2 cm, annual surface maximum, model version and time applicability','E01 E02 E03','Do not subtract unlike depth/statistics as a cycle amplitude or invent monthly temperatures from a static product'),
        ('PT-G02','evidence_guard','Native facet and footprint support before candidate claims','native mesh geometry/resolution, ROI inclusion/clipping, actual mission footprint','E01 E02 E13','Region bounding-box/triangle-centre context is not validated whole-candidate coverage or buildable area'),
        ('PT-H01','conditional_hard_constraint','Applicable component thermal envelope','local chronological boundary conditions, contact/material response, operating period and qualified component limits','E02 E03 E06','Failed if qualified applicable component temperatures exceed a mandatory envelope; Passed only with sufficient evidence; otherwise Unknown'),
        ('PT-S01','conditional_soft_preference','Lower qualified thermal-control burden','all mandatory conditions Passed, comparable mission, local heat balance, power/installation costs','E02 E13','Prefer a qualified operational burden, not universally colder terrain or smaller raw surface maximum'),
        ('PT-G03','evidence_guard','Ice stability is not detection or extraction feasibility','model definition/depth domain, corroborating composition, abundance and extraction response','E01 E13','Zero model stability depth is not detected ice; excluded depth is not no ice; thermal stability does not prove recoverable resources')]
    return pd.DataFrame([{'id':id,'classification':kind,'title':title,'required_inputs':inputs,'existing_rule_crosswalk':old,
        'decision_logic':logic,'quantity':'surface maximum K; annual mean at 2 cm K; model ice stability depth m',
        'unit':'K; m; native 3-D facet area m2','applicability':'static south-PRP model and centre-selected regional boxes, not requested mission time/footprint',
        'source':'D20_PRP PDS4 field descriptions and inapplicable Time_Coordinates; accepted Dar035/Dar044 thermal quality context',
        'evidence':'native_model_statistics.csv; regional_support.csv; resource_depth_classes.csv; field_time_applicability.csv; crosscheck_Dar044.csv',
        'limit_value':np.nan,'limit_state':'not_adopted','preference_weight':np.nan,'current_outcome':'Unknown',
        'status':'Stage 4 proposal only; not consumed by pipeline'} for id,kind,title,inputs,old,logic in definitions])


def execute(sample=False):
    subject=json.loads(CONFIG.read_text());config=json.loads(CONFIG.with_name(subject['acquisition_config']).read_text())
    with LocalRun(ROOT,'analysis/subject_polar_thermal'+('_sample' if sample else ''),subject,NOTEBOOK) as run:
        for p in [CONFIG,Path(__file__),acquired.CONFIG,Path(acquired.__file__)]:run.input(p)
        sources=acquired.catalog(run,config);e=acquired.science(sources,'D20_PRP')[0]
        path=acquired.pin(run,config,e);label=acquired.paired_path(run,config,sources,e);xml=ET.parse(label).getroot()
        fields=[]
        for f in xml.findall('.//{*}Field_Character'):
            fields.append({'field':f.findtext('{*}name'),'unit':f.findtext('{*}unit'),'meaning':' '.join((f.findtext('{*}description') or '').split()),
                'dated_time_series':False,'time_start':xml.findtext('.//{*}Time_Coordinates/{*}start_date_time'),
                'time_stop':xml.findtext('.//{*}Time_Coordinates/{*}stop_date_time'),
                'time_nil_reason':xml.find('.//{*}Time_Coordinates/{*}start_date_time').get('nilReason'),
                'calendar_use':'not applicable: model annual statistics; no fabricated monthly/yearly chronology'})
        states={};support={};resources={};scatter=[];records=0
        transform=Transformer.from_crs(MOON_GEOGRAPHIC,MOON_CRS,always_xy=True)
        columns=[f'tri{i}_{axis}' for i in [1,2,3] for axis in ['x','y','z']]+['tri_clon','tri_clat','temp_avg','temp_max','ice_depth']
        for chunk,f in enumerate(pds4_chunks(label,columns=columns,chunk_rows=40000)):
            vertices=f[[n for n in columns if n.startswith(('tri1_','tri2_','tri3_'))]].to_numpy().reshape(-1,3,3)
            area=triangle_area(vertices);area_good=np.isfinite(area)&(area>0)
            masks={'whole_south_product':np.ones(len(f),bool),**acquired.regional_masks(f.tri_clon,f.tri_clat,config['region_bounds_m'])}
            lon=np.degrees(np.arctan2(vertices[:,:,1],vertices[:,:,0]));lat=np.degrees(np.arctan2(vertices[:,:,2],np.hypot(vertices[:,:,0],vertices[:,:,1])))
            vx,vy=transform.transform(lon,lat)
            for region,mask in masks.items():
                g=f.loc[mask];a=area[mask]
                s=support.setdefault(region,{'triangles':0,'positive_area_triangles':0,'native_facet_area_m2':0.,'not_wholly_inside_ROI':0})
                s['triangles']+=len(g);s['positive_area_triangles']+=int(area_good[mask].sum());s['native_facet_area_m2']+=float(a[area_good[mask]].sum())
                if region!='whole_south_product':
                    b=config['region_bounds_m'][region];inside=((vx>=b[0])&(vx<=b[2])&(vy>=b[1])&(vy<=b[3])).all(axis=1)
                    s['not_wholly_inside_ROI']+=int((mask&~inside).sum())
                for name,edges in [('temp_avg',np.arange(0,451)),('temp_max',np.arange(0,451)),('ice_depth',np.arange(0,2.9001,.025)),('facet_area',np.geomspace(1,1e8,141))]:
                    state=states.setdefault((region,name),histogram_state(edges))
                    values=a if name=='facet_area' else g[name].to_numpy()
                    valid=(values>=0) if name=='ice_depth' else (values>0)
                    add_histogram(state,np.where(valid,values,np.nan),a)
                ice=g.ice_depth.to_numpy();valid=np.isfinite(ice)&(ice>=0)
                for name,keep in [('model_surface_stable',valid&(ice==0)),('model_positive_depth',valid&(ice>0)),('excluded_or_unknown_depth',~valid)]:
                    r=resources.setdefault((region,name),{'triangles':0,'native_facet_area_m2':0.})
                    r['triangles']+=int(keep.sum());r['native_facet_area_m2']+=float(a[keep&area_good[mask]].sum())
                if region!='whole_south_product':
                    scatter.append(g[['tri_clon','tri_clat','temp_avg','temp_max','ice_depth']].assign(region=region,native_facet_area_m2=a))
            records+=len(f)
            if chunk%20==0:print('PRP triangles read:',records,flush=True)
            if sample:break
        stats=[];hist=[]
        for (region,name),state in states.items():
            stats.append({'region':region,'field':name,**state_row(state),'summary_scope':'native facets selected by centre; area not clipped to ROI; quantiles are histogram intervals'})
            for i,(count,a) in enumerate(zip(state['counts'],state['areas'])):
                hist.append({'region':region,'field':name,'bin_left':state['edges'][i],'bin_right':state['edges'][i+1],
                    'triangles':count,'native_facet_area_m2':a,'bin_rule':'left-closed, right-open except last bin includes right edge; tails in statistics'})
        supports=pd.DataFrame([{'region':key,**value,'area_scope':'3-D native facet area, selected by triangle centre; not clipped ROI/geodesic/buildable area'} for key,value in support.items()])
        resource=pd.DataFrame([{'region':region,'depth_class':kind,**value,'meaning':'model sublimation-stability depth, not detection, abundance or recoverability'} for (region,kind),value in resources.items()])
        previous=pd.read_csv(accepted_input(run,LOCAL/'data/processed/analysis'/subject['screening_run'],'prp_region_context.csv'))
        rows=[]
        for old in previous.to_dict('records'):
            region=old['region'];a=states[region,'temp_avg'];b=states[region,'temp_max']
            rows.append({'region':region,'old_triangles':old['records'],'new_triangles':support[region]['triangles'],
                'absolute_mean_2cm_difference_K':abs(a['sum']/a['count']-old['mean_annual_2cm_K']) if a['count'] else np.nan,
                'absolute_surface_max_difference_K':abs(b['maximum']-old['max_surface_K']) if b['count'] else np.nan,
                'scope':'sample only' if sample else 'identical original triangle-count-weighted semantics; area weighting is separately named'})
        checks=pd.DataFrame(rows)
        if not sample and (not checks.old_triangles.eq(checks.new_triangles).all() or checks[['absolute_mean_2cm_difference_K','absolute_surface_max_difference_K']].max().max()>1e-9):raise ValueError('PRP old regional semantics changed')
        points=pd.concat(scatter,ignore_index=True) if scatter else pd.DataFrame(columns=['region','temp_avg','temp_max','ice_depth'])
        tables={'native_model_statistics':pd.DataFrame(stats),'native_model_histograms':pd.DataFrame(hist),
            'regional_support':supports,'resource_depth_classes':resource,'regional_triangle_values':points,
            'field_time_applicability':pd.DataFrame(fields),'crosscheck_Dar044':checks,'stage4_polar_thermal_proposals':proposals()}
        for name,frame in tables.items():frame.to_csv(run.path(name+'.csv'),index=False)
        fig,axes=plt.subplots(2,1,figsize=(12,7),layout='constrained')
        for region,g in points.groupby('region'):
            axes[0].scatter(g.temp_avg,g.temp_max,s=2,alpha=.25,label=region.split('_',3)[-1])
            valid=g.ice_depth.notna()&g.ice_depth.ge(0)
            axes[1].scatter(g.loc[valid,'temp_max'],g.loc[valid,'ice_depth'],s=2,alpha=.25)
        axes[0].set(xlabel='Annual mean at 2 cm K',ylabel='Annual surface maximum K',title='Unlike depth/statistics: NOT a thermal-cycle amplitude');axes[0].legend(fontsize=6,ncol=2)
        axes[1].set(xlabel='Annual surface maximum K',ylabel='Model stability depth m',title='Thermal-stability model only; missing/excluded depth is not no ice');save_figure(run,fig,'thermal_resource_model_context')
        fig,axes=plt.subplots(1,2,figsize=(12,5),layout='constrained')
        for region in sorted(support):
            state=states[region,'temp_max'];mid=(state['edges'][:-1]+state['edges'][1:])/2
            if state['count']:axes[0].plot(mid,state['counts']/state['count'],label=region)
            if state['area']:axes[1].plot(mid,state['areas']/state['area'],label=region)
        axes[0].set(xlabel='Surface annual maximum K',ylabel='Triangle fraction/bin',title='Equal triangle weight')
        axes[1].set(xlabel='Surface annual maximum K',ylabel='Native facet-area fraction/bin',title='Area weight; not clipped candidate footprint')
        axes[0].legend(fontsize=5);save_figure(run,fig,'surface_max_weighting_comparison')
        findings={'subject':'polar_thermal','sample':sample,'native_triangles':records,'tables':{name:len(f) for name,f in tables.items()},
            'time_applicability':'provider start/stop explicitly inapplicable; annual model statistics cannot supply calendar histories',
            'base_conclusion':'Spatial/model thermal tails, mesh support and ice-stability context are available. Unlike depth/statistics, unvalidated footprints and absent chronological response prevent component thermal or resource-operability conclusions.',
            'full_source_scope':'all selected native south PRP facets' if not sample else 'first 40000 facets only; regional support can be absent',
            'pipeline_changed':False,'adopted_limits':False,'operational_status':'Unknown',
            'remaining':['Mission-local chronological thermal forcing and component response','Validated actual candidate footprint/mesh association','Corroborated abundance and extraction/capability for resources','Other subjects and integrated Stage 4 synthesis']}
        run.path('findings.json').write_text(json.dumps(findings,indent=2));folder=run.directory
    print(json.dumps(findings,indent=2),flush=True);return folder,findings


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--sample',action='store_true')
    print(execute(parser.parse_args().sample)[0])
