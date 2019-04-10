from .time import Timer

class Track:
    def __init__(self, t, v):
        self._initial_value = v
        self.reset(t)

    def reset(self, t):
        self.timer = Timer(t)
        self._value = None
        self._regime = None

    def update(self, t, v, regime):
        dt = self.timer.update(t)
        #TODO check recursion loop?
        force = False
        if dt > 0:
            force = True
        if self._value is None:
            self._value = self._initial_value
            #force = True
        if regime is not None and regime != self._regime:
            self._regime = regime
            force = True
        if force:
            self.store(v, dt)
        return self.value

    def store(self, v, dt):
        value = v()
        if value is not None:
            self._value = value

    @property
    def value(self):
        return self._value

class Accumulate(Track):
    def reset(self, t):
        super().reset(t)
        self._rate = 0

    def store(self, v, dt):
        self._value += self._rate * dt
        self._rate = v()

class Difference(Accumulate):
    def store(self, v, dt):
        self._value = 0
        super().store(v, dt)

class Flip(Track):
    def reset(self, t):
        super().reset(t)
        self._changed = False

    def store(self, v, dt):
        value = v()
        self._changed = (value != self._value)
        self._value = value

    @property
    def value(self):
        #return self._changed
        return type(self._value)(self._changed * self._value)

class Static(Track):
    def reset(self, t):
        super().reset(t)
        self._stored = False

    def store(self, v, dt):
        if not self._stored:
            super().store(v, dt)
            self._stored = True
