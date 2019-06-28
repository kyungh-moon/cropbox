from cropbox.system import System
from cropbox.statevar import derive, parameter
from cropbox.unit import U

from numpy import exp

class VaporPressure(System):
    # Campbell and Norman (1998), p 41 Saturation vapor pressure in kPa
    a = parameter(0.611) # kPa
    b = parameter(17.502) # C
    c = parameter(240.97) # C

    @derive(alias='es', unit='kPa', nounit='T')
    def saturation(self, T, *, a, b, c):
        return a*exp((b*T)/(c+T))

    @derive(alias='ea', unit='kPa')
    def ambient(self, T, RH):
        return self.es(T) * RH

    @derive(alias='D', unit='kPa')
    def deficit(self, T, RH):
        return self.es(T) * (1 - RH)

    @derive(alias='rh', unit='')
    def relative_humidity(self, T, VPD):
        return 1 - VPD / self.es(T)

    # slope of the sat vapor pressure curve: first order derivative of Es with respect to T
    @derive(alias='Delta', unit='kPa/degC', nounit='T')
    def _saturation_slope(self, T, *, b, c):
        return self.es(T) * (b*c)/(c+T)**2 / U(1, 'degC')

    @derive(alias='s', unit='1/degC')
    def saturation_slope(self, T, P):
        return self.Delta(T) / P
