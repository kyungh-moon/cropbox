from cropbox.system import System
from cropbox.context import instance
from cropbox.statevar import accumulate, derive, difference, drive, optimize, optimize2, parameter, proxy, signal, statevar

import numpy as np
import scipy.optimize
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

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
def quadratic_solve_lower(a, b, c): return quadratic_solve(a, b, c, lower=True)
def quadratic_solve_upper(a, b, c): return quadratic_solve(a, b, c, lower=False)


class C4(System):
    #TODO: more robust interface to connect Systems (i.e. type check, automatic prop defines)
    def __init__(self, parent, leaf):
        super().__init__(parent, leaf=leaf)

    @derive(alias='Cm')
    def co2_mesophyll(self):
        Cm = self.leaf.co2_mesophyll
        return np.clip(Cm, 0, Cm)

    @derive(alias='I2')
    def light(self):
        I2 = self.leaf.light
        return np.clip(I2, 0, I2)

    @drive(alias='T')
    def temperature(self):
        return self.leaf

    nitrogen = drive('leaf', alias='N')

    ##############
    # Parameters #
    ##############

    # FIXME are they even used?
    # self.beta_ABA = 1.48e2 # Tardieu-Davies beta, Dewar (2002) Need the references !?
    # self.delta = -1.0
    # self.alpha_ABA = 1.0e-4
    # self.lambda_r = 4.0e-12 # Dewar's email
    # self.lambda_l = 1.0e-12
    # self.K_max = 6.67e-3 # max. xylem conductance (mol m-2 s-1 MPa-1) from root to leaf, Dewar (2002)

    gbs = parameter(0.003) # bundle sheath conductance to CO2, mol m-2 s-1
    # gi = parameter(1.0) # conductance to CO2 from intercelluar to mesophyle, mol m-2 s-1, assumed

    # Arrhenius equation
    @derive(alias='T_dep')
    def temperature_dependence_rate(self, Ea, T, Tb=25):
        R = 8.314 # universal gas constant (J K-1 mol-1)
        K = 273.15
        #HACK handle too low temperature values during optimization
        Tk = max(0, T + K)
        Tbk = max(0, Tb + K)
        try:
            return np.exp(Ea * (T - Tb) / (Tbk * R * Tk))
        except ZeroDivisionError:
            return 0

    @derive(alias='N_dep')
    def nitrogen_limited_rate(self, N, s=2.9, N0=0.25):
        return 2 / (1 + np.exp(-s * (max(N0, N) - N0))) - 1

    # Rd25: Values in Kim (2006) are for 31C, and the values here are normalized for 25C. SK
    @derive(alias='Rd')
    def dark_respiration(self, T_dep, Rd25=2, Ear=39800):
        return Rd25 * T_dep(Ear)

    @derive
    def Rm(self, Rd):
        return 0.5 * Rd

    @derive(alias='Jmax')
    def maximum_electron_transport_rate(self, T, T_dep, N_dep, Jm25=300, Eaj=32800, Sj=702.6, Hj=220000):
        R = 8.314

        Tb = 25
        K = 273.15
        Tk = T + K
        Tbk = Tb + K

        r = Jm25 * N_dep \
                 * T_dep(Eaj) \
                 * (1 + np.exp((Sj*Tbk - Hj) / (R*Tbk))) \
                 / (1 + np.exp((Sj*Tk  - Hj) / (R*Tk)))
        return max(0, r)

    @parameter
    def Om(self):
        # mesophyll O2 partial pressure
        O = 210 # gas units are mbar
        return O

    # Kp25: Michaelis constant for PEP caboxylase for CO2
    @derive
    def Kp(self, Kp25=80):
        return Kp25 # T dependence yet to be determined

    # Kc25: Michaelis constant of rubisco for CO2 of C4 plants (2.5 times that of tobacco), ubar, Von Caemmerer 2000
    @derive
    def Kc(self, T_dep, Kc25=650, Eac=59400):
        return Kc25 * T_dep(Eac)

    # Ko25: Michaelis constant of rubisco for O2 (2.5 times C3), mbar
    @derive
    def Ko(self, T_dep, Ko25=450, Eao=36000):
        return Ko25 * T_dep(Eao)

    @derive
    def Km(self, Kc, Om, Ko):
        # effective M-M constant for Kc in the presence of O2
        return Kc * (1 + Om / Ko)

    @derive
    def Vpmax(self, N_dep, T_dep, Vpm25=70, EaVp=75100):
        return Vpm25 * N_dep * T_dep(EaVp)

    @derive
    def Vp(self, Vpmax, Cm, Kp):
        # PEP carboxylation rate, that is the rate of C4 acid generation
        Vp = (Cm * Vpmax) / (Cm + Kp)
        Vpr = 80 # PEP regeneration limited Vp, value adopted from vC book
        Vp = np.clip(Vp, 0, Vpr)
        return Vp

    # EaVc: Sage (2002) JXB
    @derive
    def Vcmax(self, N_dep, T_dep, Vcm25=50, EaVc=55900):
        return Vcm25 * N_dep * T_dep(EaVc)

    @derive(alias='Ac')
    def enzyme_limited_photosynthesis_rate(self, Vp, gbs, Cm, Rm, Vcmax, Rd):
        # Enzyme limited A (Rubisco or PEP carboxylation)
        Ac1 = Vp + gbs*Cm - Rm
        #Ac1 = max(0, Ac1) # prevent Ac1 from being negative Yang 9/26/06
        Ac2 = Vcmax - Rd
        #print(f'Ac1 = {Ac1}, Ac2 = {Ac2}')
        Ac = min(Ac1, Ac2)
        return Ac

    # Light and electron transport limited A mediated by J
    # theta: sharpness of transition from light limitation to light saturation
    # x: Partitioning factor of J, yield maximal J at this value
    @derive(alias='Aj')
    def transport_limited_photosynthesis_rate(self, T, Jmax, Rd, Rm, I2, gbs, Cm, theta=0.5, x=0.4):
        J = quadratic_solve_lower(theta, -(I2+Jmax), I2*Jmax)
        #print(f'Jmax = {Jmax}, J = {J}')
        Aj1 = x * J/2 - Rm + gbs*Cm
        Aj2 = (1-x) * J/3 - Rd
        Aj = min(Aj1, Aj2)
        return Aj

    @derive(alias='A_net')
    def net_photosynthesis(self, Ac, Aj, beta=0.99):
        # smooting the transition between Ac and Aj
        A_net = ((Ac+Aj) - ((Ac+Aj)**2 - 4*beta*Ac*Aj)**0.5) / (2*beta)
        #print(f'Ac = {Ac}, Aj = {Aj}, A_net = {A_net}')
        return A_net

    #FIXME: currently not used variables

    # alpha: fraction of PSII activity in the bundle sheath cell, very low for NADP-ME types
    @derive(alias='Os')
    def bundle_sheath_o2(self, A_net, gbs, Om, alpha=0.0001):
        return alpha * A_net / (0.047*gbs) + Om # Bundle sheath O2 partial pressure, mbar

    @derive(alias='Cbs')
    def bundle_sheath_co2(self, A_net, Vp, Cm, Rm, gbs):
        return Cm + (Vp - A_net - Rm) / gbs # Bundle sheath CO2 partial pressure, ubar

    @derive
    def gamma(self, Rd, Km, Vcmax, Os):
        # half the reciprocal of rubisco specificity, to account for O2 dependence of CO2 comp point,
        # note that this become the same as that in C3 model when multiplied by [O2]
        gamma1 = 0.193
        gamma_star = gamma1 * Os
        return (Rd*Km + Vcmax*gamma_star) / (Vcmax - Rd)


