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
        #HACK: can't do dict comprehension in Trackable.__init__ due to _init_var access
        n = '_trackable_data'
        # if not hasattr(obj, n):
        #     setattr(obj, n, {})
        d = obj[n]
        return d

    def init(self, obj, **kwargs):
        pass

    def get(self, obj):
        return self.data(obj)[self]
