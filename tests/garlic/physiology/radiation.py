# Basic canopy architecture parameters, 10/10/00 S.Kim
# modified to represent heterogeneous canopies
# Uniform continuouse canopy: Width2 = 0
# Hedgerow canopy : Width1 = row width, Width2 = interrow, Height1 = hedge height, Height2 = 0
# Intercropping canopy: Height1, Width1, LA1 for Crop1, and so on
# Rose bent canopy: Height1=Upright canopy, Height2 = bent portion height, 10/16/02 S.Kim

from cropbox.system import System
from cropbox.statevar import constant, derive, parameter, system

from numpy import pi, sin, cos, tan, radians, log, exp, sqrt, array
from enum import Enum

# abscissas
GAUSS3 = [-0.774597, 0, 0.774597]
WEIGHT3 = [0.555556, 0.888889, 0.555556]

# absorptance not explicitly considered here because it's a leaf characteristic not canopy
# Scattering is considered as canopy characteristics and reflectance is computed based on canopy scattering
# 08-20-12, SK

class LeafAngle(Enum):
    spherical = 1
    horizontal = 2
    vertical = 3
    diaheliotropic = 4
    empirical = 5
    ellipsoidal = 6

#HACK not used
class Cover(Enum):
    glass = 1
    acrylic = 2
    polyethyl = 3
    doublepoly = 4
    whitewashed = 5
    no_cover = 6

class WaveBand(Enum):
    photothetically_active_radiation = 1
    near_infrared = 2
    longwave = 3

