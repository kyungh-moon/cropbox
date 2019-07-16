from .time import Timer

class Track:
    def __init__(self, t, v, name=''):
        self._initial_value = v
        self.__name__ = name
        self.reset(t)

    def __repr__(self):
        return f'<{self.__name__} = {self.value}>'

    def reset(self, t):
        self.timer = Timer(t)
        self._value = None
        self._regime = ''

    def check(self, t, regime):
        dt = self.timer.update(t)
        #TODO check recursion loop?
        update = False
        if dt > 0:
            update = True
        if self._value is None:
            self._value = self._initial_value
            update = True
        if regime is not None and regime != self._regime:
            self._regime = regime
            update = True
        return update

    def store(self, v):
        value = v()
        if value is not None:
            self._value = value

    def poststore(self, v):
        return None

    @property
    def value(self):
        return self._value

class Accumulate(Track):
    def reset(self, t):
        super().reset(t)
        self._rates = {}
        self._value_cache = {}

    def store(self, v):
        v = self._initial_value
        R = self._rates
        T0 = list(R.keys())
        for t in reversed(T0):
            if t in self._value_cache:
                v = self._value_cache[t]
                R = {k: R[k] for k in R if k >= t}
                T0 = list(R.keys())
                break
        t = self.timer.t
        T1 = T0[1:] + [t]
        dT = [t1 - t0 for t0, t1 in zip(T0, T1)]
        for dt, r in zip(dT, R.values()):
            if r is not None:
                v += r * dt
        self._value = v
        self._value_cache[t] = v

    def poststore(self, v):
        t = self.timer.t
        def f():
            self._rates[t] = v()
            V = self._value_cache
            self._value_cache = {k: V[k] for k in V if k == t}
        if self._regime == '':
            return f
        else:
            return None

class Difference(Accumulate):
    def poststore(self, v):
        t = self.timer.t
        def f():
            self._rates = {t: v()}
            self._value_cache = {}
        if self._regime == '':
            return f
        else:
            return None

class Flip(Track):
    def reset(self, t):
        super().reset(t)
        self._changed = False

    def store(self, v):
        value = v()
        self._changed = (value != self._value)
        self._value = value

    @property
    def value(self):
        #return self._changed
        return type(self._value)(self._changed * self._value)

class Preserve(Track):
    def reset(self, t):
        super().reset(t)
        self._stored = False

    def check(self, t, regime):
        return super().check(t, regime) and not self._stored

    def store(self, v):
        super().store(v)
        self._stored = True
