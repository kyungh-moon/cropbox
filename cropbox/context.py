from .system import System

class Context(System):
    def __init__(self, clock, config):
        self.context = self
        self.clock = clock
        self._config = config
        self._pending = []
        super().__init__(None)

    @property
    def config(self):
        return self._config

    def tick(self):
        self.clock.tick()
        self.process()
        self.update()

    def queue(self, f):
        self._pending.append(f)

    def process(self):
        [f() for f in self._pending]
        self._pending.clear()

    def update(self):
        super().update()
        [s.update() for s in self.children]
