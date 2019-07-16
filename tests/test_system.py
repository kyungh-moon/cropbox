from cropbox.system import System
from cropbox.context import instance
from cropbox.statevar import accumulate, constant, derive, difference, drive, flag, flip, optimize, parameter, produce, statevar, system, systemproxy
from cropbox.unit import U

import pytest

def test_derive():
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

def test_derive_with_cross_reference():
    class S(System):
        @derive
        def a(self):
            return self.b
        @derive
        def b(self):
            return self.a
    with pytest.raises(RecursionError):
        s = instance(S)

def test_accumulate():
    class S(System):
        @derive
        def a(self):
            return 1
        @accumulate
        def b(self):
            return self.a + 1
    s = instance(S)
    c = s.context
    assert s.a == 1 and s.b == 0
    c.advance()
    assert s.a == 1 and s.b == 2
    c.advance()
    assert s.a == 1 and s.b == 4
    c.advance()
    assert s.a == 1 and s.b == 6

def test_accumulate_with_cross_reference():
    class S(System):
        @accumulate
        def a(self):
            return self.b + 1
        @accumulate
        def b(self):
            return self.a + 1
    s = instance(S)
    c = s.context
    assert s.a == 0 and s.b == 0
    c.advance()
    assert s.a == 1 and s.b == 1
    c.advance()
    assert s.a == 3 and s.b == 3
    c.advance()
    assert s.a == 7 and s.b == 7

def test_accumulate_with_cross_reference_mirror():
    class S1(System):
        @accumulate
        def a(self):
            return self.b + 1
        @accumulate
        def b(self):
            return self.a + 2
    class S2(System):
        @accumulate
        def a(self):
            return self.b + 2
        @accumulate
        def b(self):
            return self.a + 1
    s1 = instance(S1)
    s2 = instance(S2)
    c1 = s1.context
    c2 = s2.context
    assert s1.a == s2.b and s1.b == s2.a
    c1.advance()
    c2.advance()
    assert s1.a == s2.b and s1.b == s2.a
    c1.advance()
    c2.advance()
    assert s1.a == s2.b and s1.b == s2.a
    c1.advance()
    c2.advance()
    assert s1.a == s2.b and s1.b == s2.a

def test_accumulate_with_time():
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
    assert s.a == 1 and s.b == 0
    c.advance()
    assert s.a == 1 and s.b == 1
    c.advance()
    assert s.a == 1 and s.b == 2
    c.advance()
    assert s.a == 1 and s.b == 3

def test_accumulate_transport():
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
    assert s.a == 10 and s.b == 0 and s.c == 0
    c.advance()
    assert s.a == 0 and s.b == 10 and s.c == 0
    c.advance()
    assert s.a == 0 and s.b == 0 and s.c == 10
    c.advance()
    assert s.a == 0 and s.b == 0 and s.c == 10

def test_accumulate_distribute():
    class S(System):
        @drive
        def s(self):
            return {'s': self.context.time * 100}
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
    assert c.time == 0 and s.s == 0 and s.d1 == 0 and s.d2 == 0 and s.d3 == 0
    c.advance()
    assert c.time == 1 and s.s == 100 and s.d1 == 0 and s.d2 == 0 and s.d3 == 0
    c.advance()
    assert c.time == 2 and s.s == 200 and s.d1 == 20 and s.d2 == 30 and s.d3 == 50
    c.advance()
    assert c.time == 3 and s.s == 300 and s.d1 == 60 and s.d2 == 90 and s.d3 == 150
    c.advance()
    assert c.time == 4 and s.s == 400 and s.d1 == 120 and s.d2 == 180 and s.d3 == 300

def test_difference():
    class S(System):
        @derive
        def a(self):
            return 1
        @difference
        def b(self):
            return self.a + 1
    s = instance(S)
    c = s.context
    assert s.a == 1 and s.b == 0
    c.advance()
    assert s.a == 1 and s.b == 2
    c.advance()
    assert s.a == 1 and s.b == 2
    c.advance()
    assert s.a == 1 and s.b == 2

def test_flip():
    class S(System):
        @derive
        def a(self):
            return 1
        @accumulate
        def b(self):
            return self.a + 1
        @flip
        def sa(self):
            return self.a
        @flip
        def sb(self):
            return self.b
    s = instance(S)
    c = s.context
    assert s.a == 1 and s.b == 0
    assert s.sa == 1 and s.sb == 0
    c.advance()
    assert s.a == 1 and s.b == 2
    assert s.sa == 0 and s.sb == 2
    c.advance()
    assert s.a == 1 and s.b == 4
    assert s.sa == 0 and s.sb == 4

