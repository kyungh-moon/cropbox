from cropbox.system import System
from cropbox.context import instance
from cropbox.statevar import derive, parameter, U

def test_U():
    Q = U.registry.Quantity
    assert U(1) == U('1') == 1
    assert U(1, 'm') == U('1', 'm') == U('1m') == Q(1, 'm')
    assert U(None) == U(None, None) == U(None, 'm') == None
    assert U(1, None) == 1
    assert U(1, '') == Q(1) == Q(1, None) == Q(1, '')
    a = U('1m', 'cm')
    assert a.magnitude == 100 and a.units == Q(1, 'cm').units
    assert U('N') == 'N' != U('1N')
    assert U('abc.def') == 'abc.def'
    assert U(-1) == U('-1') == -1
    assert U(.1) == U('.1') == 0.1

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
    assert s.a == U(2, 'm') and s.b == U(1, 's') and s.c == U(2, 'm/s')

def test_parameter():
    class S(System):
        a = parameter(1, unit='m')
        b = parameter(1, unit='m')
        c = parameter(1, unit='m')
        d = parameter(1, unit='m')
        e = parameter(1)
    s = instance(S, {'S': {'a': 2, 'b': '2', 'c': '2m', 'd': '200cm', 'e': '2m'}})
    assert s.a == s.b == s.c == s.d == s.e == U(2, 'm')
