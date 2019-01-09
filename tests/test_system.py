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
    assert s.a == 1 and s.b == 2
    c = s.context
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
    assert s.a == 1 and s.b == 1
    c = s.context
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
    assert s.a == 1 and s.b == 1
    c = s.context
    c.update()
    assert s.a == 1 and s.b == 2
    c.update()
    assert s.a == 1 and s.b == 3
    c.update()
    assert s.a == 1 and s.b == 4

def test_difference(instance):
    class S(System):
        @derive
        def a(self):
            return 1
        @difference
        def b(self):
            return self.a + 1
    s = instance(S)
    assert s.a == 1 and s.b == 2
    c = s.context
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
    assert s.a == 1 and s.b == 2
    assert s.c == 0 and s.d == 2
    c = s.context
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
    assert s.a == 1
    c = s.context
    c.update()
    assert s.a == 1

def test_parameter_with_config(instance):
    class S(System):
        @parameter
        def a(self):
            return 1
    s = instance(S, {'S': {'a': 2}})
    assert s.a == 2
    c = s.context
    c.update()
    assert s.a == 2

def test_drive(instance):
    class S(System):
        @drive
        def a(self):
            return {'a': self.context.time * 10}
    s = instance(S)
    assert s.a == 10
    c = s.context
    c.update()
    assert s.a == 20
    c.update()
    assert s.a == 30

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
