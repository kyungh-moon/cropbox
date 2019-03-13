from cropbox.system import System
from cropbox.context import Context
from cropbox.statevar import accumulate, derive, difference, drive, optimize, optimize2, parameter, signal, statevar

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


class C4(System):
    #TODO: more robust interface to connect Systems (i.e. type check, automatic prop defines)
    def __init__(self, parent, leaf):
        super().__init__(parent, leaf=leaf)

    @derive
    def co2_mesophyll(self):
        Cm = self.leaf.co2_mesophyll
        return np.clip(Cm, 0, Cm)

    @derive
    def light(self):
        I2 = self.leaf.light
        return np.clip(I2, 0, I2)

    ##############
    # Parameters #
    ##############

    # activation energy values
    @parameter
    def Eac(self): return 59400
    @parameter
    def Eao(self): return 36000

    @parameter
    def EaVp(self): return 75100
    @parameter
    def EaVc(self): return 55900 # Sage (2002) JXB
    @parameter
    def Eaj(self): return 32800

    @parameter
    def Hj(self): return 220000
    @parameter
    def Sj(self): return 702.6

    @parameter
    def Kc25(self): return 650 # Michaelis constant of rubisco for CO2 of C4 plants (2.5 times that of tobacco), ubar, Von Caemmerer 2000
    @parameter
    def Ko25(self): return 450 # Michaelis constant of rubisco for O2 (2.5 times C3), mbar
    @parameter
    def Kp25(self): return 80 # Michaelis constant for PEP caboxylase for CO2

    # Kim et al. (2007), Kim et al. (2006)
    # In von Cammerer (2000), Vpm25=120, Vcm25=60,Jm25=400
    # In Soo et al.(2006), under elevated C5O2, Vpm25=91.9, Vcm25=71.6, Jm25=354.2 YY
    # @paramter
    # def Vpm25(self): return 70
    # @paramter
    # def Vcm25(self): return 50
    # @paramter
    # def Jm25(self): return 300

    # switgrass params from Albaugha et al. (2014)
    # https://doi.org/10.1016/j.agrformet.2014.02.013
    # @paramter
    # def Vpm25(self): return 52
    # @paramter
    # def Vcm25(self): return 26
    # @paramter
    # def Jm25(self): return 145


    # switchgrass Vcmax from Le et al. (2010), others multiplied from Vcmax (x2, x5.5)
    @parameter
    def Vpm25(self): return 96
    @parameter
    def Vcm25(self): return 48
    @parameter
    def Jm25(self): return 264

    # @parameter
    # def Vpm25(self): return 100
    # @parameter
    # def Vcm25(self): return 50
    # @parameter
    # def Jm25(self): return 200
    #
    # @parameter
    # def Vpm25(self): return 70
    # @parameter
    # def Vcm25(self): return 50
    # @parameter
    # def Jm25(self): return 180.8

    @parameter
    def Rd25(self): return 2 # Values in Kim (2006) are for 31C, and the values here are normalized for 25C. SK

    # switchgrass params from Albaugha et al. (2014)
    # def Rd25(self): return 3.6 # not sure if it was normalized to 25 C

    @parameter
    def Ear(self): return 39800

    # FIXME are they even used?
    # self.beta_ABA = 1.48e2 # Tardieu-Davies beta, Dewar (2002) Need the references !?
    # self.delta = -1.0
    # self.alpha_ABA = 1.0e-4
    # self.lambda_r = 4.0e-12 # Dewar's email
    # self.lambda_l = 1.0e-12
    # self.K_max = 6.67e-3 # max. xylem conductance (mol m-2 s-1 MPa-1) from root to leaf, Dewar (2002)

    @parameter
    def gbs(self): return 0.003 # bundle sheath conductance to CO2, mol m-2 s-1

    #@parameter
    # def gi(self): return 1.0 # conductance to CO2 from intercelluar to mesophyle, mol m-2 s-1, assumed

    @derive
    def dark_respiration(self):
        return self.Rd25 * temperature_dependence_rate(self.Ear, self.leaf.temperature)

    @derive
    def maximum_electron_transport_rate(self):
        T = self.leaf.temperature
        N = self.leaf.nitrogen

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

    @derive
    def enzyme_limited_photosynthesis_rate(self):
        Cm = self.co2_mesophyll
        T_leaf = self.leaf.temperature

        O = 210 # gas units are mbar
        Om = O # mesophyll O2 partial pressure

        Kp = self.Kp25 # T dependence yet to be determined
        Kc = self.Kc25 * temperature_dependence_rate(self.Eac, T_leaf)
        Ko = self.Ko25 * temperature_dependence_rate(self.Eao, T_leaf)
        Km = Kc * (1 + Om / Ko) # effective M-M constant for Kc in the presence of O2

        Vpmax = self.Vpm25 * nitrogen_limited_rate(self.leaf.nitrogen) * temperature_dependence_rate(self.EaVp, T_leaf)
        Vcmax = self.Vcm25 * nitrogen_limited_rate(self.leaf.nitrogen) * temperature_dependence_rate(self.EaVc, T_leaf)

        #print(f'[N] lfNContent = {self.leaf.nitrogen}, rate = {nitrogen_limited_rate(self.leaf.nitrogen)}')
        #print(f'[T] Tleaf = {T_leaf}, rate = {temperature_dependence_rate(1, T_leaf)}')
        #print(f'Vpmax = {Vpmax}, Vcmax = {Vcmax}')

        # PEP carboxylation rate, that is the rate of C4 acid generation
        Vp = (Cm * Vpmax) / (Cm + Kp)
        Vpr = 80 # PEP regeneration limited Vp, value adopted from vC book
        Vp = np.clip(Vp, 0, Vpr)

        Rd = self.dark_respiration
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
    @derive
    def transport_limited_photosynthesis_rate(self):
        I2 = self.light
        Cm = self.co2_mesophyll
        T_leaf = self.leaf.temperature

        # sharpness of transition from light limitation to light saturation
