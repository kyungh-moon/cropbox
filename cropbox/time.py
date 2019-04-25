class Timer:
    def __init__(self, t):
        self.reset(t)

    def reset(self, t):
        self.t = t
        self.dt = 0

    def update(self, t):
        dt = t - self.t
        if dt > 0:
            self.t = t
            self.dt = dt
        #TODO: make sure dt is not negative
        return dt
