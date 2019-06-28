from cropbox.statevar import derive

from .trait import Trait

class Area(Trait):
    @derive(unit='cm^2')
    def leaf(self):
        return sum([nu.leaf.area for nu in self.p.nodal_units])

    @derive(unit='cm^2')
    def green_leaf(self):
        return sum([nu.leaf.green_area for nu in self.p.nodal_units])

    #TODO remove if unnecessary
    # @derive
    # def active_leaf_ratio(self):
    #     return self.green_leaf / self.leaf

    @derive(unit='cm^2 / m^2')
    def leaf_area_index(self):
        return self.green_leaf * self.p.planting_density / 100**2

    # actualgreenArea is the green area of leaf growing under carbon limitation
	#SK 8/22/10: There appears to be no distinction between these two variables in the code.
    @derive(unit='cm^2')
    def actual_green_leaf(self):
        return self.green_leaf

    @derive(unit='cm^2')
    def senescent_leaf(self):
        return sum([nu.leaf.senescent_area for nu in self.p.nodal_units])

    @derive(unit='cm^2')
    def potential_leaf(self):
        return sum([nu.leaf.potential_area for nu in self.p.nodal_units])

    @derive(unit='cm^2')
    def potential_leaf_increase(self):
        return sum([nu.leaf.potential_area_increase for nu in self.p.nodal_units])

    # calculate relative area increases for leaves now that they are updated
    #TODO remove if unnecessary
    # @derive
    # def relative_leaf_increase(self):
    #     return sum([nu.leaf.relative_area_increase for nu in self.p.nodal_units])

    #FIXME it doesn't seem to be 'actual' dropped leaf area
    # calculated dropped leaf area YY
    @derive(unit='cm^2')
    def dropped_leaf(self):
        return self.potential_leaf - self.green_leaf