#         theta = 0.5
        # switchgrass param from Albaugha et al. (2014)
        theta = 0.79

        Jmax = self.maximum_electron_transport_rate
        J = quadratic_solve_lower(theta, -(I2+Jmax), I2*Jmax)
        #print(f'Jmax = {Jmax}, J = {J}')
        x = 0.4 # Partitioning factor of J, yield maximal J at this value

        Rd = self.dark_respiration
        Rm = 0.5 * Rd

        Aj1 = x * J/2 - Rm + self.gbs*Cm
        Aj2 = (1-x) * J/3 - Rd
        Aj = min(Aj1, Aj2)
        return Aj

    @derive
    def combined_photosynthesis_rate(self):
        Ac = self.enzyme_limited_photosynthesis_rate
        Aj = self.transport_limited_photosynthesis_rate

        beta = 0.99 # smoothing factor
        # smooting the transition between Ac and Aj
        return ((Ac+Aj) - ((Ac+Aj)**2 - 4*beta*Ac*Aj)**0.5) / (2*beta)

    # #FIXME put them accordingly
    # @derive
    # def bundle_sheath(self):
    #     A_net = self.net_photosynthesis
    #     alpha = 0.0001 # fraction of PSII activity in the bundle sheath cell, very low for NADP-ME types
    #     Os = alpha * A_net / (0.047*self.gbs) + Om # Bundle sheath O2 partial pressure, mbar
    #     #Cbs = Cm + (Vp - A_net - Rm) / self.gbs # Bundle sheath CO2 partial pressure, ubar

    @derive
    #def photosynthesize(self, I2, Cm, T_leaf):
    def net_photosynthesis(self):
        # I2 = self.light
        # Cm = self.co2_mesophyll
        # T_leaf = self.leaf_temperature
        # Ac = self.enzyme_limited_photosynthesis_rate
        # Aj = self.transport_limited_photosynthesis_rate
        A_net = self.combined_photosynthesis_rate
        #print(f'Ac = {Ac}, Aj = {Aj}, A_net = {A_net}')
        return A_net


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


