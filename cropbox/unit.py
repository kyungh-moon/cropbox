import pint

class Unit:
    def __init__(self):
        r = pint.UnitRegistry(autoconvert_offset_to_baseunit=True)
        r.default_format = '~P'
        #r.setup_matplotlib()
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
        else:
            return Q(v, unit)
U = Unit()
