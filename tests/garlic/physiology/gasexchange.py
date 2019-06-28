from cropbox.system import System
from cropbox.statevar import accumulate, constant, derive, difference, drive, optimize, parameter, proxy, statevar, system
from cropbox.unit import U

from ..rhizosphere.soil import Soil

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
    leaf = system()

    @derive(alias='Cm', unit='umol/mol CO2')
    def co2_mesophyll(self):
        Cm = self.leaf.co2_mesophyll
        return np.clip(Cm, U(0, 'umol/mol CO2'), Cm)

    @derive(alias='I2', unit='umol/m^2/s Quanta')
    def light(self):
        I2 = self.leaf.light
        return np.clip(I2, U(0, 'umol/m^2/s Quanta'), I2)

    @drive(alias='T', unit='degC')
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

    gbs = parameter(0.003, unit='mol/m^2/s CO2') # bundle sheath conductance to CO2, mol m-2 s-1
    # gi = parameter(1.0) # conductance to CO2 from intercelluar to mesophyle, mol m-2 s-1, assumed

    # Arrhenius equation
    @derive(alias='T_dep')
    def temperature_dependence_rate(self, Ea, T, Tb=U(25, 'degC')):
        R = U(8.314, 'J/K/mol') # universal gas constant (J K-1 mol-1)
        #HACK handle too low temperature values during optimization
        Tk = max(U(0, 'degK'), T.to('degK'))
        Tbk = max(U(0, 'degK'), Tb.to('degK'))
        try:
            return np.exp(Ea * (T - Tb) / (Tbk * R * Tk))
        except ZeroDivisionError:
            return 0

    @derive(alias='N_dep')
    def nitrogen_limited_rate(self, N, s=2.9, N0=0.25):
        return 2 / (1 + np.exp(-s * (max(N0, N) - N0))) - 1

    # Rd25: Values in Kim (2006) are for 31C, and the values here are normalized for 25C. SK
    @derive(alias='Rd')
    def dark_respiration(self, T_dep, Rd25=U(2, 'umol/m^2/s O2'), Ear=U(39800, 'J/mol')):
        return Rd25 * T_dep(Ear)

    @derive
    def Rm(self, Rd):
        return 0.5 * Rd

    @derive(alias='Jmax', unit='umol/m^2/s Electron')
    def maximum_electron_transport_rate(self, T, T_dep, N_dep,
        Jm25=U(300, 'umol/m^2/s Electron'),
        Eaj=U(32800, 'J/mol'),
        Sj=U(702.6, 'J/mol/degK'),
        Hj=U(220000, 'J/mol')
    ):
        R = U(8.314, 'J/K/mol')

        Tb = U(25, 'degC')
        Tk = T.to('degK')
        Tbk = Tb.to('degK')

        r = Jm25 * N_dep \
                 * T_dep(Eaj) \
                 * (1 + np.exp((Sj*Tbk - Hj) / (R*Tbk))) \
                 / (1 + np.exp((Sj*Tk  - Hj) / (R*Tk)))
        return max(0, r)

    @parameter(unit='mbar')
    def Om(self):
        # mesophyll O2 partial pressure
        O = 210 # gas units are mbar
        return O

    # Kp25: Michaelis constant for PEP caboxylase for CO2
    @derive(unit='ubar')
    def Kp(self, Kp25=U(80, 'ubar')):
        return Kp25 # T dependence yet to be determined

    # Kc25: Michaelis constant of rubisco for CO2 of C4 plants (2.5 times that of tobacco), ubar, Von Caemmerer 2000
    @derive(unit='ubar')
    def Kc(self, T_dep, Kc25=U(650, 'ubar'), Eac=U(59400, 'J/mol')):
        return Kc25 * T_dep(Eac)

    # Ko25: Michaelis constant of rubisco for O2 (2.5 times C3), mbar
    @derive(unit='mbar')
    def Ko(self, T_dep, Ko25=U(450, 'mbar'), Eao=U(36000, 'J/mol')):
        return Ko25 * T_dep(Eao)

    @derive(unit='ubar')
    def Km(self, Kc, Om, Ko):
        # effective M-M constant for Kc in the presence of O2
        return Kc * (1 + Om / Ko)

    @derive(unit='umol/m^2/s CO2')
    def Vpmax(self, N_dep, T_dep, Vpm25=U(70, 'umol/m^2/s CO2'), EaVp=U(75100, 'J/mol')):
        return Vpm25 * N_dep * T_dep(EaVp)

    @derive(unit='umol/m^2/s CO2')
    def Vp(self, Vpmax, Cm, Kp):
        # PEP carboxylation rate, that is the rate of C4 acid generation
        Vp = (Cm * Vpmax) / (Cm + Kp / U(1, 'atm'))
        Vpr = U(80, 'umol/m^2/s CO2') # PEP regeneration limited Vp, value adopted from vC book
        Vp = np.clip(Vp, U(0, 'umol/m^2/s CO2'), Vpr)
        return Vp

    # EaVc: Sage (2002) JXB
    @derive(unit='umol/m^2/s CO2')
    def Vcmax(self, N_dep, T_dep, Vcm25=U(50, 'umol/m^2/s CO2'), EaVc=U(55900, 'J/mol')):
        return Vcm25 * N_dep * T_dep(EaVc)

    @derive(alias='Ac', unit='umol/m^2/s CO2')
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
    @derive(alias='Aj', unit='umol/m^2/s CO2')
    def transport_limited_photosynthesis_rate(self, T, Jmax, Rd, Rm, I2, gbs, Cm, theta=0.5, x=0.4):
        J = quadratic_solve_lower(theta, -(I2+Jmax), I2*Jmax)
        #print(f'Jmax = {Jmax}, J = {J}')
        Aj1 = x * J/2 - Rm + gbs*Cm
        Aj2 = (1-x) * J/3 - Rd
        Aj = min(Aj1, Aj2)
        return Aj

    @derive(alias='A_net', unit='umol/m^2/s CO2')
    def net_photosynthesis(self, Ac, Aj, beta=0.99):
        # smooting the transition between Ac and Aj
        A_net = ((Ac+Aj) - ((Ac+Aj)**2 - 4*beta*Ac*Aj)**0.5) / (2*beta)
        #print(f'Ac = {Ac}, Aj = {Aj}, A_net = {A_net}')
        return A_net

    #FIXME: currently not used variables

    # alpha: fraction of PSII activity in the bundle sheath cell, very low for NADP-ME types
    @derive(alias='Os', unit='mbar')
    def bundle_sheath_o2(self, A_net, gbs, Om, alpha=0.0001):
        return alpha * A_net / (0.047*gbs) * U(1, 'atm') + Om # Bundle sheath O2 partial pressure, mbar

    @derive(alias='Cbs', unit='ubar')
    def bundle_sheath_co2(self, A_net, Vp, Cm, Rm, gbs):
        return Cm + (Vp - A_net - Rm) / gbs # Bundle sheath CO2 partial pressure, ubar

    @derive(unit='ubar')
    def gamma(self, Rd, Km, Vcmax, Os):
        # half the reciprocal of rubisco specificity, to account for O2 dependence of CO2 comp point,
        # note that this become the same as that in C3 model when multiplied by [O2]
        gamma1 = 0.193
        gamma_star = gamma1 * Os
        return (Rd*Km + Vcmax*gamma_star) / (Vcmax - Rd)


