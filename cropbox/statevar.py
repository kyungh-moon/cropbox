from .track import Track, Accumulate, Difference, Signal

class statevar:
    def __init__(self, f=None, *, trackcls, time='time'):
        self._trackcls = trackcls
        self._time = time
        if f is not None:
            self.__call__(f)

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
        obj.__dict__[self.__name__] = self._trackcls(self.time(obj))

    def update(self, obj):
        # support custom timestamp (i.e. elongation age instead of calendar time)
        t = self.time(obj)
        # lazy evaluation preventing redundant computation
        r = lambda: self.compute(obj)
        return obj.__dict__[self.__name__].update(t, r)

def derive(f=None, **kwargs): return statevar(f, trackcls=Track, **kwargs)
def accumulate(f=None, **kwargs): return statevar(f, trackcls=Accumulate, **kwargs)
def difference(f=None, **kwargs): return statevar(f, trackcls=Difference, **kwargs)
def signal(f=None, **kwargs): return statevar(f, trackcls=Signal, **kwargs)

class parameter(statevar):
    def __init__(self, f):
        super().__init__(trackcls=Track)
        self.__call__(f)

    def compute(self, obj):
        name = self._compute.__name__
        default = self._compute(obj)
        return obj.config.get(name, default)

class drive(statevar):
    def __init__(self, f):
        super().__init__(trackcls=Track)
        self.__call__(f)

    def compute(self, obj):
        name = self._compute.__name__
        d = self._compute(obj) # i.e. return df.loc[t]
        return d[name]
