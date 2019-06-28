from cropbox.unit import U

class Weight:
    CO2 = U(44.0098, 'g / umol')
    C = U(12.0107, 'g / umol')
    CH2O = U(30.031, 'g / umol')
    H2O = U(18.01528, 'g / umol')

    C_to_CH2O_ratio = C / CH2O # 0.40
