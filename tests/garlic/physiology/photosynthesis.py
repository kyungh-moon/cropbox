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
    #FIXME remove dep to Photosynthesis
    radiation = system(Radiation, sun='p.weather.sun', photosynthesis='self')

    sunlit_weather = system(SunlitWeather, weather='p.weather', radiation='radiation')
    shaded_weather = system(ShadedWeather, weather='p.weather', radiation='radiation')

    # Calculating transpiration and photosynthesis with stomatal controlled by leaf water potential LeafWP Y
    #TODO: use self.p.nitrogen.leaf_content, leaf_width, ET_supply
    sunlit = system(GasExchange, soil='plant.soil', name='Sunlit', weather='sunlit_weather')
    shaded = system(GasExchange, soil='plant.soil', name='Shaded', weather='shaded_weather')

    @parameter(unit='cm')
    def leaf_width(self):
        # to be calculated when implemented for individal leaves
        #return 5.0 # for maize
        return 1.5 # for garlic

    @derive(alias='LAI')
    def leaf_area_index(self):
        return self.p.area.leaf_area_index

    @derive(alias='LWP')
    def leaf_water_potential(self):
        #TODO how do we get LeafWP and ET_supply?
        return self.p.soil.WP_leaf

    @derive(alias='ET_supply', unit='mol/m^2/s H2O')
    def evapotranspiration_supply(self, LAI):
        #TODO common handling logic for zero LAI
        try:
            #FIXME check unit conversion (w.r.t p.water.supply)
            # ? * (1/m^2) / (3600s/hour) / (g/umol) / (cm^2/m^2) = mol/m^2/s H2O
            # ? * (1/m^2) * (hour/3600s) * (umol/g) * (m^2/cm^2) = mol/m^2/s H2O
            # ?(g / hour) * (hour/3600s) * (umol/g) / cm^2
            return self.p.water.supply * self.p.planting_density / 3600 / Weight.H2O / LAI
        except ZeroDivisionError:
            return 0

    @derive(unit='cm^2 / m^2')
    def sunlit_leaf_area_index(self):
        return self.radiation.sunlit_leaf_area_index

    @derive(unit='cm^2 / m^2')
    def shaded_leaf_area_index(self):
        return self.radiation.shaded_leaf_area_index

    @derive
    def _weighted(self, array):
        return self.sunlit_leaf_area_index * array[0] + self.shaded_leaf_area_index * array[1]

    @derive(unit='umol/m^2/s Quanta')
    def sunlit_irradiance(self):
        return self.radiation.irradiance_Q_sunlit

    @derive(unit='umol/m^2/s Quanta')
    def shaded_irradiance(self):
        return self.radiation.irradiance_Q_shaded

    @derive
    def gross_array(self):
        return (
            self.sunlit.A_gross,
            self.shaded.A_gross,
        )

    @derive
    def net_array(self):
        return (
            self.sunlit.A_net,
            self.shaded.A_net,
        )

    @derive
    def evapotranspiration_array(self):
        return (
            self.sunlit.ET,
            self.shaded.ET,
        )

    # @derive
    # def temperature_array(self):
    #     return (
    #         self.sunlit.T_leaf,
    #         self.shaded.T_leaf,
    #     )

    @derive
    def conductance_array(self):
        return (
            self.sunlit.gs,
            self.shaded.gs,
        )

    @derive(unit='umol/m^2/s CO2')
    def gross_CO2_umol_per_m2_s(self):
        return self._weighted(self.gross_array)

    # plantsPerMeterSquare units are umol CO2 m-2 ground s-1
    # in the following we convert to g C plant-1 per hour
    # photosynthesis_gross is umol CO2 m-2 leaf s-1

    @derive(unit='umol/m^2/s CO2')
    def net_CO2_umol_per_m2_s(self):
        # grams CO2 per plant per hour
        return self._weighted(self.net_array)

    @derive(unit='umol/m^2/s H2O')
    def transpiration_H2O_mol_per_m2_s(self):
        #TODO need to save this?
        # when outputting the previous step transpiration is compared to the current step's water uptake
        #self.transpiration_old = self.transpiration
        #FIXME need to check if LAIs are negative?
        #transpiration = sunlit.ET * max(0, sunlit_LAI) + shaded.ET * max(0, shaded_LAI)
        return self._weighted(self.evapotranspiration_array)

    # final values
    #TODO check final units

    @derive
    def assimilation(self):
        # grams CO2 per plant per hour
        return self.gross_CO2_umol_per_m2_s / self.p.planting_density * self.context.interval * Weight.CO2

    @derive
    def gross(self):
        # grams carbo per plant per hour
        #FIXME check unit conversion between C/CO2 to CH2O
        return self.gross_CO2_umol_per_m2_s / self.p.planting_density * self.context.interval * Weight.CH2O

    @derive
    def net(self):
        # grams carbo per plant per hour
        #FIXME check unit conversion between C/CO2 to CH2O
        return self.net_CO2_umol_per_m2_s / self.p.planting_density * self.context.interval * Weight.CH2O

    @derive
    def transpiration(self):
        # Units of Transpiration from sunlit->ET are mol m-2 (leaf area) s-1
        # Calculation of transpiration from ET involves the conversion to gr per plant per hour
        return self.transpiration_H2O_mol_per_m2_s / self.p.planting_density * self.context.interval * Weight.H2O

    #FIXME: no sense to weight two temperature values here
    # @derive
    # def temperature(self):
    #     return self._weighted(self.temperature_array)

    @derive
    def vapor_pressure_deficit(self):
        #HACK only use sunlit leaves?
        return max(0, self.sunlit.VPD)

    @derive
    def conductance(self):
        #HACK ensure 0 when one if LAI is 0, i.e., night
        if self.sunlit_leaf_area_index == 0 or self.shaded_leaf_area_index == 0:
            return 0
        try:
            # average stomatal conductance Yang
            c = self._weighted(self.conductance_array) / self.leaf_area_index
            return max(0, c)
        except ZeroDivisionError:
            return 0