class Stomata(System):
    def __init__(self, parent, leaf):
        super().__init__(parent, leaf=leaf)

    # Ball-Berry model parameters from Miner and Bauerle 2017, used to be 0.04 and 4.0, respectively (2018-09-04: KDY)
    g0 = parameter(0.017)
    g1 = parameter(4.53)

    A_net = proxy('leaf.A_net')
    CO2 = proxy('leaf.weather.CO2')
    RH = proxy('leaf.weather.RH')

    @derive(alias='gb')
    # def update_boundary_layer(self, wind):
    def boundary_layer_conductance(self, l='leaf', w='leaf.weather'):
        # maize is an amphistomatous species, assume 1:1 (adaxial:abaxial) ratio.
        #sr = 1.0
        # switchgrass adaxial : abaxial (Awada 2002)
        # https://doi.org/10.4141/P01-031
        sr = 1.28
        ratio = (sr + 1)**2 / (sr**2 + 1)

        # characteristic dimension of a leaf, leaf width in m
        d = l.width * 0.72

        #return 1.42 # total BLC (both sides) for LI6400 leaf chamber
        gb = 1.4 * 0.147 * (max(0.1, w.wind) / d)**0.5 * ratio
        #gb = (1.4 * 1.1 * 6.62 * (wind / d)**0.5 * (P_air / (R * (273.15 + T_air)))) # this is an alternative form including a multiplier for conversion from mm s-1 to mol m-2 s-1
        # 1.1 is the factor to convert from heat conductance to water vapor conductance, an avarage between still air and laminar flow (see Table 3.2, HG Jones 2014)
        # 6.62 is for laminar forced convection of air over flat plates on projected area basis
        # when all conversion is done for each surface it becomes close to 0.147 as given in Norman and Campbell
        # multiply by 1.4 for outdoor condition, Campbell and Norman (1998), p109, also see Jones 2014, pg 59 which suggest using 1.5 as this factor.
        # multiply by ratio to get the effective blc (per projected area basis), licor 6400 manual p 1-9
        return gb

    # stomatal conductance for water vapor in mol m-2 s-1
    # gamma: 10.0 for C4 maize
    #FIXME T_leaf not used
    @derive(alias='gs', init='g0')
    # def update_stomata(self, LWP, CO2, A_net, RH, T_leaf):
    #def stomatal_conductance(self, g0, g1, gb, m, A_net='leaf.A_net', CO2='leaf.weather.CO2', RH='leaf.weather.RH', gamma=10):
    def stomatal_conductance(self, g0, g1, gb, m, A_net, CO2, RH, gamma=10):
        Cs = CO2 - (1.37 * A_net / gb) # surface CO2 in mole fraction
        Cs = max(Cs, gamma)

        a = m * g1 * A_net / Cs
        b = g0 + gb - (m * g1 * A_net / Cs)
        c = (-RH * gb) - g0
        #hs = max(np.roots([a, b, c]))
        #hs = scipy.optimize.brentq(lambda x: np.polyval([a, b, c], x), 0, 1)
        #hs = scipy.optimize.fsolve(lambda x: np.polyval([a, b, c], x), 0)
        hs = quadratic_solve_upper(a, b, c)
        #hs = np.clip(hs, 0.1, 1.0) # preventing bifurcation: used to be (0.3, 1.0) for C4 maize

        #FIXME unused?
        #T_leaf = l.temperature
        #es = w.vp.saturation(T_leaf)
        #Ds = (1 - hs) * es # VPD at leaf surface
        #Ds = w.vp.deficit(T_leaf, hs)

        gs = g0 + (g1 * m * (A_net * hs / Cs))
        gs = max(gs, g0)
        return gs

    @derive(alias='m')
    def leafp_effect(self, LWP='leaf.soil.WP_leaf', sf=2.3, phyf=-2.0):
        return (1 + np.exp(sf * phyf)) / (1 + np.exp(sf * (phyf - LWP)))

    @derive(alias='gv')
    def total_conductance_h2o(self, gs, gb):
        return gs * gb / (gs + gb)

    @derive(alias='rbc')
    def boundary_layer_resistance_co2(self, gb):
        return 1.37 / gb

    @derive(alias='rsc')
    def stomatal_resistance_co2(self, gs):
        return 1.6 / gs

    @derive(alias='rvc')
    def total_resistance_co2(self, rbc, rsc):
        return rbc + rsc


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
    nitrogen = parameter(2.0)

    # geometry
    width = parameter(10 / 100) # meters

    # soil?
    ET_supply = parameter(0)

    # dynamic properties

    # mesophyll CO2 partial pressure, ubar, one may use the same value as Ci assuming infinite mesohpyle conductance
    @derive(alias='Cm')
    def co2_mesophyll(self, A_net, w='weather', rvc='stomata.rvc'):
        P = w.P_air / 100
        Ca = w.CO2 * P # conversion to partial pressure
        Cm = Ca - A_net * rvc * P
        #print(f"+ Cm = {Cm}, Ca = {Ca}, A_net = {A_net}, gs = {self.stomata.gs}, gb = {self.stomata.gb}, rvc = {rvc}, P = {P}")
        return np.clip(Cm, 0, 2*Ca)
        #return Cm

    #FIXME is it right place? maybe need coordination with geometry object in the future
    @derive(alias='I2')
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
    def temperature_adjustment(self, w='weather', s='stomata'):
        # see Campbell and Norman (1998) pp 224-225
        # because Stefan-Boltzman constant is for unit surface area by denifition,
        # all terms including sbc are multilplied by 2 (i.e., gr, thermal radiation)
        lamda = 44000 # KJ mole-1 at 25oC
        psc = 6.66e-4
        Cp = 29.3 # thermodynamic psychrometer constant and specific heat of air (J mol-1 C-1)

        epsilon = 0.97
        sbc = 5.6697e-8

        T_air = w.T_air
        Tk = T_air + 273.15
        PFD = w.PFD
        P_air = w.P_air
        Jw = self.ET_supply

        gha = s.boundary_layer_conductance * (0.135 / 0.147) # heat conductance, gha = 1.4*.135*sqrt(u/d), u is the wind speed in m/s} Mol m-2 s-1 ?
        gv = s.total_conductance_h2o
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
            # eqn 14.6b linearized form using first order approximation of Taylor series
            return (psc1 / (w.VPD_slope + psc1)) * ((R_abs - thermal_air) / (ghr * Cp) - w.VPD / (psc1 * P_air))
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
    def ET(self, vp='weather.vp'):
        gv = self.stomata.total_conductance_h2o
        ea = vp.ambient(self.weather.T_air, self.weather.RH)
        es_leaf = vp.saturation(self.temperature)
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
        return self.weather.VPD

    @derive
    def gs(self):
        return self.leaf.stomata.stomatal_conductance


