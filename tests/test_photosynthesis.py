from . import context

from cropbox.system import System
from cropbox.context import Context
from cropbox.stage import Stage
from cropbox.statevar import derive, accumulate, difference, signal, parameter, drive, optimize

import numpy as np
import scipy.optimize
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


# Arrhenius equation
def temperature_dependence_rate(Ea, T, Tb=25.):
    R = 8.314 # universal gas constant (J K-1 mol-1)
    K = 273.15
    #HACK handle too low temperature values during optimization
    Tk = max(0, T + K)
    Tbk = max(0, Tb + K)
    try:
        return np.exp(Ea * (T - Tb) / (Tbk * R * Tk))
    except ZeroDivisionError:
        return 0


def nitrogen_limited_rate(N):
    # in Sinclair and Horie, 1989 Crop sciences, it is 4 and 0.2
    # In J Vos. et al. Field Crop study, 2005, it is 2.9 and 0.25
    # In Lindquist, weed science, 2001, it is 3.689 and 0.5
    s = 2.9 # slope
    N0 = 0.25
    return 2 / (1 + np.exp(-s * (max(N0, N) - N0))) - 1


def quadratic_solve(a, b, c, lower=True):
    if a == 0:
        return -c/b
    v = b**2 - 4*a*c
    if v < 0:
        return -b/a # imagniary roots
    else:
        sv = np.sqrt(v)
        sv *= -1 if lower else 1
        return (-b + sv) / (2*a)
quadratic_solve_lower = lambda a, b, c: quadratic_solve(a, b, c, lower=True)
quadratic_solve_upper = lambda a, b, c: quadratic_solve(a, b, c, lower=False)


class C4:
    def __init__(self, leaf_n_content, **kwargs):
        self.setup(**kwargs)
        self.leaf_n_content = leaf_n_content

    def setup(self, **kwargs):
        # activation energy values
        self.Eac = 59400
        self.Eao = 36000

        self.EaVp = 75100
        self.EaVc = 55900 # Sage (2002) JXB
        self.Eaj = 32800

        self.Hj = 220000
        self.Sj = 702.6

        self.Kc25 = 650 # Michaelis constant of rubisco for CO2 of C4 plants (2.5 times that of tobacco), ubar, Von Caemmerer 2000
        self.Ko25 = 450 # Michaelis constant of rubisco for O2 (2.5 times C3), mbar
        self.Kp25 = 80 # Michaelis constant for PEP caboxylase for CO2

        # Kim et al. (2007), Kim et al. (2006)
        # In von Cammerer (2000), Vpm25=120, Vcm25=60,Jm25=400
        # In Soo et al.(2006), under elevated C5O2, Vpm25=91.9, Vcm25=71.6, Jm25=354.2 YY
#         self.Vpm25 = 70
#         self.Vcm25 = 50
#         self.Jm25 = 300

        # switgrass params from Albaugha et al. (2014)
        # https://doi.org/10.1016/j.agrformet.2014.02.013
#         self.Vpm25 = 52
#         self.Vcm25 = 26
#         self.Jm25 = 145

        # switchgrass Vcmax from Le et al. (2010), others multiplied from Vcmax (x2, x5.5)
        self.Vpm25 = 96
        self.Vcm25 = 48
        self.Jm25 = 264

#         self.Vpm25 = 100
#         self.Vcm25 = 50
#         self.Jm25 = 200

