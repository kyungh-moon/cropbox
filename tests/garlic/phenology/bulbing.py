from cropbox.stage import Stage
from cropbox.statevar import flag

class Bulbing(Stage):
    @flag
    def ready(self):
        #FIXME over? not ready?
        return self.pheno.floral_initiation.over

    @flag
    def over(self):
        #HACK bulbing used to begin one phyllochron after floral initiation in bolting cultivars of garlic, see Meredith 2008
        return self.pheno.floral_initiation.over

    # #FIXME postprocess similar to @produce?
    # def finish(self):
    #     GDD_sum = self.pheno.gdd_recorder.rate
    #     print(f"* Bulbing: time = {self.time}, GDDsum = {GDD_sum}")