class VaporPressure(System):
    # Campbell and Norman (1998), p 41 Saturation vapor pressure in kPa
    a = parameter(0.611) # kPa
    b = parameter(17.502) # C
    c = parameter(240.97) # C

    @derive(alias='es')
    def saturation(self, T, *, a, b, c):
        return a*np.exp((b*T)/(c+T))

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
    def setup(self):
        self.vp = VaporPressure(self)

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

    @derive
    def VPD(self, T_air, RH): return self.vp.deficit(T_air, RH)

    @derive
    def VPD_slope(self, T_air, P_air): return self.vp.curve_slope(T_air, P_air)

    def __str__(self):
        w = self
        return f'PFD = {w.PFD}, CO2 = {w.CO2}, RH = {w.RH}, T_air = {w.T_air}, wind = {w.wind}, P_air = {w.P_air}'


class Soil(System):
    # pressure - leaf water potential MPa...
    @parameter
    def WP_leaf(self): return 0

    def __str__(self):
        return f'WP_leaf = {self.WP_leaf}'


config = ''

# config += """
# # Kim et al. (2007), Kim et al. (2006)
# # In von Cammerer (2000), Vpm25=120, Vcm25=60,Jm25=400
# # In Soo et al.(2006), under elevated C5O2, Vpm25=91.9, Vcm25=71.6, Jm25=354.2 YY
# C4.Vpmax.Vpm25 = 70
# C4.Vcmax.Vcm25 = 50
# C4.Jmax.Jm25 = 300
# C4.Rd.Rd25 = 2 # Values in Kim (2006) are for 31C, and the values here are normalized for 25C. SK
# """

