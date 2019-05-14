from .time import Timer
from .unit import U

class Track:
    def __init__(self, t, v):
        self._initial_value = v
        self.reset(t)

    def reset(self, t):
        self.timer = Timer(t)
        self._value = None
        self._regime = ''

    def check(self, t, regime):
        dt = self.timer.update(t)
        #TODO check recursion loop?
        force = False
        if dt > 0:
            force = True
        if self._value is None:
            self._value = self._initial_value
            force = True
        if regime is not None and regime != self._regime:
            self._regime = regime
            force = True
        return force

    def store(self, v):
        value = v()
        if value is not None:
            self._value = value
        return self.value

    @property
    def value(self):
        return self._value

class Accumulate(Track):
    def reset(self, t):
        super().reset(t)
        self._rate = None

    def store(self, v):
        if self._rate is not None:
            self._value += self._rate * self.timer.dt
        self._rate = v()
        return self.value

class Difference(Accumulate):
    def store(self, v):
        self._value = U(0, U[self._value])
        return super().store(v)

class Flip(Track):
    def reset(self, t):
        super().reset(t)
        self._changed = False

    def store(self, v):
        value = v()
        self._changed = (value != self._value)
        self._value = value
        return self.value

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
        self._stored = True
        return super().store(v)
