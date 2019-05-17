from cropbox.system import System
from cropbox.statevar import accumulate, derive, drive, system
from cropbox.util import growing_degree_days

class Organ(System):
    plant = system(alias='p')

    # organ temperature, C
    temperature = drive('p.pheno', alias='T')

    # glucose, MW = 180.18 / 6 = 30.03 g
    @accumulate(alias='C')
    def carbohydrate(self):
        return self.imported_carbohydrate # * self.respiration_adjustment

    # nitrogen content, mg
    nitrogen = accumulate('imported_nitrogen', alias='N')

    # physiological age accounting for temperature effect (in reference to endGrowth and lifeSpan, days)
    @accumulate
    def physiological_age(self, T):
        #HACK: tracking should happen after plant emergence (due to implementation of original beginFromEmergence)
        if self.p.pheno.emerged:
            #TODO support species/cultivar specific temperature parameters
            #return growing_degree_days(T=self.p.pheno.temperature, T_base=8.0, T_max=43.3)
            return growing_degree_days(T=T, T_base=4.0, T_max=40.0)

    # chronological age of an organ, days
    # @physiological_age.period
    # def chronological_age(self):
    #     pass

    # biomass, g
    # @derive
    # def mass(self):
    #     #FIXME isn't it just the amount of carbohydrate?
    #     #return self._carbohydrate / Weight.CH2O * Weight.C / Weight.C_to_CH2O_ratio
    #     return self._carbohydrate

    # #TODO remove set_mass() and directly access carbohydrate
    # def set_mass(self, mass):
    #     #self._carbohydrate = mass * Weight.C_to_CH2O_ratio / Weight.C * Weight.CH2O
    #     self._carbohydrate = mass

    # physiological days to reach the end of growth (both cell division and expansion) at optimal temperature, days
    @parameter
    def growth_duration(self):
        return 10

    # life expectancy of an organ in days at optimal temperature (fastest growing temp), days
    #FIXME not used
    @parameter
    def longevity(self):
        return 50

    # carbon allocation to roots or leaves for time increment
    #FIXME not used
    @derive
    def potential_carbohydrate_increment(self):
        return 0

    # carbon allocation to roots or leaves for time increment  gr C for roots, gr carbo dt-1
    #FIXME not used
    @derive
    def actual_carbohydrate_increment(self):
        return 0

    #TODO to be overridden
    @derive
    def self.imported_carbohydrate(self):
        return 0

    @derive
    def respiration_adjustment(self, Ka=0.1, Rm=0.02):
        # this needs to be worked on, currently not used at all
        # Ka: growth respiration
        # Rm: maintenance respiration
        return 1 - (Ka + Rm)
