from cropbox.system import System
from cropbox.context import instance
from cropbox.statevar import accumulate, derive, difference, drive, optimize, parameter, signal, statevar

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
    c.update()
    assert s.a == 1 and s.b == 2
    c.update()
    assert s.a == 1 and s.b == 4
    c.update()
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
    c.update()
    assert s.a == 1 and s.b == 1
    c.update()
    assert s.a == 3 and s.b == 3
    c.update()
    assert s.a == 7 and s.b == 7

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
    c.update()
    assert s.a == 1 and s.b == 1
    c.update()
    assert s.a == 1 and s.b == 2
    c.update()
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
    c.update()
    assert s.a == 0 and s.b == 10 and s.c == 0
    c.update()
    assert s.a == 0 and s.b == 0 and s.c == 10
    c.update()
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
    assert s.s == 100 and s.d1 == 0 and s.d2 == 0 and s.d3 == 0
    c.update()
    assert s.s == 200 and s.d1 == 20 and s.d2 == 30 and s.d3 == 50
    c.update()
    assert s.s == 300 and s.d1 == 60 and s.d2 == 90 and s.d3 == 150
    c.update()
    assert s.s == 400 and s.d1 == 120 and s.d2 == 180 and s.d3 == 300

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
    c.update()
    assert s.a == 1 and s.b == 2
    c.update()
    assert s.a == 1 and s.b == 2
    c.update()
    assert s.a == 1 and s.b == 2

def test_signal():
    class S(System):
        @derive
        def a(self):
            return 1
        @accumulate
        def b(self):
            return self.a + 1
        @signal
        def sa(self):
            return self.a
        @signal
        def sb(self):
            return self.b
    s = instance(S)
    c = s.context
    assert s.a == 1 and s.b == 0
    assert s.sa == 1 and s.sb == 0
    c.update()
    assert s.a == 1 and s.b == 2
    assert s.sa == 0 and s.sb == 2
    c.update()
    assert s.a == 1 and s.b == 4
    assert s.sa == 0 and s.sb == 4

def test_parameter():
    class S(System):
        @parameter
        def a(self):
            return 1
    s = instance(S)
    c = s.context
    assert s.a == 1
    c.update()
    assert s.a == 1

def test_parameter_with_config():
    class S(System):
        @parameter
        def a(self):
            return 1
    s = instance(S, {'S': {'a': 2}})
    c = s.context
    assert s.a == 2
    c.update()
    assert s.a == 2

def test_drive_with_dict():
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
    assert c.time == 1 and s.a == 10
    c.update()
    assert c.time == 2 and s.a == 20
    c.update()
    assert c.time == 3 and s.a == 30

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

def test_clock():
    class S(System):
        pass
    s = instance(S)
    c = s.context
    assert c.time == 0
    c.update()
    assert c.time == 1
    c.update()
    assert c.time == 2

def test_clock_with_config():
    class S(System):
        pass
    s = instance(S, {'Clock': {'start': 5, 'interval': 10}})
    c = s.context
    assert c.time == 5
    c.update()
    assert c.time == 15
    c.update()
    assert c.time == 25

def test_abbr():
    class S(System):
        @derive(abbr='aa')
        def a(self):
            return 1
        @derive(abbr='bb,bbb')
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
        @derive(abbr='a')
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
    s = instance(S)
    assert s.a == s.b == s.c == s.d == 1

def test_inline():
    class S(System):
        a = derive(1)
        b = derive(2, abbr='c')
    s = instance(S)
    assert s.a == 1
    assert s.b == s.c == 2

def test_plot():
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

def test_cytoscape():
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
    #nx.write_graphml(g, 'cy.graphml')
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
    with open('cy.json', 'w') as f:
        import json
        f.write(json.dumps(cy))
