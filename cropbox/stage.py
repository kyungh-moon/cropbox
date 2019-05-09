from .system import System
from .statevar import drive, flag, system

class Stage(System):
    phenology = system(alias='pheno')
    temperature = drive('pheno', alias='T')
    optimal_temperature = drive('pheno', alias='T_opt')
    ceiling_temperature = drive('pheno', alias='T_ceil')

    @flag
    def ready(self):
        return False

    @flag
    def over(self):
        return False

    @flag
    def ing(self):
        return self.ready and not self.over