class Stomata(System):
    @system
    def leaf(self):
        return System

    # Ball-Berry model parameters from Miner and Bauerle 2017, used to be 0.04 and 4.0, respectively (2018-09-04: KDY)
    g0 = parameter(0.017, unit='mmol/m^2/s H2O')
    g1 = parameter(4.53)

    A_net = proxy('leaf.A_net')
    CO2 = proxy('leaf.weather.CO2')
    RH = proxy('leaf.weather.RH')

    @parameter(alias='drb', unit='H2O/CO2')
    def diffusivity_ratio_boundary_layer(self):
        return 1.37

    @parameter(alias='dra', unit='H2O/CO2')
    def diffusivity_ratio_air(self):
        return 1.6

    @derive(alias='gb', unit='mol/m^2/s H2O', nounit='lw,ww')
    # def update_boundary_layer(self, wind):
    def boundary_layer_conductance(self, lw='leaf.width', ww='leaf.weather.wind'):
        # maize is an amphistomatous species, assume 1:1 (adaxial:abaxial) ratio.
        #sr = 1.0
        # switchgrass adaxial : abaxial (Awada 2002)
        # https://doi.org/10.4141/P01-031
        sr = 1.28
        ratio = (sr + 1)**2 / (sr**2 + 1)

        # characteristic dimension of a leaf, leaf width in m
        d = lw * 0.72

        #return 1.42 # total BLC (both sides) for LI6400 leaf chamber
        gb = 1.4 * 0.147 * (max(0.1, ww) / d)**0.5 * ratio
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
    @derive(alias='gs', init='g0', unit='mol/m^2/s H2O')
    # def update_stomata(self, LWP, CO2, A_net, RH, T_leaf):
    #def stomatal_conductance(self, g0, g1, gb, m, A_net='leaf.A_net', CO2='leaf.weather.CO2', RH='leaf.weather.RH', gamma=10):
    def stomatal_conductance(self, g0, g1, gb, m, A_net, CO2, RH, drb, gamma=U(10, 'umol/mol')):
        Cs = CO2 - (drb * A_net / gb) # surface CO2 in mole fraction
        Cs = max(Cs, gamma)

        a = m * g1 * A_net / Cs
        b = g0 + gb - a
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

    @derive(alias='gv', unit='mmol/m^2/s H2O')
    def total_conductance_h2o(self, gs, gb):
        return gs * gb / (gs + gb)

    @derive(alias='rbc')
    def boundary_layer_resistance_co2(self, gb, drb):
        return drb / gb

    @derive(alias='rsc')
    def stomatal_resistance_co2(self, gs, dra):
        return dra / gs

    @derive(alias='rvc')
    def total_resistance_co2(self, rbc, rsc):
        return rbc + rsc


