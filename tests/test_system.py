from . import context

from cropbox.system import System
from cropbox.context import Context
from cropbox.stage import Stage
from cropbox.statevar import derive, accumulate, difference, signal, parameter
from cropbox.time import Clock

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
        print("f")
        return self.e + 1

    @accumulate(time='slow_time')
    def fd(self):
        return self.e + 1

    @property
    def slow_time(self):
        return 0.5 * self.time

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
def test_system():
    config = configparser.ConfigParser()
    config['Leaf'] = {'elongation_rate': 2.0}
    c = Context(Clock(t=1, dt=1), config)
    c.branch(Leaf)
    c.branch(Stage)
    c.tick()
    l = c.children[0]
    print(' '.join([f"{k}={getattr(l, k)}" for k in l._statevar_names]))
    c.tick()
    print(' '.join([f"{k}={getattr(l, k)}" for k in l._statevar_names]))
    c.tick()
    print(' '.join([f"{k}={getattr(l, k)}" for k in l._statevar_names]))
    c.tick()
    print(' '.join([f"{k}={getattr(l, k)}" for k in l._statevar_names]))
