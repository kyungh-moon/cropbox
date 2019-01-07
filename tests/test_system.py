from . import context

from cropbox.system import System
from cropbox.context import Context
from cropbox.stage import Stage
from cropbox.statevar import statevar, derive, accumulate, difference, signal, parameter, drive, optimize

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
        return 0.5 * self.context.time

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

    @drive
    def temperature(self):
        return {'temperature': self.context.time*10}

    @derive
    def aa(self):
        return self.ci**2

    @derive
    def bb(self):
        return 2*self.ci + 1

    @optimize(lower=0, upper=10)
    def ci(self):
        return self.aa - self.bb

import configparser
import networkx as nx
import matplotlib.pyplot as plt
def test_system():
    config = configparser.ConfigParser()
    config['Clock'] = {'start': 0, 'interval': 1}
    config['Leaf'] = {'elongation_rate': 2.0}
    c = Context(config)
    c.branch(Leaf)
    c.branch(Stage)
    print(f't = {c.time}')
    c.update()
    print(f't = {c.time}')
    l = c.children[0]
    plt.figure(figsize=(12,12))
    g = statevar.trace.graph
    #g.remove_node('_time')
    nx.draw_circular(g, with_labels=True)
    plt.savefig('graph.png')
    print(' '.join([f"{k}={getattr(l, k)}" for k in l._statevar_names]))
    c.update()
    print(f't = {c.time}')
    print(' '.join([f"{k}={getattr(l, k)}" for k in l._statevar_names]))
    c.update()
    print(f't = {c.time}')
    print(' '.join([f"{k}={getattr(l, k)}" for k in l._statevar_names]))
    c.update()
    print(f't = {c.time}')
    print(' '.join([f"{k}={getattr(l, k)}" for k in l._statevar_names]))
