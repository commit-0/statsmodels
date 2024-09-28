"""
Univariate structural time series models

TODO: tests: "** On entry to DLASCL, parameter number  4 had an illegal value"

Author: Chad Fulton
License: Simplified-BSD
"""
from warnings import warn
import numpy as np
from statsmodels.compat.pandas import Appender
from statsmodels.tools.tools import Bunch
from statsmodels.tools.sm_exceptions import OutputWarning, SpecificationWarning
import statsmodels.base.wrapper as wrap
from statsmodels.tsa.filters.hp_filter import hpfilter
from statsmodels.tsa.tsatools import lagmat
from .mlemodel import MLEModel, MLEResults, MLEResultsWrapper
from .initialization import Initialization
from .tools import companion_matrix, constrain_stationary_univariate, unconstrain_stationary_univariate, prepare_exog
_mask_map = {1: 'irregular', 2: 'fixed intercept', 3: 'deterministic constant', 6: 'random walk', 7: 'local level', 8: 'fixed slope', 11: 'deterministic trend', 14: 'random walk with drift', 15: 'local linear deterministic trend', 31: 'local linear trend', 27: 'smooth trend', 26: 'random trend'}

class UnobservedComponents(MLEModel):
    """
    Univariate unobserved components time series model

    These are also known as structural time series models, and decompose a
    (univariate) time series into trend, seasonal, cyclical, and irregular
    components.

    Parameters
    ----------

    endog : array_like
        The observed time-series process :math:`y`
    level : {bool, str}, optional
        Whether or not to include a level component. Default is False. Can also
        be a string specification of the level / trend component; see Notes
        for available model specification strings.
    trend : bool, optional
        Whether or not to include a trend component. Default is False. If True,
        `level` must also be True.
    seasonal : {int, None}, optional
        The period of the seasonal component, if any. Default is None.
    freq_seasonal : {list[dict], None}, optional.
        Whether (and how) to model seasonal component(s) with trig. functions.
        If specified, there is one dictionary for each frequency-domain
        seasonal component.  Each dictionary must have the key, value pair for
        'period' -- integer and may have a key, value pair for
        'harmonics' -- integer. If 'harmonics' is not specified in any of the
        dictionaries, it defaults to the floor of period/2.
    cycle : bool, optional
        Whether or not to include a cycle component. Default is False.
    autoregressive : {int, None}, optional
        The order of the autoregressive component. Default is None.
    exog : {array_like, None}, optional
        Exogenous variables.
    irregular : bool, optional
        Whether or not to include an irregular component. Default is False.
    stochastic_level : bool, optional
        Whether or not any level component is stochastic. Default is False.
    stochastic_trend : bool, optional
        Whether or not any trend component is stochastic. Default is False.
    stochastic_seasonal : bool, optional
        Whether or not any seasonal component is stochastic. Default is True.
    stochastic_freq_seasonal : list[bool], optional
        Whether or not each seasonal component(s) is (are) stochastic.  Default
        is True for each component.  The list should be of the same length as
        freq_seasonal.
    stochastic_cycle : bool, optional
        Whether or not any cycle component is stochastic. Default is False.
    damped_cycle : bool, optional
        Whether or not the cycle component is damped. Default is False.
    cycle_period_bounds : tuple, optional
        A tuple with lower and upper allowed bounds for the period of the
        cycle. If not provided, the following default bounds are used:
        (1) if no date / time information is provided, the frequency is
        constrained to be between zero and :math:`\\pi`, so the period is
        constrained to be in [0.5, infinity].
        (2) If the date / time information is provided, the default bounds
        allow the cyclical component to be between 1.5 and 12 years; depending
        on the frequency of the endogenous variable, this will imply different
        specific bounds.
    mle_regression : bool, optional
        Whether or not to estimate regression coefficients by maximum likelihood
        as one of hyperparameters. Default is True.
        If False, the regression coefficients are estimated by recursive OLS,
        included in the state vector.
    use_exact_diffuse : bool, optional
        Whether or not to use exact diffuse initialization for non-stationary
        states. Default is False (in which case approximate diffuse
        initialization is used).

    See Also
    --------
    statsmodels.tsa.statespace.structural.UnobservedComponentsResults
    statsmodels.tsa.statespace.mlemodel.MLEModel

    Notes
    -----

    These models take the general form (see [1]_ Chapter 3.2 for all details)

    .. math::

        y_t = \\mu_t + \\gamma_t + c_t + \\varepsilon_t

    where :math:`y_t` refers to the observation vector at time :math:`t`,
    :math:`\\mu_t` refers to the trend component, :math:`\\gamma_t` refers to the
    seasonal component, :math:`c_t` refers to the cycle, and
    :math:`\\varepsilon_t` is the irregular. The modeling details of these
    components are given below.

    **Trend**

    The trend component is a dynamic extension of a regression model that
    includes an intercept and linear time-trend. It can be written:

    .. math::

        \\mu_t = \\mu_{t-1} + \\beta_{t-1} + \\eta_{t-1} \\\\
        \\beta_t = \\beta_{t-1} + \\zeta_{t-1}

    where the level is a generalization of the intercept term that can
    dynamically vary across time, and the trend is a generalization of the
    time-trend such that the slope can dynamically vary across time.

    Here :math:`\\eta_t \\sim N(0, \\sigma_\\eta^2)` and
    :math:`\\zeta_t \\sim N(0, \\sigma_\\zeta^2)`.

    For both elements (level and trend), we can consider models in which:

    - The element is included vs excluded (if the trend is included, there must
      also be a level included).
    - The element is deterministic vs stochastic (i.e. whether or not the
      variance on the error term is confined to be zero or not)

    The only additional parameters to be estimated via MLE are the variances of
    any included stochastic components.

    The level/trend components can be specified using the boolean keyword
    arguments `level`, `stochastic_level`, `trend`, etc., or all at once as a
    string argument to `level`. The following table shows the available
    model specifications:

    +----------------------------------+--------------------------------------+--------------------+--------------------------------------------------+
    | Model name                       | Full string syntax                   | Abbreviated syntax | Model                                            |
    +==================================+======================================+====================+==================================================+
    | No trend                         | `'irregular'`                        | `'ntrend'`         | .. math:: y_t = \\varepsilon_t                    |
    +----------------------------------+--------------------------------------+--------------------+--------------------------------------------------+
    | Fixed intercept                  | `'fixed intercept'`                  |                    | .. math:: y_t = \\mu                              |
    +----------------------------------+--------------------------------------+--------------------+--------------------------------------------------+
    | Deterministic constant           | `'deterministic constant'`           | `'dconstant'`      | .. math:: y_t = \\mu + \\varepsilon_t              |
    +----------------------------------+--------------------------------------+--------------------+--------------------------------------------------+
    | Local level                      | `'local level'`                      | `'llevel'`         | .. math:: y_t &= \\mu_t + \\varepsilon_t \\\\        |
    |                                  |                                      |                    |     \\mu_t &= \\mu_{t-1} + \\eta_t                  |
    +----------------------------------+--------------------------------------+--------------------+--------------------------------------------------+
    | Random walk                      | `'random walk'`                      | `'rwalk'`          | .. math:: y_t &= \\mu_t \\\\                        |
    |                                  |                                      |                    |     \\mu_t &= \\mu_{t-1} + \\eta_t                  |
    +----------------------------------+--------------------------------------+--------------------+--------------------------------------------------+
    | Fixed slope                      | `'fixed slope'`                      |                    | .. math:: y_t &= \\mu_t \\\\                        |
    |                                  |                                      |                    |     \\mu_t &= \\mu_{t-1} + \\beta                   |
    +----------------------------------+--------------------------------------+--------------------+--------------------------------------------------+
    | Deterministic trend              | `'deterministic trend'`              | `'dtrend'`         | .. math:: y_t &= \\mu_t + \\varepsilon_t \\\\        |
    |                                  |                                      |                    |     \\mu_t &= \\mu_{t-1} + \\beta                   |
    +----------------------------------+--------------------------------------+--------------------+--------------------------------------------------+
    | Local linear deterministic trend | `'local linear deterministic trend'` | `'lldtrend'`       | .. math:: y_t &= \\mu_t + \\varepsilon_t \\\\        |
    |                                  |                                      |                    |     \\mu_t &= \\mu_{t-1} + \\beta + \\eta_t          |
    +----------------------------------+--------------------------------------+--------------------+--------------------------------------------------+
    | Random walk with drift           | `'random walk with drift'`           | `'rwdrift'`        | .. math:: y_t &= \\mu_t \\\\                        |
    |                                  |                                      |                    |     \\mu_t &= \\mu_{t-1} + \\beta + \\eta_t          |
    +----------------------------------+--------------------------------------+--------------------+--------------------------------------------------+
    | Local linear trend               | `'local linear trend'`               | `'lltrend'`        | .. math:: y_t &= \\mu_t + \\varepsilon_t \\\\        |
    |                                  |                                      |                    |     \\mu_t &= \\mu_{t-1} + \\beta_{t-1} + \\eta_t \\\\ |
    |                                  |                                      |                    |     \\beta_t &= \\beta_{t-1} + \\zeta_t             |
    +----------------------------------+--------------------------------------+--------------------+--------------------------------------------------+
    | Smooth trend                     | `'smooth trend'`                     | `'strend'`         | .. math:: y_t &= \\mu_t + \\varepsilon_t \\\\        |
    |                                  |                                      |                    |     \\mu_t &= \\mu_{t-1} + \\beta_{t-1} \\\\          |
    |                                  |                                      |                    |     \\beta_t &= \\beta_{t-1} + \\zeta_t             |
    +----------------------------------+--------------------------------------+--------------------+--------------------------------------------------+
    | Random trend                     | `'random trend'`                     | `'rtrend'`         | .. math:: y_t &= \\mu_t \\\\                        |
    |                                  |                                      |                    |     \\mu_t &= \\mu_{t-1} + \\beta_{t-1} \\\\          |
    |                                  |                                      |                    |     \\beta_t &= \\beta_{t-1} + \\zeta_t             |
    +----------------------------------+--------------------------------------+--------------------+--------------------------------------------------+

    Following the fitting of the model, the unobserved level and trend
    component time series are available in the results class in the
    `level` and `trend` attributes, respectively.

    **Seasonal (Time-domain)**

    The seasonal component is modeled as:

    .. math::

        \\gamma_t = - \\sum_{j=1}^{s-1} \\gamma_{t+1-j} + \\omega_t \\\\
        \\omega_t \\sim N(0, \\sigma_\\omega^2)

    The periodicity (number of seasons) is s, and the defining character is
    that (without the error term), the seasonal components sum to zero across
    one complete cycle. The inclusion of an error term allows the seasonal
    effects to vary over time (if this is not desired, :math:`\\sigma_\\omega^2`
    can be set to zero using the `stochastic_seasonal=False` keyword argument).

    This component results in one parameter to be selected via maximum
    likelihood: :math:`\\sigma_\\omega^2`, and one parameter to be chosen, the
    number of seasons `s`.

    Following the fitting of the model, the unobserved seasonal component
    time series is available in the results class in the `seasonal`
    attribute.

    **Frequency-domain Seasonal**

    Each frequency-domain seasonal component is modeled as:

    .. math::

        \\gamma_t & =  \\sum_{j=1}^h \\gamma_{j, t} \\\\
        \\gamma_{j, t+1} & = \\gamma_{j, t}\\cos(\\lambda_j)
                        + \\gamma^{*}_{j, t}\\sin(\\lambda_j) + \\omega_{j,t} \\\\
        \\gamma^{*}_{j, t+1} & = -\\gamma^{(1)}_{j, t}\\sin(\\lambda_j)
                            + \\gamma^{*}_{j, t}\\cos(\\lambda_j)
                            + \\omega^{*}_{j, t}, \\\\
        \\omega^{*}_{j, t}, \\omega_{j, t} & \\sim N(0, \\sigma_{\\omega^2}) \\\\
        \\lambda_j & = \\frac{2 \\pi j}{s}

    where j ranges from 1 to h.

    The periodicity (number of "seasons" in a "year") is s and the number of
    harmonics is h.  Note that h is configurable to be less than s/2, but
    s/2 harmonics is sufficient to fully model all seasonal variations of
    periodicity s.  Like the time domain seasonal term (cf. Seasonal section,
    above), the inclusion of the error terms allows for the seasonal effects to
    vary over time.  The argument stochastic_freq_seasonal can be used to set
    one or more of the seasonal components of this type to be non-random,
    meaning they will not vary over time.

    This component results in one parameter to be fitted using maximum
    likelihood: :math:`\\sigma_{\\omega^2}`, and up to two parameters to be
    chosen, the number of seasons s and optionally the number of harmonics
    h, with :math:`1 \\leq h \\leq \\lfloor s/2 \\rfloor`.

    After fitting the model, each unobserved seasonal component modeled in the
    frequency domain is available in the results class in the `freq_seasonal`
    attribute.

    **Cycle**

    The cyclical component is intended to capture cyclical effects at time
    frames much longer than captured by the seasonal component. For example,
    in economics the cyclical term is often intended to capture the business
    cycle, and is then expected to have a period between "1.5 and 12 years"
    (see Durbin and Koopman).

    .. math::

        c_{t+1} & = \\rho_c (\\tilde c_t \\cos \\lambda_c t
                + \\tilde c_t^* \\sin \\lambda_c) +
                \\tilde \\omega_t \\\\
        c_{t+1}^* & = \\rho_c (- \\tilde c_t \\sin \\lambda_c  t +
                \\tilde c_t^* \\cos \\lambda_c) +
                \\tilde \\omega_t^* \\\\

    where :math:`\\omega_t, \\tilde \\omega_t iid N(0, \\sigma_{\\tilde \\omega}^2)`

    The parameter :math:`\\lambda_c` (the frequency of the cycle) is an
    additional parameter to be estimated by MLE.

    If the cyclical effect is stochastic (`stochastic_cycle=True`), then there
    is another parameter to estimate (the variance of the error term - note
    that both of the error terms here share the same variance, but are assumed
    to have independent draws).

    If the cycle is damped (`damped_cycle=True`), then there is a third
    parameter to estimate, :math:`\\rho_c`.

    In order to achieve cycles with the appropriate frequencies, bounds are
    imposed on the parameter :math:`\\lambda_c` in estimation. These can be
    controlled via the keyword argument `cycle_period_bounds`, which, if
    specified, must be a tuple of bounds on the **period** `(lower, upper)`.
    The bounds on the frequency are then calculated from those bounds.

    The default bounds, if none are provided, are selected in the following
    way:

    1. If no date / time information is provided, the frequency is
       constrained to be between zero and :math:`\\pi`, so the period is
       constrained to be in :math:`[0.5, \\infty]`.
    2. If the date / time information is provided, the default bounds
       allow the cyclical component to be between 1.5 and 12 years; depending
       on the frequency of the endogenous variable, this will imply different
       specific bounds.

    Following the fitting of the model, the unobserved cyclical component
    time series is available in the results class in the `cycle`
    attribute.

    **Irregular**

    The irregular components are independent and identically distributed (iid):

    .. math::

        \\varepsilon_t \\sim N(0, \\sigma_\\varepsilon^2)

    **Autoregressive Irregular**

    An autoregressive component (often used as a replacement for the white
    noise irregular term) can be specified as:

    .. math::

        \\varepsilon_t = \\rho(L) \\varepsilon_{t-1} + \\epsilon_t \\\\
        \\epsilon_t \\sim N(0, \\sigma_\\epsilon^2)

    In this case, the AR order is specified via the `autoregressive` keyword,
    and the autoregressive coefficients are estimated.

    Following the fitting of the model, the unobserved autoregressive component
    time series is available in the results class in the `autoregressive`
    attribute.

    **Regression effects**

    Exogenous regressors can be pass to the `exog` argument. The regression
    coefficients will be estimated by maximum likelihood unless
    `mle_regression=False`, in which case the regression coefficients will be
    included in the state vector where they are essentially estimated via
    recursive OLS.

    If the regression_coefficients are included in the state vector, the
    recursive estimates are available in the results class in the
    `regression_coefficients` attribute.

    References
    ----------
    .. [1] Durbin, James, and Siem Jan Koopman. 2012.
       Time Series Analysis by State Space Methods: Second Edition.
       Oxford University Press.
    """

    def __init__(self, endog, level=False, trend=False, seasonal=None, freq_seasonal=None, cycle=False, autoregressive=None, exog=None, irregular=False, stochastic_level=False, stochastic_trend=False, stochastic_seasonal=True, stochastic_freq_seasonal=None, stochastic_cycle=False, damped_cycle=False, cycle_period_bounds=None, mle_regression=True, use_exact_diffuse=False, **kwargs):
        self.level = level
        self.trend = trend
        self.seasonal_periods = seasonal if seasonal is not None else 0
        self.seasonal = self.seasonal_periods > 0
        if freq_seasonal:
            self.freq_seasonal_periods = [d['period'] for d in freq_seasonal]
            self.freq_seasonal_harmonics = [d.get('harmonics', int(np.floor(d['period'] / 2))) for d in freq_seasonal]
        else:
            self.freq_seasonal_periods = []
            self.freq_seasonal_harmonics = []
        self.freq_seasonal = any((x > 0 for x in self.freq_seasonal_periods))
        self.cycle = cycle
        self.ar_order = autoregressive if autoregressive is not None else 0
        self.autoregressive = self.ar_order > 0
        self.irregular = irregular
        self.stochastic_level = stochastic_level
        self.stochastic_trend = stochastic_trend
        self.stochastic_seasonal = stochastic_seasonal
        if stochastic_freq_seasonal is None:
            self.stochastic_freq_seasonal = [True] * len(self.freq_seasonal_periods)
        else:
            if len(stochastic_freq_seasonal) != len(freq_seasonal):
                raise ValueError('Length of stochastic_freq_seasonal must equal length of freq_seasonal: {!r} vs {!r}'.format(len(stochastic_freq_seasonal), len(freq_seasonal)))
            self.stochastic_freq_seasonal = stochastic_freq_seasonal
        self.stochastic_cycle = stochastic_cycle
        self.damped_cycle = damped_cycle
        self.mle_regression = mle_regression
        self.use_exact_diffuse = use_exact_diffuse
        self.trend_specification = None
        if isinstance(self.level, str):
            self.trend_specification = level
            self.level = False
            trend_attributes = ['irregular', 'level', 'trend', 'stochastic_level', 'stochastic_trend']
            for attribute in trend_attributes:
                if not getattr(self, attribute) is False:
                    warn('Value of `%s` may be overridden when the trend component is specified using a model string.' % attribute, SpecificationWarning)
                    setattr(self, attribute, False)
            spec = self.trend_specification
            if spec == 'irregular' or spec == 'ntrend':
                self.irregular = True
                self.trend_specification = 'irregular'
            elif spec == 'fixed intercept':
                self.level = True
            elif spec == 'deterministic constant' or spec == 'dconstant':
                self.irregular = True
                self.level = True
                self.trend_specification = 'deterministic constant'
            elif spec == 'local level' or spec == 'llevel':
                self.irregular = True
                self.level = True
                self.stochastic_level = True
                self.trend_specification = 'local level'
            elif spec == 'random walk' or spec == 'rwalk':
                self.level = True
                self.stochastic_level = True
                self.trend_specification = 'random walk'
            elif spec == 'fixed slope':
                self.level = True
                self.trend = True
            elif spec == 'deterministic trend' or spec == 'dtrend':
                self.irregular = True
                self.level = True
                self.trend = True
                self.trend_specification = 'deterministic trend'
            elif spec == 'local linear deterministic trend' or spec == 'lldtrend':
                self.irregular = True
                self.level = True
                self.stochastic_level = True
                self.trend = True
                self.trend_specification = 'local linear deterministic trend'
            elif spec == 'random walk with drift' or spec == 'rwdrift':
                self.level = True
                self.stochastic_level = True
                self.trend = True
                self.trend_specification = 'random walk with drift'
            elif spec == 'local linear trend' or spec == 'lltrend':
                self.irregular = True
                self.level = True
                self.stochastic_level = True
                self.trend = True
                self.stochastic_trend = True
                self.trend_specification = 'local linear trend'
            elif spec == 'smooth trend' or spec == 'strend':
                self.irregular = True
                self.level = True
                self.trend = True
                self.stochastic_trend = True
                self.trend_specification = 'smooth trend'
            elif spec == 'random trend' or spec == 'rtrend':
                self.level = True
                self.trend = True
                self.stochastic_trend = True
                self.trend_specification = 'random trend'
            else:
                raise ValueError("Invalid level/trend specification: '%s'" % spec)
        if trend and (not level):
            warn('Trend component specified without level component; deterministic level component added.', SpecificationWarning)
            self.level = True
            self.stochastic_level = False
        if not (self.irregular or (self.level and self.stochastic_level) or (self.trend and self.stochastic_trend) or (self.seasonal and self.stochastic_seasonal) or (self.freq_seasonal and any(self.stochastic_freq_seasonal)) or (self.cycle and self.stochastic_cycle) or self.autoregressive):
            warn('Specified model does not contain a stochastic element; irregular component added.', SpecificationWarning)
            self.irregular = True
        if self.seasonal and self.seasonal_periods < 2:
            raise ValueError('Seasonal component must have a seasonal period of at least 2.')
        if self.freq_seasonal:
            for p in self.freq_seasonal_periods:
                if p < 2:
                    raise ValueError('Frequency Domain seasonal component must have a seasonal period of at least 2.')
        self.trend_mask = self.irregular * 1 | self.level * 2 | self.level * self.stochastic_level * 4 | self.trend * 8 | self.trend * self.stochastic_trend * 16
        if self.trend_specification is None:
            self.trend_specification = _mask_map.get(self.trend_mask, None)
        self.k_exog, exog = prepare_exog(exog)
        self.regression = self.k_exog > 0
        self._k_seasonal_states = (self.seasonal_periods - 1) * self.seasonal
        self._k_freq_seas_states = sum((2 * h for h in self.freq_seasonal_harmonics)) * self.freq_seasonal
        self._k_cycle_states = self.cycle * 2
        k_states = self.level + self.trend + self._k_seasonal_states + self._k_freq_seas_states + self._k_cycle_states + self.ar_order + (not self.mle_regression) * self.k_exog
        k_posdef = self.stochastic_level * self.level + self.stochastic_trend * self.trend + self.stochastic_seasonal * self.seasonal + sum((2 * h if self.stochastic_freq_seasonal[ix] else 0 for ix, h in enumerate(self.freq_seasonal_harmonics))) * self.freq_seasonal + self.stochastic_cycle * self._k_cycle_states + self.autoregressive
        self._loglikelihood_burn = kwargs.get('loglikelihood_burn', None)
        self._unused_state = False
        if k_states == 0:
            if not self.irregular:
                raise ValueError('Model has no components specified.')
            k_states = 1
            self._unused_state = True
        if k_posdef == 0:
            k_posdef = 1
        super(UnobservedComponents, self).__init__(endog, k_states, k_posdef=k_posdef, exog=exog, **kwargs)
        self.setup()
        if self.k_exog > 0:
            self.ssm._time_invariant = False
        self.data.param_names = self.param_names
        if cycle_period_bounds is None:
            freq = self.data.freq[0] if self.data.freq is not None else ''
            if freq in ('A', 'Y'):
                cycle_period_bounds = (1.5, 12)
            elif freq == 'Q':
                cycle_period_bounds = (1.5 * 4, 12 * 4)
            elif freq == 'M':
                cycle_period_bounds = (1.5 * 12, 12 * 12)
            else:
                cycle_period_bounds = (2, np.inf)
        self.cycle_frequency_bound = (2 * np.pi / cycle_period_bounds[1], 2 * np.pi / cycle_period_bounds[0])
        self._init_keys += ['level', 'trend', 'seasonal', 'freq_seasonal', 'cycle', 'autoregressive', 'irregular', 'stochastic_level', 'stochastic_trend', 'stochastic_seasonal', 'stochastic_freq_seasonal', 'stochastic_cycle', 'damped_cycle', 'cycle_period_bounds', 'mle_regression'] + list(kwargs.keys())
        self.initialize_default()

    def setup(self):
        """
        Setup the structural time series representation
        """
        pass

    def transform_params(self, unconstrained):
        """
        Transform unconstrained parameters used by the optimizer to constrained
        parameters used in likelihood evaluation
        """
        pass

    def untransform_params(self, constrained):
        """
        Reverse the transformation
        """
        pass

