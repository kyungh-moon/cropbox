from cropbox.statevar import constant, derive, system

from .organ import Organ

class Sheath(Organ):
    nodal_unit = system()

    @derive
    def rank(self):
        return self.nodal_unit.rank

    @derive
    def mass(self):
        #FIXME sheath biomass
        return 0
