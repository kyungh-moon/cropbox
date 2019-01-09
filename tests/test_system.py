from . import context

from cropbox.system import System
from cropbox.context import Context
from cropbox.stage import Stage
from cropbox.statevar import statevar, derive, accumulate, difference, signal, parameter, drive, optimize

import pytest

@pytest.fixture
def instance():
    def _instance(systemcls, config_dict=None):
        import configparser
        config = configparser.ConfigParser()
        if config_dict is not None:
            config.read_dict(config_dict)
        c = Context(config)
        c.branch(systemcls)
        c.update()
        return c.children[0]
    return _instance

def test_derive(instance):
    class S(System):
        @derive
        def a(self):
            return 1
        @derive
        def b(self):
            return 2
        @derive
        def c(self):
            return self.a + self.b
    s = instance(S)
    assert s.a == 1 and s.b == 2 and s.c == 3

def test_accumulate(instance):
    class S(System):
        @derive
        def a(self):
            return 1
        @accumulate
        def b(self):
            return self.a + 1
    s = instance(S)
    c = s.context
    assert s.a == 1 and s.b == 2
    c.update()
    assert s.a == 1 and s.b == 4
    c.update()
    assert s.a == 1 and s.b == 6
    c.update()
    assert s.a == 1 and s.b == 8

def test_accumulate_with_cross_reference(instance):
    class S(System):
        @accumulate
        def a(self):
            return self.b + 1
        @accumulate
        def b(self):
            return self.a + 1
    s = instance(S)
    c = s.context
    assert s.a == 1 and s.b == 1
    c.update()
    assert s.a == 3 and s.b == 3
    c.update()
    assert s.a == 7 and s.b == 7
    c.update()
    assert s.a == 15 and s.b == 15

def test_accumulate_with_time(instance):
    class S(System):
        @derive
        def a(self):
            return 1
        @accumulate(time='t')
        def b(self):
            return self.a + 1
        @property
        def t(self):
            return 0.5 * self.context.time
    s = instance(S)
    c = s.context
    assert s.a == 1 and s.b == 1
    c.update()
    assert s.a == 1 and s.b == 2
    c.update()
    assert s.a == 1 and s.b == 3
    c.update()
    assert s.a == 1 and s.b == 4

def test_accumulate_transport(instance):
    class S(System):
        @accumulate(init=10)
        def a(self):
            return -max(self.a - self.b, 0)
        @accumulate
        def b(self):
            return max(self.a - self.b, 0) - max(self.b - self.c, 0)
        @accumulate
        def c(self):
            return max(self.b - self.c, 0)
    s = instance(S)
    c = s.context
    assert s.a == 0 and s.b == 10 and s.c == 0
    c.update()
    assert s.a == 0 and s.b == 0 and s.c == 10
    c.update()
    assert s.a == 0 and s.b == 0 and s.c == 10

def test_accumulate_distribute(instance):
    class S(System):
        @drive
        def s(self):
            return {'s': (self.context.time + 1) * 100}
        @accumulate
        def d1(self):
            return self.s * 0.2
        @accumulate
        def d2(self):
            return self.s * 0.3
        @accumulate
        def d3(self):
            return self.s * 0.5
    s = instance(S)
    c = s.context
    assert s.s == 200 and s.d1 == 20 and s.d2 == 30 and s.d3 == 50
    c.update()
    assert s.s == 300 and s.d1 == 60 and s.d2 == 90 and s.d3 == 150
    c.update()
    assert s.s == 400 and s.d1 == 120 and s.d2 == 180 and s.d3 == 300

def test_difference(instance):
    class S(System):
        @derive
        def a(self):
            return 1
        @difference
        def b(self):
            return self.a + 1
    s = instance(S)
    c = s.context
    assert s.a == 1 and s.b == 2
    c.update()
    assert s.a == 1 and s.b == 2
    c.update()
    assert s.a == 1 and s.b == 2
    c.update()
    assert s.a == 1 and s.b == 2

def test_signal(instance):
    class S(System):
        @derive
        def a(self):
            return 1
        @accumulate
        def b(self):
            return self.a + 1
        @signal
        def c(self):
            return self.a
        @signal
        def d(self):
            return self.b
    s = instance(S)
    c = s.context
    assert s.a == 1 and s.b == 2
    assert s.c == 0 and s.d == 2
    c.update()
    assert s.a == 1 and s.b == 4
    assert s.c == 0 and s.d == 4
    c.update()
    assert s.a == 1 and s.b == 6
    assert s.c == 0 and s.d == 6

def test_parameter(instance):
    class S(System):
        @parameter
        def a(self):
            return 1
    s = instance(S)
    c = s.context
    assert s.a == 1
    c.update()
    assert s.a == 1

def test_parameter_with_config(instance):
    class S(System):
        @parameter
        def a(self):
            return 1
    s = instance(S, {'S': {'a': 2}})
    c = s.context
    assert s.a == 2
    c.update()
    assert s.a == 2

def test_drive_with_dict(instance):
    class S(System):
        @drive
        def a(self):
            return {'a': self.context.time * 10}
    s = instance(S)
    c = s.context
    assert s.a == 10
    c.update()
    assert s.a == 20
    c.update()
    assert s.a == 30

def test_drive_with_dataframe(instance):
    import pandas as pd
    class S(System):
        @property
        def df(self):
            return pd.DataFrame({'a': [0, 10, 20, 30]}, [0, 1, 2, 3])
        @drive
        def a(self):
            return self.df.loc[self.context.time]
    s = instance(S)
    c = s.context
    assert c.time == 1 and s.a == 10
    c.update()
    assert c.time == 2 and s.a == 20
    c.update()
    assert c.time == 3 and s.a == 30

def test_optimize(instance):
    class S(System):
        @derive
        def a(self):
            return 2*self.x
        @derive
        def b(self):
            return self.x + 1
        @optimize(lower=0, upper=2)
        def x(self):
            return self.a - self.b
    s = instance(S)
    assert s.x == 1
    assert s.a == s.b == 2

def test_clock(instance):
    class S(System):
        pass
    s = instance(S)
    c = s.context
    assert c.time == 1
    c.update()
    assert c.time == 2
    c.update()
    assert c.time == 3

def test_clock_with_config(instance):
    class S(System):
        pass
    s = instance(S, {'Clock': {'start': 5, 'interval': 10}})
    c = s.context
    assert c.time == 15
    c.update()
    assert c.time == 25
    c.update()
    assert c.time == 35

def test_plot(instance):
    class S(System):
        @derive
        def a(self):
            return 1
        @accumulate
        def b(self):
            return self.a
    #FIXME: graph should be automatically reset
    statevar.trace.reset()
    s = instance(S)
    g = statevar.trace.graph
    import matplotlib.pyplot as plt
    plt.figure(figsize=(12, 12))
    import networkx as nx
    nx.draw_circular(g, with_labels=True)
    plt.savefig('graph.png')
