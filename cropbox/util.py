def growing_degree_days(T, T_base, T_opt=None, T_max=None):
    if T_opt is not None:
        T = min(T, T_opt)
    if T_max is not None:
        T = T_base if T >= T_max else T
    return max(T - T_base, 0)

def beta_thermal_func(T, T_opt, T_max, T_min=0, beta=1):
    if not T_min < T < T_max:
        return 0
    if not T_min < T_opt < T_max:
        return 0
    # beta function, See Yin et al. (1995), Ag For Meteorol., Yan and Hunt (1999) AnnBot, SK
    T_on = (T_opt - T_min)
    T_xo = (T_max - T_opt)
    f = (T - T_min) / T_on
    g = (T_max - T) / T_xo
    alpha = beta * T_on / T_xo
    return f**alpha * g**beta

def q10_thermal_func(T, T_opt, Q10=2.0):
    return Q10 ** ((T - T_opt) / 10)