#         self.Vpm25 = 70
#         self.Vcm25 = 50
#         self.Jm25 = 180.8

        # Values in Kim (2006) are for 31C, and the values here are normalized for 25C. SK
        self.Rd25 = 2
        self.Ear = 39800

        # switchgrass params from Albaugha et al. (2014)
        #self.Rd25 = 3.6 # not sure if it was normalized to 25 C

        #FIXME are they even used?
        #self.beta_ABA = 1.48e2 # Tardieu-Davies beta, Dewar (2002) Need the references !?
        #self.delta = -1.0
        #self.alpha_ABA = 1.0e-4
        #self.lambda_r = 4.0e-12 # Dewar's email
        #self.lambda_l = 1.0e-12
        #self.K_max = 6.67e-3 # max. xylem conductance (mol m-2 s-1 MPa-1) from root to leaf, Dewar (2002)

        self.gbs = 0.003 # bundle sheath conductance to CO2, mol m-2 s-1
        #self.gi = 1.0 # conductance to CO2 from intercelluar to mesophyle, mol m-2 s-1, assumed

        for k, v in kwargs.items():
            setattr(self, k, v)

    def _dark_respiration(self, T_leaf):
        return self.Rd25 * temperature_dependence_rate(self.Ear, T_leaf)

    def _maximum_electron_transport_rate(self, T, N):
        R = 8.314

        Tb = 25
        K = 273.15
        Tk = T + K
        Tbk = Tb + K

        Sj = self.Sj
        Hj = self.Hj

        r = self.Jm25 * nitrogen_limited_rate(N) \
                      * temperature_dependence_rate(self.Eaj, T) \
                      * (1 + np.exp((Sj*Tbk - Hj) / (R*Tbk))) \
                      / (1 + np.exp((Sj*Tk  - Hj) / (R*Tk)))
        return max(0, r)

    def _enzyme_limited_photosynthesis_rate(self, Cm, T_leaf):
        O = 210 # gas units are mbar
        Om = O # mesophyll O2 partial pressure

        Kp = self.Kp25 # T dependence yet to be determined
        Kc = self.Kc25 * temperature_dependence_rate(self.Eac, T_leaf)
        Ko = self.Ko25 * temperature_dependence_rate(self.Eao, T_leaf)
        Km = Kc * (1 + Om / Ko) # effective M-M constant for Kc in the presence of O2

        Vpmax = self.Vpm25 * nitrogen_limited_rate(self.leaf_n_content) * temperature_dependence_rate(self.EaVp, T_leaf)
        Vcmax = self.Vcm25 * nitrogen_limited_rate(self.leaf_n_content) * temperature_dependence_rate(self.EaVc, T_leaf)

        #print(f'[N] lfNContent = {self.leaf_n_content}, rate = {nitrogen_limited_rate(self.leaf_n_content)}')
        #print(f'[T] Tleaf = {T_leaf}, rate = {temperature_dependence_rate(1, T_leaf)}')
        #print(f'Vpmax = {Vpmax}, Vcmax = {Vcmax}')

        # PEP carboxylation rate, that is the rate of C4 acid generation
        Vp = (Cm * Vpmax) / (Cm + Kp)
        Vpr = 80 # PEP regeneration limited Vp, value adopted from vC book
        Vp = np.clip(Vp, 0, Vpr)

        Rd = self._dark_respiration(T_leaf)
        Rm = 0.5 * Rd

        #print(f'Rd = {Rd}, Rm = {Rm}')

        #FIXME where should gamma be at?
        # half the reciprocal of rubisco specificity, to account for O2 dependence of CO2 comp point,
        # note that this become the same as that in C3 model when multiplied by [O2]
        #gamma1 = 0.193
        #gamma_star = gamma1 * Os
        #gamma = (Rd*Km + Vcmax*gamma_star) / (Vcmax - Rd)

        # Enzyme limited A (Rubisco or PEP carboxylation)
        Ac1 = Vp + self.gbs*Cm - Rm
        #Ac1 = max(0, Ac1) # prevent Ac1 from being negative Yang 9/26/06
        Ac2 = Vcmax - Rd
        #print(f'Ac1 = {Ac1}, Ac2 = {Ac2}')
        Ac = min(Ac1, Ac2)
        return Ac

    # Light and electron transport limited A mediated by J
    def _transport_limited_photosynthesis_rate(self, I2, Cm, T_leaf):
        # sharpness of transition from light limitation to light saturation
