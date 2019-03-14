from .track import Track, Accumulate, Difference, Signal, Static

#HACK: to implement @optimize, need better way of controlling this
#TODO: probably need a full dependency graph between variables to push updates downwards
#FORCE_UPDATE = False

import inspect
import networkx as nx
import pint
import uuid

ureg = pint.UnitRegistry()
ureg.default_format = '~P'
#ureg.setup_matplotlib()
Q = ureg.Quantity

class Trace:
    def __init__(self):
        self.reset()

    def reset(self):
        self._stack = []
        self.graph = nx.DiGraph()

    @property
    def stack(self):
        def extract(s):
            try:
                x = s[-1]
            except IndexError:
                return s
            else:
                return extract(x) if type(x) is list else s
        return extract(self._stack)

    def push(self, v, isolate=False):
        v = [v] if isolate else v
        self.stack.append(v)

    def pop(self):
        v = self.stack.pop()
        def clean():
            if len(self.stack) == 0 and len(self._stack) > 0:
                self._stack.pop()
                clean()
        clean()
        return v

    def __call__(self, var, obj, isolate=False):
        self._mem = (var, obj, isolate)
        return self

    def __enter__(self):
        v, o, i = self._mem
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
        s = len(self.stack)*' '
        #self.stack.append(v)
        self.push(v, isolate=i)
        #print(f'{s} > {v.__name__}')
        return self

    def __exit__(self, *excs):
        #v = self.stack.pop()
        v = self.pop()
        s = len(self.stack)*' '
        #print(f'{s} < {v.__name__}')

    def is_stacked(self, var):
        return len([v for v in self.stack if v is var]) > 1

    @property
    def is_update_forced(self):
        try:
            x = self._stack[-1]
        except IndexError:
            return False
        else:
            return True if type(x) is list else False

class statevar:
    trace = Trace()

    def __init__(self, f=None, *, track, time='context.time', init=0, unit=None, name=None, abbr=None):
        self._track_cls = track
        self._time_var = time
        self._init_var = init
        self._unit_str = unit
        self._name_str = name
        self._abbr_lst = abbr.split(',') if abbr else []
        if f is not None:
            self.__call__(f)

    def __call__(self, f):
        if callable(f):
            fun = f
            name = f.__name__
        else:
            fun = lambda self: f
            name = f'_statevar_{uuid.uuid4().hex}'
        name = self._name_str if self._name_str else name
        self.__name__ = name
        self._name = f'_{name}'
        self._compute_fun = fun
        return self

    def __get__(self, obj, objtype):
        v = self.update(obj)
        if self._unit_str is None:
            return v
        else:
            try:
                return v.to(self._unit_str)
            except AttributeError:
                return v * ureg[self._unit_str]

    def time(self, obj):
        return obj.get(self._time_var)

    def compute(self, obj):
        return self._compute(obj)

    def _compute(self, obj):
        s = inspect.signature(self._compute_fun)
        vs = [n if p.default is p.empty else p.default for n, p in s.parameters.items() if n != 'self']
        args = [obj.get(v) for v in vs]
        return self._compute_fun(obj, *args)

    def init(self, obj):
        t = self.time(obj)
        v = obj.get(self._init_var)
        setattr(obj, self._name, self._track_cls(t, v))

    def update(self, obj):
        with self.trace(self, obj):
            return self._update(obj)

    def _update(self, obj):
        #HACK: prevent recursion loop already in computation tree
        tr = getattr(obj, self._name)
        if self.trace.is_stacked(self):
            return tr._value
        # support custom timestamp (i.e. elongation age instead of calendar time)
        t = self.time(obj)
        # lazy evaluation preventing redundant computation
        r = lambda: self.compute(obj)
        #HACK: prevent premature initialization?
        return tr.update(t, r, force=self.trace.is_update_forced)

    def __repr__(self):
        return f'<{self.__name__}>'

def derive(f=None, **kwargs): return statevar(f, track=Track, **kwargs)
def accumulate(f=None, **kwargs): return statevar(f, track=Accumulate, **kwargs)
def difference(f=None, **kwargs): return statevar(f, track=Difference, **kwargs)
def signal(f=None, **kwargs): return statevar(f, track=Signal, **kwargs)
def static(f=None, **kwargs): return statevar(f, track=Static, **kwargs)

#TODO: use @proxy <: @var replacing @property, also make @state <: @var

class parameter(statevar):
    def __init__(self, f=None, *, type=float, **kwargs):
        self._type = type
        super().__init__(f, track=Track, **kwargs)

    def time(self, obj):
        # doesn't change at t=0 ensuring only one update
        return 0

    def compute(self, obj):
        k = self.__name__
        v = self._compute(obj)
        return obj.context.option(obj, k, v, self._type)

class drive(statevar):
    def __init__(self, f, **kwargs):
        super().__init__(track=Track, **kwargs)
        self.__call__(f)

    def compute(self, obj):
        d = self._compute(obj) # i.e. return df.loc[t]
        return d[self.__name__]

import scipy.optimize

class optimize(statevar):
    def __init__(self, f=None, *, lower, upper, **kwargs):
        self._lower_var = lower
        self._upper_var = upper
        super().__init__(f, track=Track, **kwargs)

    def compute(self, obj):
        tr = getattr(obj, self._name)
        def cost(x):
            with self.trace(self, obj, isolate=True):
                tr._value = x
                return self._compute(obj)
        l = obj.get(self._lower_var)
        u = obj.get(self._upper_var)
        #TODO: use optimize.minimize_scalar() instead?
        v = scipy.optimize.brentq(cost, l, u)
        # trigger update with final value
        cost(v)
        return v

class optimize2(statevar):
    def __init__(self, f=None, *, bracket=None, **kwargs):
        self._bracket_var = bracket
        super().__init__(f, track=Track, **kwargs)

    def compute(self, obj):
        tr = getattr(obj, self._name)
        def cost(x):
            print(f'opt2: {x}')
            with self.trace(self, obj, isolate=True):
                tr._value = x
                return self._compute(obj)
        bracket = obj.get(self._bracket_var)
        v = float(scipy.optimize.minimize_scalar(cost, bracket).x)
        # trigger update with final value
        cost(v)
        return v
