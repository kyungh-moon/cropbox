from cropbox.statevar import constant, derive, system

from .organ import Organ
from .leaf import Leaf
from .sheath import Sheath

class NodalUnit(Organ):
    rank = constant()
    leaf = system(Leaf, plant='self.plant', nodal_unit='self')
    sheath = system(Sheath, plant='self.plant', nodal_unit='self')

    @derive
    def mass(self):
        return self.leaf.mass + self.sheath.mass
