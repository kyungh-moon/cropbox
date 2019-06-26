from cropbox.stage import Stage
from cropbox.statevar import accumulate, drive, derive, flag, parameter, system
from cropbox.util import beta_thermal_func

class Emergence(Stage):
    @parameter(alias='R_max', unit='1/day')
    def maximum_emergence_rate(self):
        #HACK: can't use self.pheno.leaf_appearance.maximum_leaf_tip_appearance_rate due to recursion
        return 0.20

    @parameter
    def emergence_date(self):
        return None

    @parameter
    def begin_from_emergence(self):
        return False

    @accumulate(unit='')
    def rate(self, R_max, T, T_opt, T_ceil):
        return R_max * beta_thermal_func(T, T_opt, T_ceil)

    @flag
    def ready(self):
        return self.pheno.germination.over

    @flag
    def over(self):
        if self.begin_from_emergence:
            return self.context.time >= self.emergence_date
        else:
            return self.rate >= 1.0

    # #FIXME postprocess similar to @produce?
    # def finish(self):
    #     GDD_sum = self.pheno.gdd_recorder.rate
    #     T_grow = self.pheno.growing_temperature
    #     print(f"* Emergence: time = {self.time}, GDDsum = {GDD_sum}, Growing season T = {T_grow}")

    #     #HACK reset GDD tracker after emergence
    #     self.emerge_GDD = GDD_sum
    #     self.pheno.gdd_recorder.reset()
