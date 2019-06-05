from cropbox.statevar import derive

from .trait import Trait

class Water(Trait):
    @derive
    def supply(self): # ET_supply
        return 0
