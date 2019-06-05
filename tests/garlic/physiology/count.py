from cropbox.statevar import derive

from .trait import Trait

class Count(Trait):
    @derive
    def total_growing_leaves(self):
        return sum([nu.leaf.growing for nu in self.p.nodal_units])

    @derive
    def total_initiated_leaves(self):
        return self.p.pheno.leaves_initiated

    @derive
    def total_appeared_leaves(self):
        return self.p.pheno.leaves_appeared

    @derive
    def total_mature_leaves(self):
        return sum([nu.leaf.mature for nu in self.p.nodal_units])

    @derive
    def total_dropped_leaves(self):
        return sum([nu.leaf.dropped for nu in self.p.nodal_units])