#         theta = 0.5
        # switchgrass param from Albaugha et al. (2014)
        theta = 0.79

        Jmax = self._maximum_electron_transport_rate(T_leaf, self.leaf_n_content)
        J = quadratic_solve_lower(theta, -(I2+Jmax), I2*Jmax)
        #print(f'Jmax = {Jmax}, J = {J}')
        x = 0.4 # Partitioning factor of J, yield maximal J at this value

        Rd = self._dark_respiration(T_leaf)
        Rm = 0.5 * Rd

        Aj1 = x * J/2 - Rm + self.gbs*Cm
        Aj2 = (1-x) * J/3 - Rd
        Aj = min(Aj1, Aj2)
        return Aj

    def _combined_photosynthesis_rate(self, Ac, Aj):
        beta = 0.99 # smoothing factor
        # smooting the transition between Ac and Aj
        return ((Ac+Aj) - ((Ac+Aj)**2 - 4*beta*Ac*Aj)**0.5) / (2*beta)

    #FIXME put them accordingly
    def _bundle_sheath(self, A_net):
        alpha = 0.0001 # fraction of PSII activity in the bundle sheath cell, very low for NADP-ME types
        Os = alpha * A_net / (0.047*self.gbs) + Om # Bundle sheath O2 partial pressure, mbar
        #Cbs = Cm + (Vp - A_net - Rm) / self.gbs # Bundle sheath CO2 partial pressure, ubar

    def photosynthesize(self, I2, Cm, T_leaf):
        #assert I2 >= 0 and Cm >= 0
        I2 = np.clip(I2, 0, I2)
        Cm = np.clip(Cm, 0, Cm)

        Ac = self._enzyme_limited_photosynthesis_rate(Cm, T_leaf)
        Aj = self._transport_limited_photosynthesis_rate(I2, Cm, T_leaf)
        A_net = self._combined_photosynthesis_rate(Ac, Aj)
        #print(f'Ac = {Ac}, Aj = {Aj}, A_net = {A_net}')
        return A_net


def gb(leaf_width, sr=1):
    ratio = (sr + 1)**2 / (sr**2 + 1)
    d = 10/100 * 0.72
    return 1.4 * 0.147 * (0.1 / d)**0.5 * ratio

def gs_licor(r, g0, g1, gb, **kwargs):
    A_net = r['Photo']
    CO2 = r['CO2S']
    RH = r['RH_S'] / 100
    Cs = CO2 - (1.37 * A_net / gb) # surface CO2 in mole fraction
    a = g1 * A_net / Cs
    b = g0 + gb - (g1 * A_net / Cs)
    c = (-RH * gb) - g0
    v = b**2 - 4*a*c
    Hs = np.where(v >= 0, (-b + np.sqrt(v)) / (2*a), -b/a)
    Hs = np.clip(Hs, 0.1, 1.0) # preventing bifurcation: used to be (0.3, 1.0) for C4 maize
    gs = g0 + (g1 * (A_net * Hs / Cs))
    gs = np.maximum(gs, g0)
    return gs

def gs_cost(x, *args):
    #g0, g1 = x
    g0 = 0.017
    g1 = x[0]
    df, gb = args
    gs0 = df['Cond']
    gs1 = gs_licor(df, g0, g1, gb)
    return sum((gs1 - gs0)**2)

# gs_param_default = {'g0': 0.017, 'g1': 4.53}
gs_param_default = {'g0': 0.04, 'g1': 4.0}


#HACK Should be faster than scipy.optimize.fixed_point
#def fixed_point(func, x0, args=(), xtol=1e-08, maxiter=100):
def fixed_point(func, x0, args=(), xtol=1e-02, maxiter=100):
    x1 = x0
    for i in range(maxiter):
        x = x1
        x1 = func(x, *args)
        if abs(x1 - x) < xtol:
            return x1
    else:
        #print(f"Failed to converge after {maxiter} iterations, {x} != {x1}, return original {x0}") #raise RuntimeError
        #return x0
        #print(f"Failed to converge after {maxiter} iterations, {x} != {x1}, return last {x1}") #raise RuntimeError
        #return x1
        print(f"Failed to converge after {maxiter} iterations, {x} != {x1}, return larger {max(x, x1)}") #raise RuntimeError
        return max(x, x1)

