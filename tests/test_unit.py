from . import context

from cropbox.system import System
from cropbox.context import Context
from cropbox.statevar import derive, Q

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

def test_unit(instance):
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