class Stomata(System):
    def __init__(self, parent, leaf):
        super().__init__(parent, leaf=leaf)

    # in P. J. Sellers, et al.Science 275, 502 (1997)
    # g0 is b, of which the value for c4 plant is 0.04
    # and g1 is m, of which the value for c4 plant is about 4 YY
    # @parameter
    # def g0(self): return 0.04
    # @parameter
    # def g1(self): return 4.0

    # Ball-Berry model parameters from Miner and Bauerle 2017, used to be 0.04 and 4.0, respectively (2018-09-04: KDY)
    @parameter
    def g0(self): return 0.017
    @parameter
    def g1(self): return 4.53

    # calibrated above for our switchgrass dataset
    # @parameter
    # def g0(self): return 0.04
    # @parameter
    # def g1(self): return 1.89

    # @parameter
    # def g0(self): return 0.02
    # @parameter
    # def g1(self): return 2.0

    # parameters from Le et. al (2010)
    # @parameter
    # def g0(self): return 0.008
    # @parameter
    # def g1(self): return 8.0

    # for garlic
    # @parameter
    # def g0(self): return 0.096
    # @parameter
    # def g1(self): return 6.824

    #FIXME initial value never used
    #self.leafp_effect = 1 # At first assume there is not drought stress, so assign 1 to leafpEffect. Yang 8/20/06

    @derive
    # def update_boundary_layer(self, wind):
    def boundary_layer_conductance(self):
        # maize is an amphistomatous species, assume 1:1 (adaxial:abaxial) ratio.
        #sr = 1.0
        # switchgrass adaxial : abaxial (Awada 2002)
        # https://doi.org/10.4141/P01-031
        sr = 1.28
        ratio = (sr + 1)**2 / (sr**2 + 1)

        # characteristic dimension of a leaf, leaf width in m
        d = self.leaf.width * 0.72

        #return 1.42 # total BLC (both sides) for LI6400 leaf chamber
        gb = 1.4 * 0.147 * (max(0.1, self.leaf.weather.wind) / d)**0.5 * ratio
        #gb = (1.4 * 1.1 * 6.62 * (wind / d)**0.5 * (P_air / (R * (273.15 + T_air)))) # this is an alternative form including a multiplier for conversion from mm s-1 to mol m-2 s-1
        # 1.1 is the factor to convert from heat conductance to water vapor conductance, an avarage between still air and laminar flow (see Table 3.2, HG Jones 2014)
        # 6.62 is for laminar forced convection of air over flat plates on projected area basis
        # when all conversion is done for each surface it becomes close to 0.147 as given in Norman and Campbell
        # multiply by 1.4 for outdoor condition, Campbell and Norman (1998), p109, also see Jones 2014, pg 59 which suggest using 1.5 as this factor.
        # multiply by ratio to get the effective blc (per projected area basis), licor 6400 manual p 1-9
        return gb

    # stomatal conductance for water vapor in mol m-2 s-1
    #FIXME T_leaf not used
    @derive(init='g0')
    # def update_stomata(self, LWP, CO2, A_net, RH, T_leaf):
    def stomatal_conductance(self):
        # params
        g0 = self.g0
        g1 = self.g1
        gb = self.boundary_layer_conductance

        CO2 = self.leaf.weather.CO2
        A_net = self.leaf.A_net
        RH = self.leaf.weather.RH
        T_leaf = self.leaf.temperature

        #FIXME proper use of gamma
        #gamma = 10.0 # for C4 maize
        gamma = 10.0 #FIXME supposed to be temperature dependent gamma for C3 garlic
        Cs = CO2 - (1.37 * A_net / gb) # surface CO2 in mole fraction
        if Cs <= gamma:
            Cs = gamma + 1

        m = self.leafp_effect

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
        return gs

    @derive
    def leafp_effect(self):
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
        LWP = self.leaf.soil.WP_leaf
        m = (1 + np.exp(sf * phyf)) / (1 + np.exp(sf * (phyf - LWP)))
        #print(f'[LWP] pressure = {LWP}, effect = {m}')
        return m

    @derive
    def total_conductance_h2o(self):
        gs = self.stomatal_conductance
        gb = self.boundary_layer_conductance
        return gs * gb / (gs + gb)

    @derive
    def boundary_layer_resistance_co2(self):
        return 1.37 / self.boundary_layer_conductance

    @derive
    def stomatal_resistance_co2(self):
        return 1.6 / self.stomatal_conductance

    @derive
    def total_resistance_co2(self):
        return self.boundary_layer_resistance_co2 + self.stomatal_resistance_co2


