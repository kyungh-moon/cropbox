from .system import System
from .statevar import accumulate, parameter

class Clock(System):
    def __init__(self, config):
        self.tick = 0
        super().__init__(None)

    @parameter
    def start(self):
        return 0

    @parameter
    def interval(self):
        return 1

    def update(self):
        self.tick += 1
        super().update(recursive=True)

    @accumulate(time='tick', init='start')
    def time(self):
        return self.interval
