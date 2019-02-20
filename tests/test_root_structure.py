from . import context

from cropbox.system import System
from cropbox.context import Context
from cropbox.statevar import accumulate, derive, parameter, static

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

import random
import trimesh
import numpy as np

def test_root_structure(instance):
    class R(System):
        @accumulate
        def age(self):
            return 1.0

        @derive
        def elongation_rate(self):
            # if self.age > 10:
            #     return 0.2
            #return 1.0
            return random.gauss(1.0, 0.2)

        @static
        def branching_angle(self):
            #return 30
            return random.gauss(30, 10)

        @parameter
        def branching_interval(self):
            return 5.0

        @parameter
        def branching_chance(self):
            #return 1
            return 0.5

        @parameter
        def branching_zone(self):
            #return 1.0
            return 0

        @derive
        def branched_length(self):
            return 0

        @parameter
        def diameter(self):
            return 0.1

        @accumulate
        def length(self):
            return self.elongation_rate

        #TODO: need own decorator for branching actions?
        @derive
        def last_branching_length(self):
            l = self.length
            ll = self.last_branching_length
            if l - ll > self.branching_interval:
                if random.random() <= self.branching_chance:
                    print(f'branch at l = {l}')
                    self.branch(R, **{'branched_length': l - self.branching_zone})
                    return l
            return ll

        def render(self):
            s = trimesh.scene.scene.Scene()
            #TODO: make System's own walker method
            def visit(r, pn=None):
                if r.length == 0:
                    return
                m = trimesh.creation.cylinder(radius=r.diameter, height=r.length)
                if pn is None:
                    m.visual.face_colors = (255, 0, 0, 255)
                #m.apply_translation((0, 0, -r.length/2 + r.branching_zone))
                m.apply_translation((0, 0, -r.length/2))
                y = (random.random() > 0.5) * 2 - 1
                R = trimesh.transformations.rotation_matrix(angle=np.radians(r.branching_angle), direction=(0, y, 0))
                #T = trimesh.transformations.translation_matrix((0, 0, r.length - r.branching_zone))
                T = trimesh.transformations.translation_matrix((0, 0, r.length))
                if pn is None:
                    T2 = trimesh.transformations.translation_matrix((0, 0, 0))
                else:
                    T2 = trimesh.transformations.translation_matrix((0, 0, -r.parent.length + r.branched_length))
                M = trimesh.transformations.concatenate_matrices(T2, R, T)

                n = s.add_geometry(m, parent_node_name=pn, transform=M)
                for cr in r.children:
                    visit(cr, n)
            visit(self)
            s.show()
            return s

    r = instance(R)
    c = r.context
    T = range(50)
    H = []
    P = []
    for t in T:
        c.update()
    r.render()
    breakpoint()
