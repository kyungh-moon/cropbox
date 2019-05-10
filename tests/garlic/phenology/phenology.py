# from ..common import Death, Emergence, Germination, LeafAppearance
# from ..recorder import GddRecorder, GstRecorder, GtiRecorder
# from .bulbing import Bulbing
# from .floralinitiation import FloralInitiation
# from .leafinitiation import LeafInitiationWithStorage
# from .scape import Bulbiling, Flowering, Scape, ScapeAppearance, ScapeRemoval

from cropbox.system import System
from cropbox.statevar import derive, flag, parameter, system

from .germination import Germination
from .emergence import Emergence
from .leafinitiation import LeafInitiationWithStorage
from .leafappearance import LeafAppearance
from .floralinitiation import FloralInitiation
from .bulbing import Bulbing
from .scape import Bulbiling, Flowering, Scape, ScapeAppearance, ScapeRemoval
from .death import Death

#TODO make common Weather class
class Weather(System):
    @parameter
    def T_air(self): return 25 # C

    #FIXME is day_length part of Weather?
    @parameter
    def day_length(self): return 12 # hours

#TODO make common Soil class
class Soil(System):
    @parameter
    def T_soil(self): return 10 # C

#TODO make a common class to be shared by Garlic and MAIZSIM
class Phenology(System):
    weather = system(Weather)
    soil = system(Soil)

    @parameter
    def storage_days(self):
        pass

    @parameter
    def initial_leaf_number_at_harvest(self):
        return 4

    @parameter(alias='R_max_LIR')
    def maximum_leaf_initiation_rate(self):
        pass

    @parameter(alias='R_max_LTAR')
    def maximum_leaf_tip_appearance_rate(self):
        pass

    @parameter(alias='T_opt')
    def optimal_temperature(self):
        return 22.28

    @parameter(alias='T_ceil')
    def ceiling_temperature(self):
        return 34.23

    @parameter
    def emergence_date(self):
        pass

    @parameter
    def critical_photoperiod(self):
        pass

    @parameter
    def scape_removal_date(self):
        pass

    # def setup(self):
    #     # mean growing season temperature since germination, SK 1-19-12
    #     self.gst_recorder = gstr = GstRecorder(self)
    #     self.gdd_recorder = gddr = GddRecorder(self)
    #     self.gti_recorder = gtir = GtiRecorder(self)

    #     self.germination = g = Germination(self)
    #     self.emergence = e = Emergence(self, R_max=R_max_LTAR, T_opt=T_opt, T_ceil=T_ceil, emergence_date=emergence_date)
    #     self.leaf_initiation = li = LeafInitiationWithStorage(self, initial_leaves_at_harvest=initial_leaf_number_at_harvest, R_max=R_max_LIR, T_opt=T_opt, T_ceil=T_ceil, storage_days=storage_days)
    #     self.leaf_appearance = la = LeafAppearance(self, R_max=R_max_LTAR, T_opt=T_opt, T_ceil=T_ceil)
    #     self.floral_initiation = fi = FloralInitiation(self, critical_photoperiod=critical_photoperiod)
    #     self.bulbing = bi = Bulbing(self)
    #     self.scape = s = Scape(self, R_max=R_max_LTAR, T_opt=T_opt, T_ceil=T_ceil)
    #     self.scape_appearance = sa = ScapeAppearance(self, s)
    #     self.scape_removal = sr = ScapeRemoval(self, s, scape_removal_date=scape_removal_date)
    #     self.flowering = f = Flowering(self, s)
    #     self.bulbiling = b = Bulbiling(self, s)
    #     self.death = d = Death(self)

    #     self.stages = [
    #         gstr, gddr, gtir,
    #         g, e, li, la, fi, bi, s, sa, sr, f, b, d,
    #     ]

    # def update(self, t):
    #     #queue = self._queue()
    #     [s.update(t) for s in self.stages if s.ready]

    #     #FIXME remove finish() for simplicity
    #     [s.finish() for s in self.stages if s.over]

    #     self.stages = [s for s in self.stages if not s.over]

    # #TODO some methods for event records? or save them in Stage objects?
    # #def record(self, ...):
    # #    pass

    germination = system(Germination, phenology='self')
    emergence = system(Emergence, phenology='self')
    leaf_initiation = system(LeafInitiationWithStorage, phenology='self')
    leaf_appearance = system(LeafAppearance, phenology='self')
    floral_initiation = system(FloralInitiation, phenology='self')
    bulbing = system(Bulbing, phenology='self')
    scape = system(Scape, phenology='self')
    scape_appearance = system(ScapeAppearance, phenology='self', scape='scape')
    scape_removal = system(ScapeRemoval, phenology='self', scape='scape')
    flowering = system(Flowering, phenology='self', scape='scape')
    bulbiling = system(Bulbiling, phenology='self', scape='scape')
    death = system(Death, phenology='self')

    ############
    # Accessor #
    ############

    @derive
    def leaves_potential(self):
        return max(self.leaves_generic, self.leaves_total)

    @parameter
    def leaves_generic(self):
        return 10

    @derive
    def leaves_total(self):
        return self.leaves_initiated

    @derive
    def leaves_initiated(self):
        return self.leaf_initiation.leaves

    @derive
    def leaves_appeared(self):
        return self.leaf_appearance.leaves

    @derive(alias='T')
    def temperature(self):
        if self.leaves_appeared < 9:
            #FIXME soil module is not implemented yet
            #T = self.soil.T_soil
            #HACK garlic model does not use soil temperature
            T = self.weather.T_air
        else:
            T = self.weather.T_air
        #FIXME T_cur doesn't go below zero, but is it fair assumption?
        return T if T > 0 else 0

    # @derive
    # def growing_temperature(self):
    #     return self.gst_recorder.rate

    # common

    @flag
    def germinating(self):
        return self.germination.ing

    @flag
    def germinated(self):
        return self.germination.over

    @flag
    def emerging(self):
        return self.emergence.ing

    @flag
    def emerged(self):
        return self.emergence.over

    # garlic

    @flag
    def floral_initiated(self):
        return self.floral_initiation.over

    @flag
    def scaping(self):
        return self.scape.ing

    @flag
    def scape_appeared(self):
        return self.scape_appearance.over

    @flag
    def scape_removed(self):
        return self.scape_removal.over

    @flag
    def flowered(self):
        return self.flowering.over

    @flag
    def bulb_maturing(self):
        #FIXME clear definition of bulb maturing
        return self.scape_removed or self.bulbiling.over

    # common

    @flag
    def dead(self):
        return self.death.over

    # # GDDsum
    # @derive
    # def gdd_after_emergence(self):
    #     if self.emergence.over:
    #         #HACK tracker is reset when emergence is over
    #         return self.gdd_recorder.rate
    #     else:
    #         return 0

    # @property
    # def current_stage(self):
    #     if self.emerged:
    #         return "Emerged"
    #     elif self.dead:
    #         return "Inactive"
    #     else:
    #         return "none"

    # @property
    # def development_phase(self):
    #     if not self.germinated:
    #         return "seed"
    #     elif not self.floral_initiated:
    #         return "vegetative"
    #     elif self.dead:
    #         return "dead"
    #     elif not self.scape_removed:
    #         return "bulb_growth_with_scape"
    #     else:
    #         return "bulb_growth_without_scape"
