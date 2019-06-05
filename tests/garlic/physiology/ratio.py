from cropbox.statevar import derive

from .trait import Trait
from .weight import Weight

class Ratio(Trait):
    @derive
    def carbon_to_mass(self):
        # 40% C, See Kim et al. (2007) EEB
        return Weight.C_to_CH2O_ratio

    @derive
    def shoot_to_root(self):
        return 0.7

    @derive
    def root_to_shoot(self):
        return 1 - self.shoot_to_root

    @derive
    def leaf_to_stem(self):
        return 0.9

    @derive
    def stem_to_leaf(self):
        return 1 - self.leaf_to_stem

    @derive
    def initial_leaf(self):
        #TODO how to handle primordia?
        return self.shoot_to_root * self.leaf_to_stem / self.p.primordia
