from cropbox.system import System
from cropbox.statevar import constant, derive, drive, parameter, system

from .vaporpressure import VaporPressure
from .sun import Sun
from .calendar import datetime_from_julian_day_WEA

import pandas as pd

#TODO: use improved @drive
#TODO: implement @unit
class Weather(System):
    @system(alias='vp')
    def vapor_pressure(self):
        return VaporPressure

    @system(weather='self')
    def sun(self):
        return Sun

    @parameter
    def filename(self):
        return ''

    @parameter
    def timezone(self):
        return None

    @constant(alias='df')
    def dataframe(self, filename, timezone):
        df = pd.read_csv(filename, sep='\s+')
        df['timestamp'] = df.apply(lambda r: datetime_from_julian_day_WEA(r.year, r.jday, r.time, tzinfo=None), axis=1)
        return df.set_index('timestamp').tz_localize(timezone, ambiguous='infer')

    @derive
    def key(self):
        return self.context.datetime

    @derive
    def store(self):
        return self.df.loc[self.key]
        #return {'SolRad': 1500, 'CO2': 400, 'RH': 0.6, 'T_air': 25, 'wind': 2.0, 'P_air': 100}

    @drive(alias='PFD', key='SolRad', unit='umol/m^2/s Quanta')
    def photon_flux_density(self):
        #return 1500 # umol m-2 s-1
        return self.store

    #TODO make CO2 parameter?
    @parameter(unit='umol/mol CO2')
    #@drive
    def CO2(self):
        return 400 # ppm
        #return self.store

    @drive(key='RH', unit='percent')
    def RH(self):
        #return 0.6 # 0~1
        return self.store

    @drive(key='Tair', unit='degC')
    def T_air(self):
        #return 25 # C
        return self.store

    @drive(key='Wind', unit='m/s')
    def wind(self):
        #return 2.0 # meters s-1
        return self.store

    #TODO make P_air parameter?
    @parameter(unit='kPa')
    #@drive
    def P_air(self):
        return 100 # kPa
        #return self.store

    @derive
    def VPD(self, T_air, RH): return self.vp.deficit(T_air, RH)

    @derive
    def saturation_slope(self, T_air, P_air): return self.vp.saturation_slope(T_air, P_air)

    def __str__(self):
        w = self
        return f'PFD = {w.PFD}, CO2 = {w.CO2}, RH = {w.RH}, T_air = {w.T_air}, wind = {w.wind}, P_air = {w.P_air}'