# config += """
# [C4]
# # switgrass params from Albaugha et al. (2014)
# # https://doi.org/10.1016/j.agrformet.2014.02.013
# C4.Vpmax.Vpm25 = 52
# C4.Vcmax.Vcm25 = 26
# C4.Jmax.Jm25 = 145
# """

# config += """
# # switchgrass Vcmax from Le et al. (2010), others multiplied from Vcmax (x2, x5.5)
# C4.Vpmax.Vpm25 = 96
# C4.Vcmax.Vcm25 = 48
# C4.Jmax.Jm25 = 264
# """

# config += """
# C4.Vpmax.Vpm25 = 100
# C4.Vcmax.Vcm25 = 50
# C4.Jmax.Jm25 = 200
# """

# config += """
# C4.Vpmax.Vpm25 = 70
# C4.Vcmax.Vcm25 = 50
# C4.Jmax.Jm25 = 180.8
# """

# config += """
# # switchgrass params from Albaugha et al. (2014)
# C4.Rd.Rd25 = 3.6 # not sure if it was normalized to 25 C
# C4.Aj.theta = 0.79
# """

# config += """
# # In Sinclair and Horie, Crop Sciences, 1989
# C4.N_dep.s = 4
# C4.N_dep.N0 = 0.2
# # In J Vos et al. Field Crop Research, 2005
# C4.N_dep.s = 2.9
# C4.N_dep.N0 = 0.25
# # In Lindquist, Weed Science, 2001
# C4.N_dep.s = 3.689
# C4.N_dep.N0 = 0.5
# """

