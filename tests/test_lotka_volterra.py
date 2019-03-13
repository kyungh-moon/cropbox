from cropbox.system import System
from cropbox.context import instance
from cropbox.statevar import accumulate, parameter

import matplotlib.pyplot as plt

def test_lotka_volterra():
    class S(System):
        @parameter
        def prey_birth_rate(self):
            return 1.0

        @parameter
        def prey_death_rate(self):
            return 0.1

        @parameter
        def predator_death_rate(self):
            return 1.5

        @parameter
        def predator_reproduction_rate(self):
            return 0.75

        @parameter
        def prey_initial_population(self):
            return 10

        @parameter
        def predator_initial_population(self):
            return 5

        @accumulate(init='prey_initial_population')
        def prey_population(self):
            a = self.prey_birth_rate
            b = self.prey_death_rate
            H = self.prey_population
            P = self.predator_population
            return a*H - b*H*P

        @accumulate(init='predator_initial_population')
        def predator_population(self):
            b = self.prey_death_rate
            c = self.predator_death_rate
            d = self.predator_reproduction_rate
            H = self.prey_population
            P = self.predator_population
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
