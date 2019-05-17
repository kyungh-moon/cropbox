from cropbox.system import System
from cropbox.statevar import derive, drive, parameter, produce, system

from .atmosphere.weather import Weather
from .rhizosphere.soil import Soil
from .phenology.phenology import Phenology
from .physiology.

class Plant(System):
    weather = system(Weather)
    soil = system(Soil)

    phenology = system(Phenology, alias='pheno', plant='self')
    photosynthesis = system(Photosynthesis, plant='self')

    mass = system(Mass, plant='self')
    area = system(Area, plant='self')
    count = system(Count, plant='self')
    ratio = system(Ratio, plant='self')
    #carbon = system(Carbon, plant='self')
    #nitrogen = system(Nitrogen, plant='self')
    water = system(Water, plant='self')

    #TODO pass PRIMORDIA as initial_leaves
    primordia = parameter(5)

    bulb = system(None)
    scape = system(None)
    root = system(None)
    nodal_units = system([])

    #TODO find a better place?
    @parameter # unit (m-2)
    def planting_density(self):
        return 55

    @produce(target='nodal_units')
    def initiate_primordia(self):
        if len(self.nodal_units) == 0:
            return [(NodalUnit, {'rank': i+1}) for i in range(self.primordia)]

    @produce(target='root')
    def initiate_root(self):
        if not self.root:
            if self.pheno.emerging:
                #TODO import_carbohydrate(self.soil.total_root_weight)
                return (Root, {})

    @produce(target='nodal_units')
    def initiate_leaves(self):
        if not (self.pheno.germinating or self.pheno.dead):
            def f(i):
                try:
                    self.nodal_units[i]
                except IndexError:
                    return (NodalUnit, {'rank': i+1})
                else:
                    return None
            return [f(i) for i in range(self.pheno.leaves_initiated)]

class Trait(System):
    plant = system(alias='p')
