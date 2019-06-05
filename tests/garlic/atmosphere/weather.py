from cropbox.system import System
from cropbox.statevar import constant, derive, drive, parameter, system

from numpy import exp
import pandas as pd

class VaporPressure(System):
    # Campbell and Norman (1998), p 41 Saturation vapor pressure in kPa
    a = parameter(0.611) # kPa
    b = parameter(17.502) # C
    c = parameter(240.97) # C

    @derive(alias='es')
    def saturation(self, T, *, a, b, c):
        return a*exp((b*T)/(c+T))

    @derive(alias='ea')
    def ambient(self, T, RH):
        return self.es(T) * RH

    @derive(alias='vpd')
    def deficit(self, T, RH):
        return self.es(T) * (1 - RH)

    @derive(alias='rh')
    def relative_humidity(self, T, VPD):
        return 1 - VPD / self.es(T)

    # slope of the sat vapor pressure curve: first order derivative of Es with respect to T
    @derive(alias='cs')
    def curve_slope(self, T, P, *, b, c):
        return self.es(T) * (b*c)/(c+T)**2 / P

#TODO: use improved @drive
#TODO: implement @unit
class Weather(System):
    @system(alias='vp')
    def vapor_pressure(self):
        return VaporPressure

    @parameter
    def filename(self):
        return ''

    @constant(alias='df')
    def dataframe(self):
        #FIXME: use real file
        #return pd.read_csv(self.filename)
        return pd.DataFrame()

    @derive
    def key(self):
        return self.context.time

    @derive
    def store(self):
        #FIXME: use actual dataframe
        #return self.df.loc[self.key]
        return {'PFD': 1500, 'CO2': 400, 'RH': 0.6, 'T_air': 25, 'wind': 2.0, 'P_air': 100}

    @drive
    def PFD(self):
        #return 1500 # umol m-2 s-1
        return self.store

    @drive
    def CO2(self):
        #return 400 # ppm
        return self.store

    @drive
    def RH(self):
        #return 0.6 # 0~1
        return self.store

    @drive
    def T_air(self):
        #return 25 # C
        return self.store

    @drive
    def wind(self):
        #return 2.0 # meters s-1
        return self.store

    @drive
    def P_air(self):
        #return 100 # kPa
        return self.store

    @derive
    def VPD(self, T_air, RH): return self.vp.deficit(T_air, RH)

    @derive
    def VPD_slope(self, T_air, P_air): return self.vp.curve_slope(T_air, P_air)

    def __str__(self):
        w = self
        return f'PFD = {w.PFD}, CO2 = {w.CO2}, RH = {w.RH}, T_air = {w.T_air}, wind = {w.wind}, P_air = {w.P_air}'
