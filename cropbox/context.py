from .system import System
from .statevar import accumulate, parameter

class Clock(System):
    def __init__(self):
        self.tick = 0
        super().__init__(None)

    @parameter
    def start(self):
        return 0

    @parameter
    def interval(self):
        return 1

    def update(self, recursive):
        self.tick += 1
        super().update(recursive)

    @accumulate(time='tick', init='start')
    def time(self):
        return self.interval

class Context(Clock):
    def __init__(self, config):
        super().__init__()
        self.context = self
        self.config = config
        self._pending = []

    def option(self, k, v=None, vtype=float):
        #HACK: try section names for base classes up to System (not inclusive)
        S = [c.__name__ for c in self.__class__.mro()]
        S = S[:S.index('System')]
        for s in S:
            try:
                v = self.config[s][k]
            except KeyError:
                pass
        return vtype(v)

    def queue(self, f):
        self._pending.append(f)

    def update(self):
        # process pending operations
        [f() for f in self._pending]
        self._pending.clear()

        # update state variables recursively
        super().update(recursive=True)

        #TODO: process aggregate (i.e. transport) operations?
