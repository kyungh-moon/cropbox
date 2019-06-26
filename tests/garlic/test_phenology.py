from cropbox.context import instance

from .phenology.phenology import Phenology
from .physiology.plant import Plant

import datetime
import os

config={
    'Clock': {
        'unit': 'day',
        'start_datetime': datetime.datetime(2007, 10, 1),
    },
    'Weather': {
        'filename': os.path.dirname(__file__) + '/data/2007.wea',
        'timezone': 'Asia/Seoul',
    }
}

p = instance(Phenology, config)
for i in range(10):
    print(f't = {p.context.time}, rate = {p.germination.rate}, over = {p.germination.over}')
    p.context.advance()

p = instance(Plant, config)
p.context.advance()
breakpoint()
