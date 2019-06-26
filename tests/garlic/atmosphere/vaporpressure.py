from cropbox.system import System
from cropbox.statevar import derive, parameter

from numpy import exp

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
