from cropbox.system import System
from cropbox.statevar import constant, derive, system

class NodalUnit(System):
    plant = system()
    rank = constant()
    leaf = system()
    #sheath = system()

    @derive
    def mass(self):
        return self.leaf.mass #+ self.sheath.mass
