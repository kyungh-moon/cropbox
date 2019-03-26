import networkx as nx

class Trace:
    def __init__(self):
        self.reset()

    def reset(self):
        self._stack = []
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

    def push(self, v, isolate=False):
        v = [v] if isolate else v
        self.stack.append(v)

    def pop(self):
        v = self.stack.pop()
        def clean():
            if len(self.stack) == 0 and len(self._stack) > 0:
                self._stack.pop()
                clean()
        clean()
        return v

    def __call__(self, var, obj, isolate=False):
        self._mem = (var, obj, isolate)
        return self

    def __enter__(self):
        v, o, i = self._mem
        del self._mem
        try:
            s = self.stack[-1]
            #FIXME: graph should be reset for every update
            self.graph.add_edge(s.__name__, v.__name__)
        except:
            pass
        #TODO: give each System object a name
        #TODO: check dupliate?
        self.graph.add_node(o.__class__.__name__, type='Class', group='')
        self.graph.add_node(v.__name__, type=v.__class__.__name__, group=o.__class__.__name__)
        s = len(self.stack)*' '
        #self.stack.append(v)
        self.push(v, isolate=i)
        #print(f'{s} > {v.__name__}')
        return self

    def __exit__(self, *excs):
        #v = self.stack.pop()
        v = self.pop()
        s = len(self.stack)*' '
        #print(f'{s} < {v.__name__}')

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