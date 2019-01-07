from .track import Track, Accumulate, Difference, Signal

class statevar:
    def __init__(self, f=None, *, track, time='context.time', init=''):
        self._track_cls = track
        self._time_var = time
        self._init_var = init
        if f is not None:
            self.__call__(f)

    def __call__(self, f):
        self.__name__ = f'_{f.__name__}'
        self._compute = f
        return self

    def __get__(self, obj, objtype):
        return self.update(obj)

    def time(self, obj):
        return obj.get(self._time_var)

    def compute(self, obj):
        return self._compute(obj)

    def setup(self, obj):
        t = self.time(obj)
        v = obj.get(self._init_var, 0)
        setattr(obj, self.__name__, self._track_cls(t, v))

    def update(self, obj):
        # support custom timestamp (i.e. elongation age instead of calendar time)
        t = self.time(obj)
        # lazy evaluation preventing redundant computation
        r = lambda: self.compute(obj)
        return getattr(obj, self.__name__).update(t, r, force=FORCE_UPDATE)

def derive(f=None, **kwargs): return statevar(f, track=Track, **kwargs)
def accumulate(f=None, **kwargs): return statevar(f, track=Accumulate, **kwargs)
def difference(f=None, **kwargs): return statevar(f, track=Difference, **kwargs)
def signal(f=None, **kwargs): return statevar(f, track=Signal, **kwargs)

#TODO: use @proxy <: @var replacing @property, also make @state <: @var

class parameter(statevar):
    def __init__(self, f=None, *, type=float):
        self._type = type
        super().__init__(f, track=Track)

    def time(self, obj):
        # doesn't change at t=0 ensuring only one update
        return 0

    def compute(self, obj):
        k = self._compute.__name__
        v = self._compute(obj)
        return obj.context.option(k, v, self._type)

class drive(statevar):
    def __init__(self, f):
        super().__init__(track=Track)
        self.__call__(f)

    def compute(self, obj):
        name = self._compute.__name__
        d = self._compute(obj) # i.e. return df.loc[t]
        return d[name]
