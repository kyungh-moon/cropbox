from .track import Track, Accumulate, Difference, Signal, Static

#HACK: to implement @optimize, need better way of controlling this
#TODO: probably need a full dependency graph between variables to push updates downwards
#FORCE_UPDATE = False

import inspect
import networkx as nx
import pint

class Unit:
    def __init__(self):
        r = pint.UnitRegistry()
        r.default_format = '~P'
        #r.setup_matplotlib()
        self.registry = r

    def __call__(self, v, unit=None):
        if v is None:
            return v
        try:
            #HACK: avoid collision (variable named 'm' vs. unit string 'm')
            if not v[0].isalpha():
                v = self.registry(v)
        except:
            pass
        if unit is None:
            return v
        Q = self.registry.Quantity
        if isinstance(v, Q):
            return v.to(unit)
        else:
            return Q(v, unit)
U = Unit()

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

    def __init__(self, f=None, *, track, time='context.time', init=0, unit=None, alias=None):
        self._track_cls = track
        self._time_var = time
        self._init_var = init
        self._unit_qtt = U(unit)
        self._alias_lst = alias.split(',') if alias else []
        if f is not None:
            self.__call__(f)

    def __call__(self, f):
        if callable(f):
            fun = f
        elif isinstance(f, str):
            fun = lambda self: self[f]
        else:
            fun = lambda self: f
        self._compute_fun = fun
        return self

    def set_name(self, name):
        self.__name__ = name
        self._tr_name = f'_{name}'

    def __get__(self, obj, objtype):
        v = self.update(obj)
        return U(v, self._unit_qtt)

    def time(self, obj):
        return obj[self._time_var]

    def compute(self, obj):
        return self._compute(obj)

    def _compute(self, obj):
        fun = self._compute_fun
        ps = inspect.signature(fun).parameters
        def resolve(k, p, i):
            if i == 0:
                a = obj
            else:
                a = obj.option(fun, k)
            if a is None:
                v = p.default
                if v is not p.empty:
                    a = obj[v]
                else:
                    #HACK: distinguish KeyError raised by missing k, or by running statevar definition
                    if k in obj._statevars:
                        a = obj[k]
                    else:
                        return None
            return (k, a)
        params = dict(filter(None, [resolve(*t, i) for i, t in enumerate(ps.items())]))
        if len(ps) == len(params):
            return fun(**params)
        else:
            def f(*args, **kwargs):
                p = params.copy()
                p.update(kwargs)
                q = dict(zip([k for k in ps if k not in p], args))
                return fun(**p, **q)
            return f

    def init(self, obj):
        t = self.time(obj)
        v = obj[self._init_var]
        setattr(obj, self._tr_name, self._track_cls(t, v))

    def update(self, obj):
        with self.trace(self, obj):
            return self._update(obj)

    def _update(self, obj):
        #HACK: prevent recursion loop already in computation tree
        tr = getattr(obj, self._tr_name)
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

class proxy(statevar):
    def __init__(self, f=None, **kwargs):
        super().__init__(f, track=Track, **kwargs)

    def time(self, obj):
        # doesn't change at t=0 ensuring only one update
        return 0

class parameter(proxy):
    def compute(self, obj):
        # allow override by external option
        v = obj.option(self)
        if v is None:
            v = super().compute(obj)
        return v

class drive(statevar):
    def __init__(self, f=None, **kwargs):
        super().__init__(f, track=Track, **kwargs)

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
        tr = getattr(obj, self._tr_name)
        def cost(x):
            with self.trace(self, obj, isolate=True):
                tr._value = x
                return self._compute(obj)
        l = obj[self._lower_var]
        u = obj[self._upper_var]
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
        tr = getattr(obj, self._tr_name)
        def cost(x):
            print(f'opt2: {x}')
            with self.trace(self, obj, isolate=True):
                tr._value = x
                return self._compute(obj)
        bracket = obj[self._bracket_var]
        v = float(scipy.optimize.minimize_scalar(cost, bracket).x)
        # trigger update with final value
        cost(v)
        return v
