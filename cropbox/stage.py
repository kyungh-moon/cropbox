from .system import System
from .statevar import derive, flag

class Stage(System):
    @flag
    def ready(self):
        return False

    @flag
    def over(self):
        return False

    @flag
    def ing(self):
        return self.ready and not self.over
