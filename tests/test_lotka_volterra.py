from cropbox.system import System
from cropbox.context import instance
from cropbox.statevar import accumulate, parameter

import matplotlib.pyplot as plt

def test_lotka_volterra():
    class S(System):
        @parameter(abbr='a')
        def prey_birth_rate(self):
            return 1.0

        @parameter(abbr='b')
        def prey_death_rate(self):
            return 0.1

        @parameter(abbr='c')
        def predator_death_rate(self):
            return 1.5

        @parameter(abbr='d')
        def predator_reproduction_rate(self):
            return 0.75

        @parameter(abbr='H0')
        def prey_initial_population(self):
            return 10

        @parameter(abbr='P0')
        def predator_initial_population(self):
            return 5

        @accumulate(abbr='H', init='H0')
        def prey_population(self, a, b, H, P):
            return a*H - b*H*P

        @accumulate(abbr='P', init='P0')
        def predator_population(self, b, c, d, H, P):
            return d*b*H*P - c*P

    s = instance(S, {'Clock': {'interval': 0.01}})
    c = s.context
    T = range(2000)
    H = []
    P = []
    for t in T:
        c.update()
        #print(f't = {t}: H = {s.prey_population}, P={s.predator_population}')
        H.append(s.prey_population)
        P.append(s.predator_population)
    plt.plot(T, H, label='Prey')
    plt.plot(T, P, label='Predator')
    plt.xlabel('Time')
    plt.ylabel('Population')
    plt.legend()
    #plt.show()
    plt.savefig('lotka_volterra.png')