class UnobservedComponentsResults(MLEResults):
    """
    Class to hold results from fitting an unobserved components model.

    Parameters
    ----------
    model : UnobservedComponents instance
        The fitted model instance

    Attributes
    ----------
    specification : dictionary
        Dictionary including all attributes from the unobserved components
        model instance.

    See Also
    --------
    statsmodels.tsa.statespace.kalman_filter.FilterResults
    statsmodels.tsa.statespace.mlemodel.MLEResults
    """

    def __init__(self, model, params, filter_results, cov_type=None, **kwargs):
        super(UnobservedComponentsResults, self).__init__(model, params, filter_results, cov_type, **kwargs)
        self.df_resid = np.inf
        self._init_kwds = self.model._get_init_kwds()
        self._k_states_by_type = {'seasonal': self.model._k_seasonal_states, 'freq_seasonal': self.model._k_freq_seas_states, 'cycle': self.model._k_cycle_states}
        self.specification = Bunch(**{'level': self.model.level, 'trend': self.model.trend, 'seasonal_periods': self.model.seasonal_periods, 'seasonal': self.model.seasonal, 'freq_seasonal': self.model.freq_seasonal, 'freq_seasonal_periods': self.model.freq_seasonal_periods, 'freq_seasonal_harmonics': self.model.freq_seasonal_harmonics, 'cycle': self.model.cycle, 'ar_order': self.model.ar_order, 'autoregressive': self.model.autoregressive, 'irregular': self.model.irregular, 'stochastic_level': self.model.stochastic_level, 'stochastic_trend': self.model.stochastic_trend, 'stochastic_seasonal': self.model.stochastic_seasonal, 'stochastic_freq_seasonal': self.model.stochastic_freq_seasonal, 'stochastic_cycle': self.model.stochastic_cycle, 'damped_cycle': self.model.damped_cycle, 'regression': self.model.regression, 'mle_regression': self.model.mle_regression, 'k_exog': self.model.k_exog, 'trend_specification': self.model.trend_specification})

    @property
    def level(self):
        """
        Estimates of unobserved level component

        Returns
        -------
        out: Bunch
            Has the following attributes:

            - `filtered`: a time series array with the filtered estimate of
                          the component
            - `filtered_cov`: a time series array with the filtered estimate of
                          the variance/covariance of the component
            - `smoothed`: a time series array with the smoothed estimate of
                          the component
            - `smoothed_cov`: a time series array with the smoothed estimate of
                          the variance/covariance of the component
            - `offset`: an integer giving the offset in the state vector where
                        this component begins
        """
        pass

    @property
    def trend(self):
        """
        Estimates of of unobserved trend component

        Returns
        -------
        out: Bunch
            Has the following attributes:

            - `filtered`: a time series array with the filtered estimate of
                          the component
            - `filtered_cov`: a time series array with the filtered estimate of
                          the variance/covariance of the component
            - `smoothed`: a time series array with the smoothed estimate of
                          the component
            - `smoothed_cov`: a time series array with the smoothed estimate of
                          the variance/covariance of the component
            - `offset`: an integer giving the offset in the state vector where
                        this component begins
        """
        pass

    @property
    def seasonal(self):
        """
        Estimates of unobserved seasonal component

        Returns
        -------
        out: Bunch
            Has the following attributes:

            - `filtered`: a time series array with the filtered estimate of
                          the component
            - `filtered_cov`: a time series array with the filtered estimate of
                          the variance/covariance of the component
            - `smoothed`: a time series array with the smoothed estimate of
                          the component
            - `smoothed_cov`: a time series array with the smoothed estimate of
                          the variance/covariance of the component
            - `offset`: an integer giving the offset in the state vector where
                        this component begins
        """
        pass

    @property
    def freq_seasonal(self):
        """
        Estimates of unobserved frequency domain seasonal component(s)

        Returns
        -------
        out: list of Bunch instances
            Each item has the following attributes:

            - `filtered`: a time series array with the filtered estimate of
                          the component
            - `filtered_cov`: a time series array with the filtered estimate of
                          the variance/covariance of the component
            - `smoothed`: a time series array with the smoothed estimate of
                          the component
            - `smoothed_cov`: a time series array with the smoothed estimate of
                          the variance/covariance of the component
            - `offset`: an integer giving the offset in the state vector where
                        this component begins
        """
        pass

    @property
    def cycle(self):
        """
        Estimates of unobserved cycle component

        Returns
        -------
        out: Bunch
            Has the following attributes:

            - `filtered`: a time series array with the filtered estimate of
                          the component
            - `filtered_cov`: a time series array with the filtered estimate of
                          the variance/covariance of the component
            - `smoothed`: a time series array with the smoothed estimate of
                          the component
            - `smoothed_cov`: a time series array with the smoothed estimate of
                          the variance/covariance of the component
            - `offset`: an integer giving the offset in the state vector where
                        this component begins
        """
        pass

    @property
    def autoregressive(self):
        """
        Estimates of unobserved autoregressive component

        Returns
        -------
        out: Bunch
            Has the following attributes:

            - `filtered`: a time series array with the filtered estimate of
                          the component
            - `filtered_cov`: a time series array with the filtered estimate of
                          the variance/covariance of the component
            - `smoothed`: a time series array with the smoothed estimate of
                          the component
            - `smoothed_cov`: a time series array with the smoothed estimate of
                          the variance/covariance of the component
            - `offset`: an integer giving the offset in the state vector where
                        this component begins
        """
        pass

    @property
    def regression_coefficients(self):
        """
        Estimates of unobserved regression coefficients

        Returns
        -------
        out: Bunch
            Has the following attributes:

            - `filtered`: a time series array with the filtered estimate of
                          the component
            - `filtered_cov`: a time series array with the filtered estimate of
                          the variance/covariance of the component
            - `smoothed`: a time series array with the smoothed estimate of
                          the component
            - `smoothed_cov`: a time series array with the smoothed estimate of
                          the variance/covariance of the component
            - `offset`: an integer giving the offset in the state vector where
                        this component begins
        """
        pass

    def plot_components(self, which=None, alpha=0.05, observed=True, level=True, trend=True, seasonal=True, freq_seasonal=True, cycle=True, autoregressive=True, legend_loc='upper right', fig=None, figsize=None):
        """
        Plot the estimated components of the model.

        Parameters
        ----------
        which : {'filtered', 'smoothed'}, or None, optional
            Type of state estimate to plot. Default is 'smoothed' if smoothed
            results are available otherwise 'filtered'.
        alpha : float, optional
            The confidence intervals for the components are (1 - alpha) %
        observed : bool, optional
            Whether or not to plot the observed series against
            one-step-ahead predictions.
            Default is True.
        level : bool, optional
            Whether or not to plot the level component, if applicable.
            Default is True.
        trend : bool, optional
            Whether or not to plot the trend component, if applicable.
            Default is True.
        seasonal : bool, optional
            Whether or not to plot the seasonal component, if applicable.
            Default is True.
        freq_seasonal : bool, optional
            Whether or not to plot the frequency domain seasonal component(s),
            if applicable. Default is True.
        cycle : bool, optional
            Whether or not to plot the cyclical component, if applicable.
            Default is True.
        autoregressive : bool, optional
            Whether or not to plot the autoregressive state, if applicable.
            Default is True.
        fig : Figure, optional
            If given, subplots are created in this figure instead of in a new
            figure. Note that the grid will be created in the provided
            figure using `fig.add_subplot()`.
        figsize : tuple, optional
            If a figure is created, this argument allows specifying a size.
            The tuple is (width, height).

        Notes
        -----
        If all options are included in the model and selected, this produces
        a 6x1 plot grid with the following plots (ordered top-to-bottom):

        0. Observed series against predicted series
        1. Level
        2. Trend
        3. Seasonal
        4. Freq Seasonal
        5. Cycle
        6. Autoregressive

        Specific subplots will be removed if the component is not present in
        the estimated model or if the corresponding keyword argument is set to
        False.

        All plots contain (1 - `alpha`) %  confidence intervals.
        """
        pass

class UnobservedComponentsResultsWrapper(MLEResultsWrapper):
    _attrs = {}
    _wrap_attrs = wrap.union_dicts(MLEResultsWrapper._wrap_attrs, _attrs)
    _methods = {}
    _wrap_methods = wrap.union_dicts(MLEResultsWrapper._wrap_methods, _methods)
wrap.populate_wrapper(UnobservedComponentsResultsWrapper, UnobservedComponentsResults)