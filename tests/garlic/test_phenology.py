from cropbox.context import instance

from .phenology.phenology import Phenology
from .physiology.plant import Plant

config = ''
p = instance(Phenology, config)

for i in range(10):
    print(f't = {p.context.time}, rate = {p.germination.rate}, over = {p.germination.over}')
    p.context.advance()

p = instance(Plant, config)
breakpoint()