def test_constant():
    class S(System):
        @derive
        def a(self):
            return 1
        @accumulate
        def b(self):
            return self.a + 1
        @constant
        def c(self):
            return self.b + 1
    s = instance(S)
    c = s.context
    assert s.a == 1 and s.b == 0 and s.c == 1
    c.advance()
    assert s.a == 1 and s.b == 2 and s.c == 1
    c.advance()
    assert s.a == 1 and s.b == 4 and s.c == 1

def test_parameter():
    class S(System):
        @parameter
        def a(self):
            return 1
    s = instance(S)
    c = s.context
    assert s.a == 1
    c.advance()
    assert s.a == 1

def test_parameter_with_config():
    class S(System):
        @parameter
        def a(self):
            return 1
    s = instance(S, config={'S': {'a': 2}})
    c = s.context
    assert s.a == 2
    c.advance()
    assert s.a == 2

def test_parameter_with_config_alias():
    class S(System):
        @parameter(alias='aa')
        def a(self):
            return 1
        @parameter(alias='b')
        def bb(self):
            return 1
    s = instance(S, config={'S': {'a': 2, 'b': 2}})
    assert s.a == 2
    assert s.b == 2

def test_drive_with_dict():
    class S(System):
        @drive
        def a(self):
            return {'a': self.context.time * 10}
    s = instance(S)
    c = s.context
    assert c.time == 0 and s.a == 0
    c.advance()
    assert c.time == 1 and s.a == 10
    c.advance()
    assert c.time == 2 and s.a == 20
    c.advance()
    assert c.time == 3 and s.a == 30

def test_drive_with_key():
    class S(System):
        @drive(key='b')
        def a(self):
            return {'b': 1}
    s = instance(S)
    c = s.context
    assert s.a == 1

def test_drive_with_dataframe():
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
    assert c.time == 0 and s.a == 0
    c.advance()
    assert c.time == 1 and s.a == 10
    c.advance()
    assert c.time == 2 and s.a == 20
    c.advance()
    assert c.time == 3 and s.a == 30

def test_drive_with_system():
    class T(System):
        @derive
        def a(self):
            return 1
        @derive
        def b(self):
            return 2
    class S(System):
        @system
        def t(self):
            return T
        @drive(alias='aa')
        def a(self):
            return self.t
        b = drive('t', alias='bb')
        c = derive('t.b')
    s = instance(S)
    assert s.a == s.aa == s.t.a == 1
    assert s.b == s.bb == s.t.b == s.c == 2

def test_flag():
    class S(System):
        @flag
        def a(self):
            return True
        @flag
        def b(self):
            return False
        @flag(prob=0)
        def c(self):
            return True
        @flag(prob=1)
        def d(self):
            return False
        zero = derive(0)
        one = derive(1)
        @flag(prob='zero')
        def e(self):
            return True
        @flag(prob='one')
        def f(self):
            return False
    s = instance(S)
    assert s.a and not s.b
    assert not s.c and not s.d
    assert not s.e and not s.f

def test_systemproxy():
    class T(System):
        @derive
        def a(self):
            return 1
    class S(System):
        t = systemproxy(T)
    s = instance(S)
    assert s.a == s.t.a == 1

def test_produce():
    class S(System):
        @produce
        def a(self):
            return S
    s = instance(S)
    c = s.context
    assert len(s.children) == 0
    c.advance()
    assert len(s.children) == 1 and len(s.children[0].children) == 0
    c.advance()
    assert len(s.children) == 2 and len(s.children[0].children) == 1 and len(s.children[1].children) == 0

def test_produce_with_kwargs():
    class S(System):
        @produce
        def a(self):
            return (S, {'t': self.context.time + 1}) # produced in the next time step
        @constant(init=0)
        def t(self):
            return None
    s = instance(S)
    c = s.context
    assert len(s.children) == 0 and s.t == 0
    c.advance()
    assert len(s.children) == 1 and s.t == 0
    s1 = s.children[0]
    assert len(s1.children) == 0 and s1.t == 1
    c.advance()
    s2 = s.children[1]
    s11 = s1.children[0]
    assert len(s.children) == 2 and len(s1.children) == 1 and len(s2.children) == 0
    assert s.t == 0 and s1.t == 1 and s2.t == 2 and s11.t == 2

