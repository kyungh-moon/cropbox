from cropbox.stage import Stage
from cropbox.statevar import accumulate, flag, parameter, system, systemproxy
from cropbox.util import beta_thermal_func

class Scape(Stage):
    @parameter(alias='R_max')
    def maximum_scaping_rate(self):
        #HACK use LTAR
        return self.pheno.leaf_appearance.maximum_leaf_tip_appearance_rate

    @accumulate
    def rate(self, R_max, T, T_opt, T_ceil):
        return R_max * beta_thermal_func(T, T_opt, T_ceil)

    @flag
    def ready(self):
        return self.pheno.leaf_appearance.over and self.pheno.floral_initiation.over

    @flag
    def over(self):
        return self.pheno.flowering.over or self.pheno.scape_removal.over

class ScapeAppearance(Stage):
    scape = systemproxy()

    @flag
    def over(self):
        return self.rate >= 3.0 and not self.pheno.scape_removal.over

    # def finish(self):
    #     print(f"* Scape Tip Visible: time = {self.time}, leaves = {self.pheno.leaves_appeared} / {self.pheno.leaves_initiated}")

class ScapeRemoval(Stage):
    scape = systemproxy()

    @parameter(init=None)
    def scape_removal_date(self):
        #FIXME handling default (non-removal) value
        pass

    @flag
    def ready(self):
        return self.pheno.scape_appearance.over

    @flag
    def over(self):
        if self.scape_removal_date is None:
            return False
        else:
            return self.pheno.context.time >= self.scape_removal_date

    # def finish(self):
    #     print(f"* Scape Removed and Bulb Maturing: time = {self.time}")

#TODO clean up naming (i.e. remove -ing prefix)
class Flowering(Stage):
    scape = systemproxy()

    @flag
    def over(self):
        return self.rate >= 5.0 and not self.pheno.scape_removal.over

    # def finish(self):
    #     print(f"* Inflorescence Visible and Flowering: time = {self.time}")

#TODO clean up naming (i.e. remove -ing prefix)
class Bulbiling(Stage):
    scape = systemproxy()

    @flag
    def over(self):
        return self.rate >= 5.5 and not self.pheno.scape_removal.over

    # def finish(self):
    #     print(f"* Bulbil and Bulb Maturing: time = {self.time}")
