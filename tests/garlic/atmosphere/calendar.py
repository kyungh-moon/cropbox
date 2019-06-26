import datetime
import pytz

JULIAN_EPOCH_USDA = 2415078.5 # 1990-03-01
JULIAN_EPOCH_UNIX = 2440587.5 # 1970-01-01

def datetime_from_julian_day_WEA(year, jday, time='00:00', tzinfo=None, fold=0):
    d = datetime.datetime.strptime(f'{year}-{jday} {time}', '%Y-%j %H:%M')
    if tzinfo is None:
        # astimezone(None) sets local timezone
        return d
    else:
        #FIXME is replacing fold mandatory?
        #return d.replace(fold=fold).astimezone(tzinfo)
        return tzinfo.localize(d)

def julian_day_from_datetime(clock):
    return int(clock.strftime('%j'))

def round_datetime(clock):
    return (clock + datetime.timedelta(seconds=0.5)).replace(microsecond=0)

def datetime_from_julian_day_2DSOIL(jday, jhour=0):
    d = (jday + jhour) + (JULIAN_EPOCH_USDA - JULIAN_EPOCH_UNIX)
    #HACK prevent degenerate timestamps due to precision loss
    clock = datetime.datetime.utcfromtimestamp(d * (24 * 60 * 60))
    return Timer.round_datetime(clock)

def julian_day_from_datetime_2DSOIL(clock, hourly=False):
    j = clock.replace(tzinfo=datetime.timezone.utc).timestamp() / (24 * 60 * 60) - (JULIAN_EPOCH_USDA - JULIAN_EPOCH_UNIX)
    return j if hourly else int(j)

def julian_hour_from_datetime_2DSOIL(clock):
    return Timer.julian_day_from_datetime(clock, hourly=True) - Timer.julian_day_from_datetime(clock, hourly=False)
