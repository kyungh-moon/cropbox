from cropbox.stage import Stage
from cropbox.statevar import accumulate, drive, derive, flag, parameter, system
from cropbox.util import beta_thermal_func

class LeafAppearance(Stage):
    @parameter(alias='R_max')
    def maximum_leaf_tip_appearance_rate(self):
        return 0.20

    @accumulate
    def rate(self, R_max, T, T_opt, T_ceil):
        return R_max * beta_thermal_func(T, T_opt, T_ceil)

    @flag
    def ready(self):
        if self.pheno.emergence.begin_from_emergence:
            return self.pheno.emergence.over
        else:
            return self.pheno.germination.over

    @flag
    def over(self):
        initiated_leaves = self.pheno.leaf_initiation.leaves
        #HACK ensure leaves are initiated
        return self.leaves >= initiated_leaves > 0

    @derive
    def leaves(self):
        #HACK set initial leaf appearance to 1, not 0, to better describe stroage effect (2016-11-14: KDY, SK, JH)
        if self.pheno.emergence.begin_from_emergence and self.ready:
            initial_leaves = 1
        else:
            initial_leaves = 0
        return int(initial_leaves + self.rate)
