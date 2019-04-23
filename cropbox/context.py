from .system import System
from .statevar import accumulate, parameter, system
import toml

class Clock(System):
    def __init__(self):
        self.tick = 0
        super().__init__()

    @parameter
    def start(self):
        return 0

    @parameter
    def interval(self):
        return 1

    def update(self):
        self.tick += 1
        super().update()

    @accumulate(time='tick', init='start')
    def time(self):
        return self.interval

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
        [f() for f in self._pending]
        self._pending.clear()

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
