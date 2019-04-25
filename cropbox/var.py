class var:
    def __init__(self, f=None, *, alias=None, **kwargs):
        self._alias_lst = alias.split(',') if alias else []
        self._kwargs = kwargs
        self.__call__(f)

    def __call__(self, f):
        if callable(f):
            fun = f
        elif isinstance(f, str):
            fun = lambda self: self[f]
        else:
            fun = lambda self: f
        self._wrapped_fun = fun
        return self

    def __set_name__(self, owner, name):
        if name in self._alias_lst:
            # name should have been already set by original
            return
        # names are set when type.__new__() gets called in TrackableMeta.__new__()
        self.__name__ = name

    def __repr__(self):
        return f'<{self.__name__}>'

    def __get__(self, obj, objtype):
        return self.get(obj)

    def data(self, obj):
        n = '_trackable_data'
        try:
            #HACK: avoid hasattr() calling __getattr__() when n is not found in __dict__
            obj.__dict__[n]
        except KeyError:
            setattr(obj, n, {})
        return getattr(obj, n)

    def init(self, obj, **kwargs):
        pass

    def get(self, obj):
        d = self.data(obj)
        try:
            return d[self]
        except KeyError:
            self.init(obj, **obj._kwargs)
            return d[self]
