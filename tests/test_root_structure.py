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
        @derive
        def elongation_rate(self):
            return random.gauss(1.0, 0.2)

        @static
        def branching_angle(self):
            return random.gauss(20, 10)

        @parameter
        def branching_interval(self):
            return 3.0

        @parameter
        def branching_chance(self):
            return 0.5

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
                    self.branch(R, **{'branched_length': l})
                    return l
            return ll

        def render(self):
            s = trimesh.scene.scene.Scene()
            #TODO: make System's own walker method?
            def visit(r, pn=None):
                l = r.length
                if l == 0:
                    return
                m = trimesh.creation.cylinder(radius=r.diameter, height=l, sections=4)
                if pn is None:
                    m.visual.face_colors = (255, 0, 0, 255)
                # put segment end at origin
                m.apply_translation((0, 0, l/2))
                # put root end at parent's tip
                T1 = trimesh.transformations.translation_matrix((0, 0, -l))
                # rotate root segment along random axis (x: random, y: left or right)
                angle = np.radians(r.branching_angle)
                direction = (random.random(), (random.random() > 0.5) * 2 - 1, 0)
                R = trimesh.transformations.rotation_matrix(angle, direction)
                # put root segment at parent's branching point
                z = 0 if pn is None else r.parent.length - r.branched_length
                T2 = trimesh.transformations.translation_matrix((0, 0, z))
                M = trimesh.transformations.concatenate_matrices(T2, R, T1)
                # add root segment
                n = s.add_geometry(m, parent_node_name=pn, transform=M)
                # visit recursively
                [visit(cr, n) for cr in r.children]
            visit(self)
            s.show()
            return s

    r = instance(R)
    c = r.context
    T = range(50)
    [c.update() for t in T]
    r.render()