class PhotosyntheticLeaf(System):
    def setup(self):
        self.stomata = Stomata(self, leaf=self)
        #TODO support modular interface
        self.photosynthesis = C4(self, leaf=self) # for maize
        #self.photosynthesis = C3(self, leaf=self) # for garlic

    #TODO organize leaf properties like water (LWP), nitrogen content?
    #TODO introduce a leaf geomtery class for leaf_width
    #TODO introduce a soil class for ET_supply

    ###########
    # Drivers #
    ###########

    # static properties

    @parameter
    def nitrogen(self):
        return 2.0

    # geometry
    @parameter
    def width(self):
        return 10 / 100 # meters

    # soil?
    @parameter
    def ET_supply(self):
        return 0

    # dynamic properties

    # mesophyll CO2 partial pressure, ubar, one may use the same value as Ci assuming infinite mesohpyle conductance
    @derive
    def co2_mesophyll(self):
        A_net = self.A_net
        T_leaf = self.temperature

        #self.stomata.update(self.weather, self.water, A_net, T_leaf)
        P = self.weather.P_air / 100
        Ca = self.weather.CO2 * P # conversion to partial pressure
        rsc = self.stomata.total_resistance_co2
        Cm = Ca - A_net * rsc * P
        #print(f"+ Cm = {Cm}, Ca = {Ca}, A_net = {A_net}, gs = {self.stomata.gs}, gb = {self.stomata.gb}, rsc = {rsc}, P = {P}")
        return np.clip(Cm, 0, 2*Ca)
        #return Cm

    #FIXME is it right place? maybe need coordination with geometry object in the future
    @derive
    def light(self):
        #FIXME make scatt global parameter?
        scatt = 0.15 # leaf reflectance + transmittance
        f = 0.15 # spectral correction

        Ia = self.weather.PFD * (1 - scatt) # absorbed irradiance
        I2 = Ia * (1 - f) / 2 # useful light absorbed by PSII
        return I2

    @optimize2
    def A_net(self):
        #I2 = self.light
        A_net0 = self.A_net
        #print(f"A_net0 = {A_net0}")
        #Cm0 = self.co2_mesophyll
        A_net1 = self.photosynthesis.net_photosynthesis
        #Cm1 = co2_mesophyll(A_net1)
        #print(f"- I2 = {I2}, Cm0 = {Cm0}, T_leaf = {T_leaf}, A_net0 = {A_net0}, A_net1 = {A_net1}, Cm1 = {Cm1}")
        #             return A_net1
        return (A_net1 - A_net0)**2

    @derive
    def Rd(self):
        return self.photosynthesis.dark_respiration

    @derive
    def A_gross(self):
        return max(0, self.A_net + self.Rd) # gets negative when PFD = 0, Rd needs to be examined, 10/25/04, SK

    #FIXME: needed?
    @derive
    def Ci(self):
        return self.co2_mesophyll

    #TODO: use @optimize
    @derive
    def temperature_adjustment(self):
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

        gha = self.stomata.boundary_layer_conductance * (0.135 / 0.147) # heat conductance, gha = 1.4*.135*sqrt(u/d), u is the wind speed in m/s} Mol m-2 s-1 ?
        gv = self.stomata.total_conductance_h2o
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
            return (psc1 / (VaporPressure.curve_slope(T_air, P_air) + psc1)) * ((R_abs - thermal_air) / (ghr * Cp) - VPD / (psc1 * P_air))
        else:
            return (R_abs - thermal_air - lamda * Jw) / (Cp * ghr)

    @derive
    def temperature(self):
        T_air = self.weather.T_air
        T_leaf = T_air + self.temperature_adjustment
        return T_leaf

    #TODO: expand @optimize decorator to support both cost function and variable definition
    # @temperature.optimize or minimize?
    # def temperature(self):
    #     return (self.temperature - self.new_temperature)**2

    @derive
    def ET(self):
        gv = self.stomata.total_conductance_h2o
        ea = VaporPressure.ambient(self.weather.T_air, self.weather.RH)
        es_leaf = VaporPressure.saturation(self.temperature)
        ET = gv * ((es_leaf - ea) / self.weather.P_air) / (1 - (es_leaf + ea) / self.weather.P_air)
        return max(0, ET) # 04/27/2011 dt took out the 1000 everything is moles now


#FIXME initialize weather and leaf more nicely, handling None case for properties
class GasExchange(System):
    def setup(self):
        #TODO: use externally initialized Weather / Soil
        self.weather = w = Weather(self)
        self.soil = s = Soil(self)
        self.leaf = PhotosyntheticLeaf(self, weather=w, soil=s)

    @derive
    def A_gross(self):
        return self.leaf.A_gross

    @derive
    def A_net(self):
        return self.leaf.A_net

    @derive
    def ET(self):
        return self.leaf.ET

    @derive
    def T_leaf(self):
        return self.leaf.temperature

    @derive
    def VPD(self):
        #TODO: use Weather directly, instead of through PhotosyntheticLeaf
        return VaporPressure.deficit(self.weather.T_air, self.weather.RH)

    @derive
    def gs(self):
        return self.leaf.stomata.stomatal_conductance


#TODO: use improved @drive
#TODO: implement @unit
class Weather(System):
    @parameter
    def PFD(self): return 1500 # umol m-2 s-1

    @parameter
    def CO2(self): return 400 # ppm

    @parameter
    def RH(self): return 0.6 # 0~1

    @parameter
    def T_air(self): return 25 # C

    @parameter
    def wind(self): return 2.0 # meters s-1

    @parameter
    def P_air(self): return 100 # kPa

    def __str__(self):
        w = self.weather
        return f'PFD = {w.PFD}, CO2 = {w.CO2}, RH = {w.RH}, T_air = {w.T_air}, wind = {w.wind}, P_air = {w.P_air}'


class Soil(System):
    @parameter
    def WP_leaf(self): return 0

    def __str__(self):
        return f'WP_leaf = {self.WP_leaf}'


import configparser
config = configparser.ConfigParser()
c = Context(config)
c.branch(GasExchange)
c.update()
