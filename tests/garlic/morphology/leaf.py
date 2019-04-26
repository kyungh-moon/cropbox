from cropbox.context import instance
from cropbox.system import System
from cropbox.statevar import accumulate, constant, derive, difference, drive, flag, parameter, system

from numpy import clip, exp, sqrt

class Leaf(Systme):
    rank = constant(None)

    # cm dd-1 Fournier and Andrieu 1998 Pg239.
    # This is the "potential" elongation rate with no water stress Yang
    # @property
    # def elongation_rate(self):
    #     return 0.564

    # max elongation rate (cm per day) at optipmal temperature
    # (Topt: 31C with Tbase = 9.8C using 0.564 cm/dd rate from Fournier 1998 paper above
    @parameter(alias='LER')
    def maximum_elongation_rate(self):
        return 12.0

    @parameter(alias='LM_min')
    def minimum_length_of_longest_leaf(self):
        return 60.0

    # leaf lamina width to length ratio
    @parameter
    def length_to_width_ratio(self):
        #return 0.106 # for maize
        return 0.05 # for garlic

    # leaf area coeff with respect to L*W (A_LW)
    @parameter
    def area_ratio(self):
        return 0.75

    # staygreen trait of the hybrid
    # stay green for this value times growth period after peaking before senescence begins
    # An analogy for this is that with no other stresses involved,
    # it takes 15 years to grow up, stays active for 60 years,
    # and age the last 15 year if it were for a 90 year life span creature.
    # Once fully grown, the clock works differently so that the hotter it is quicker it ages
    @parameter
    def stay_green(self):
        return 3.5

    @parameter
    def aging_rate(self):
        return self.maximum_elongation_rate

    #############
    # Variables #
    #############

    #FIXME
    @derive
    def potential_leaves(self):
        return self.p.pheno.leaves_potential

    #FIXME
    @derive
    def extra_leaves(self):
        return self.p.pheno.leaves_potential - self.p.pheno.leaves_generic

    @derive(alias='maximum_length')
    def maximum_length_of_longest_leaf(self, LM_min, extra_leaves, k=0):
        # no length adjustment necessary for garlic, unlike MAIZE (KY, 2016-10-12)
        #k = 0 # 24.0
        return sqrt(LM_min**2 + k * extra_leaves)

    @derive
    def maximum_width(self):
        # Fournier and Andrieu(1998) Pg242 YY
        return self.maximum_length * self.length_to_width_ratio

    @derive
    def maximum_area(self):
        # daughtry and hollinger (1984) Fournier and Andrieu(1998) Pg242 YY
        return self.maximum_length * self.maximum_width * self.area_ratio

    @derive
    def area_from_length(self, length):
        #HACK ensure zero area for zero length
        if length == 0:
            return 0
        else:
            # for garlic, see JH's thesis
            return 0.639945 + 0.954957*length + 0.005920*length**2

    @derive
    def area_increase_from_length(self, length):
        # for garlic, see JH's thesis
        return 0.954957 + 2*0.005920*length

    #TODO better name, shared by growth_duration and pontential_area
    #TODO should be a plant parameter not leaf (?)
    @derive
    def rank_effect(self, potential_leaves, rank, weight=1):
        l = potential_leaves
        n_m = 5.93 + 0.33 * l # the rank of the largest leaf. YY
        a = (-10.61 + 0.25 * l) * weight
        b = (-5.99 + 0.27 * l) * weight
        # equation 7 in Fournier and Andrieu (1998). YY

        # equa 8(b)(Actually eqn 6? - eqn 8 deals with leaf age - DT)
        # in Fournier and Andrieu(1998). YY
        scale = rank / n_m - 1
        return exp(a * scale**2 + b * scale**3)

    @derive
    def potential_length(self):
        # for MAIZSIM
        #return self.maximum_length * self.rank_effect(weight=0.5)
        # for beta fn calibrated from JH's thesis for SP and KM varieties, 8/10/15, SK
        #FIXME: leaves_potential is already max(leaves_generic, leaves_total)?
        n = max(self.p.pheno.leaves_potential, self.p.pheno.leaves_generic)
        l_t = 1.64 * n
        l_pk = 0.88 * n
        #TODO make BetaFunc generic for non-temperature use
        #HACK BetaFunc.create() inefficient since registry signature keeps changing
        return BetaFunc._calc(T=self.rank, R_max=self.maximum_length, T_opt=l_pk, T_max=l_t)

    # from CLeaf::calc_dimensions()
    # LM_min is a length characteristic of the longest leaf,in Fournier and Andrieu 1998, it was 90 cm
    # LA_max is a fn of leaf no (Birch et al, 1998 fig 4) with largest reported value near 1000cm2. This is implemented as lfno_effect below, SK
    # LM_min of 115cm gives LA of largest leaf 1050cm2 when totalLeaves are 25 and Nt=Ng, SK 1-20-12
    # Without lfno_effect, it can be set to 97cm for the largest leaf area to be at 750 cm2 with Nt ~= Ng (Lmax*Wmax*0.75) based on Muchow, Sinclair, & Bennet (1990), SK 1-18-2012
    # Eventually, this needs to be a cultivar parameter and included in input file, SK 1-18-12
    # the unit of k is cm^2 (Fournier and Andrieu 1998 Pg239). YY
    # L_max is the length of the largest leaf when grown at T_peak. Here we assume LM_min is determined at growing Topt with minmal (generic) leaf no, SK 8/2011
    # If this routine runs before TI, totalLeaves = genericLeafNo, and needs to be run with each update until TI and total leaves are finalized, SK
    @derive
    def growth_duration(self):
        # shortest possible linear phase duration in physiological time (days instead of GDD) modified
        days = self.potential_length / self.maximum_elongation_rate
        # for garlic
        return 1.5 * days

    @derive
    def phase1_delay(self, rank):
        # not used in MAIZSIM because LTAR is used to initiate leaf growth.
        # Fournier's value : -5.16+1.94*rank;equa 11 Fournier and Andrieu(1998) YY, This is in plastochron unit
        return max(0, -5.16 + 1.94 * rank)

    @derive
    def leaf_number_effect(self, potential_leaves):
        # Fig 4 of Birch et al. (1998)
        return clip(exp(-1.17 + 0.047 * potential_leaves), 0.5, 1.0)

    @derive
    def potential_area(self):
        # for MAIZSIM
        # equa 6. Fournier and Andrieu(1998) multiplied by Birch et al. (1998) leaf no effect
        # LA_max the area of the largest leaf
        # PotentialArea potential final area of a leaf with rank "n". YY
        #return self.maximum_area * self.leaf_number_effect * self.rank_effect(weight=1)
        # for garlic
        return self.area_from_length(self.potential_length)

    @derive
    def green_ratio(self):
        return 1 - self.senescence_ratio

    @derive
    def green_area(self):
        return self.green_ratio * self.area

    @accumulate
    def elongation_age(self): #TODO add td in the args
        #TODO implement Parent and Tardieu (2011, 2012) approach for leaf elongation in response to T and VPD, and normalized at 20C, SK, Nov 2012
        # elongAge indicates where it is now along the elongation stage or duration.
        # duration is determined by totallengh/maxElongRate which gives the shortest duration to reach full elongation in the unit of days.
        #FIXME no need to check here, as it will be compared against duration later anyways
        #return min(self._elongation_tracker.rate, self.growth_duration)
        if self.appeared and not self.mature:
            return BetaFunc.create(
                R_max=1.0,
                T_opt=self.p.pheno.optimal_temperature,
                T_max=self.p.pheno.ceiling_temperature
            ).calc(self.p.pheno.temperature)

    #TODO move to common module (i.e. Organ?)
    def _beta_growth(self, t, c_m, t_e, t_m=None, t_b=0, delta=1):
        #FIXME clipping necessary?
        t = np.clip(t, 0., t_e)
        t_m = t_e / 2 if t_m is None else t_m
        t_et = t_e - t
        t_em = t_e - t_m
        t_tb = t - t_b
        t_mb = t_m - t_b
        return c_m * ((t_et / t_em) * (t_tb / t_mb)**(t_mb / t_em))**delta

    @derive
    def potential_elongation_rate(self):
        if self.growing:
            #TODO proper integration with scipy.integrate
            return self._beta_growth(
                t=self.elongation_age,
                c_m=self.maximum_elongation_rate,
                t_e=self.growth_duration,
            )

    @derive
    def _temperature_effect(self, T_grow, T_peak, T_base):
        # T_peak is the optimal growth temperature at which the potential leaf size determined in calc_mophology achieved.
        # Similar concept to fig 3 of Fournier and Andreiu (1998)

        # phyllochron corresponds to PHY in Lizaso (2003)
        # phyllochron needed for next leaf appearance in degree days (GDD8) - 08/16/11, SK.
        #phyllochron = (dv->get_T_Opt()- Tb)/(dv->get_Rmax_LTAR());

        T_ratio = (T_grow - T_base) / (T_peak - T_base)
        # final leaf size is adjusted by growth temperature determining cell size during elongation
        return max(0, T_ratio * np.exp(1 - T_ratio))

    @derive
    def temperature_effect(self):
        #return self._temperature_effect(T_grow=self.p.pheno.growing_temperature, T_peak=18.7, T_base=8.0) # for MAIZSIM
        #FIXME garlic model uses current temperature, not average growing temperature
        #return self._temperature_effect(T_grow=self.p.pheno.temperature, T_peak=self.p.pheno.optimal_temperature, T_base=0) # for garlic
        #FIXME garlic model does not actually use tempeature effect on final leaf size calculation
        return 1.0 # for garlic

    @derive
    def potential_expansion_rate(self):
        t = self.elongation_age
        t_e = self.growth_duration # 1.5 * w_max / c_m
        t = min(t, t_e)
        #FIXME can we introduce new w_max here when w_max in t_e (growth duration) supposed to be potential length?
        w_max = self.potential_area
        # c_m from Eq. 9, r (= dw/dt / c_m) from Eq. 7 of Yin (2003)
        #HACK can be more simplified
        #c_m = 1.5 / t_e * w_max
        #r = 4 * t * (t_e - t) / t_e**2
        t_m = t_e / 2
        c_m = (2*t_e - t_m) / (t_e * (t_e - t_m)) * (t_m / t_e)**(t_m / (t_e - t_m)) * w_max
        r = (t_e - t) / (t_e - t_m) * (t / t_m)**(t_m / (t_e - t_m))
        #FIXME dt here is physiological time, whereas timestep multiplied in potential_area_increase is chronological time
        return c_m * r # dw/dt

    @derive
    def potential_area_increase(self):
        ##area = max(0, water_effect * T_effect * self.potential_area * (1 + (t_e - self.elongation_age) / (t_e - t_m)) * (self.elongation_age / t_e)**(t_e / (t_e - t_m)))
        #maximum_expansion_rate = T_effect * self.potential_area * (2*t_e - t_m) / (t_e * (t_e - t_m)) * (t_m / t_e)**(t_m / (t_e - t_m))
        # potential leaf area increase without any limitations
        #return max(0, maximum_expansion_rate * max(0, (t_e - self.elongation_age) / (t_e - t_m) * (self.elongation_age / t_m)**(t_m / (t_e - t_m))) * self.timestep)
        if self.growing:
            # for MAIZSIM
            #return self.potential_expansion_rate * self.timestep
            # for garlic
            #TODO need common framework dealing with derivatives
            #return self.area_increase_from_length(self.actual_length_increase)
            return self.area_from_length(self.length + self.actual_length_increase) - self.area
        else:
            return 0

    # create a function which simulates the reducing in leaf expansion rate
    # when predawn leaf water potential decreases. Parameterization of rf_psil
    # and rf_sensitivity are done with the data from Boyer (1970) and Tanguilig et al (1987) YY
    @derive
    def _water_potential_effect(self, psi_predawn, threshold):
        #psi_predawn = self.p.soil.WP_leaf_predawn
        psi_th = threshold # threshold wp below which stress effect shows up

        # DT Oct 10, 2012 changed this so it was not as sensitive to stress near -0.5 lwp
        # SK Sept 16, 2014 recalibrated/rescaled parameter estimates in Yang's paper. The scale of Boyer data wasn't set correctly
        # sensitivity = 1.92, LeafWPhalf = -1.86, the sensitivity parameter may be raised by 0.3 to 0.5 to make it less sensitivy at high LWP, SK
        s_f = 0.4258 # 0.5
        psi_f = -1.4251 # -1.0
        return min(1.0, (1 + exp(s_f * psi_f)) / (1 + exp(s_f * (psi_f - (psi_predawn - psi_th)))))

    @derive
    def water_potential_effect(self, threshold):
        # for MAIZSIM
        #return self._water_potential_effect(self.p.soil.WP_leaf_predawn, threshold)
        # for garlic
        return 1.0

    @derive
    def carbon_effect(self):
        return 1.0

    @accumulate(time='elongation_age')
    def length(self):
        #TODO: incorporate stress effects as done in actual_area_increase()
        return self.potential_elongation_rate

    @difference(time='elongation_age')
    def actual_length_increase(self):
        return self.potential_elongation_rate

    # actual area
    @derive
    def area(self):
        # See Kim et al. (2012) Agro J. for more information on how this relationship has been derermined basned on multiple studies and is applicable across environments
        water_effect = self.water_potential_effect(-0.8657)

        # place holder
        carbon_effect = self.carbon_effect

        # growth temperature effect is now included here, outside of potential area increase calculation
        #TODO water and carbon effects are not multiplicative?
        return min(water_effect, carbon_effect) * self.temperature_effect * self.area_from_length(self.length)

    @property
    def actual_area_increase(self):
        #FIXME area increase tracking should be done by some gobal state tracking manager
        raise NotImplementedError("actual_area_increase")

    @property
    def relative_area_increase(self):
        #HACK meaning changed from 'relative to other leaves' (spatial) to 'relative to previous state' (temporal)
        # adapted from CPlant::calcPerLeafRelativeAreaIncrease()
        #return self.potential_area_increase / self.nodal_unit.plant.area.potential_leaf_increase
        da = self.actual_area_increase
        a = self.area - da
        if a > 0:
            return da / a
        else:
            return 0

    @accumulate
    def stay_green_water_stress_duration(self):
        if self.mature:
            # One day of cumulative severe water stress (i.e., water_effect = 0.0 around -4MPa) would result in a reduction of leaf lifespan in relation staygreeness and growthDuration, SK
            # if scale is 1.0, one day of severe water stress shortens one day of stayGreenDuration
            #TODO remove WaterStress and use general Accumulator with a lambda function?
            return WaterStress.create(scale=0.5).calc(self.water_potential_effect(-4.0))

    @derive
    def stay_green_duration(self):
        # SK 8/20/10: as in Sinclair and Horie, 1989 Crop sciences, N availability index scaled between 0 and 1 based on
        #nitrogen_index = max(0, (2 / (1 + np.exp(-2.9 * (self.g_content - 0.25))) - 1))
        return max(0, self.stay_green * self.growth_duration - self.stay_green_water_stress_duration)

    @accumulate
    def active_age(self):
        # Assumes physiological time for senescence is the same as that for growth though this may be adjusted by stayGreen trait
        # a peaked fn like beta fn not used here because aging should accelerate with increasing T not slowing down at very high T like growth,
        # instead a q10 fn normalized to be 1 at T_opt is used, this means above Top aging accelerates.
        #TODO support clipping with @rate option or sub-decorator (i.e. @active_age.clip)
        #FIXME no need to check here, as it will be compared against duration later anyways
        #return min(self._aging_tracker.rate, self.stay_green_duration)
        if self.mature and not self.aging:
            #TODO only for MAIZSIM
            return Q10Func.create(T_opt=self.p.pheno.optimal_temperature).calc(self.p.pheno.temperature)

    @accumulate
    def senescence_water_stress_duration(self):
        if self.aging:
            # if scale is 0.5, one day of severe water stress at predawn shortens one half day of agingDuration
            #TODO remove WaterStress and use general Accumulator with a lambda function?
            return WaterStress.create(scale=0.5).calc(self.water_potential_effect(-4.0))

    @derive
    def senescence_duration(self):
        # end of growth period, time to maturity
        return max(0, self.growth_duration - self.senescence_water_stress_duration)

    #TODO active_age and senescence_age could share a tracker with separate intervals
    @accumulate
    def senescence_age(self):
        #TODO support clipping with @rate option or sub-decorator (i.e. @active_age.clip)
        #FIXME no need to check here, as it will be compared against duration later anyways
        #return min(self._senescence_tracker.rate, self.senescence_duration)
        #FIXME need to remove dependency cycle? (senescence_age -> senescence_ratio -> dead -> senescence_age)
        if self.aging and not self.dead:
            return Q10Func.create(T_opt=self.p.pheno.optimal_temperature).calc(self.p.pheno.temperature)

    @derive
    #TODO confirm if it really means the senescence ratio, not rate
    def senescence_ratio(self):
        # for MAIZSIM
        # t = self.senescence_age
        # t_e = self.senescence_duration
        # if t >= t_e:
        #     return 1
        # else:
        #     t_m = t_e / 2
        #     r = (1 + (t_e - t) / (t_e - t_m)) * (t / t_e)**(t_e / (t_e - t_m))
        #     return np.clip(r, 0., 1.)
        # for garlic
        #HACK prevents nan
        if self.length == 0:
            r = 0.
        else:
            r = self.aging_rate * self.senescence_age / self.length
        return clip(r, 0., 1.)

    @derive
    def senescent_area(self):
        # Leaf senescence accelerates with drought and heat. see http://www.agry.purdue.edu/ext/corn/news/timeless/TopLeafDeath.html
        # rate = self._growth_rate(self.senescence_age, self.senescence_duration)
        # return rate * self.timestep * self.area
        return self.senescence_ratio * self.area

    @derive
    def specific_leaf_area(self):
        # temporary for now - it should vary by age. Value comes from some of Soo's work
        #return 200.0
        try:
            return self.area / self.mass
        except:
            return 0

    # Maturity

    @accumulate
    def maturity(self):
        #HACK: tracking should happen after plant emergence (due to implementation of original beginFromEmergence)
        if self.p.pheno.emerged and not self.mature:
            return GrowingDegreeDays.create(T_base=4.0, T_opt=None, T_max=40.0).calc(self.p.pheno.temperature)

    # Nitrogen

    #FIXME avoid incorrect cycle detection (nitrogen member vs. module) - ?
    @derive
    def nitrogen(self):
        #TODO is this default value needed?
        # no N stress
        #return 3.0
        #TODO remove self.p.* referencing
        return self.p.nitrogen.leaf_content

    ##########
    # States #
    ##########

    @flag
    def initiated(self):
        # no explicit initialize() here
        return True

    @flag
    def appeared(self):
        return self.rank <= self.p.pheno.leaves_appeared

    @flag
    def growing(self):
        return self.appeared and not self.mature

    @flag
    def mature(self):
        return self.elongation_age >= self.growth_duration or self.area >= self.potential_area

    @flag
    def aging(self):
        # for MAIZSIM
        #return self.active_age >= self.stay_green_duration
        # for garlic
        return self.mature and self.physiological_age > self.stay_green * self.maturity

    @flag
    def dead(self):
        #return self.senescent_area >= self.area
        return self.senescence_ratio >= 1
        #return self.senescence_age >= self.senescence_duration?

    @flag
    def dropped(self):
        return self.mature and self.dead
