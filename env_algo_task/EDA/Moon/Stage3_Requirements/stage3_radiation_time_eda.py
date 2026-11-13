"""Radiation calendar support, descriptive upper-tail segments and solar covariation checks."""
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

from decision_eda import accepted_input
from environment_workflow import LocalRun
from environment_time import calendar_summary,fixed_month_comparison
from stage3_mission_eda import LOCAL,ROOT,save_figure

CONFIG=Path(__file__).with_name('stage3_subject_config.json')
NOTEBOOK='Moon/Stage3_Requirements/Dar_049_radiation_calendar_extremes.ipynb'


def upper_tail_segments(daily,quantile=.95):
    """Descriptive consecutive observed high-summary dates, not physical event detection or duration."""
    if not 0<quantile<1:raise ValueError('Choose an interior descriptive quantile')
    thresholds,segments=[],[]
    for sid,g in daily.groupby('series_id'):
        g=g.sort_values('date');values=g.daily_max.dropna();threshold=values.quantile(quantile)
        selected=g.daily_max.gt(threshold)&g.daily_max.notna()
        thresholds.append({'series_id':sid,'quantile':quantile,'sample_daily_max_quantile':threshold,
            'valid_daily_max_dates':len(values),'strictly_above_dates':int(selected.sum()),
            'threshold_role':'sample distribution tag, NOT a physical hazard or operational safety limit'})
        high=g.loc[selected].copy()
        if high.empty:continue
        groups=high.date.diff().ne(pd.Timedelta(days=1)).cumsum()
        for _,part in high.groupby(groups):
            first,last=part.date.min(),part.date.max()
            segments.append({'series_id':sid,'start_utc_day':first,'last_observed_utc_day':last,
                'consecutive_high_summary_dates':len(part),'maximum_reported_daily_max':part.daily_max.max(),
                'sample_daily_max_quantile':threshold,'first_selected_date_in_source':first==g.date.min(),
                'last_selected_date_in_source':last==g.date.max(),
                'interpretation':'consecutive observed high daily summaries; missing/unsupported dates split segments; not event duration, independent event count or dose'})
    columns=['series_id','start_utc_day','last_observed_utc_day','consecutive_high_summary_dates',
             'maximum_reported_daily_max','sample_daily_max_quantile','first_selected_date_in_source','last_selected_date_in_source','interpretation']
    return pd.DataFrame(thresholds),pd.DataFrame(segments,columns=columns)


def correlation(a,b):
    return a.corr(b,method='spearman') if len(a)>=30 and a.nunique()>1 and b.nunique()>1 else np.nan


def solar_association(daily,solar):
    rows=[];pairs=[]
    s=solar[['date','daily_median']].rename(columns={'daily_median':'solar_daily_band'})
    if s.date.duplicated().any():raise ValueError('Solar comparison must use one qualified band/day')
    for sid,g in daily.groupby('series_id'):
        pair=g[['date','daily_median']].merge(s,on='date',validate='one_to_one').dropna().sort_values('date')
        pair['series_id']=sid;pairs.append(pair)
        for label,part in [('all_common_dates',pair),*[(str(year),part) for year,part in pair.groupby(pair.date.dt.year)]]:
            consecutive=part.date.diff().eq(pd.Timedelta(days=1))
            a,b=part.daily_median.diff().loc[consecutive],part.solar_daily_band.diff().loc[consecutive]
            rows.append({'series_id':sid,'comparison_window':label,'paired_valid_dates':len(part),
                'spearman_daily_levels':correlation(part.daily_median,part.solar_daily_band),
                'consecutive_daily_difference_pairs':int(consecutive.sum()),'spearman_daily_first_differences':correlation(a,b),
                'interpretation':'descriptive levels/year strata/consecutive-day differences; no causal, significance, dose or forecasting model'})
    return pd.DataFrame(rows),pd.concat(pairs,ignore_index=True)