class VaporPressure:
    # Campbell and Norman (1998), p 41 Saturation vapor pressure in kPa
    a = 0.611 # kPa
    b = 17.502 # C
    c = 240.97 # C

    #FIXME August-Roche-Magnus formula gives slightly different parameters
    # https://en.wikipedia.org/wiki/Clausius–Clapeyron_relation
    #a = 0.61094 # kPa
    #b = 17.625 # C
    #c = 243.04 # C

    @classmethod
    def saturation(cls, T):
        a, b, c = cls.a, cls.b, cls.c
        return a*np.exp((b*T)/(c+T))

    @classmethod
    def ambient(cls, T, RH):
        es = cls.saturation(T)
        return es * RH

    @classmethod
    def deficit(cls, T, RH):
        es = cls.saturation(T)
        return es * (1 - RH)

    @classmethod
    def relative_humidity(cls, T, VPD):
        es = cls.saturation(T)
        return 1 - VPD / es

    # slope of the sat vapor pressure curve: first order derivative of Es with respect to T
    @classmethod
    def curve_slope(cls, T, P):
        es = cls.saturation(T)
        b, c = cls.b, cls.c
        slope = es * (b*c)/(c+T)**2 / P
        return slope


class Stomata:
    def __init__(self, leaf_width, **kwargs):
        self.setup(leaf_width, **kwargs)

    #TODO support parameter configuration for multiple species/cultivars
    def setup(self, leaf_width, **kwargs):
        # in P. J. Sellers, et al.Science 275, 502 (1997)
        # g0 is b, of which the value for c4 plant is 0.04
        # and g1 is m, of which the value for c4 plant is about 4 YY
        #self.g0 = 0.04
        #self.g1 = 4.0

        # Ball-Berry model parameters from Miner and Bauerle 2017, used to be 0.04 and 4.0, respectively (2018-09-04: KDY)
        self.g0 = 0.017
        self.g1 = 4.53

        # calibrated above for our switchgrass dataset
#         self.g0 = 0.04
#         self.g1 = 1.89

