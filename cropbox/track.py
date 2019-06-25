from .time import Timer
from .unit import U

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
        self._rate = None
        self._values = {}

    def store(self, v):
        if self._rate is not None:
            if self._regime == '':
                try:
                    self._value = self._original_value
                    breakpoint()
                    del self._original_value
                except:
                    pass
                self._value += self._rate * self.timer.dt
            else:
                #breakpoint()
                try:
                    self._original_value
                except:
                    self._original_value = self._value
                else:
                    self._value = self._original_value
                self._value += self._rate * self.timer.dt

        T0 = list(self._rates.keys())
        T1 = T0[1:] + [self.timer.t]
        DT = T1 - T0
        v = 0
        for dt, r in zip(DT, self._rates.values()):
            v += r * dt
        self._value2 = v

        #self._rate = v()

    def poststore(self, v):
        def f():
            self._rate = v()
            self._rates[self.timer.t] = self._rate
        if self._regime == '':
            return f
        else:
            return None

    @property
    def value(self):
        #return self._value
        return self._value2

class Difference(Accumulate):
    def store(self, v):
        self._value = U(0, U[self._value])
        super().store(v)

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
