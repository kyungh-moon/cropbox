import pint

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

def clip(v, lower=None, upper=None):
    if lower is not None:
        v = max(v, lower)
    if upper is not None:
        v = min(v, upper)
    return v
