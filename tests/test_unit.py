from . import context

from cropbox.system import System
from cropbox.context import instance
from cropbox.statevar import derive, Q

def test_unit():
    class S(System):
        @derive(unit='m')
        def a(self):
            return 2
        @derive(unit='s')
        def b(self):
            return 1
        @derive(unit='m/s')
        def c(self):
            return self.a / self.b
    s = instance(S)
    assert s.a == Q(2, 'm') and s.b == Q(1, 's') and s.c == Q(2, 'm/s')
