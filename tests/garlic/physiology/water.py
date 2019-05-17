from cropbox.statevar import derive

from .plant import Trait

class Water(Trait):
    @derive
    def supply(self): # ET_supply
        return 0
