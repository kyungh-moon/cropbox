from cropbox.statevar import derive

from .trait import Trait

class Water(Trait):
    #FIXME check unit (w.r.t photosynthesis.ET_supply)
    #FIXME check name (probably not the same as photosynthesis.ET_supply)
    @derive(unit='g/hr')
    def supply(self): # ET_supply
        return 0
