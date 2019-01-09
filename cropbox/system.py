from .statevar import statevar
import functools

class TrackableMeta(type):
    def __new__(metacls, name, bases, namespace):
        cls = type.__new__(metacls, name, bases, namespace)
        def remember(key, decorator):
            d = {k: v for (k, v) in namespace.items() if isinstance(v, decorator)}
            d = dict(getattr(cls, key, {}), **d)
            setattr(cls, key, d)
        remember('_statevars', statevar)
        return cls

class Trackable(metaclass=TrackableMeta):
    @property
    def _statevar_names(self):
        return self._statevars.keys()

    @property
    def _statevar_objs(self):
        return self._statevars.values()

    def setup(self):
        [s.setup(self) for s in self._statevar_objs]
        self.update()

    def update(self):
        [s.update(self) for s in self._statevar_objs]

    _force_update = False

    def force_update(cls, flag):
        cls._force_update = flag

class System(Trackable):
    def __init__(self, parent):
        self.parent = parent
        self.children = []
        if parent is not None:
            parent.children.append(self)
            self.context = parent.context
        self.setup()

    def get(self, name, *args):
        # support direct specification of value, i.e. 0
        if not isinstance(name, str):
            return name
        #HACK: support nested reference, i.e. 'context.time'
        return functools.reduce(lambda o, n: getattr(o, n, *args), [self] + name.split('.'))

    @property
    def neighbors(self):
        s = {self.parent} if self.parent is not None else {}
        return s | set(self.children)

    def branch(self, systemcls):
        self.context.queue(lambda: systemcls(self))

    def update(self, recursive=False):
        super().update()
        if recursive:
            [s.update() for s in self.children]
