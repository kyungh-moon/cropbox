from .track import Track, Accumulate, Difference, Signal

#HACK: to implement @optimize, need better way of controlling this
#TODO: probably need a full dependency graph between variables to push updates downwards
#FORCE_UPDATE = False

import networkx as nx

class Trace:
    def __init__(self):
        self.reset()

    def reset(self):
        self.stack = []
        self.graph = nx.DiGraph()

    def __call__(self, var, obj):
        self._mem = (var, obj)
        return self

    def __enter__(self):
        v, o = self._mem
        del self._mem
        try:
            s = self.stack[-1]
            #FIXME: graph should be reset for every update
            self.graph.add_edge(s.__name__, v.__name__)
        except:
            pass
        #TODO: give each System object a name
        #TODO: check dupliate?
        self.graph.add_node(o.__class__.__name__, type='Class', group='')
        self.graph.add_node(v.__name__, type=v.__class__.__name__, group=o.__class__.__name__)
        self.stack.append(v)
        return self

    def __exit__(self, *excs):
        self.stack.pop()

    def is_stacked(self, var):
        return len([v for v in self.stack if v is var]) > 1

class statevar:
    trace = Trace()

    def __init__(self, f=None, *, track, time='context.time', init=0):
        self._track_cls = track
        self._time_var = time
        self._init_var = init
        if f is not None:
            self.__call__(f)

    def __call__(self, f):
        self.__name__ = f.__name__
        self._name = f'_{f.__name__}'
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
        v = obj.get(self._init_var)
        setattr(obj, self._name, self._track_cls(t, v))

    def update(self, obj):
        with self.trace(self, obj):
            return self._update(obj)

    def _update(self, obj):
        # support custom timestamp (i.e. elongation age instead of calendar time)
        t = self.time(obj)
        # lazy evaluation preventing redundant computation
        r = lambda: self.compute(obj)
        return getattr(obj, self._name).update(t, r, force=obj._force_update)

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
        return obj.context.option(obj, k, v, self._type)

class drive(statevar):
    def __init__(self, f):
        super().__init__(track=Track)
        self.__call__(f)

    def compute(self, obj):
        name = self._compute.__name__
        d = self._compute(obj) # i.e. return df.loc[t]
        return d[name]

import scipy.optimize

class optimize(statevar):
    def __init__(self, f=None, *, lower, upper):
        self._lower_var = lower
        self._upper_var = upper
        super().__init__(f, track=Track)

    def compute(self, obj):
        tr = getattr(obj, self._name)
        #HACK: prevent recursion loop already in computation tree
        if self.trace.is_stacked(self):
            return tr._value
        def loss(x):
            tr._value = x
            return self._compute(obj)
        l = obj.get(self._lower_var)
        u = obj.get(self._upper_var)
        obj.force_update(True)
        v = scipy.optimize.brentq(loss, l, u)
        obj.force_update(False)
        tr._value == v
        return v
