from .statevar import statevar, system
from .unit import U
from collections import ChainMap
from functools import reduce

# ChainMap order is backwards like multiple inheritance
decorators = (statevar, system)

class TrackableMeta(type):
    def __new__(metacls, name, bases, namespace):
        # manage var decorators in namespace
        def restruct(namespace, decorator):
            # namespace of vars
            n1 = {k: v for k, v in namespace.items() if isinstance(v, decorator)}
            # namespace of var aliases
            n2 = {k: v for d in [{k: v for k in v._alias_lst} for v in n1.values()] for k, v in d.items()}
            n1.update(n2)
            return n1
        ns = {f'_{d.__name__}': restruct(namespace, d) for d in decorators}
        var_namespace = dict(ChainMap(*ns.values()))

        # construct a new Trackable class
        cls = type.__new__(metacls, name, bases, dict(ChainMap(var_namespace, namespace)))

        #FIXME: maybe no need for remember anymore
        # remember each {var}s in `_{var}`
        def remember(cls, key, namespace):
            d = dict(getattr(cls, key, {}), **namespace)
            setattr(cls, key, d)
        remember(cls, '_trackable', var_namespace)
        [remember(cls, k, n) for k, n in ns.items()]
        return cls

class Trackable(metaclass=TrackableMeta):
    def __init__(self, **kwargs):
        self._kwargs = kwargs
        # force update here to ensure all trackables get initialized
        self.update()

    def __getattr__(self, name):
        if name == 'self':
            return self
        try:
            v = self._trackable[name]
        except KeyError:
            raise AttributeError(f"{self} has no attribute '{name}'.")
        else:
            return v.__get__(self, type(self))

    def update(self):
        [v.get(self) for v in dict.fromkeys(self._trackable.values())]

class Configurable:
    def option(self, *keys, config):
        def expand(k):
            if isinstance(k, System):
                #HACK: populate base classes down to System (not inclusive) for section names
                S = k.__class__.mro()
                return [s.__name__ for s in S[:S.index(System)]]
            if isinstance(k, statevar):
                return [k.__name__] + k._alias_lst
            if callable(k):
                return k.__name__
            else:
                return k
        keys = [expand(k) for k in keys]
        return self._option(*keys, config=config)

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
                return self._option(*keys, config=config[key])
            except KeyError:
                return None

class System(Trackable, Configurable):
    def __getitem__(self, name):
        # support direct specification of value, i.e. 0
        # support string value with unit, i.e. '1 m'
        v = U(name)
        if isinstance(v, str):
            # support nested reference, i.e. 'context.time'
            return reduce(lambda o, k: getattr(o, k), [self] + v.split('.'))
        else:
            return v

    def __iter__(self):
        #HACK: prevent infinite loop due to generous __getitem__
        raise TypeError('System is not iterable.')

    def setup(self):
        return {}

    def option(self, *keys, config=None):
        if config is None:
            config = self.context._config
        v = super().option(self, *keys, config=config)
        try:
            return self[v]
        #HACK: support unit string bypass
        except AttributeError:
            return v

    def collect(self, recursive=True, exclude_self=True):
        def cast(v):
            if v is None:
                return set()
            try:
                #FIXME: assume v is an iterable of System, not other types
                return set(v)
            except TypeError:
                return {v}
        def visit(s, S=set()):
            SS = set.union(*[cast(s[n]) for n in s._system])
            for ss in SS:
                if ss in S:
                    continue
                S.add(ss)
                if recursive:
                    visit(ss, S)
            return S
        S = visit(self)
        if exclude_self:
            return S - {self}
        else:
            return S

    context = system()
    parent = system()
    children = system([])

    @property
    def neighbors(self):
        s = {self.parent} if self.parent is not None else {}
        return s | set(self.children)
