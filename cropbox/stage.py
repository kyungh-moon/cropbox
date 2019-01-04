from .system import System
from .statevar import derive

class Stage(System):
    @derive
    def ready(self):
        return False

    @derive
    def over(self):
        return False

    @derive
    def ing(self):
        return self.ready and not self.over