#         self.g0 = 0.02
#         self.g1 = 2.0

        # parameters from Le et. al (2010)
        #self.g0 = 0.008
        #self.g1 = 8.0

        # for garlic
        #self.g0 = 0.096
        #self.g1 = 6.824

        self.gb = 0. # boundary layer conductance
        self.gs = 0. # stomatal conductance

        self.leaf_width = leaf_width / 100 # meters
        #FIXME initial value never used
        #self.leafp_effect = 1 # At first assume there is not drought stress, so assign 1 to leafpEffect. Yang 8/20/06

        # override g0, g1 here
        for k, v in kwargs.items():
            setattr(self, k, v)

    def update(self, weather, LWP, A_net=0, T_leaf=None):
        if T_leaf is None:
            T_leaf = weather.T_air

        self.update_boundary_layer(weather.wind)
        self.update_stomata(LWP, weather.CO2, A_net, weather.RH, T_leaf)
        #print(f"       gb = {self.gb}, gs = {self.gs}")

    def update_boundary_layer(self, wind):
        # maize is an amphistomatous species, assume 1:1 (adaxial:abaxial) ratio.
        #sr = 1.0
        # switchgrass adaxial : abaxial (Awada 2002)
        # https://doi.org/10.4141/P01-031
        sr = 1.28
        ratio = (sr + 1)**2 / (sr**2 + 1)

        # characteristic dimension of a leaf, leaf width in m
        d = self.leaf_width * 0.72

        #return 1.42 # total BLC (both sides) for LI6400 leaf chamber
        self.gb = 1.4 * 0.147 * (max(0.1, wind) / d)**0.5 * ratio
        #self.gb = (1.4 * 1.1 * 6.62 * (wind / d)**0.5 * (P_air / (R * (273.15 + T_air)))) # this is an alternative form including a multiplier for conversion from mm s-1 to mol m-2 s-1
        # 1.1 is the factor to convert from heat conductance to water vapor conductance, an avarage between still air and laminar flow (see Table 3.2, HG Jones 2014)
        # 6.62 is for laminar forced convection of air over flat plates on projected area basis
        # when all conversion is done for each surface it becomes close to 0.147 as given in Norman and Campbell
        # multiply by 1.4 for outdoor condition, Campbell and Norman (1998), p109, also see Jones 2014, pg 59 which suggest using 1.5 as this factor.
        # multiply by ratio to get the effective blc (per projected area basis), licor 6400 manual p 1-9
        return self.gb

    # stomatal conductance for water vapor in mol m-2 s-1
    #FIXME T_leaf not used
    def update_stomata(self, LWP, CO2, A_net, RH, T_leaf):
        # params
        g0 = self.g0
        g1 = self.g1
        gb = self.gb

        #FIXME proper use of gamma
        #gamma = 10.0 # for C4 maize
        gamma = 10.0 #FIXME supposed to be temperature dependent gamma for C3 garlic
        Cs = CO2 - (1.37 * A_net / gb) # surface CO2 in mole fraction
        if Cs <= gamma:
            Cs = gamma + 1

        m = self._leafp_effect(LWP)

        a = m * g1 * A_net / Cs
        b = g0 + gb - (m * g1 * A_net / Cs)
        c = (-RH * gb) - g0
        #hs = max(np.roots([a, b, c]))
        #hs = scipy.optimize.brentq(lambda x: np.polyval([a, b, c], x), 0, 1)
        #hs = scipy.optimize.fsolve(lambda x: np.polyval([a, b, c], x), 0)
        hs = quadratic_solve_upper(a, b, c)
        #hs = np.clip(hs, 0.1, 1.0) # preventing bifurcation: used to be (0.3, 1.0) for C4 maize

        #FIXME unused?
        #es = VaporPressure.saturation(tleaf)
        #Ds = (1 - hs) * es # VPD at leaf surface
        Ds = VaporPressure.deficit(T_leaf, hs)

        gs = g0 + (g1 * m * (A_net * hs / Cs))
        #print(f'Cs = {Cs}, m = {m}, a = {a}, b = {b}, c = {c}, gs = {gs}')
        gs = max(gs, g0)

        # this below is an example of how you can write temporary data to a debug window. It can be copied and
        # pasted into excel for plotting. Dennis See above where the CString object is created.
        #print(f"gs = {gs} LWP = {LWP} Ds = {Ds} T_leaf = {T_leaf} Cs = {Cs} A_net = {A_net} hs = {hs} RH = {RH}")
        self.gs = gs
        return self.gs

    def _leafp_effect(self, LWP):
        # pressure - leaf water potential MPa...
#         sf = 2.3 # sensitivity parameter Tuzet et al. 2003 Yang
#         phyf = -1.2 # reference potential Tuzet et al. 2003 Yang
        #? = -1.68 # minimum sustainable leaf water potential (Albaugha 2014)
        # switchgrass params from Le et al. (2010)
#         sf = 6.5
#         phyf = -1.3
        # hand-picked
        sf = 2.3
        phyf = -2.0
        m = (1 + np.exp(sf * phyf)) / (1 + np.exp(sf * (phyf - LWP)))
        #print(f'[LWP] pressure = {LWP}, effect = {m}')
        return m

    def total_conductance_h2o(self):
        gs = self.gs
        gb = self.gb
        return gs * gb / (gs + gb)

    def boundary_layer_resistance_co2(self):
        return 1.37 / self.gb

    def stomatal_resistance_co2(self):
        return 1.6 / self.gs

    def total_resistance_co2(self):
        return self.boundary_layer_resistance_co2() + self.stomatal_resistance_co2()