# config += """
# # in P. J. Sellers, et al.Science 275, 502 (1997)
# # g0 is b, of which the value for c4 plant is 0.04
# # and g1 is m, of which the value for c4 plant is about 4 YY
# Stomata.g0 = 0.04
# Stomata.g1 = 4.0
# """

# config += """
# # Ball-Berry model parameters from Miner and Bauerle 2017, used to be 0.04 and 4.0, respectively (2018-09-04: KDY)
# Stomata.g0 = 0.017
# Stomata.g1 = 4.53
# """

# config += """
# # calibrated above for our switchgrass dataset
# Stomata.g0 = 0.04
# Stomata.g1 = 1.89
# """

# config += """
# Stomata.g0 = 0.02
# Stomata.g1 = 2.0
# """

# config += """
# # parameters from Le et. al (2010)
# Stomata.g0 = 0.008
# Stomata.g1 = 8.0
# """

# config += """
# # for garlic
# Stomata.g0 = 0.0096
# Stomata.g1 = 6.824
# """

# config += """
# Stomata.m.sf = 2.3 # sensitivity parameter Tuzet et al. 2003 Yang
# Stomata.m.phyf = -1.2 # reference potential Tuzet et al. 2003 Yang
# """

# config += """
# #? = -1.68 # minimum sustainable leaf water potential (Albaugha 2014)
# # switchgrass params from Le et al. (2010)
# Stomata.m.sf = 6.5
# Stomata.m.phyf = -1.3
# """

# config += """
# #FIXME August-Roche-Magnus formula gives slightly different parameters
# # https://en.wikipedia.org/wiki/Clausius–Clapeyron_relation
# VaporPressure.a = 0.61094 # kPa
# VaporPressure.b = 17.625 # C
# VaporPressure.c = 243.04 # C
# """

ge = instance(GasExchange, config)