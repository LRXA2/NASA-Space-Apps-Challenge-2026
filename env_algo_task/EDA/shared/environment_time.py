"""Explicit UTC comparison bins; calendar seasons are not lunar climate seasons."""
import numpy as np
import pandas as pd

KINDS = ('month', 'quarter', 'four_month_term', 'half_year', 'year', 'two_year', 'calendar_season')


def bucket_bounds(date, kind, anchor=2000):
    date = pd.Timestamp(date)
    date = date.tz_localize('UTC') if date.tzinfo is None else date.tz_convert('UTC')
    if pd.isna(date):
        raise ValueError('Missing UTC timestamp')
    year, month = date.year, date.month
    if kind in {'month','quarter','four_month_term','half_year'}:
        width = {'month':1,'quarter':3,'four_month_term':4,'half_year':6}[kind]
        first = 1+width*((month-1)//width)
        start = pd.Timestamp(year=year,month=first,day=1,tz='UTC')
        stop = start+pd.DateOffset(months=width)
        number = (month-1)//width+1
        label = {'month':f'{year}-{month:02d}','quarter':f'{year}Q{number}',
                 'four_month_term':f'{year}-T4M{number}','half_year':f'{year}-H{number}'}[kind]
    elif kind in {'year','two_year'}:
        width = 1 if kind=='year' else 2
        first = year if width==1 else anchor+2*((year-anchor)//2)
        start = pd.Timestamp(year=first,month=1,day=1,tz='UTC')
        stop = start+pd.DateOffset(years=width)
        label = str(first) if width==1 else f'{first}-{first+1}'
    elif kind=='calendar_season':
        first = 12 if month in [12,1,2] else 3 if month<6 else 6 if month<9 else 9
        start_year = year-1 if month<3 else year
        start = pd.Timestamp(year=start_year,month=first,day=1,tz='UTC')
        stop = start+pd.DateOffset(months=3)
        season = {12:'DJF',3:'MAM',6:'JJA',9:'SON'}[first]
        label = f'{stop.year if first==12 else year}-{season}'
    else:
        raise ValueError('Unsupported calendar comparison kind: '+str(kind))
    return start,stop,label


def longest_true(values):
    values = np.asarray(values,dtype=bool)
    edges = np.diff(np.r_[False,values,False].astype('int8'))
    return int((np.flatnonzero(edges==-1)-np.flatnonzero(edges==1)).max()) if values.any() else 0


def calendar_summary(daily, kinds=KINDS, anchor=2000):
    """Equal weight per valid day, complete calendar denominators and explicit gaps."""
    required = {'series_id','date','daily_median','daily_max','recorded_samples','valid_samples'}
    if required-set(daily):
        raise ValueError('Daily context lacks required fields: '+str(required-set(daily)))
    f = daily.copy()
    f['date'] = pd.to_datetime(f.date,utc=True)
    if f.date.isna().any() or not f.date.eq(f.date.dt.floor('D')).all():
        raise ValueError('Daily summaries require known UTC midnight date labels')
    if f.duplicated(['series_id','date']).any():
        raise ValueError('Duplicate series/date; reconcile native samples before aggregation')
    if (not np.isfinite(f[['recorded_samples','valid_samples']]).all().all()
            or (f.valid_samples<0).any() or (f.valid_samples>f.recorded_samples).any()
            or np.isinf(f[['daily_median','daily_max']]).any().any()):
        raise ValueError('Invalid daily value/count support')
    rows = []
    for sid,g in f.groupby('series_id',sort=True):
        g = g.set_index('date').sort_index()
        first,last = g.index.min(),g.index.max()+pd.Timedelta(days=1)
        for kind in kinds:
            cursor,_,_ = bucket_bounds(first,kind,anchor)
            while cursor<last:
                start,stop,label = bucket_bounds(cursor,kind,anchor)
                dates = pd.date_range(start,stop-pd.Timedelta(days=1),freq='D')
                part = g.loc[(g.index>=start)&(g.index<stop)]
                v = part.daily_median.dropna()
                present = dates.isin(part.index)
                valid = dates.isin(part.index[part.daily_median.notna()])
                within = max(0,(min(stop,last)-max(start,first)).days)
                row = {'series_id':sid,'period_kind':kind,'period':label,
                    'period_start_utc':start.isoformat(),'period_stop_exclusive_utc':stop.isoformat(),
                    'expected_calendar_days':len(dates),'days_inside_observed_source_span':within,
                    'partial_source_span_period':start<first or stop>last,
                    'recorded_days':len(part),'valid_days':len(v),
                    'valid_day_fraction':len(v)/len(dates),
                    'valid_day_fraction_inside_source_span':len(v)/within if within else np.nan,
                    'recorded_samples':int(part.recorded_samples.sum()),
                    'valid_samples':int(part.valid_samples.sum()),
                    'median_of_daily_values':v.median(),'p05_of_daily_values':v.quantile(.05),
                    'p95_of_daily_values':v.quantile(.95),'minimum_daily_value':v.min(),'maximum_daily_value':v.max(),
                    'maximum_of_reported_daily_maxima':part.daily_max.max(),
                    'longest_absent_date_run_days':longest_true(~present),
                    'longest_unsupported_date_run_days':longest_true(~valid),
                    'interpretation':'UTC calendar comparison, not lunar seasons, elapsed qualified exposure or a forecast'}
                if 'valid_seconds' in part:
                    row['reported_valid_seconds'] = part.valid_seconds.sum(min_count=1)
                rows.append(row)
                cursor = stop
    return pd.DataFrame(rows)


def fixed_month_comparison(daily, start_month=1, stop_month=12):
    """Same month range in each year, retaining partial years and valid-day support."""
    if not 1<=start_month<=stop_month<=12:
        raise ValueError('Use an inclusive non-wrapping calendar-month range')
    f = daily.copy();f['date'] = pd.to_datetime(f.date,utc=True)
    if f.duplicated(['series_id','date']).any():
        raise ValueError('Duplicate series/date')
    f = f.loc[f.date.dt.month.between(start_month,stop_month)]
    rows = []
    for (sid,year),g in f.groupby(['series_id',f.date.dt.year]):
        start = pd.Timestamp(year=int(year),month=start_month,day=1,tz='UTC')
        stop = pd.Timestamp(year=int(year),month=stop_month,day=1,tz='UTC')+pd.DateOffset(months=1)
        v = g.daily_median.dropna()
        rows.append({'series_id':sid,'year':int(year),'months_inclusive':f'{start_month:02d}-{stop_month:02d}',
            'expected_days':(stop-start).days,'recorded_days':len(g),'valid_days':len(v),
            'median_daily_value':v.median(),'p05_daily_value':v.quantile(.05),'p95_daily_value':v.quantile(.95),
            'maximum_daily_value':v.max(),'interpretation':'same calendar months, not a trend-significance or seasonality test'})
    return pd.DataFrame(rows)
