from .system import System
from .statevar import accumulate

class Clock(System):
    def __init__(self, start, interval):
        self.start = start
        self.interval = interval
        self.tick = 0
        super().__init__(None)

    def update(self):
        self.tick += self.interval
        super().update(recursive=True)

    @accumulate(time='tick', init='start')
    def time(self):
        return self.interval