class PhotosyntheticLeaf:
    #TODO organize leaf properties like water (LWP), nitrogen content?
    #TODO introduce a leaf geomtery class for leaf_width
    #TODO introduce a soil class for ET_supply
    def __init__(self, water, nitrogen, width, weather, ET_supply, ps_params={}, gs_params={}):
        # static properties
        self.water = water
        self.nitrogen = nitrogen

        # geometry
        self.width = width

        # weather
        self.weather = weather

        # soil
        self.ET_supply = ET_supply

        #TODO better management of output variables
        # dynamic properties
        self.temperature = None
        self.A_net = 0
        self.Rd = 0
        self.A_gross = 0
        self.Ci = 0

        self.stomata = Stomata(width, **gs_params)
        self.stomata.update(weather, water, A_net=0)

        #TODO support modular interface
        self.photosynthesis = C4(nitrogen, **ps_params) # for maize
        #self.photosynthesis = C3(nitrogen, **ps_params) # for garlic

    def co2_mesophyll(self, A_net, T_leaf):
        self.stomata.update(self.weather, self.water, A_net, T_leaf)
        P = self.weather.P_air / 100
        Ca = self.weather.CO2 * P # conversion to partial pressure
        rsc = self.stomata.total_resistance_co2()
        Cm = Ca - A_net * rsc * P
        #print(f"+ Cm = {Cm}, Ca = {Ca}, A_net = {A_net}, gs = {self.stomata.gs}, gb = {self.stomata.gb}, rsc = {rsc}, P = {P}")
        return np.clip(Cm, 0, 2*Ca)
        #return Cm

    def optimize_stomata(self, T_leaf):
        #FIXME is it right place? maybe need coordination with geometry object in the future
        def light():
            #FIXME make scatt global parameter?
            scatt = 0.15 # leaf reflectance + transmittance
            f = 0.15 # spectral correction

            Ia = self.weather.PFD * (1 - scatt) # absorbed irradiance
            I2 = Ia * (1 - f) / 2 # useful light absorbed by PSII
            return I2

        def update_stomata(A_net):
            self.stomata.update(self.weather, self.water, A_net, T_leaf)

        # mesophyll CO2 partial pressure, ubar, one may use the same value as Ci assuming infinite mesohpyle conductance
        def co2_mesophyll(A_net):
            update_stomata(A_net)

            P = self.weather.P_air / 100
            Ca = self.weather.CO2 * P # conversion to partial pressure
            rsc = self.stomata.total_resistance_co2()
            Cm = Ca - A_net * rsc * P
            #print(f"+ Cm = {Cm}, Ca = {Ca}, A_net = {A_net}, gs = {self.stomata.gs}, gb = {self.stomata.gb}, rsc = {rsc}, P = {P}")
            return np.clip(Cm, 0, 2*Ca)
            #return Cm

        def cost(x):
            I2 = light()
            A_net0 = x
            #print(f"A_net0 = {A_net0}")
            Cm0 = co2_mesophyll(A_net0)
            A_net1 = self.photosynthesis.photosynthesize(I2, Cm0, T_leaf)
            #Cm1 = co2_mesophyll(A_net1)
            #print(f"- I2 = {I2}, Cm0 = {Cm0}, T_leaf = {T_leaf}, A_net0 = {A_net0}, A_net1 = {A_net1}, Cm1 = {Cm1}")
#             return A_net1
            return (A_net1 - A_net0)**2

        def cost2(x):
            I2 = light()
            Cm0 = x
            A_net1 = self.photosynthesis.photosynthesize(I2, Cm0, T_leaf)
            Cm1 = co2_mesophyll(A_net1)
            #print(f"- I2 = {I2}, Cm0 = {Cm0}, T_leaf = {T_leaf}, A_net1 = {A_net1}, Cm1 = {Cm1}")
