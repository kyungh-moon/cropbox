from .system import System
from .statevar import accumulate, parameter, statevar, U
import toml

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
    def __init__(self, config=None):
        self.context = self
        self._pending = []
        self.configure(config)
        super().__init__()

    def configure(self, config):
        if config is None:
            d = {}
        elif isinstance(config, dict):
            d = config
        else:
            d = toml.loads(config)
        self._config = d

    def option(self, *keys, config=None):
        if config is None:
            c = self._config
        def expand(k):
            if isinstance(k, System):
                #HACK: populate base classes down to System (not inclusive) for section names
                S = k.__class__.mro()
                return [s.__name__ for s in S[:S.index(System)]]
            if isinstance(k, statevar):
                return [k.__name__] + k._alias_lst
            else:
                return k
        keys = [expand(k) for k in keys]
        v = self._option(*keys, config=c)
        return U(v)

    def _option(self, *keys, config):
        if not keys:
            return config
        key, *keys = keys
        if isinstance(key, list):
            for k in key:
                v = self._option(k, *keys, config=config)
                if v is not None:
                    return v
        else:
            try:
                c = config[key]
            except KeyError:
                return None
            else:
                return self._option(*keys, config=c)

    def queue(self, f):
        self._pending.append(f)

    def update(self):
        # process pending operations
        [f() for f in self._pending]
        self._pending.clear()

        # update state variables recursively
        super().update(recursive=True)

        #TODO: process aggregate (i.e. transport) operations?

def instance(systemcls, config=None):
    c = Context(config)
    c.branch(systemcls)
    c.update()
    return c.children[0]
