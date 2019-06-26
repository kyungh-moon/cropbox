from cropbox.context import instance

from .phenology.phenology import Phenology
from .physiology.plant import Plant

import datetime
import os

config={
    'Clock': {
        'unit': 'hour',
        'start_datetime': datetime.datetime(2007, 10, 1),
    },
    'Weather': {
        'filename': os.path.dirname(__file__) + '/data/2007.wea',
        'timezone': 'Asia/Seoul',
    }
}

p = instance(Phenology, config)
for i in range(30):
    print(f't = {p.context.time}, rate = {p.germination.rate}, over = {p.germination.over}')
    p.context.advance()

p = instance(Plant, config)
for i in range(300):
    print(f't = {p.context.datetime}')
    p.context.advance()
breakpoint()