def test_produce_with_none():
    class S(System):
        @produce
        def a(self):
            return None
    s = instance(S)
    c = s.context
    assert len(s.children) == 0
    c.advance()
    assert len(s.children) == 0

def test_optimize():
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

def test_optimize_with_unit():
    class S(System):
        @derive(unit='m')
        def a(self):
            return 2*self.x
        @derive(unit='m')
        def b(self):
            return self.x + U(1, 'm')
        @optimize(lower=U(0, 'm'), upper=U(2, 'm'), unit='m')
        def x(self):
            return self.a - self.b
    s = instance(S)
    assert s.x == U(1, 'm')
    assert s.a == s.b == U(2, 'm')

def test_clock():
    class S(System):
        pass
    s = instance(S)
    c = s.context
    assert c.time == 0
    c.advance()
    assert c.time == 1
    c.advance()
    assert c.time == 2

def test_clock_with_config():
    class S(System):
        pass
    s = instance(S, config={'Clock': {'start': 5, 'interval': 10}})
    c = s.context
    assert c.time == 5
    c.advance()
    assert c.time == 15
    c.advance()
    assert c.time == 25

def test_clock_with_datetime():
    import datetime
    class S(System):
        pass
    s = instance(S, config={'Clock': {
        'unit': 'day',
        'start_datetime': datetime.datetime(2019, 1, 1),
        }})
    c = s.context
    assert c.datetime == datetime.datetime(2019, 1, 1)
    c.advance()
    assert c.datetime == datetime.datetime(2019, 1, 2)
    c.advance()
    assert c.datetime == datetime.datetime(2019, 1, 3)

def test_alias():
    class S(System):
        @derive(alias='aa')
        def a(self):
            return 1
        @derive(alias='bb,bbb')
        def b(self):
            return 2
        @derive
        def c(self):
            return self.a + self.aa + self.b + self.bb + self.bbb
    s = instance(S)
    assert s.a == s.aa == 1
    assert s.b == s.bb == s.bbb == 2
    assert s.c == 8

def test_args():
    class S(System):
        @derive(alias='a')
        def a_long_named_var(self):
            return 1
        @derive
        def b(self):
            return self.a_long_named_var
        @derive
        def c(self, a_long_named_var):
            return a_long_named_var
        @derive
        def d(self, a):
            return a
        @derive
        def e(self, ee='a'):
            return ee
        @derive
        def f(self, ff=1):
            return ff
    s = instance(S)
    assert s.a == s.b == s.c == s.d == s.e == s.f == 1

def test_args_with_config():
    class S(System):
        @derive
        def a(self, b):
            return b
    s = instance(S, config={'S': {'a': {'b': 1}}})
    assert s.a == 1

def test_args_partial():
    class S(System):
        @derive
        def a(self, b, c, d=0):
            return b + c + d
        @derive
        def b(self):
            return 1
    s = instance(S)
    assert s.a(c=1) == 2
    assert s.a(c=2) == 3
    assert s.a(c=2, d=1) == 4
    assert s.a(1) == 2

def test_inline():
    class S(System):
        a = derive(1)
        b = derive(2, alias='c')
    s = instance(S)
    assert s.a == 1
    assert s.b == s.c == 2

def test_getitem():
    class S(System):
        @derive
        def a(self):
            return 1
    s = instance(S)
    assert s.a == s['a'] == 1

def test_plot(tmp_path):
    class S(System):
        @derive
        def a(self):
            return 1
        @accumulate
        def b(self):
            return self.a
    #FIXME: graph should be automatically reset
    statevar.trace.reset(build_graph=True)
    s = instance(S)
    g = statevar.trace.graph
    import matplotlib.pyplot as plt
    plt.figure(figsize=(12, 12))
    import networkx as nx
    nx.draw_circular(g, with_labels=True)
    plt.savefig(tmp_path/'graph.png')

def test_cytoscape(tmp_path):
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
    #import networkx as nx
    #nx.write_graphml(g, tmp_path/'cy.graphml')
    cy = {
        'elements': {
            'nodes': [],
            'edges': [],
        }
    }
    for n in g.nodes():
        cy['elements']['nodes'].append({
            'data': {
                'id': n,
                'label': n,
                'type': g.node[n]['type'],
                'parent': g.node[n]['group'],
            }
        })
    for e in g.edges():
        cy['elements']['edges'].append({
            'data': {
                'id': f'{e[0]}__{e[1]}',
                'source': e[0],
                'target': e[1],
            }
        })
    with open(tmp_path/'graph.json', 'w') as f:
        import json
        f.write(json.dumps(cy))