def proposals():
    definitions=[
        ('RA-G01','evidence_guard','Preserve radiation quantity, detector and orbit','counter/flux/dose identity, platform, energy, response/version, acquisition quality','E04 E10 E11 E12','GOES is Earth-orbit space-weather context; LRO orbital counters are not local shielded crew dose. Do not pool channels or use Earth climate as lunar conditions'),
        ('RA-G02','evidence_guard','Upper-tail tags are not detected hazardous events','native subdaily field/response, valid timing/live time, event definition and attribution','E04 E10 E14','Daily quantile segments describe observed summaries only; gaps split them; no event rate/duration, absence-of-event or safe-month inference'),
        ('RA-H01','conditional_hard_constraint','Applicable crew/equipment radiation envelope','local field and secondary transport, shielding/configuration, exposure duration, qualified response and adopted applicable limit','E04 E06 E10','Failed if qualified applicable demand exceeds a mandatory limit; Passed only with sufficient applicable evidence; otherwise Unknown. A preference cannot compensate for a mandatory failure'),
        ('RA-S01','conditional_soft_preference','Lower qualified radiation-protection burden','mandatory conditions Passed, comparable activities, transport/response-based protection/EVA/shelter burden','E04 E13','Prefer supported operational burden, not raw minimum counter/flux or universally thicker shielding'),
        ('RA-G03','evidence_guard','Calendar/solar associations are descriptive','same qualified dates, instrument support, common-time trend, appropriate geometry and response','E14 E15 E16','Compare levels with within-year and consecutive-day differences; agreement does not establish cause or calibrate dose')]
    return pd.DataFrame([{'id':id,'classification':kind,'title':title,'required_inputs':inputs,'existing_rule_crosswalk':old,
        'decision_logic':logic,'quantity':'instrument-specific counts/flux, or qualified local response-specific dose as applicable',
        'unit':'source catalog units; no counts/flux-to-dose substitution','applicability':'source orbit/epoch; local lunar mission applicability must be established',
        'source':'accepted Dar041/Dar043 quality and instrument metadata; Dar044 contemporary SEE; existing E04/E10-E16 evidence guards',
        'evidence':'series_catalog.csv; calendar_context.csv; descriptive_upper_tail_thresholds.csv; observed_upper_tail_segments.csv; solar_associations.csv',
        'limit_value':np.nan,'limit_state':'not_adopted','preference_weight':np.nan,'current_outcome':'Unknown',
        'status':'Stage 4 proposal only; not consumed by pipeline'} for id,kind,title,inputs,old,logic in definitions])


