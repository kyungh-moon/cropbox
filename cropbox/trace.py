from .logger import logger

class Trace:
    def __init__(self):
        self.reset()

    def reset(self):
        self._stack = []
        self._regime = ['']

    @property
    def stack(self):
        def extract(s):
            try:
                x = s[-1]
            except IndexError:
                return s
            else:
                return extract(x) if type(x) is list else s
        return extract(self._stack)

    @property
    def indent(self):
        def count(s):
            try:
                n = count(s[-1])
            except:
                return len(s)
            else:
                return len(s) + n - 1
        return count(self._stack) * ' ' * 2

    @property
    def regime(self):
        return self._regime[-1]

    def push(self, v, regime=None):
        if regime is not None and regime != self.regime:
            v = [v]
            self._regime.append(regime)
        self.stack.append(v)

    def pop(self):
        v = self.stack.pop()
        def clean():
            if len(self.stack) == 0 and len(self._stack) > 0:
                self._stack.pop()
                self._regime.pop()
                clean()
        clean()
        return v

    def peek(self):
        try:
            return self.stack[-1]
        except:
            return None

    def __call__(self, var, obj, regime=None):
        self._mem = (var, obj, regime)
        return self

    def __enter__(self):
        v, o, r = self._mem
        del self._mem
        s = self.peek()
        self.push(v, regime=r)
        logger.trace(f'{self.indent}> {v.__name__} ({r}) - {self._stack}')
        return self

    def __exit__(self, *excs):
        v = self.pop()
        #logger.trace(f'{self.indent}< {v.__name__} - {self._stack}')

    def is_stacked(self, var):
        return len([v for v in self.stack if v is var]) > 1

    @property
    def is_update_forced(self):
        try:
            x = self._stack[-1]
        except IndexError:
            return False
        else:
            return True if type(x) is list else False