class Radiation(System):
    sun = system()

    # cumulative LAI at the layer
    @parameter(alias='LAI')
    def leaf_area_index(self):
        return 0

    @parameter
    def leaf_angle(self):
        return LeafAngle.ellipsoidal

    # ratio of horizontal to vertical axis of an ellipsoid
    @parameter(alias='LAF')
    def leaf_angle_factor(self):
        return 1

    @parameter
    def wave_band(self):
        return WaveBand.photothetically_active_radiation

    # scattering coefficient (reflectance + transmittance)
    @parameter(alias='s')
    def scattering(self):
        return 0.15

    # clumping index
    @parameter
    def clumping(self):
        return 1

    #r_h=0.05, #FIXME reflectance?

    # Forward from Sun

    @derive
    def current_zenith_angle(self):
        return self.sun.zenith_angle

    @derive(alias='I0_dr')
    def directional_photosynthetic_radiation(self):
        return self.sun.directional_photosynthetic_radiation

    @derive(alias='I0_df')
    def diffusive_photosynthetic_radiation(self):
        return self.sun.diffusive_photosynthetic_radiation

    # Leaf angle stuff?

    #TODO better name?
    @derive
    def leaf_angle_coeff(self, zenith_angle):
        elevation_angle = 90 - zenith_angle
        #FIXME need to prevent zero like sin_beta / cot_beta?
        a = radians(elevation_angle)
        t = radians(zenith_angle)
        # leaf angle distribution parameter
        x = self.leaf_angle_factor
        return {
            # When Lt accounts for total path length, division by sin(elev) isn't necessary
            LeafAngle.spherical: 1 / (2*sin(a)),
            LeafAngle.horizontal: 1,
            LeafAngle.vertical: 1 / (tan(a) * pi/2),
            LeafAngle.empirical: 0.667,
            LeafAngle.diaheliotropic: 1 / sin(a),
            LeafAngle.ellipsoidal: sqrt(x**2 + tan(t)**2) / (x + 1.774 * (x+1.182)**-0.733),
        }[self.leaf_angle]

    #TODO make it @property if arg is not needed
    # Kb: Campbell, p 253, Ratio of projected area to hemi-surface area for an ellisoid
    #TODO rename to extinction_coeff?
    # extiction coefficient assuming spherical leaf dist
    @derive
    def projection_ratio_at(self, zenith_angle):
        return self.leaf_angle_coeff(zenith_angle) * self.clumping

    @derive(alias='Kb')
    def projection_ratio(self, current_zenith_angle):
        return self.projection_ratio_at(current_zenith_angle)

    # diffused light ratio to ambient, itegrated over all incident angles from -90 to 90
    @constant
    def _angles(self):
        return array([(pi/4) * (g + 1) for g in GAUSS3])

    # diffused fraction (fdf)
    #FIXME name it
    @derive
    def _F(self, x, angles):
        # Why multiplied by 2?
        return ((pi/4) * (2 * x * sin(angles) * cos(angles)) * WEIGHT3).sum()

    # Kd: K for diffuse light, the same literature as above
    @derive(alias='Kd')
    def diffusion_ratio(self, LAI):
        if LAI == 0:
            return 0
        angles = self._angles
        coeffs = array([self.leaf_angle_coeff(a) for a in angles])
        F = self._F(exp(-coeffs * LAI), angles)
        K = -log(F) / LAI
        return K * self.clumping

    ##############################
    # dePury and Farquhar (1997) #
    ##############################

    # Kb1: Kb prime in de Pury and Farquhar(1997)
    @derive(alias='Kb1')
    #TODO better name
    def projection_ratio_prime(self, Kb, s):
        return Kb * sqrt(1 - s)

    # Kd1: Kd prime in de Pury and Farquhar(1997)
    @derive(alias='Kd1')
    #TODO better name
    def diffusion_ratio_prime(self, Kd, s):
        return Kd * sqrt(1 - s)

    ################
    # Reflectivity #
    ################

    @derive
    #TODO better name?
    def reflectivity(self, rho_h, Kb, Kd):
        return rho_h * (2*Kb / (Kb + Kd))

    # canopy reflection coefficients for beam horizontal leaves, beam uniform leaves, and diffuse radiations

    # rho_h: canopy reflectance of beam irradiance on horizontal leaves, de Pury and Farquhar (1997)
    # also see Campbell and Norman (1998) p 255 for further info on potential problems
    @derive(alias='rho_h')
    def canopy_reflectivity_horizontal_leaf(self, s):
        return (1 - sqrt(1 - s)) / (1 + sqrt(1 - s))

    #TODO make consistent interface with siblings
    # rho_cb: canopy reflectance of beam irradiance for uniform leaf angle distribution, de Pury and Farquhar (1997)
    @derive
    def canopy_reflectivity_uniform_leaf_at(self, zenith_angle):
        rho_h = self.canopy_reflectivity_horizontal_leaf
        Kb = self.projection_ratio_at(zenith_angle)
        rho_cb = 1 - exp(-2 * rho_h * Kb / (1 + Kb))
        return rho_cb

    @derive(alias='rho_cb')
    def canopy_reflectivity_uniform_leaf(self, current_zenith_angle):
        return self.canopy_reflectivity_uniform_leaf_at(current_zenith_angle)

    # rho_cd: canopy reflectance of diffuse irradiance, de Pury and Farquhar (1997) Table A2
    @derive(alias='rho_cd')
    def canopy_reflectivity_diffusion(self):
        if self.sun.diffusive_photosynthetic_radiation == 0:
            return 0
        angles = self._angles
        rhos = array([self.canopy_reflectivity_uniform_leaf_at(a) for a in angles])
        # Probably the eqn A21 in de Pury is missing the integration terms of the angles??
        return self._F(rhos, angles)

    # rho_soil: soil reflectivity for PAR band
    @parameter
    def soil_reflectivity(self):
        return 0.10

    #######################
    # I_l?: dePury (1997) #
    #######################

    # I_lb: dePury (1997) eqn A3
    @derive(alias='I_lb')
    def irradiance_lb(self, L):
        I0_dr = self.sun.directional_photosynthetic_radiation
        rho_cb = self.canopy_reflectivity_uniform_leaf
        Kb1 = self.projection_ratio_prime
        return I0_dr * (1 - rho_cb) * Kb1 * exp(-Kb1 * L)

    # I_ld: dePury (1997) eqn A5
    @derive(alias='I_ld')
    def irradiance_ld(self, L):
        I0_df = self.sun.diffusive_photosynthetic_radiation
        rho_cb = self.canopy_reflectivity_uniform_leaf
        Kd1 = self.diffusion_ratio_prime
        return I0_df * (1 - rho_cb) * Kd1 * exp(-Kd1 * L)

    # I_l: dePury (1997) eqn A5
    @derive(alias='I_l')
    def irradiance_l(self, L):
        return self.irradiance_lb(L) + self.irradiance_ld(L)

    # I_lbSun: dePury (1997) eqn A5
    @derive
    def irradiance_l_sunlit(self, L):
        I0_dr = self.sun.directional_photosynthetic_radiation
        s = self.scattering
        Kb = self.projection_ratio
        I_lb_sunlit = I0_dr * (1 - s) * Kb
        I_l_sunlit = I_lb_sunlit + self.irradiance_l_shaded(L)
        return I_l_sunlit

    # I_lSH: dePury (1997) eqn A5
    @derive
    def irradiance_l_shaded(self, L):
        return self.irradiance_ld(L) + self.irradiance_lbs(L)

    # I_lbs: dePury (1997) eqn A5
    @derive(alias='I_lbs')
    def irradiance_lbs(self, L):
        I0_dr = self.sun.directional_photosynthetic_radiation
        rho_cb = self.canopy_reflectivity_uniform_leaf
        s = self.scattering
        Kb1 = self.projection_ratio_prime
        Kb = self.projection_ratio
        return I0_dr * ((1 - rho_cb) * Kb1 * exp(-Kb1 * L) - (1 - s) * Kb * exp(-Kb * L))

    # I0tot: total irradiance at the top of the canopy,
    # passed over from either observed PAR or TSolar or TIrradiance
    @derive
    def irradiance_I0_tot(self):
        I0_dr = self.sun.directional_photosynthetic_radiation
        I0_df = self.sun.diffusive_photosynthetic_radiation
        return I0_dr + I0_df

    ########
    # I_c? #
    ########

    # I_tot, I_sun, I_shade: absorved irradiance integrated over LAI per ground area

    # I_c: Total irradiance absorbed by the canopy, de Pury and Farquhar (1997)
    @derive
    def canopy_irradiance(self, rho_cb, I0_dr, I0_df, Kb1, Kd1, LAI):
        #I_c = self.canopy_sunlit_irradiance + self.canopy_shaded_irradiance
        def I(I0, K):
            return ((1 - rho_cb) * I0 * (1 - exp(-K * LAI))).sum()
        I_tot = I(I0_dr, Kb1) + I(I0_df, Kd1)
        return I_tot

    # I_cSun: The irradiance absorbed by the sunlit fraction, de Pury and Farquhar (1997)
    # should this be the same os Qsl? 03/02/08 SK
    @derive
    def canopy_sunlit_irradiance(self, s, rho_cb, rho_cd, I0_dr, I0_df, Kb, Kb1, Kd1, LAI):
        I_c_sunlit = \
            I0_dr * (1 - s) * (1 - exp(-Kb * LAI)) + \
            I0_df * (1 - rho_cd) * (1 - exp(-(Kd1 + Kb) * LAI)) * Kd1 / (Kd1 + Kb) + \
            I0_dr * ((1 - rho_cb) * (1 - exp(-(Kb1 + Kb) * LAI)) * Kb1 / (Kb1 + Kb) - (1 - s) * (1 - exp(-2*Kb * LAI)) / 2)
        return I_c_sunlit

    # I_cSh: The irradiance absorbed by the shaded fraction, de Pury and Farquhar (1997)
    @derive
    def canopy_shaded_irradiance(self):
        I_c = self.canopy_irradiance
        I_c_sunlit = self.canopy_sunlit_irradiance
        I_c_shaded = I_c - I_c_sunlit
        return I_c_shaded

    ######
    # Q? #
    ######

    # @derive
    # def sunlit_photon_flux_density(self):
    #     return self._sunlit_Q
    #
    # @derive
    # def shaded_photon_flux_density(self):
    #     return self._shaded_Q

    # Qtot: total irradiance (dir + dif) at depth L, simple empirical approach
    @derive
    def irradiance_Q_tot(self, L):
        I0_tot = self.irradiance_I0_tot
        s = self.scattering
        Kb = self.projection_ratio
        Kd = self.diffusion_ratio
        Q_tot = I0_tot * exp(-sqrt(1 - s) * ((Kb + Kd) / 2) * L)
        return Q_tot

    # Qbt: total beam radiation at depth L
    @derive
    def irradiance_Q_bt(self, L):
        I0_dr = self.sun.directional_photosynthetic_radiation
        s = self.scattering
        Kb = self.projection_ratio
        Q_bt = I0_dr * exp(-sqrt(1 - s) * Kb * L)
        return Q_bt

    # net diffuse flux at depth of L within canopy
    @derive
    def irradiance_Q_d(self, L):
        I0_df = self.sun.diffusive_photosynthetic_radiation
        s = self.scattering
        Kd = self.diffusion_ratio
        Q_d = I0_df * exp(-sqrt(1 - s) * Kd * L)
        return Q_d

    # weighted average absorved diffuse flux over depth of L within canopy
    # accounting for exponential decay, Campbell p261
    @derive
    def irradiance_Q_dm(self, LAI):
        if LAI > 0:
            # Integral Qd / Integral L
            I0_df = self.sun.diffusive_photosynthetic_radiation
            s = self.scattering
            Kd = self.diffusion_ratio
            Q_dm = I0_df * (1 - exp(-sqrt(1 - s) * Kd * LAI)) / (sqrt(1 - s) * Kd * LAI)
        else:
            Q_dm = 0
        return Q_dm

    # unintercepted beam (direct beam) flux at depth of L within canopy
    @derive
    def irradinace_Q_b(self, L):
        I0_dr = self.sun.directional_photosynthetic_radiation
        Kb = self.projection_ratio
        Q_b = I0_dr * exp(-Kb * L)
        return Q_b

    # mean flux density on sunlit leaves
    @derive
    def irradiance_Q_sunlit(self, I0_dr, Kb):
        return I0_dr * Kb + self.irradiance_Q_shaded

    # flux density on sunlit leaves at delpth L
    @derive
    def irradiance_Q_sunlit_at(self, L, *, I0_dr, Kb):
        return I0_dr * Kb + self.irradiance_Q_shaded(L)

    # mean flux density on shaded leaves over LAI
    @derive
    def irradiance_Q_shaded(self):
        # It does not include soil reflection
        return self.irradiance_Q_dm + self.irradiance_Q_scm

    # diffuse flux density on shaded leaves at depth L
    @derive
    def irradiance_Q_shaded_at(self, L):
        # It does not include soil reflection
        return self.irradiance_Q_d(L) + self.irradiance_Q_sc(L)

    # weighted average of Soil reflectance over canopy accounting for exponential decay
    @derive
    def irradiance_Q_soilm(self, LAI):
        if LAI > 0:
            # Integral Qd / Integral L
            rho_soil = self.soil_reflectivity
            s = self.scattering
            Kd = self.diffusion_ratio
            Q_soil = self.irradiance_Q_soil
            Q_soilm = Q_soil * rho_soil * (1 - exp(-sqrt(1 - s) * Kd * LAI)) / (sqrt(1 - s) * Kd * LAI)
        else:
            Q_soilm = 0
        return Q_soilm

    # weighted average scattered radiation within canopy
    @derive
    def irradiance_Q_scm(self, LAI):
        if LAI > 0:
            # Integral Qd / Integral L
            rho_soil = self.soil_reflectivity
            s = self.scattering
            Kd = self.diffusion_ratio
            Q_soil = self.irradiance_Q_soil
            Q_soilm = Q_soil * rho_soil * (1 - exp(-sqrt(1 - s) * Kd * LAI)) / (sqrt(1 - s) * Kd * LAI)

            I0_dr = self.sun.directional_photosynthetic_radiation
            s = self.scattering
            Kb = self.projection_ratio

            # total beam including scattered absorbed by canopy
            #FIXME should the last part be multiplied by LAI like others?
            total_beam = I0_dr * (1 - exp(-sqrt(1 - s) * Kb * LAI)) / (sqrt(1 - s) * Kb)
            # non scattered beam absorbed by canopy
            nonscattered_beam = I0_dr * (1 - exp(-Kb * LAI)) / Kb
            Q_scm = (total_beam - nonscattered_beam) / LAI
            # Campbell and Norman (1998) p 261, Average between top (where scattering is 0) and bottom.
            #Q_scm = (self.irradiance_Q_bt(LAI) - self.irradiance_Q_b(LAI)) / 2
        else:
            Q_scm = 0
        return Q_scm

    # scattered radiation at depth L in the canopy
    @derive
    def irradiance_Q_sc(self, L):
        Q_bt = self.irradiance_Q_bt(L)
        Q_b = self.irradiance_Q_b(L)
        # total beam - nonscattered beam at depth L
        return Q_bt - Q_b

    # total PFD at the soil sufrace under the canopy
    @derive
    def irradiance_Q_soil(self, LAI):
        return self.irradiance_Q_tot(LAI)

    ###################
    # Leaf Area Index #
    ###################

    # sunlit LAI assuming closed canopy; thus not accurate for row or isolated canopy
    @derive
    def sunlit_leaf_area_index(self):
        if self.sun.elevation_angle <= 5:
            return 0
        else:
            Kb = self.projection_ratio
            LAI = self.leaf_area_index
            return (1 - exp(-Kb * LAI)) / Kb

    # shaded LAI assuming closed canopy
    @derive
    def shaded_leaf_area_index(self):
        return self.leaf_area_index - self.sunlit_leaf_area_index

    # sunlit fraction of current layer
    @derive
    def sunlit_fraction(self, L):
        if self.sun.elevation_angle <= 5:
            return 0
        else:
            Kb = self.projection_ratio
            return exp(-Kb * L)

    @derive
    def shaded_fraction(self, L):
        return 1 - self.sunlit_fraction(L)
