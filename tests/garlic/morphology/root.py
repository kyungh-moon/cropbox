from cropbox.statevar import constant, derive, system

from .organ import Organ

class Root(Organ):
    plant = system()
    rank = constant()
    leaf = system()
    #sheath = system()

    @derive
    def mass(self):
        #FIXME root biomass
        return 0
