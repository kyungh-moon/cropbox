from cropbox.statevar import parameter
from cropbox.system import System

#TODO implement proper soil module
class Soil(System):
    @parameter
    def T_soil(self):
        return 10 # C

    # pressure - leaf water potential MPa...
    @parameter
    def WP_leaf(self):
        return 0

    @parameter
    def total_root_weight(self):
        return 0

    def __str__(self):
        return f'T_soil = {self.T_soil}, WP_leaf = {self.WP_leaf}, total_root_weight = {self.total_root_weight}'
