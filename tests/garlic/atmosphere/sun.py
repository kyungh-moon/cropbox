# Unit to calculate solar geometry including solar elevation, declination,
#  azimuth etc using TSolar class. Data are hidden. 03/15/00 SK
# - 1st Revision 10/10/00: Changed to dealing only upto the top of the canopy. Radiation transter within the canopy is now a separate module.
# - added functins to calculate global radiation, atmospheric emissivity, etc as in Spitters et al. (1986), 3/18/01, SK
# 24Dec03, SK
# - added a function to calculate day length based on Campbell and Norman (1998) p 170,
# - added overloads to SetVal
# 2Aug04, SK
# - Translated to C++ from Delphi
# - revised some functions according to "An introduction to solar radiaiton" by Iqbal (1983)
# - (To Do) Add algorithms for instantaneous diffuse and direct radiation predictions from daily global solar radiation for given time
# - (To Do) This can be done by first applying sinusoidal model to the daily data to simulate hourly global solar radiation
# - (To Do) Then the division model of diffuse and direct radiations was applied
# - added direct and diffuse separation functions according to Weiss and Norman (1985), 3/16/05

from cropbox.context import instance
from cropbox.system import System
from cropbox.statevar import constant, derive, drive, parameter, system

from numpy import pi, sin, cos, tan, arcsin, arccos, radians, degrees, log, exp

class Location(System):
    latitude = parameter(36)
    longitude = parameter(128)
    altitude = parameter(20)

class Weather(System):
    photosynthetic_active_radiation = parameter(1000, alias='PAR')

