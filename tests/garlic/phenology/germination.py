from cropbox.stage import Stage
from cropbox.statevar import accumulate, drive, derive, flag, parameter, system
from cropbox.util import beta_thermal_func

class Germination(Stage):
    @parameter(alias='R_max')
    def maximum_germination_rate(self):
        return 0.45

    @accumulate
    def rate(self, R_max, T, T_opt, T_ceil):
        #FIXME prevent extra accumulation after it's `over`
        if self.ing:
            return R_max * beta_thermal_func(T, T_opt, T_ceil)

    @flag
    def ready(self):
        return True

    @flag
    def over(self):
        return self.rate >= 0.5 or self.pheno.emergence.begin_from_emergence

    # #FIXME postprocess similar to @produce?
    # def finish(self):
    #     GDD_sum = self.pheno.gdd_recorder.rate
    #     dt = self.pheno.timestep * 24 * 60 # per min
    #     print(f"* Germinated: time = {self.time}, GDDsum = {GDD_sum}, time step (min) = {dt}")
