import networkx as nx

from .logger import logger

class Trace:
    def __init__(self):
        self.reset()

    def reset(self, build_graph=False):
        self._stack = []
        self._regime = ['']
        self.build_graph = build_graph
        if self.build_graph:
            self.graph = nx.DiGraph()

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
        return count(self._stack) * ' '

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

    def __call__(self, var, obj, regime=None):
        self._mem = (var, obj, regime)
        return self

    def __enter__(self):
        v, o, r = self._mem
        del self._mem
        try:
            s = self.stack[-1]
            if self.build_graph:
                #FIXME: graph should be reset for every update
                self.graph.add_edge(s.__name__, v.__name__)
        except:
            pass
        if self.build_graph:
            #TODO: give each System object a name
            #TODO: check dupliate?
            self.graph.add_node(o.__class__.__name__, type='Class', group='')
            self.graph.add_node(v.__name__, type=v.__class__.__name__, group=o.__class__.__name__)
        s = self.indent
        #self.stack.append(v)
        self.push(v, regime=r)
        logger.trace(f'{s*2}> {v.__name__} ({r}) - {self._stack}')
        return self

    def __exit__(self, *excs):
        #v = self.stack.pop()
        v = self.pop()
        s = self.indent
        #logger.trace(f'{s}< {v.__name__} - {self._stack}')

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