def execute(sample=False):
    subject=json.loads(CONFIG.read_text())
    with LocalRun(ROOT,'analysis/subject_radiation_time'+('_sample' if sample else ''),subject,NOTEBOOK) as run:
        for p in [CONFIG,Path(__file__),LOCAL/'EDA/shared/environment_time.py']:run.input(p)
        oldfolder=LOCAL/'data/processed/analysis'/subject['temporal_run']
        daily=pd.read_csv(accepted_input(run,oldfolder,'daily_context.csv'));daily=daily.loc[daily.series_id.str.startswith('RAD_')].copy()
        daily['date']=pd.to_datetime(daily.date,utc=True)
        catalog=pd.read_csv(accepted_input(run,oldfolder,'series_catalog.csv'));catalog=catalog.loc[catalog.series_id.isin(daily.series_id)].copy()
        if sample:
            ids=['RAD_CRATER_SEC_selected_state',sorted(s for s in daily.series_id.unique() if s.startswith('RAD_GOES16'))[0]]
            daily=daily.loc[daily.series_id.isin(ids)];catalog=catalog.loc[catalog.series_id.isin(ids)]
        solar=pd.read_csv(accepted_input(run,LOCAL/'data/processed/analysis'/subject['screening_run'],'daily_context.csv'))
        solar=solar.loc[solar.series_id.eq('SEE_v012_FUV_115_180')].copy();solar['date']=pd.to_datetime(solar.date,utc=True)
        if solar.empty:raise ValueError('Expected qualified contemporary FUV band')
        calendar=calendar_summary(daily,subject['time_bins'],subject['two_year_anchor'])
        thresholds,segments=upper_tail_segments(daily)
        associations,pairs=solar_association(daily,solar)
        oldmonths=pd.read_csv(accepted_input(run,oldfolder,'monthly_context.csv'))
        oldmonths=oldmonths.loc[oldmonths.series_id.isin(daily.series_id)]
        # Old aggregation has the same day-weighted median; retain support differences in separate explicit fields.
        print('Prior monthly columns:',','.join(oldmonths.columns),flush=True)
        monthly=calendar.loc[calendar.period_kind.eq('month')]
        tables={'daily_context':daily,'series_catalog':catalog,'calendar_context':calendar,
            'matched_June_October_years':fixed_month_comparison(daily,6,10),
            'descriptive_upper_tail_thresholds':thresholds,'observed_upper_tail_segments':segments,
            'solar_associations':associations,'paired_solar_daily_values':pairs,
            'previous_monthly_context':oldmonths,'stage4_radiation_proposals':proposals()}
        # Cross-check by source dates instead of relying on similar-looking plots.
        oldname='median_of_daily_medians'
        if oldname not in oldmonths:raise ValueError('Prior monthly median contract changed')
        oldmonths['period_start_utc']=pd.to_datetime(oldmonths.period_start_utc,utc=True)
        compare=oldmonths[['series_id','period_start_utc',oldname]].merge(
            monthly.assign(period_start_utc=pd.to_datetime(monthly.period_start_utc))[['series_id','period_start_utc','median_of_daily_values']],on=['series_id','period_start_utc'],validate='one_to_one')
        compare['support_changed']=compare[oldname].isna()!=compare.median_of_daily_values.isna()
        compare['absolute_difference']=(compare[oldname]-compare.median_of_daily_values).abs()
        if len(compare)!=len(oldmonths) or compare.support_changed.any() or compare.absolute_difference.fillna(0).max()>1e-10:raise ValueError('Calendar extension changed accepted monthly medians')
        tables['crosscheck_Dar043']=compare
        for name,frame in tables.items():frame.to_csv(run.path(name+'.csv'),index=False)
        ids=['RAD_CRATER_SEC_selected_state',*[s for s in catalog.series_id if '_s0_c0_' in s]]
        for sid in ids:
            g=daily.loc[daily.series_id.eq(sid)];month=monthly.loc[monthly.series_id.eq(sid)]
            fig,axes=plt.subplots(2,1,figsize=(12,6),sharex=True,layout='constrained')
            axes[0].scatter(g.date,g.daily_max,s=3,label='reported daily maximum');axes[0].plot(g.date,g.daily_median,label='daily median')
            axes[0].plot(pd.to_datetime(month.period_start_utc),month.median_of_daily_values,label='month median of days',linewidth=2)
            axes[0].set(ylabel=catalog.set_index('series_id').loc[sid,'unit'],title=sid+'; context, not local dose/safety');axes[0].legend(fontsize=8)
            axes[1].plot(pd.to_datetime(month.period_start_utc),month.valid_day_fraction,label='valid-day fraction')
            if g.valid_seconds.notna().any():axes[1].scatter(g.date,g.valid_seconds/86400,s=2,label='reported valid seconds / UTC day')
            axes[1].set(ylabel='Support fraction',ylim=(-.02,1.02));axes[1].legend(fontsize=8)
            save_figure(run,fig,sid+'_levels_support')
        crater=associations.loc[associations.series_id.eq('RAD_CRATER_SEC_selected_state')]
        findings={'subject':'radiation','sample':sample,'series':daily.series_id.nunique(),'daily_rows':len(daily),
            'first_utc':str(daily.date.min()),'last_utc':str(daily.date.max()),'tables':{n:len(f) for n,f in tables.items()},
            'crater_solar_descriptive_checks':crater.to_dict('records'),'time_contract':subject['time_contract'],
            'base_conclusion':'Calendar support and observed upper tails reveal what averages hide. Orbital counters, Earth-orbit space-weather flux and solar associations cannot certify local shielded exposure, event recurrence or a safe arrival season.',
            'full_source_scope':'all accepted radiation daily series; no expansion of the earlier sparse primary-event cohort',
            'pipeline_changed':False,'adopted_limits':False,'operational_status':'Unknown',
            'remaining':['Three capped CRaTER primary pairs and sparse-primary cohort scope','Local transport/shielding/response and adopted applicable limits','Subdaily physical event definition and qualified exposure','Other subjects and integrated Stage 4 synthesis']}
        run.path('findings.json').write_text(json.dumps(findings,indent=2));folder=run.directory
    print(json.dumps(findings,indent=2),flush=True);return folder,findings


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--sample',action='store_true')
    print(execute(parser.parse_args().sample)[0])