#             return Cm1
            return (Cm1 - Cm0)**2

        #FIXME avoid passing self.stomata object to optimizer
        # iteration to obtain Cm from Ci and A, could be re-written using more efficient method like newton-raphson method
        #print(f" - min st {self.A_net}")
#         self.A_net = fixed_point(cost, self.A_net)
        #self.A_net = scipy.optimize.newton(cost, self.A_net, fprime=lambda x: maxiter=1000)
        #self.A_net = scipy.optimize.newton(cost2, co2_mesophyll(self.A_net), maxiter=1000)
        #self.A_net = scipy.optimize.newton(cost2, co2_mesophyll(self.A_net), fprime=lambda x: (cost(x+1)-cost(x)), maxiter=1000)
#         res = scipy.optimize.minimize(cost, self.A_net, method='Nelder-Mead')
#         self.A_net = res.x[0]
#         if not res.success:
#             print(res.message)

        #Ca = self.weather.CO2 * self.weather.P_air / 100
        #Cm = scipy.optimize.minimize_scalar(cost2, bounds=(0, 2*Ca), method='bounded', options={'disp': 1}).x
        #Cm = scipy.optimize.minimize_scalar(cost2).x
        #self.A_net = self.photosynthesis.photosynthesize(light(), Cm, T_leaf)
#         self.A_net = scipy.optimize.minimize_scalar(cost, bounds=(0, 100), method='bounded', options={'disp': 1}).x
#         Cm = co2_mesophyll(self.A_net)
        self.A_net = scipy.optimize.minimize_scalar(cost).x
        #print(f'minimize scalar: Cm = {Cm}, A_net = {self.A_net}')
        #print(f" - min st {self.A_net}")

        #HACK ensure stomata state matches with the final A_net
        update_stomata(self.A_net)
        #print(f'Cm = {co2_mesophyll(self.A_net)}')

        self.Rd = self.photosynthesis._dark_respiration(T_leaf)
        self.A_gross = max(0., self.A_net + self.Rd) # gets negative when PFD = 0, Rd needs to be examined, 10/25/04, SK

        self.Ci = co2_mesophyll(self.A_net)

    def update_temperature(self):
        # see Campbell and Norman (1998) pp 224-225
        # because Stefan-Boltzman constant is for unit surface area by denifition,
        # all terms including sbc are multilplied by 2 (i.e., gr, thermal radiation)
        lamda = 44000 # KJ mole-1 at 25oC
        psc = 6.66e-4
        Cp = 29.3 # thermodynamic psychrometer constant and specific heat of air (J mol-1 C-1)

        epsilon = 0.97
        sbc = 5.6697e-8

        T_air = self.weather.T_air
        Tk = T_air + 273.15
        RH = self.weather.RH
        PFD = self.weather.PFD
        P_air = self.weather.P_air
        Jw = self.ET_supply

        gha = self.stomata.gb * (0.135 / 0.147) # heat conductance, gha = 1.4*.135*sqrt(u/d), u is the wind speed in m/s} Mol m-2 s-1 ?
        gv = self.stomata.total_conductance_h2o()
        gr = 4 * epsilon * sbc * Tk**3 / Cp * 2 # radiative conductance, 2 account for both sides
        ghr = gha + gr
        thermal_air = epsilon * sbc * Tk**4 * 2 # emitted thermal radiation
        psc1 = psc * ghr / gv # apparent psychrometer constant

        PAR = PFD / 4.55
        # If total solar radiation unavailable, assume NIR the same energy as PAR waveband
        NIR = PAR
        scatt = 0.15
        # shortwave radiation (PAR (=0.85) + NIR (=0.15) solar radiation absorptivity of leaves: =~ 0.5
        # times 2 for projected area basis
        R_abs = (1 - scatt)*PAR + scatt*NIR + 2*(epsilon * sbc * Tk**4)

        # debug dt I commented out the changes that yang made for leaf temperature for a test. I don't think they work
        if Jw == 0:
            VPD = VaporPressure.deficit(T_air, RH)
            # eqn 14.6b linearized form using first order approximation of Taylor series
            T_leaf = T_air + (psc1 / (VaporPressure.curve_slope(T_air, P_air) + psc1)) * ((R_abs - thermal_air) / (ghr * Cp) - VPD / (psc1 * P_air))
        else:
            T_leaf = T_air + (R_abs - thermal_air - lamda * Jw) / (Cp * ghr)
        return T_leaf

    def exchange(self):
        def cost(x):
            T_leaf0 = x
            self.optimize_stomata(T_leaf0)
            T_leaf1 = self.update_temperature()
