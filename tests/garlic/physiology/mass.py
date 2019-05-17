from cropbox.statevar import derive, parameter

from .plant import Trait

class Mass(Trait):
    # seed weight g/seed
    @parameter
    def initial_seed(self):
        return 0.275

    #HACK carbon mass of seed is pulled in the reserve
    @derive
    def seed(self):
        return self.initial_seed - self.p.carbon.reserve_from_seed

    @derive
    #def stem(self): # for maize
    def sheath(self): # for garlic
        # dt the addition of C_reserve here only serves to maintain a total for the mass. It could have just as easily been added to total mass.
        # C_reserve is added to stem here to represent soluble TNC, SK
        #return sum([nu.stem.mass for nu in self.p.nodal_units]) + self.p.carbon.reserve
        return sum([nu.sheath.mass for nu in self.p.nodal_units]) + self.p.carbon.reserve

    @derive
    def initial_leaf(self):
        return self.initial_seed * self.p.ratio.initial_leaf

    # this is the total mass of active leaves that are not entirely dead (e.g., dropped).
    # It would be slightly greather than the green leaf mass because some senesced leaf area is included until they are complely aged (dead), SK
    @derive
    def active_leaf(self):
        return sum([nu.leaf.mass for nu in self.p.nodal_units if not nu.leaf.dropped])

    @derive
    def dropped_leaf(self):
        return sum([nu.leaf.mass for nu in self.p.nodal_units if nu.leaf.dropped])

    @derive
    def total_leaf(self):
        # this should equal to activeLeafMass + droppedLeafMass
        return sum([nu.leaf.mass for nu in self.p.nodal_units])

    @derive
    def leaf(self):
        return self.total_leaf

    # for maize

    # @property
    # def ear(self):
    #     return self.p.ear.mass

    # for garlic

    @derive
    def bulb(self):
        return self.p.bulb.mass

    @derive
    def scape(self):
        return self.p.scape.mass

    @derive
    def stalk(self):
        #FIXME inconsistency: stem vs. sheath
        return self.sheath + self.scape

    @derive
    def root(self):
        return self.p.root.mass

    @derive
    def shoot(self):
        # for maize
        #return self.seed + self.stem + self.leaf + self.ear
        # for garlic
        return self.seed + self.stalk + self.leaf + self.bulb

    @derive
    def total(self):
        #HACK include mobilized carbon pool (for more accurate mass under germination)
        #return self.shoot + self.root + self.p.carbon.pool
        return self.shoot + self.root

    # this will only be used for total leaf area adjustment.
    # If the individual leaf thing works out this will be deleted.
    @derive
    def potential_carbon_demand(self, SLA=200):
        # Just a mocking value for now. Need to find a more mechanistic way to simulate change in SLA YY
        # SK 8/20/10: changed it to 200 cm2/g based on data from Kim et al. (2007) EEB
        # units are biomass not carbon
        leaf_mass_demand = self.p.area.potential_leaf_increase / SLA
        # potential_carbon_demand = carbon_demand # for now only carbon demand for leaf is calculated.
        return leaf_mass_demand