class PhotosyntheticLeaf(System):
    weather = system()
    soil = system()

    @system(leaf='self')
    def stomata(self):
        return Stomata

    photosynthesis = system(C4, leaf='self') # for maize
    #photosynthesis = system(C3, leaf='self') # for garlic

    #TODO organize leaf properties like water (LWP), nitrogen content?
    #TODO introduce a leaf geomtery class for leaf_width
    #TODO introduce a soil class for ET_supply

    ###########
    # Drivers #
    ###########

    # static properties
    nitrogen = parameter(2.0)

    # geometry
    width = parameter(10 / 100, unit='m') # meters

    # soil?
    ET_supply = parameter(0, unit='mol/m^2/s H2O') # actual water uptake rate (mol H2O m-2 s-1)

    # dynamic properties

    # mesophyll CO2 partial pressure, ubar, one may use the same value as Ci assuming infinite mesohpyle conductance
    @derive(alias='Cm,Ci', unit='umol/mol CO2')
    def co2_mesophyll(self, A_net, w='weather', rvc='stomata.rvc'):
        P = w.P_air / U(100, 'kPa')
        Ca = w.CO2 * P # conversion to partial pressure
        Cm = Ca - A_net * rvc * P
        #print(f"+ Cm = {Cm}, Ca = {Ca}, A_net = {A_net}, gs = {self.stomata.gs}, gb = {self.stomata.gb}, rvc = {rvc}, P = {P}")
        return np.clip(Cm, U(0, 'umol/mol CO2'), 2*Ca)
        #return Cm

    #FIXME is it right place? maybe need coordination with geometry object in the future
    @derive(alias='I2', unit='umol/m^2/s Quanta')
    def light(self):
        #FIXME make scatt global parameter?
        scatt = 0.15 # leaf reflectance + transmittance
        f = 0.15 # spectral correction

        Ia = self.weather.PPFD * (1 - scatt) # absorbed irradiance
        I2 = Ia * (1 - f) / 2 # useful light absorbed by PSII
        return I2

    @optimize(alias='A_net', unit='umol/m^2/s CO2')
    def net_photosynthesis(self):
        #I2 = self.light
        A_net0 = self.A_net
        #print(f"A_net0 = {A_net0}")
        #Cm0 = self.co2_mesophyll
        A_net1 = self.photosynthesis.net_photosynthesis
        #Cm1 = co2_mesophyll(A_net1)
        #print(f"- I2 = {I2}, Cm0 = {Cm0}, T_leaf = {T_leaf}, A_net0 = {A_net0}, A_net1 = {A_net1}, Cm1 = {Cm1}")
        #             return A_net1
        return (A_net1 - A_net0)**2

    @derive(alias='Rd')
    def dark_respiration(self):
        return self.photosynthesis.dark_respiration

    @derive(alias='A_gross')
    def gross_photosynthesis(self):
        return max(0, self.A_net + self.Rd) # gets negative when PFD = 0, Rd needs to be examined, 10/25/04, SK

    @derive(alias='gs')
    def stomatal_conductance(self):
        return self.stomata.stomatal_conductance

    #TODO: use @optimize
    @derive(unit='delta_degC')
    def temperature_adjustment(self, w='weather', s='stomata',
        # see Campbell and Norman (1998) pp 224-225
        # because Stefan-Boltzman constant is for unit surface area by denifition,
        # all terms including sbc are multilplied by 2 (i.e., gr, thermal radiation)
        lamda=U(44.0, 'kJ/mol'), # KJ mole-1 at 25oC
        Cp=U(29.3, 'J/mol/degC'), # thermodynamic psychrometer constant and specific heat of air (J mol-1 C-1)
        epsilon=0.97,
        sbc=U(5.6697e-8, 'J/m^2/s/degK^4'), # Stefan-Boltzmann constant (W m-2 K-4)
    ):
        T_air = w.T_air
        Tk = T_air.to('degK')
        PFD = w.PPFD
        P_air = w.P_air
        Jw = self.ET_supply

        gha = s.boundary_layer_conductance * (0.135 / 0.147) # heat conductance, gha = 1.4*.135*sqrt(u/d), u is the wind speed in m/s} Mol m-2 s-1 ?
        gv = s.total_conductance_h2o
        gr = 4 * epsilon * sbc * Tk**3 / Cp * 2 # radiative conductance, 2 account for both sides
        ghr = gha + gr
        thermal_air = epsilon * sbc * Tk**4 * 2 # emitted thermal radiation
        psc = Cp / lamda # psychrometric constant (C-1)
        psc1 = psc * ghr / gv # apparent psychrometer constant

        PAR = U(PFD.to('umol/m^2/s Quanta').magnitude / 4.55, 'J/m^2/s') # W m-2
        # If total solar radiation unavailable, assume NIR the same energy as PAR waveband
        NIR = PAR
        scatt = 0.15
        # shortwave radiation (PAR (=0.85) + NIR (=0.15) solar radiation absorptivity of leaves: =~ 0.5
        # times 2 for projected area basis
        R_abs = (1 - scatt)*PAR + scatt*NIR + 2*(epsilon * sbc * Tk**4)

        # debug dt I commented out the changes that yang made for leaf temperature for a test. I don't think they work
        if Jw == 0:
            # (R_abs - thermal_air - lamda * gv * w.VPD / P_air) / (Cp * ghr + lamda * w.saturation_slope * gv) # eqn 14.6a
            # eqn 14.6b linearized form using first order approximation of Taylor series
            return (psc1 / (w.saturation_slope + psc1)) * ((R_abs - thermal_air) / (ghr * Cp) - w.VPD / (psc1 * P_air))
        else:
            return (R_abs - thermal_air - lamda * Jw) / (Cp * ghr)

    @derive(alias='T', unit='degC')
    def temperature(self):
        T_air = self.weather.T_air
        T_leaf = T_air + self.temperature_adjustment
        return T_leaf

    #TODO: expand @optimize decorator to support both cost function and variable definition
    # @temperature.optimize or minimize?
    # def temperature(self):
    #     return (self.temperature - self.new_temperature)**2

    @derive(alias='ET')
    def evapotranspiration(self, vp='weather.vp'):
        gv = self.stomata.total_conductance_h2o
        ea = vp.ambient(self.weather.T_air, self.weather.RH)
        es_leaf = vp.saturation(self.temperature)
        ET = gv * ((es_leaf - ea) / self.weather.P_air) / (1 - (es_leaf + ea) / self.weather.P_air)
        return max(0, ET) # 04/27/2011 dt took out the 1000 everything is moles now


#FIXME initialize weather and leaf more nicely, handling None case for properties
class GasExchange(System):
    weather = system(alias='w')
    soil = system()
    leaf = system(PhotosyntheticLeaf, weather='weather', soil='soil')

    @constant
    def name(self):
        return ''

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
