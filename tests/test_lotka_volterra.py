from cropbox.system import System
from cropbox.context import instance
from cropbox.statevar import accumulate, parameter

import matplotlib.pyplot as plt

def test_lotka_volterra(tmp_path):
    class S(System):
        @parameter(alias='a')
        def prey_birth_rate(self):
            return 1.0

        @parameter(alias='b')
        def prey_death_rate(self):
            return 0.1

        @parameter(alias='c')
        def predator_death_rate(self):
            return 1.5

        @parameter(alias='d')
        def predator_reproduction_rate(self):
            return 0.75

        @parameter(alias='H0')
        def prey_initial_population(self):
            return 10

        @parameter(alias='P0')
        def predator_initial_population(self):
            return 5

        @accumulate(alias='H', init='H0')
        def prey_population(self, a, b, H, P):
            return a*H - b*H*P

        @accumulate(alias='P', init='P0')
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
    plt.savefig(tmp_path/'lotka_volterra.png')
