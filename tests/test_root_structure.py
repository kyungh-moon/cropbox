from cropbox.system import System
from cropbox.context import instance
from cropbox.statevar import accumulate, constant, derive, flag, parameter, produce
from cropbox.unit import U

import random
import trimesh
import numpy as np

def test_root_structure(tmp_path):
    class R(System):
        @derive(unit='cm / 1')
        def elongation_rate(self):
            return random.gauss(1.0, 0.2)

        @constant(unit='deg')
        def branching_angle(self):
            return random.gauss(20, 10)

        @parameter(unit='cm')
        def branching_interval(self):
            return 3.0

        @parameter
        def branching_chance(self):
            return 0.5

        @flag(prob='branching_chance')
        def is_branching(self, l='length', ll='last_branching_length', i='branching_interval'):
            return l - ll > i

        @constant(unit='cm')
        def branched_length(self):
            return None

        @parameter(unit='cm')
        def diameter(self):
            return 0.1

        @accumulate(unit='cm')
        def length(self):
            return self.elongation_rate

        @derive(unit='cm')
        def last_branching_length(self):
            if self.is_branching:
                return self.length

        @produce
        def branch(self):
            if self.is_branching:
                l = self.length
                print(f'branch at l = {l}')
                return (R, {'branched_length': l})

        def render(self):
            s = trimesh.scene.scene.Scene()
            #TODO: make System's own walker method?
            def visit(r, pn=None):
                l = U.magnitude(r.length, 'cm')
                if l == 0:
                    return
                m = trimesh.creation.cylinder(radius=U.magnitude(r.diameter, 'cm'), height=l, sections=4)
                if pn is None:
                    m.visual.face_colors = (255, 0, 0, 255)
                # put segment end at origin
                m.apply_translation((0, 0, l/2))
                # put root end at parent's tip
                T1 = trimesh.transformations.translation_matrix((0, 0, -l))
                # rotate root segment along random axis (x: random, y: left or right)
                angle = U.magnitude(r.branching_angle, 'rad')
                direction = (random.random(), (random.random() > 0.5) * 2 - 1, 0)
                R = trimesh.transformations.rotation_matrix(angle, direction)
                # put root segment at parent's branching point
                z = 0 if pn is None else U.magnitude(r.parent.length - r.branched_length, 'cm')
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
    T = range(30)
    [c.advance() for t in T]
    r.render()

    from cropbox.graph import transform, write
    write(transform(r), tmp_path/'root.json')
