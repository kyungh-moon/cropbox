from cropbox.stage import Stage
from cropbox.statevar import flag, parameter

class FloralInitiation(Stage):
    @parameter(alias='critPPD')
    def critical_photoperiod(self):
        return 12

    @flag
    def ready(self):
        return self.pheno.germination.over

    @flag
    def over(self):
        w = self.pheno.weather
        #FIXME solstice consideration is broken (flag turns false after solstice) and maybe unnecessary
        # solstice = w.time.tz.localize(datetime.datetime(w.time.year, 6, 21))
        # # no MAX_LEAF_NO implied unlike original model
        # return w.time <= solstice and w.day_length >= self.critical_photoperiod
        return w.day_length >= self.critical_photoperiod

    # #FIXME postprocess similar to @produce?
    # def finish(self):
    #     GDD_sum = self.pheno.gdd_recorder.rate
    #     print(f"* Floral initiation: time = {self.time}, GDDsum = {GDD_sum}")