class Sun(System):
    # conversion factor from W/m2 to PFD (umol m-2 s-1) for PAR waveband (median 550 nm of 400-700 nm) of solar radiation,
    # see Campbell and Norman (1994) p 149
    # 4.55 is a conversion factor from W to photons for solar radiation, Goudriaan and van Laar (1994)
    # some use 4.6 i.e., Amthor 1994, McCree 1981, Challa 1995.
    PHOTON_UMOL_PER_J = constant(4.6)

    # solar constant, Iqbal (1983)
    #FIXME better to be 1361 or 1362 W/m-2?
    SOLAR_CONSTANT = parameter(1370.0, alias='SC')

    location = system(Location)
    weather = system(Weather)

    # @derive time? -- takes account different Julian day conventions (03-01 vs. 01-01)
    @derive(alias='t', init=None)
    def datetime(self):
        #FIXME: how to drive time variable?
        return self.context.datetime

    @derive(alias='d', init=None)
    def day(self, t):
        #FIXME: properly drive time
        return t.day

    @derive(alias='h', init=None)
    def hour(self, t):
        #FIXME: properly drive time
        return t.hour

    latitude = drive('location', alias='lat') # DO NOT convert to radians for consistency
    longitude = drive('location', alias='long') # leave it as in degrees, used only once for solar noon calculation
    altitude = drive('location', alias='alt') # unit='m'

    photosynthetic_active_radiation = drive('weather', alias='PAR') # unit='umol m-2 s-1'
    transmissivity = parameter(0.5, alias='tau') # atmospheric transmissivity, Goudriaan and van Laar (1994) p 30

    #####################
    # Solar Coordinates #
    #####################

    #HACK always use degrees for consistency and easy tracing
    @derive(alias='dec')
    def declination_angle(self, d):
        #FIXME pascal version of LightEnv uses iqbal()
        return self._declination_angle_spencer

    # Goudriaan 1977
    @derive
    def _declination_angle_goudriaan(self, d):
        g = 2*pi * (d + 10)/365
        return -23.45 * cos(g)

    # Resenberg, blad, verma 1982
    @derive
    def _declination_angle_resenberg(self, d):
        g = 2*pi * (d - 172)/365
        return 23.5 * cos(g)

    # Iqbal (1983) Pg 10 Eqn 1.3.3, and sundesign.com
    @derive
    def _declination_angle_iqbal(self, d):
        g = 2*pi * (d + 284)/365
        return 23.45 * sin(g)

    # Campbell and Norman, p168
    @derive #(unit='degree')
    def _declination_angle_campbell(self, d):
        a = radians(356.6 + 0.9856*d)
        b = radians(278.97 + 0.9856*d + 1.9165*sin(a))
        r = arcsin(0.39785*sin(b))
        return degrees(r)

    # Spencer equation, Iqbal (1983) Pg 7 Eqn 1.3.1. Most accurate among all
    @derive
    def _declination_angle_spencer(self, d):
        # gamma: day angle
        g = 2*pi*(d - 1) / 365
        r = 0.006918 - 0.399912*cos(g) + 0.070257*sin(g) - 0.006758*cos(2*g) + 0.000907*sin(2*g) -0.002697*cos(3*g) + 0.00148*sin(3*g)
        return degrees(r)

    @constant(alias='dph') # (unit='degree')
    def degree_per_hour(self):
        return 360 / 24

    # LC is longitude correction for Light noon, Wohlfart et al, 2000; Campbell & Norman 1998
    @derive(alias='LC')
    def longitude_correction(self, long, dph):
        # standard meridian for pacific time zone is 120 W, Eastern Time zone : 75W
        # LC is positive if local meridian is east of standard meridian, i.e., 76E is east of 75E
        #standard_meridian = -120
        meridian = round(long / dph) * dph
        #FIXME use standard longitude sign convention
        #return (long - meridian) / dph
        #HACK this assumes inverted longitude sign that MAIZSIM uses
        return (meridian - long) / dph

    @derive(alias='ET')
    def equation_of_time(self, d):
        f = radians(279.575 + 0.9856*d)
        return (-104.7*sin(f) + 596.2*sin(2*f) + 4.3*sin(3*f) - 12.7*sin(4*f) \
                -429.3*cos(f) - 2.0*cos(2*f) + 19.3*cos(3*f)) / (60 * 60)

    @derive
    def solar_noon(self, LC, ET):
        return 12 - LC - ET

    @derive
    def _cos_hour_angle(self, angle, latitude, declination_angle):
        # this value should never become negative because -90 <= latitude <= 90 and -23.45 < decl < 23.45
        #HACK is this really needed for crop models?
        # preventing division by zero for N and S poles
        #denom = fmax(denom, 0.0001)
        # sunrise/sunset hour angle
        #TODO need to deal with lat_bound to prevent tan(90)?
        #lat_bound = radians(68)? radians(85)?
        # cos(h0) at cos(theta_s) = 0 (solar zenith angle = 90 deg == elevation angle = 0 deg)
        #return -tan(latitude) * tan(declination_angle)
        w_s = radians(angle) # zenith angle
        p = radians(latitude)
        d = radians(declination_angle)
        return (cos(w_s) - sin(p) * sin(d)) / (cos(p) * cos(d))

    @derive # (unit='degree')
    def hour_angle_at_horizon(self):
        c = self._cos_hour_angle(angle=90)
        # in the polar region during the winter, sun does not rise
        if c > 1:
            return 0
        # white nights during the summer in the polar region
        elif c < -1:
            return 180
        else:
            return degrees(arccos(c))

    @derive
    def half_day_length(self):
        # from Iqbal (1983) p 16
        return self.hour_angle_at_horizon / self.degree_per_hour

    @derive
    def day_length(self):
        return self.half_day_length * 2

    @derive
    def sunrise(self):
        return self.solar_noon - self.half_day_length

    @derive
    def sunset(self):
        return self.solar_noon + self.half_day_length

    @derive
    def hour_angle(self):
        return (self.hour - self.solar_noon) * self.degree_per_hour

    @derive # (unit='degree')
    def elevation_angle(self, hour_angle, declination_angle, latitude):
        #FIXME When time gets the same as solarnoon, this function fails. 3/11/01 ??
        h = radians(hour_angle)
        p = radians(latitude)
        d = radians(declination_angle)
        r = arcsin(cos(h) * cos(d) * cos(p) + sin(d) * sin(p))
        return degrees(r)

    @derive
    def zenith_angle(self):
        return 90 - self.elevation_angle

    # The solar azimuth angle is the angular distance between due South and the
    # projection of the line of sight to the sun on the ground.
    # View point from south, morning: +, afternoon: -
	# See An introduction to solar radiation by Iqbal (1983) p 15-16
	# Also see http://www.susdesign.com/sunangle/index.html
    @derive # (unit='degree')
    def azimuth_angle(self, elevation_angle, declination_angle, latitude):
        d = radians(declination_angle)
        t_s = radians(elevation_angle)
        p = radians(latitude)
        r = arccos((sin(d) - sin(t_s) * sin(p)) / (cos(t_s) * cos(p)))
        return degrees(abs(r))

    ###################
    # Solar Radiation #
    ###################

    # atmospheric pressure in kPa
    @derive
    def atmospheric_pressure(self, altitude):
        try:
            # campbell and Norman (1998), p 41
            return 101.3 * exp(-altitude / 8200)
        except:
            return 100

    @derive
    def optical_air_mass_number(self, elevation_angle):
        t_s = max(0, radians(elevation_angle))
        #FIXME need to do max(0.0001, sin(t_s))?
        try:
            return self.atmospheric_pressure / (101.3 * sin(t_s))
        except:
            return 0

    @derive
    # Campbell and Norman's global solar radiation, this approach is used here
    #TODO rename to insolation?
    def solar_radiation(self, elevation_angle, day, SC):
        t_s = max(0, radians(elevation_angle))
        g = 2*pi*(day - 10) / 365
        return SC * sin(t_s) * (1 + 0.033*cos(g))

    @derive
    def directional_solar_radiation(self):
        return self.directional_coeff * self.solar_radiation

    @derive
    def diffusive_solar_radiation(self):
        return self.diffusive_coeff * self.solar_radiation

    @derive
    def directional_coeff(self, transmissivity, optical_air_mass_number):
        # Goudriaan and van Laar's global solar radiation
        def goudriaan(tau):
            #FIXME should be goudriaan() version
            return tau * (1 - self.diffusive_coeff)
        # Takakura (1993), p 5.11
        def takakura(tau, m):
            return tau**m
        # Campbell and Norman (1998), p 173
        def campbell(tau, m):
            return tau**m
        return campbell(transmissivity, optical_air_mass_number)

    # Fdif: Fraction of diffused light
    @derive
    def diffusive_coeff(self, transmissivity, optical_air_mass_number):
        # Goudriaan and van Laar's global solar radiation
        def goudriaan(tau):
            # clear sky : 20% diffuse
            if tau >= 0.7:
                return 0.2
            # cloudy sky: 100% diffuse
            elif tau <= 0.3:
                return 1
            # inbetween
            else:
                return 1.6 - 2*tau
        # Takakura (1993), p 5.11
        def takakura(tau, m):
            return (1 - tau**m) / (1 - 1.4*log(tau)) / 2
        # Campbell and Norman (1998), p 173
        def campbell(tau, m):
            return (1 - tau**m) * 0.3
        return campbell(transmissivity, optical_air_mass_number)

    @derive
    def directional_fraction(self):
        try:
            return 1 / (1 + self.diffusive_coeff / self.directional_coeff)
        except:
            return 0

    @derive
    def diffusive_fraction(self):
        try:
            return 1 / (1 + self.directional_coeff / self.diffusive_coeff)
        except:
            return 0

    # PARfr
    @derive
    #TODO better naming: extinction? transmitted_fraction?
    def photosynthetic_coeff(self, transmissivity):
        #if self.elevation_angle <= 0:
        #    return 0
        #TODO: implement Weiss and Norman (1985), 3/16/05
        def weiss():
            pass
        # Goudriaan and van Laar (1994)
        def goudriaan(tau):
            # clear sky (tau >= 0.7): 45% is PAR
            if tau >= 0.7:
                return 0.45
            # cloudy sky (<= 0.3): 55% is PAR
            elif tau <= 0.3:
                return 0.55
            else:
                return 0.625 - 0.25*tau
        return goudriaan(transmissivity)

    # PARtot: total PAR (umol m-2 s-1) on horizontal surface
    @derive(alias='PARtot')
    def photosynthetic_active_radiation_total(self, PAR):
        if self.PAR is not None:
            return self.PAR
        else:
            return self.solar_radiation * self.photosynthetic_coeff * self.PHOTON_UMOL_PER_J

    # PARdir
    @derive
    def directional_photosynthetic_radiation(self, PARtot):
        return self.directional_fraction * PARtot

    # PARdif
    @derive
    def diffusive_photosynthetic_radiation(self, PARtot):
        return self.diffusive_fraction * PARtot

def test_sun(tmp_path):
    T = range(24*2)
    def plot(v):
        import datetime
        s = instance(Sun, {'Clock': {
            'unit': 'hour',
            'start_datetime': datetime.datetime(2019, 1, 1),
        }})
        c = s.context
        V = []
        for t in T:
            c.advance()
            V.append(s[v])
        import matplotlib.pyplot as plt
        plt.figure()
        plt.plot(T, V)
        plt.xlabel('time')
        plt.ylabel(v)
        plt.savefig(tmp_path/f'{v}.png')
    plot('declination_angle')
    plot('elevation_angle')
    plot('directional_coeff')
    plot('diffusive_coeff')
    breakpoint()
