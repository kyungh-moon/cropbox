from cropbox.context import instance
from cropbox.system import System
from cropbox.statevar import accumulate, constant, derive, flag, parameter, system

class Germination(System):
    @parameter(alias='R_max')
    def maximum_germination_rate(self):
        return 0.45

    @derive
    def rate(self):
        return ...

    @flag
    def over(self):
        return self.rate >= 0.5 or self.pheno.emergence.begin_from_emergence

    #FIXME postprocess similar to @produce?
    def finish(self):
        GDD_sum = self.pheno.gdd_recorder.rate
        dt = self.pheno.timestep * 24 * 60 # per min
        print(f"* Germinated: time = {self.time}, GDDsum = {GDD_sum}, time step (min) = {dt}")
