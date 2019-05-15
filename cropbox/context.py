from .system import System
from .statevar import accumulate, derive, parameter, system, Priority
import toml

from collections import defaultdict

class Clock(System):
    def __init__(self):
        self._tick = 0
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

    @property
    def tick(self):
        return self._tick

    def advance(self):
        self._tick += 1
        self.update()

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
        self._pending = defaultdict(list)
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

    def queue(self, f, priority=Priority.DEFAULT):
        if f is None:
            return
        self._pending[priority].append(f)

    def update(self):
        # process pending operations from last timestep (i.e. @produce)
        self.flush(post=False)

        # update state variables recursively
        super().update()
        [s.update() for s in self.collect()]

        # process pending operations from current timestep (i.e. @flag, @accumulate)
        self.flush(post=True)

        #TODO: process aggregate (i.e. transport) operations?

    def flush(self, post=False):
        #HACK: avoid more pending operations added during iteration
        if post:
            f = lambda k: k >= 0
        else:
            f = lambda k: k < 0
        keys = list(filter(f, self._pending))
        pending = {k: self._pending[k] for k in keys}
        [self._pending.pop(k) for k in keys]
        for i, p in sorted(pending.items()):
            for f in p:
                f()

def instance(systemcls, config=None):
    c = Context(config)
    s = systemcls(context=c, parent=c)
    c.children.append(s)
    c.flush(post=True)
    return s
