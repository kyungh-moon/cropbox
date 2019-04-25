from .system import System
from .statevar import accumulate, derive, parameter, system
import toml

class Clock(System):
    def __init__(self):
        self.tick = 0
        super().__init__()

    @parameter(init=None)
    def unit(self):
        return None

    @parameter(unit='unit')
    def start(self):
        return 0

    @parameter(unit='unit')
    def interval(self):
        return 1

    def update(self):
        self.tick += 1
        super().update()

    @accumulate(time='tick', init='start', unit='unit')
    def time(self):
        return self.interval

    @parameter(init=None)
    def start_datetime(self):
        return None

    @derive(init=None)
    def datetime(self, start_datetime):
        if start_datetime is None:
            #raise ValueError('base datetime is unknown')
            return None
        else:
            return start_datetime + self.time

class Context(Clock):
    def __init__(self, config=None):
        self._pending = []
        self.configure(config)
        super().__init__()

    @system
    def context(self):
        return self

    def configure(self, config):
        if config is None:
            d = {}
        elif isinstance(config, dict):
            d = config
        else:
            d = toml.loads(config)
        self._config = d

    def queue(self, f):
        self._pending.append(f)

    def update(self):
        # process pending operations
        #HACK: avoid more pending operations added during iteration
        #TODO: more structured way of operation handling (i.e. distinction between pre/post ops)
        pending = self._pending.copy()
        self._pending.clear()
        [f() for f in pending]

        # update state variables recursively
        super().update()
        [s.update() for s in self.collect()]

        #TODO: process aggregate (i.e. transport) operations?

def instance(systemcls, config=None):
    c = Context(config)
    s = systemcls(context=c, parent=c)
    c.children.append(s)
    c.update()
    return s
