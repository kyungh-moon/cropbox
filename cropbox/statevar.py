from .track import Track, Accumulate, Difference, Signal

class statevar:
    def __init__(self, track, time='time'):
        self._track = track
        self._time = time

    def __call__(self, f):
        self.__name__ = f"_{f.__name__}"
        self._compute = f
        return self

    def __get__(self, obj, objtype):
        return self.update(obj)

    def time(self, obj):
        return getattr(obj, self._time)

    def compute(self, obj):
        return self._compute(obj)

    def setup(self, obj):
        obj.__dict__[self.__name__] = self._track(self.time(obj))

    def update(self, obj):
        # support custom timestamp (i.e. elongation age instead of calendar time)
        t = self.time(obj)
        # lazy evaluation preventing redundant computation
        r = lambda: self.compute(obj)
        return obj.__dict__[self.__name__].update(t, r)

def derive(f): return statevar(track=Track)(f)
def accumulate(f): return statevar(track=Accumulate)(f)
def difference(f): return statevar(track=Difference)(f)
def signal(f): return statevar(track=Signal)(f)

class parameter(statevar):
    def __init__(self, f):
        super().__init__(track=Track)
        self.__call__(f)

    def compute(self, obj):
        name = self._compute.__name__
        default = self._compute(obj)
        return obj.config.get(name, default)
