import pint
import numpy as np

class Unit:
    def __init__(self):
        r = pint.UnitRegistry(autoconvert_offset_to_baseunit=True)
        r.default_format = '~P'
        #r.setup_matplotlib()
        r.define('percent = 0.01*count')
        r.define('Carbon = []')
        r.define('Nitrogen = []')
        r.define('H2O = []')
        r.define('CO2 = []')
        r.define('O2 = []')
        r.define('CH2O = []')
        r.define('Quanta = []')
        r.define('Electron = []')
        self.registry = r

    def __call__(self, v, unit=None):
        if v is None:
            return v
        try:
            #HACK: avoid collision (variable named 'm' vs. unit string 'm')
            if not v[0].isalpha():
                v = self.registry(v)
        except:
            pass
        if unit is None:
            return v
        Q = self.registry.Quantity
        if isinstance(v, Q):
            return v.to(unit)
        elif callable(v):
            return lambda *a, **k: U(v(*a, **k), unit)
        else:
            return Q(v, unit)

    def __getitem__(self, v):
        try:
            return v.units
        except AttributeError:
            return None

    def magnitude(self, v, unit=None):
        Q = self.registry.Quantity
        if isinstance(v, Q):
            if unit:
                v = v.to(unit)
            return v.magnitude
        else:
            return v

U = Unit()

def clip(v, lower=None, upper=None, unit=None):
    if unit is None:
        if isinstance(v, U.registry.Quantity):
            unit = v.units
    if lower is not None:
        v = max(U(v, unit), U(lower, unit))
    if upper is not None:
        v = min(U(v, unit), U(upper, unit))
    return v

#TODO: replace with `Q.from_list()` when new version of pint gets released
def array(a, unit=None, **kwargs):
    if unit is None:
        v = a[0]
        if isinstance(v, U.registry.Quantity):
            unit = v.units
    return U(np.array([U.magnitude(v, unit) for v in a]), unit)