#             return T_leaf1
            #print(f'T_leaf0 = {T_leaf0}, T_leaf1 = {T_leaf1}')
            return (T_leaf1 - T_leaf0)**2

        #print(f"min st {self.weather.T_air}")
#         self.temperature = cost(self.weather.T_air)
#         self.temperature = fixed_point(cost, self.weather.T_air)
#         self.temperature = scipy.optimize.newton(cost, self.weather.T_air, maxiter=100)
#         res = scipy.optimize.minimize(cost, self.weather.T_air, method='Nelder-Mead')
#         self.temperature = res.x[0]
#         if not res.success:
#             print(res.message)
        #self.temperature = self.update_temperature()
        self.temperature = scipy.optimize.minimize_scalar(cost).x
        #print(f"min end {self.temperature}")

        #HACK ensure leaf state matches with the final temperature
        self.optimize_stomata(self.temperature)

    @property
    def ET(self):
        gv = self.stomata.total_conductance_h2o()
        ea = VaporPressure.ambient(self.weather.T_air, self.weather.RH)
        es_leaf = VaporPressure.saturation(self.temperature)
        ET = gv * ((es_leaf - ea) / self.weather.P_air) / (1 - (es_leaf + ea) / self.weather.P_air)
        return max(0., ET) # 04/27/2011 dt took out the 1000 everything is moles now


#FIXME initialize weather and leaf more nicely, handling None case for properties
class GasExchange:
    def __init__(self, s_type):
        self.s_type = s_type
        self.weather = None
        self.soil = None
        self.leaf = None

    def setup(self, weather, soil, leaf_n_content, leaf_width, ET_supply, ps_params={}, gs_params={}):
        self.weather = weather
        self.soil = soil
        self.leaf = PhotosyntheticLeaf(soil.WP_leaf, leaf_n_content, leaf_width, weather, ET_supply, ps_params, gs_params)
        self.leaf.exchange()

    @property
    def A_gross(self):
        return self.leaf.A_gross if self.leaf else 0

    @property
    def A_net(self):
        return self.leaf.A_net if self.leaf else 0

    @property
    def ET(self):
        return self.leaf.ET if self.leaf else 0

    @property
    def T_leaf(self):
        return self.leaf.temperature if self.leaf else np.nan

    @property
    def VPD(self):
        return VaporPressure.deficit(self.weather.T_air, self.weather.RH) if self.weather else np.nan

    @property
    def gs(self):
        return self.leaf.stomata.gs if self.leaf else np.nan


class Weather:
    def __init__(self):
        self.reset()

    def reset(self):
        self.PFD = None # umol m-2 s-1
        self.CO2 = None # ppm
        self.RH = None # 0~1
        self.T_air = None # C
        self.wind = None # meters s-1
        self.P_air = None # kPa

    def __str__(self):
        return f'PFD = {self.PFD}, CO2 = {self.CO2}, RH = {self.RH}, T_air = {self.T_air}, wind = {self.wind}, P_air = {self.P_air}'


class Soil:
    def __init__(self):
        self.reset()

    def reset(self):
        self.WP_leaf = None

    def __str__(self):
        return f'WP_leaf = {self.WP_leaf}'
