from .time import Timer

class Track:
    def __init__(self, t):
        self.reset(t)

    def reset(self, t):
        self.timer = Timer(t)
        self._value = None

    def update(self, t, v):
        dt = self.timer.update(t)
        if self._value is None:
            self._value = 0
            self.store(v, dt)
        elif dt > 0:
            self.store(v, dt)
        return self.value

    def store(self, v, dt):
        self._value = v()

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

class Signal(Track):
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
