class Clock:
    def __init__(self, t, dt):
        self.t = t
        self.dt = dt

    def tick(self):
        self.t += self.dt

    @property
    def time(self):
        return self.t

    @property
    def interval(self):
        return self.dt

class Timer:
    def __init__(self, t):
        self.reset(t)

    def reset(self, t):
        self.t = t
        self.dt = 0

    def update(self, t):
        dt = self._interval(t)
        if dt > 0:
            self.t = t
            self.dt = dt
        #TODO: make sure dt is not negative
        return dt

    def _interval(self, t):
        if t == self.t:
            return 0
        try:
            d = t - self.t
        except TypeError:
            #TODO: better return None?
            return 0
        try:
            return d.total_seconds() / (24*60*60) # per day
        except AttributeError:
            return d
