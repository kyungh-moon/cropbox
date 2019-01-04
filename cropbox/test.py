from .system import System
from .context import Context
from .stage import Stage
from .statevar import derive, accumulate, difference, signal, parameter
from .time import Clock

class Leaf(System):
    @parameter
    def elongation_rate(self):
        return 1.0

    @accumulate
    def d(self):
        print("d")
        return self.a + 1

    @difference
    def di(self):
        return self.a + 1

    @accumulate
    def e(self):
        print("e")
        return self.f + 1

    @accumulate
    def f(self):
        print("e")
        return self.e + 1

    @derive
    def a(self):
        print("a")
        return 1

    @derive
    def b(self):
        print("b")
        return 2

    @derive
    def c(self):
        print("c")
        return self.a + self.b

    @signal
    def aa(self):
        return self.a

    @signal
    def dd(self):
        return self.d

    @signal
    def aaa(self):
        return self.a

import configparser
config = configparser.ConfigParser()
config['Leaf'] = {} #{'elongation_rate': 2.0}
c = Context(Clock(t=1, dt=1), config)
c.branch(Leaf)
c.branch(Stage)
c.tick()
l = c.children[0]
print(' '.join([str(getattr(l, k)) for k in l._statevar_names]))
c.tick()
print(' '.join([str(getattr(l, k)) for k in l._statevar_names]))
c.tick()
print(' '.join([str(getattr(l, k)) for k in l._statevar_names]))
c.tick()
print(' '.join([str(getattr(l, k)) for k in l._statevar_names]))
