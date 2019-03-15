from .statevar import statevar
import functools

class TrackableMeta(type):
    def __new__(metacls, name, bases, namespace):
        # manage statevars in namespace
        def restruct(namespace, decorator):
            # original namespace excluding statevars
            n0 = {k: v for k, v in namespace.items() if not isinstance(v, decorator)}
            # namespace of statevars
            n1 = {k: v for k, v in namespace.items() if isinstance(v, decorator)}
            # namespace of statevar aliases
            n2 = {k: v for d in [{k: v for k in v._name_lst} for v in n1.values()] for k, v in d.items()}
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

    def __getitem__(self, key):
        return getattr(self, key)

    def update(self):
        [s.update(self) for s in self._statevars.values()]

class System(Trackable):
    def __init__(self, parent, **kwargs):
        self.parent = parent
        self.children = []
        if parent is not None:
            parent.children.append(self)
            self.context = parent.context
        self.setup()
        [setattr(self, k, v) for k, v in kwargs.items()]
        super().__init__()

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

    def branch(self, systemcls, **kwargs):
        self.context.queue(lambda: systemcls(self, **kwargs))

    def setup(self):
        pass

    def update(self, recursive=True):
        super().update()
        if recursive:
            [s.update() for s in self.children]
