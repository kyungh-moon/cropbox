from cropbox.stage import Stage
from cropbox.statevar import accumulate, drive, derive, flag, parameter, system
from cropbox.util import beta_thermal_func

class LeafInitiation(Stage):
    @parameter
    def initial_leaves(self):
        return 0

    @parameter(alias='R_max', unit='1/day')
    def maximum_leaf_initiation_rate(self):
        return 0.20

    @accumulate(unit='')
    def rate(self, R_max, T, T_opt, T_ceil):
        return R_max * beta_thermal_func(T, T_opt, T_ceil)

    @flag
    def ready(self):
        #HACK original garlic model assumed leaves are being initiated when the seeds are sown
        #HACK maize model model assumed leaf initiation begins when germination is over
        return self.pheno.germination.over

    @flag
    def over(self):
        # for maize
        #return self.pheno.tassel_initiation.over
        # for garlic
        return self.pheno.floral_initiation.over

    @derive
    def leaves(self):
        # no MAX_LEAF_NO implied unlike original model
        return int(self.initial_leaves + self.rate)

class LeafInitiationWithStorage(LeafInitiation):
    @parameter(alias='SD', unit='day')
    def storage_days(self):
        pass

    @parameter(alias='ST')
    def storage_temperature(self):
        return 5.0

    @parameter(alias='ILN')
    def initial_leaves_at_harvest(self):
        return 0

    @derive(alias='ILS')
    def initial_leaves_during_storage(self, R_max, T, T_opt, T_ceil, SD):
        return R_max * beta_thermal_func(T=T, T_opt=T_opt, T_max=T_ceil) * SD

    @derive
    def initial_leaves(self, ILN, ILS):
        return ILN + ILS
