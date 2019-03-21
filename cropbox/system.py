from .statevar import statevar, U
from functools import reduce

class TrackableMeta(type):
    def __new__(metacls, name, bases, namespace):
        # manage statevars in namespace
        def restruct(namespace, decorator):
            # original namespace excluding statevars
            n0 = {k: v for k, v in namespace.items() if not isinstance(v, decorator)}
            # namespace of statevars
            n1 = {k: v for k, v in namespace.items() if isinstance(v, decorator)}
            # set statevar name same as binding variable name
            [v.set_name(k) for k, v in n1.items()]
            # namespace of statevar aliases
            n2 = {k: v for d in [{k: v for k in v._alias_lst} for v in n1.values()] for k, v in d.items()}
            n1.update(n2)
            n0.update(n1)
            return n0, n1
        namespace, statevars = restruct(namespace, statevar)

        # construct a new Trackable class
        cls = type.__new__(metacls, name, bases, namespace)

        # remember statevars in `_statevars`
        def remember(cls, key, statevars, decorator=statevar):
            d = dict(getattr(cls, key, {}), **statevars)
            setattr(cls, key, d)
        remember(cls, '_statevars', statevars, statevar)
        return cls

class Trackable(metaclass=TrackableMeta):
    def __init__(self):
        [s.init(self) for s in self._statevars.values()]
        #FIXME: can we avoid this? otherwise, no way to initialize Systems with mutual dependency
        #self.update()

    def __getattr__(self, name):
        return self._statevars[name].__get__(self, type(self))

    def update(self):
        [s.update(self) for s in self._statevars.values()]

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
    def __init__(self, parent, **kwargs):
        self.parent = parent
        self.children = []
        if parent is not None:
            parent.children.append(self)
            self.context = parent.context
        super().__init__()
        [setattr(self, k, v) for k, v in kwargs.items()]
        self.setup()

    def __getitem__(self, key):
        # support direct specification of value, i.e. 0
        # support string value with unit, i.e. '1 m'
        v = U(key)
        if isinstance(v, str):
            # support nested reference, i.e. 'context.time'
            return reduce(lambda o, k: getattr(o, k), [self] + v.split('.'))
        else:
            return v

    @property
    def neighbors(self):
        s = {self.parent} if self.parent is not None else {}
        return s | set(self.children)

    def branch(self, systemcls, **kwargs):
        self.context.queue(lambda: systemcls(self, **kwargs))

    def setup(self):
        pass

    def option(self, *keys, config=None):
        if config is None:
            config = self.context._config
        v = super().option(self, *keys, config=config)
        return self[v]

    def update(self, recursive=True):
        super().update()
        if recursive:
            [s.update() for s in self.children]
