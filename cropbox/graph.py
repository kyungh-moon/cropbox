import ast
from astpretty import pprint
from functools import reduce
import inspect
import networkx as nx
import re
import textwrap

from .statevar import drive, flag, statevar, system
from .logger import logger

def write(root, filename):
    g = nx.DiGraph()
    S = root.collect(exclude_self=False)

    def add_node(i, name, alias, cls, system):
        logger.trace(f'id = {i}, name = {name}, alias = {alias}, cls = {cls}, system = {system}')
        g.add_node(i, name=name, alias=alias, cls=cls, system=system)

    def add_edge(si, di, alias, rel):
        logger.trace(f'sid = {si}, did = {di}, alias = {alias}, rel = {rel}')
        g.add_edge(si, di, rel=rel)

    def trackable(s, dn):
        if isinstance(dn, str):
            dns = dn.split('.')
        elif isinstance(dn, list):
            dns = dn
        else:
            return None
        if len(dns) > 1:
            ss = reduce(lambda o, k: o[k], [s] + dns[:-1])
        else:
            ss = s
        dn = dns[-1]
        if dn == 'self':
            return None
        try:
            d = ss._trackable[dn]
            return ss._trackable_data[d]
        except (AttributeError, KeyError):
            #HACK: assume arg supporting state variable
            return None

    def add_edge2(si, s, dn, alias, rel):
        t = trackable(s, dn)
        if t is not None:
            add_edge(si, id(t), alias=alias, rel=rel)

    def visit(s):
        si = id(s)
        sn = s.__class__.__name__
        add_node(si, name=sn, alias=None, cls='System', system=None)
        for v in set(s._trackable.values()):
            n = v.__name__
            vcn = v.__class__.__name__
            va = v._alias_lst
            if isinstance(v, system):
                d = s[n]
                if d is None:
                    continue
                elif isinstance(d, list):
                    [add_edge(si, id(dd), alias=va, rel=n) for dd in d]
                else:
                    add_edge(si, id(d), alias=va, rel=n)
            elif isinstance(v, statevar):
                vi = id(s._trackable_data[v])
                add_node(vi, name=n, alias=va, cls=vcn, system=si)
                fun = v._wrapped_fun
                ps = inspect.signature(fun).parameters
                kw = {}
                for p in ps.values():
                    if p.default is p.empty:
                        dn = p.name
                    else:
                        dn = p.default
                    if trackable(s, dn):
                        kw[p.name] = dn
                    if type(dn) is not str:
                        #TODO: record parameter values?
                        continue
                    add_edge2(vi, s, dn, alias=va, rel='')

                # support inline @drive
                if isinstance(v, drive):
                    try:
                        dn = inspect.getclosurevars(fun).nonlocals['f']
                        add_edge2(vi, s, [dn, n], alias=va, rel='')
                    except KeyError:
                        pass

                # support `prob` var for @flag
                if isinstance(v, flag):
                    if isinstance(v._prob_var, str):
                        add_edge2(vi, s, v._prob_var, alias='', rel='prob')

                # support `init` var
                if isinstance(v._init_var, str):
                    add_edge2(vi, s, v._init_var, alias='', rel='init')
                # support `time` var
                # if isinstance(v._time_var, str):
                #     add_edge2(vi, s, v._time_var, alias='', rel='time')

                src = inspect.getsource(fun)
                src = textwrap.dedent(src)
                m = ast.parse(src)
                class Visitor(ast.NodeVisitor):
                    def __init__(self, kw):
                        self.kw = kw
                    def visit_Attribute(self, node):
                        self.process(node)
                    def visit_Subscript(self, node):
                        self.process(node)
                    def process(self, node):
                        def gather(n):
                            if isinstance(n, ast.Attribute):
                                return gather(n.value) + [n.attr]
                            if isinstance(n ,ast.Subscript):
                                return gather(n.value) + [n.slice.value]
                            elif isinstance(n, ast.Name):
                                return [n.id]
                            elif isinstance(n, ast.Str):
                                return [n.s]
                        l = gather(node)
                        if l[0] in kw:
                            l[0] = kw[l[0]]
                        if trackable(s, l):
                            add_edge2(vi, s, l, alias=va, rel='')
                Visitor(kw).visit(m)
    [visit(s) for s in S]

    #nx.write_graphml(g, f'{filename}.graphml')
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
                'label': g.node[n]['name'],
                #'alias': g.node[n]['alias'],
                'type': g.node[n]['cls'],
                'parent': g.node[n]['system'],
            }
        })
    for e in g.edges():
        cy['elements']['edges'].append({
            'data': {
                'id': f'{e[0]}__{e[1]}',
                'label': g.edges[e]['rel'],
                'source': e[0],
                'target': e[1],
            }
        })
    with open(filename, 'w') as f:
        import json
        f.write(json.dumps(cy))
