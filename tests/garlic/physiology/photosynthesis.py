from cropbox.statevar import constant, derive, parameter, system, systemproxy
from cropbox.system import System

from .trait import Trait
from .gasexchange import GasExchange
from .radiation import Radiation
from .weight import Weight
from ..atmosphere.sun import Sun
from ..atmosphere.weather import Weather

import numpy as np

class SunlitWeather(Weather):
    weather = systemproxy()
    radiation = system()
    photosynthetic_photon_flux_density = derive('radiation.irradiance_Q_sunlit', alias='PPFD', unit='umol/m^2/s Quanta')

class ShadedWeather(Weather):
    weather = systemproxy()
    radiation = system()
    photosynthetic_photon_flux_density = derive('radiation.irradiance_Q_shaded', alias='PPFD', unit='umol/m^2/s Quanta')

#TODO rename to CarbonAssimilation or so? could be consistently named as CarbonPartition, CarbonAllocation...
class Photosynthesis(Trait):
    radiation = system(Radiation, sun='p.weather.sun', LAI='LAI', LAF='LAF')

    sunlit_weather = system(SunlitWeather, weather='p.weather', radiation='radiation')
    shaded_weather = system(ShadedWeather, weather='p.weather', radiation='radiation')

    # Calculating transpiration and photosynthesis with stomatal controlled by leaf water potential LeafWP Y
    #TODO: use self.p.nitrogen.leaf_content, leaf_width, ET_supply
    sunlit = system(GasExchange, soil='plant.soil', name='Sunlit', weather='sunlit_weather')
    shaded = system(GasExchange, soil='plant.soil', name='Shaded', weather='shaded_weather')

    #tau = 0.50 # atmospheric transmittance, to be implemented as a variable => done

    @parameter(alias='LAF')
    def leaf_angle_factor(self):
        # leaf angle factor for corn leaves, Campbell and Norman (1998)
        return 1.37

    @parameter(unit='cm')
    def leaf_width(self):
        return 5.0 # to be calculated when implemented for individal leaves

    @derive(alias='LAI')
    def leaf_area_index(self):
        return self.p.area.leaf_area_index

    @derive(alias='LWP')
    def leaf_water_potential(self):
        #TODO how do we get LeafWP and ET_supply?
        return self.p.soil.WP_leaf

    @derive(alias='ET_supply')
    def evapotranspiration_supply(self, LAI):
        #TODO common handling logic for zero LAI
        try:
            return self.p.water.supply * self.p.planting_density / 3600 / 18.01 / LAI
        except ZeroDivisionError:
            return 0

    @derive
    def sunlit_leaf_area_index(self):
        return self.radiation.sunlit_leaf_area_index

    @derive
    def shaded_leaf_area_index(self):
        return self.radiation.shaded_leaf_area_index

    @derive
    def leaf_area_index_array(self):
        return np.array([
            self.sunlit_leaf_area_index,
            self.shaded_leaf_area_index,
        ])

    @derive
    def _weighted(self, array):
        return self.leaf_area_index_array.dot(array)

    @derive
    def sunlit_irradiance(self):
        return self.radiation.irradiance_Q_sunlit

    @derive
    def shaded_irradiance(self):
        return self.radiation.irradiance_Q_shaded

    @derive
    def gross_array(self):
        return np.array([
            self.sunlit.A_gross,
            self.shaded.A_gross,
        ])

    @derive
    def net_array(self):
        return np.array([
            self.sunlit.A_net,
            self.shaded.A_net,
        ])

    @derive
    def evapotranspiration_array(self):
        return np.array([
            self.sunlit.ET,
            self.shaded.ET,
        ])

    @derive
    def temperature_array(self):
        return np.array([
            self.sunlit.T_leaf,
            self.shaded.T_leaf,
        ])

    @derive
    def conductance_array(self):
        return np.array([
            self.sunlit.gs,
            self.shaded.gs,
        ])

    @derive
    def gross_CO2_umol_per_m2_s(self):
        return self._weighted(self.gross_array)

    # plantsPerMeterSquare units are umol CO2 m-2 ground s-1
    # in the following we convert to g C plant-1 per hour
    # photosynthesis_gross is umol CO2 m-2 leaf s-1

    @derive
    def net_CO2_umol_per_m2_s(self):
        # grams CO2 per plant per hour
        return self._weighted(self.net_array)

    @derive
    def transpiration_H2O_mol_per_m2_s(self):
        #TODO need to save this?
        # when outputting the previous step transpiration is compared to the current step's water uptake
        #self.transpiration_old = self.transpiration
        #FIXME need to check if LAIs are negative?
        #transpiration = sunlit.ET * max(0, sunlit_LAI) + shaded.ET * max(0, shaded_LAI)
        return self._weighted(self.evapotranspiration_array)

    #TODO consolidate unit conversions somewhere else

    @constant
    def _mol_per_umol(self):
        return 1 / 1e6

    @derive
    def _plant_per_m2(self):
        return 1 / self.p.planting_density

    @derive
    def _min_step_per_sec(self):
        #FIXME: proper use of context.interval and unit
        return 60 * 60 # self.p.initials.timestep

    # final values

    @derive
    def assimilation(self):
        # grams CO2 per plant per hour
        return np.prod([
            self.gross_CO2_umol_per_m2_s,
            self._mol_per_umol,
            self._plant_per_m2,
            self._min_step_per_sec,
            Weight.CO2,
        ])

    @derive
    def gross(self):
        # grams carbo per plant per hour
        return np.prod([
            self.gross_CO2_umol_per_m2_s,
            self._mol_per_umol,
            self._plant_per_m2,
            self._min_step_per_sec,
            Weight.CH2O,
        ])

    @derive
    def net(self):
        # grams carbo per plant per hour
        return np.prod([
            self.net_CO2_umol_per_m2_s,
            self._mol_per_umol,
            self._plant_per_m2,
            self._min_step_per_sec,
            Weight.CH2O,
        ])

    @derive
    def transpiration(self):
        # Units of Transpiration from sunlit->ET are mol m-2 (leaf area) s-1
        # Calculation of transpiration from ET involves the conversion to gr per plant per hour
        #FIXME _min_step_per_sec used instead of fixed 3600 = 60 * 60
        return np.prod([
            self.transpiration_H2O_mol_per_m2_s,
            self._plant_per_m2,
            self._min_step_per_sec,
            Weight.H2O,
        ])

    @derive
    def temperature(self):
        return self._weighted(self.temperature_array)

    @derive
    def vapor_pressure_deficit(self):
        #HACK only use sunlit leaves?
        return max(0, self.sunlit.VPD)

    @derive
    def conductance(self):
        #HACK ensure 0 when one if LAI is 0, i.e., night
        if (self.leaf_area_index_array == 0).any():
            return 0
        try:
            # average stomatal conductance Yang
            c = self._weighted(self.conductance_array) / self.leaf_area_index
            return max(0, c)
        except ZeroDivisionError:
            return 0
