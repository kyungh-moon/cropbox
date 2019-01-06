from .system import System

class Context(System):
    def __init__(self, clock, config):
        clock.context = self
        super().__init__(clock)
        self._config = config
        self._pending = []

    @property
    def clock(self):
        return self.parent

    @property
    def config(self):
        return self._config

    def queue(self, f):
        self._pending.append(f)

    def update(self):
        # process pending operations
        [f() for f in self._pending]
        self._pending.clear()

        # update state variables recursively
        super().update(recursive=True)
