from .unit import U

import inspect

class var:
    def __init__(self, f=None, *, unit=None, nounit=None, alias=None, **kwargs):
        self._unit_var = unit
        self._nounit_lst = nounit.split(',') if nounit else []
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
        v = self.get(obj)
        return self.unit(obj, v)

    def data(self, obj):
        n = '_trackable_data'
        try:
            #HACK: avoid hasattr() calling __getattr__() when n is not found in __dict__
            obj.__dict__[n]
        except KeyError:
            setattr(obj, n, {})
        return getattr(obj, n)

    def unit(self, obj, v):
        try:
            # unit string returned by other variable
            u = obj[self._unit_var]
        except:
            # unit string as is
            u = self._unit_var
        return U(v, u)

    def init(self, obj, **kwargs):
        v = self.compute(obj)
        uv = self.unit(obj, v)
        self.set(obj, uv)

    def get(self, obj):
        d = self.data(obj)
        try:
            return d[self]
        except KeyError:
            self.init(obj, **obj._kwargs)
            return d[self]

    def set(self, obj, value):
        d = self.data(obj)
        d[self] = value

    def compute(self, obj):
        fun = self._wrapped_fun
        ps = inspect.signature(fun).parameters
        def resolve_arg(k, p, i):
            if i == 0:
                return (k, obj)
            a = obj.option(fun, k)
            if a is not None:
                return (k, a)
            v = p.default
            if v is not p.empty:
                return (k, obj[v])
            #HACK: distinguish KeyError raised by missing k, or by running statevar definition
            elif k in obj._trackable:
                return (k, obj[k])
            else:
                return None
        params = [resolve_arg(*t, i) for i, t in enumerate(ps.items())]
        params = filter(None, params)
        def resolve_unit(k, v):
            if k in self._nounit_lst:
                v = U.magnitude(v)
            return v
        params = {k: resolve_unit(k, v) for k, v in params}
        if len(ps) == len(params):
            return fun(**params)
        else:
            def f(*args, **kwargs):
                p = params.copy()
                p.update(kwargs)
                q = dict(zip([k for k in ps if k not in p], args))
                a = dict(**p, **q)
                a = {k: resolve_unit(k, v) for k, v in a.items()}
                return fun(**a)
            return f
