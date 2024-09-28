"""
SARIMAX Model

Author: Chad Fulton
License: Simplified-BSD
"""
from warnings import warn
import numpy as np
import pandas as pd
from statsmodels.compat.pandas import Appender
from statsmodels.tools.tools import Bunch
from statsmodels.tools.data import _is_using_pandas
from statsmodels.tools.decorators import cache_readonly
import statsmodels.base.wrapper as wrap
from statsmodels.tsa.arima.specification import SARIMAXSpecification
from statsmodels.tsa.arima.params import SARIMAXParams
from statsmodels.tsa.tsatools import lagmat
from .initialization import Initialization
from .mlemodel import MLEModel, MLEResults, MLEResultsWrapper
from .tools import companion_matrix, diff, is_invertible, constrain_stationary_univariate, unconstrain_stationary_univariate, prepare_exog, prepare_trend_spec, prepare_trend_data

class SARIMAX(MLEModel):
    """
    Seasonal AutoRegressive Integrated Moving Average with eXogenous regressors
    model

    Parameters
    ----------
    endog : array_like
        The observed time-series process :math:`y`
    exog : array_like, optional
        Array of exogenous regressors, shaped nobs x k.
    order : iterable or iterable of iterables, optional
        The (p,d,q) order of the model for the number of AR parameters,
        differences, and MA parameters. `d` must be an integer
        indicating the integration order of the process, while
        `p` and `q` may either be an integers indicating the AR and MA
        orders (so that all lags up to those orders are included) or else
        iterables giving specific AR and / or MA lags to include. Default is
        an AR(1) model: (1,0,0).
    seasonal_order : iterable, optional
        The (P,D,Q,s) order of the seasonal component of the model for the
        AR parameters, differences, MA parameters, and periodicity.
        `D` must be an integer indicating the integration order of the process,
        while `P` and `Q` may either be an integers indicating the AR and MA
        orders (so that all lags up to those orders are included) or else
        iterables giving specific AR and / or MA lags to include. `s` is an
        integer giving the periodicity (number of periods in season), often it
        is 4 for quarterly data or 12 for monthly data. Default is no seasonal
        effect.
    trend : str{'n','c','t','ct'} or iterable, optional
        Parameter controlling the deterministic trend polynomial :math:`A(t)`.
        Can be specified as a string where 'c' indicates a constant (i.e. a
        degree zero component of the trend polynomial), 't' indicates a
        linear trend with time, and 'ct' is both. Can also be specified as an
        iterable defining the non-zero polynomial exponents to include, in
        increasing order. For example, `[1,1,0,1]` denotes
        :math:`a + bt + ct^3`. Default is to not include a trend component.
    measurement_error : bool, optional
        Whether or not to assume the endogenous observations `endog` were
        measured with error. Default is False.
    time_varying_regression : bool, optional
        Used when an explanatory variables, `exog`, are provided
        to select whether or not coefficients on the exogenous regressors are
        allowed to vary over time. Default is False.
    mle_regression : bool, optional
        Whether or not to use estimate the regression coefficients for the
        exogenous variables as part of maximum likelihood estimation or through
        the Kalman filter (i.e. recursive least squares). If
        `time_varying_regression` is True, this must be set to False. Default
        is True.
    simple_differencing : bool, optional
        Whether or not to use partially conditional maximum likelihood
        estimation. If True, differencing is performed prior to estimation,
        which discards the first :math:`s D + d` initial rows but results in a
        smaller state-space formulation. See the Notes section for important
        details about interpreting results when this option is used. If False,
        the full SARIMAX model is put in state-space form so that all
        datapoints can be used in estimation. Default is False.
    enforce_stationarity : bool, optional
        Whether or not to transform the AR parameters to enforce stationarity
        in the autoregressive component of the model. Default is True.
    enforce_invertibility : bool, optional
        Whether or not to transform the MA parameters to enforce invertibility
        in the moving average component of the model. Default is True.
    hamilton_representation : bool, optional
        Whether or not to use the Hamilton representation of an ARMA process
        (if True) or the Harvey representation (if False). Default is False.
    concentrate_scale : bool, optional
        Whether or not to concentrate the scale (variance of the error term)
        out of the likelihood. This reduces the number of parameters estimated
        by maximum likelihood by one, but standard errors will then not
        be available for the scale parameter.
    trend_offset : int, optional
        The offset at which to start time trend values. Default is 1, so that
        if `trend='t'` the trend is equal to 1, 2, ..., nobs. Typically is only
        set when the model created by extending a previous dataset.
    use_exact_diffuse : bool, optional
        Whether or not to use exact diffuse initialization for non-stationary
        states. Default is False (in which case approximate diffuse
        initialization is used).
    **kwargs
        Keyword arguments may be used to provide default values for state space
        matrices or for Kalman filtering options. See `Representation`, and
        `KalmanFilter` for more details.

    Attributes
    ----------
    measurement_error : bool
        Whether or not to assume the endogenous
        observations `endog` were measured with error.
    state_error : bool
        Whether or not the transition equation has an error component.
    mle_regression : bool
        Whether or not the regression coefficients for
        the exogenous variables were estimated via maximum
        likelihood estimation.
    state_regression : bool
        Whether or not the regression coefficients for
        the exogenous variables are included as elements
        of the state space and estimated via the Kalman
        filter.
    time_varying_regression : bool
        Whether or not coefficients on the exogenous
        regressors are allowed to vary over time.
    simple_differencing : bool
        Whether or not to use partially conditional maximum likelihood
        estimation.
    enforce_stationarity : bool
        Whether or not to transform the AR parameters
        to enforce stationarity in the autoregressive
        component of the model.
    enforce_invertibility : bool
        Whether or not to transform the MA parameters
        to enforce invertibility in the moving average
        component of the model.
    hamilton_representation : bool
        Whether or not to use the Hamilton representation of an ARMA process.
    trend : str{'n','c','t','ct'} or iterable
        Parameter controlling the deterministic
        trend polynomial :math:`A(t)`. See the class
        parameter documentation for more information.
    polynomial_ar : ndarray
        Array containing autoregressive lag polynomial lags, ordered from
        lowest degree to highest. The polynomial begins with lag 0.
        Initialized with ones, unless a coefficient is constrained to be
        zero (in which case it is zero).
    polynomial_ma : ndarray
        Array containing moving average lag polynomial lags, ordered from
        lowest degree to highest. Initialized with ones, unless a coefficient
        is constrained to be zero (in which case it is zero).
    polynomial_seasonal_ar : ndarray
        Array containing seasonal moving average lag
        polynomial lags, ordered from lowest degree
        to highest. Initialized with ones, unless a
        coefficient is constrained to be zero (in which
        case it is zero).
    polynomial_seasonal_ma : ndarray
        Array containing seasonal moving average lag
        polynomial lags, ordered from lowest degree
        to highest. Initialized with ones, unless a
        coefficient is constrained to be zero (in which
        case it is zero).
    polynomial_trend : ndarray
        Array containing trend polynomial coefficients,
        ordered from lowest degree to highest. Initialized
        with ones, unless a coefficient is constrained to be
        zero (in which case it is zero).
    k_ar : int
        Highest autoregressive order in the model, zero-indexed.
    k_ar_params : int
        Number of autoregressive parameters to be estimated.
    k_diff : int
        Order of integration.
    k_ma : int
        Highest moving average order in the model, zero-indexed.
    k_ma_params : int
        Number of moving average parameters to be estimated.
    seasonal_periods : int
        Number of periods in a season.
    k_seasonal_ar : int
        Highest seasonal autoregressive order in the model, zero-indexed.
    k_seasonal_ar_params : int
        Number of seasonal autoregressive parameters to be estimated.
    k_seasonal_diff : int
        Order of seasonal integration.
    k_seasonal_ma : int
        Highest seasonal moving average order in the model, zero-indexed.
    k_seasonal_ma_params : int
        Number of seasonal moving average parameters to be estimated.
    k_trend : int
        Order of the trend polynomial plus one (i.e. the constant polynomial
        would have `k_trend=1`).
    k_exog : int
        Number of exogenous regressors.

    Notes
    -----
    The SARIMA model is specified :math:`(p, d, q) \\times (P, D, Q)_s`.

    .. math::

        \\phi_p (L) \\tilde \\phi_P (L^s) \\Delta^d \\Delta_s^D y_t = A(t) +
            \\theta_q (L) \\tilde \\theta_Q (L^s) \\zeta_t

    In terms of a univariate structural model, this can be represented as

    .. math::

        y_t & = u_t + \\eta_t \\\\
        \\phi_p (L) \\tilde \\phi_P (L^s) \\Delta^d \\Delta_s^D u_t & = A(t) +
            \\theta_q (L) \\tilde \\theta_Q (L^s) \\zeta_t

    where :math:`\\eta_t` is only applicable in the case of measurement error
    (although it is also used in the case of a pure regression model, i.e. if
    p=q=0).

    In terms of this model, regression with SARIMA errors can be represented
    easily as

    .. math::

        y_t & = \\beta_t x_t + u_t \\\\
        \\phi_p (L) \\tilde \\phi_P (L^s) \\Delta^d \\Delta_s^D u_t & = A(t) +
            \\theta_q (L) \\tilde \\theta_Q (L^s) \\zeta_t

    this model is the one used when exogenous regressors are provided.

    Note that the reduced form lag polynomials will be written as:

    .. math::

        \\Phi (L) \\equiv \\phi_p (L) \\tilde \\phi_P (L^s) \\\\
        \\Theta (L) \\equiv \\theta_q (L) \\tilde \\theta_Q (L^s)

    If `mle_regression` is True, regression coefficients are treated as
    additional parameters to be estimated via maximum likelihood. Otherwise
    they are included as part of the state with a diffuse initialization.
    In this case, however, with approximate diffuse initialization, results
    can be sensitive to the initial variance.

    This class allows two different underlying representations of ARMA models
    as state space models: that of Hamilton and that of Harvey. Both are
    equivalent in the sense that they are analytical representations of the
    ARMA model, but the state vectors of each have different meanings. For
    this reason, maximum likelihood does not result in identical parameter
    estimates and even the same set of parameters will result in different
    loglikelihoods.

    The Harvey representation is convenient because it allows integrating
    differencing into the state vector to allow using all observations for
    estimation.

    In this implementation of differenced models, the Hamilton representation
    is not able to accommodate differencing in the state vector, so
    `simple_differencing` (which performs differencing prior to estimation so
    that the first d + sD observations are lost) must be used.

    Many other packages use the Hamilton representation, so that tests against
    Stata and R require using it along with simple differencing (as Stata
    does).

    If `filter_concentrated = True` is used, then the scale of the model is
    concentrated out of the likelihood. A benefit of this is that there the
    dimension of the parameter vector is reduced so that numerical maximization
    of the log-likelihood function may be faster and more stable. If this
    option in a model with measurement error, it is important to note that the
    estimated measurement error parameter will be relative to the scale, and
    is named "snr.measurement_error" instead of "var.measurement_error". To
    compute the variance of the measurement error in this case one would
    multiply `snr.measurement_error` parameter by the scale.

    If `simple_differencing = True` is used, then the `endog` and `exog` data
    are differenced prior to putting the model in state-space form. This has
    the same effect as if the user differenced the data prior to constructing
    the model, which has implications for using the results:

    - Forecasts and predictions will be about the *differenced* data, not about
      the original data. (while if `simple_differencing = False` is used, then
      forecasts and predictions will be about the original data).
    - If the original data has an Int64Index, a new RangeIndex will be created
      for the differenced data that starts from one, and forecasts and
      predictions will use this new index.

    Detailed information about state space models can be found in [1]_. Some
    specific references are:

    - Chapter 3.4 describes ARMA and ARIMA models in state space form (using
      the Harvey representation), and gives references for basic seasonal
      models and models with a multiplicative form (for example the airline
      model). It also shows a state space model for a full ARIMA process (this
      is what is done here if `simple_differencing=False`).
    - Chapter 3.6 describes estimating regression effects via the Kalman filter
      (this is performed if `mle_regression` is False), regression with
      time-varying coefficients, and regression with ARMA errors (recall from
      above that if regression effects are present, the model estimated by this
      class is regression with SARIMA errors).
    - Chapter 8.4 describes the application of an ARMA model to an example
      dataset. A replication of this section is available in an example
      IPython notebook in the documentation.

    References
    ----------
    .. [1] Durbin, James, and Siem Jan Koopman. 2012.
       Time Series Analysis by State Space Methods: Second Edition.
       Oxford University Press.
    """

    def __init__(self, endog, exog=None, order=(1, 0, 0), seasonal_order=(0, 0, 0, 0), trend=None, measurement_error=False, time_varying_regression=False, mle_regression=True, simple_differencing=False, enforce_stationarity=True, enforce_invertibility=True, hamilton_representation=False, concentrate_scale=False, trend_offset=1, use_exact_diffuse=False, dates=None, freq=None, missing='none', validate_specification=True, **kwargs):
        self._spec = SARIMAXSpecification(endog, exog=exog, order=order, seasonal_order=seasonal_order, trend=trend, enforce_stationarity=None, enforce_invertibility=None, concentrate_scale=concentrate_scale, dates=dates, freq=freq, missing=missing, validate_specification=validate_specification)
        self._params = SARIMAXParams(self._spec)
        order = self._spec.order
        seasonal_order = self._spec.seasonal_order
        self.order = order
        self.seasonal_order = seasonal_order
        self.seasonal_periods = seasonal_order[3]
        self.measurement_error = measurement_error
        self.time_varying_regression = time_varying_regression
        self.mle_regression = mle_regression
        self.simple_differencing = simple_differencing
        self.enforce_stationarity = enforce_stationarity
        self.enforce_invertibility = enforce_invertibility
        self.hamilton_representation = hamilton_representation
        self.concentrate_scale = concentrate_scale
        self.use_exact_diffuse = use_exact_diffuse
        if self.time_varying_regression and self.mle_regression:
            raise ValueError('Models with time-varying regression coefficients must integrate the coefficients as part of the state vector, so that `mle_regression` must be set to False.')
        self._params.ar_params = -1
        self.polynomial_ar = self._params.ar_poly.coef
        self._polynomial_ar = self.polynomial_ar.copy()
        self._params.ma_params = 1
        self.polynomial_ma = self._params.ma_poly.coef
        self._polynomial_ma = self.polynomial_ma.copy()
        self._params.seasonal_ar_params = -1
        self.polynomial_seasonal_ar = self._params.seasonal_ar_poly.coef
        self._polynomial_seasonal_ar = self.polynomial_seasonal_ar.copy()
        self._params.seasonal_ma_params = 1
        self.polynomial_seasonal_ma = self._params.seasonal_ma_poly.coef
        self._polynomial_seasonal_ma = self.polynomial_seasonal_ma.copy()
        self.trend = trend
        self.trend_offset = trend_offset
        self.polynomial_trend, self.k_trend = prepare_trend_spec(self.trend)
        self._polynomial_trend = self.polynomial_trend.copy()
        self._k_trend = self.k_trend
        self.k_ar = self._spec.max_ar_order
        self.k_ar_params = self._spec.k_ar_params
        self.k_diff = int(order[1])
        self.k_ma = self._spec.max_ma_order
        self.k_ma_params = self._spec.k_ma_params
        self.k_seasonal_ar = self._spec.max_seasonal_ar_order * self._spec.seasonal_periods
        self.k_seasonal_ar_params = self._spec.k_seasonal_ar_params
        self.k_seasonal_diff = int(seasonal_order[1])
        self.k_seasonal_ma = self._spec.max_seasonal_ma_order * self._spec.seasonal_periods
        self.k_seasonal_ma_params = self._spec.k_seasonal_ma_params
        self._k_diff = self.k_diff
        self._k_seasonal_diff = self.k_seasonal_diff
        if self.hamilton_representation and (not (self.simple_differencing or self._k_diff == self._k_seasonal_diff == 0)):
            raise ValueError('The Hamilton representation is only available for models in which there is no differencing integrated into the state vector. Set `simple_differencing` to True or set `hamilton_representation` to False')
        self._k_order = max(self.k_ar + self.k_seasonal_ar, self.k_ma + self.k_seasonal_ma + 1)
        if self._k_order == 1 and self.k_ar + self.k_seasonal_ar == 0:
            if self.time_varying_regression:
                self._k_order = 0
        self._k_exog, exog = prepare_exog(exog)
        self.k_exog = self._k_exog
        self.mle_regression = self.mle_regression and exog is not None and (self._k_exog > 0)
        self.state_regression = not self.mle_regression and exog is not None and (self._k_exog > 0)
        if self.state_regression and self._k_order == 0:
            self.measurement_error = True
        k_states = self._k_order
        if not self.simple_differencing:
            k_states += self.seasonal_periods * self._k_seasonal_diff + self._k_diff
        if self.state_regression:
            k_states += self._k_exog
        k_posdef = int(self._k_order > 0)
        self.state_error = k_posdef > 0
        if self.state_regression and self.time_varying_regression:
            k_posdef += self._k_exog
        if self.state_regression:
            kwargs.setdefault('initial_variance', 10000000000.0)
        self._loglikelihood_burn = kwargs.get('loglikelihood_burn', None)
        self.k_params = self.k_ar_params + self.k_ma_params + self.k_seasonal_ar_params + self.k_seasonal_ma_params + self._k_trend + self.measurement_error + int(not self.concentrate_scale)
        if self.mle_regression:
            self.k_params += self._k_exog
        self.orig_endog = endog
        self.orig_exog = exog
        if not _is_using_pandas(endog, None):
            endog = np.asanyarray(endog)
        self.orig_k_diff = self._k_diff
        self.orig_k_seasonal_diff = self._k_seasonal_diff
        if self.simple_differencing and (self._k_diff > 0 or self._k_seasonal_diff > 0):
            self._k_diff = 0
            self._k_seasonal_diff = 0
        self._k_states_diff = self._k_diff + self.seasonal_periods * self._k_seasonal_diff
        self.nobs = len(endog)
        self.k_states = k_states
        self.k_posdef = k_posdef
        super(SARIMAX, self).__init__(endog, exog=exog, k_states=k_states, k_posdef=k_posdef, **kwargs)
        if self.concentrate_scale:
            self.ssm.filter_concentrated = True
        if self._k_exog > 0 or len(self.polynomial_trend) > 1:
            self.ssm._time_invariant = False
        self.ssm['design'] = self.initial_design
        self.ssm['state_intercept'] = self.initial_state_intercept
        self.ssm['transition'] = self.initial_transition
        self.ssm['selection'] = self.initial_selection
        if self.concentrate_scale:
            self.ssm['state_cov', 0, 0] = 1.0
        self._init_keys += ['order', 'seasonal_order', 'trend', 'measurement_error', 'time_varying_regression', 'mle_regression', 'simple_differencing', 'enforce_stationarity', 'enforce_invertibility', 'hamilton_representation', 'concentrate_scale', 'trend_offset'] + list(kwargs.keys())
        if self.ssm.initialization is None:
            self.initialize_default()

    def initialize(self):
        """
        Initialize the SARIMAX model.

        Notes
        -----
        These initialization steps must occur following the parent class
        __init__ function calls.
        """
        pass

    def initialize_default(self, approximate_diffuse_variance=None):
        """Initialize default"""
        pass

    @property
    def initial_design(self):
        """Initial design matrix"""
        pass

    @property
    def initial_state_intercept(self):
        """Initial state intercept vector"""
        pass

    @property
    def initial_transition(self):
        """Initial transition matrix"""
        pass

    @property
    def initial_selection(self):
        """Initial selection matrix"""
        pass

    @property
    def start_params(self):
        """
        Starting parameters for maximum likelihood estimation
        """
        pass

    @property
    def endog_names(self, latex=False):
        """Names of endogenous variables"""
        pass
    params_complete = ['trend', 'exog', 'ar', 'ma', 'seasonal_ar', 'seasonal_ma', 'exog_variance', 'measurement_variance', 'variance']

    @property
    def param_terms(self):
        """
        List of parameters actually included in the model, in sorted order.

        TODO Make this an dict with slice or indices as the values.
        """
        pass

    @property
    def param_names(self):
        """
        List of human readable parameter names (for parameters actually
        included in the model).
        """
        pass

    @property
    def model_orders(self):
        """
        The orders of each of the polynomials in the model.
        """
        pass

    @property
    def model_names(self):
        """
        The plain text names of all possible model parameters.
        """
        pass

    @property
    def model_latex_names(self):
        """
        The latex names of all possible model parameters.
        """
        pass

    def transform_params(self, unconstrained):
        """
        Transform unconstrained parameters used by the optimizer to constrained
        parameters used in likelihood evaluation.

        Used primarily to enforce stationarity of the autoregressive lag
        polynomial, invertibility of the moving average lag polynomial, and
        positive variance parameters.

        Parameters
        ----------
        unconstrained : array_like
            Unconstrained parameters used by the optimizer.

        Returns
        -------
        constrained : array_like
            Constrained parameters used in likelihood evaluation.

        Notes
        -----
        If the lag polynomial has non-consecutive powers (so that the
        coefficient is zero on some element of the polynomial), then the
        constraint function is not onto the entire space of invertible
        polynomials, although it only excludes a very small portion very close
        to the invertibility boundary.
        """
        pass

    def untransform_params(self, constrained):
        """
        Transform constrained parameters used in likelihood evaluation
        to unconstrained parameters used by the optimizer

        Used primarily to reverse enforcement of stationarity of the
        autoregressive lag polynomial and invertibility of the moving average
        lag polynomial.

        Parameters
        ----------
        constrained : array_like
            Constrained parameters used in likelihood evaluation.

        Returns
        -------
        constrained : array_like
            Unconstrained parameters used by the optimizer.

        Notes
        -----
        If the lag polynomial has non-consecutive powers (so that the
        coefficient is zero on some element of the polynomial), then the
        constraint function is not onto the entire space of invertible
        polynomials, although it only excludes a very small portion very close
        to the invertibility boundary.
        """
        pass

    def update(self, params, transformed=True, includes_fixed=False, complex_step=False):
        """
        Update the parameters of the model

        Updates the representation matrices to fill in the new parameter
        values.

        Parameters
        ----------
        params : array_like
            Array of new parameters.
        transformed : bool, optional
            Whether or not `params` is already transformed. If set to False,
            `transform_params` is called. Default is True..

        Returns
        -------
        params : array_like
            Array of parameters.
        """
        pass

    def _get_extension_time_varying_matrices(self, params, exog, out_of_sample, extend_kwargs=None, transformed=True, includes_fixed=False, **kwargs):
        """
        Get time-varying state space system matrices for extended model

        Notes
        -----
        We need to override this method for SARIMAX because we need some
        special handling in the `simple_differencing=True` case.
        """
        pass

class SARIMAXResults(MLEResults):
    """
    Class to hold results from fitting an SARIMAX model.

    Parameters
    ----------
    model : SARIMAX instance
        The fitted model instance

    Attributes
    ----------
    specification : dictionary
        Dictionary including all attributes from the SARIMAX model instance.
    polynomial_ar : ndarray
        Array containing autoregressive lag polynomial coefficients,
        ordered from lowest degree to highest. Initialized with ones, unless
        a coefficient is constrained to be zero (in which case it is zero).
    polynomial_ma : ndarray
        Array containing moving average lag polynomial coefficients,
        ordered from lowest degree to highest. Initialized with ones, unless
        a coefficient is constrained to be zero (in which case it is zero).
    polynomial_seasonal_ar : ndarray
        Array containing seasonal autoregressive lag polynomial coefficients,
        ordered from lowest degree to highest. Initialized with ones, unless
        a coefficient is constrained to be zero (in which case it is zero).
    polynomial_seasonal_ma : ndarray
        Array containing seasonal moving average lag polynomial coefficients,
        ordered from lowest degree to highest. Initialized with ones, unless
        a coefficient is constrained to be zero (in which case it is zero).
    polynomial_trend : ndarray
        Array containing trend polynomial coefficients, ordered from lowest
        degree to highest. Initialized with ones, unless a coefficient is
        constrained to be zero (in which case it is zero).
    model_orders : list of int
        The orders of each of the polynomials in the model.
    param_terms : list of str
        List of parameters actually included in the model, in sorted order.

    See Also
    --------
    statsmodels.tsa.statespace.kalman_filter.FilterResults
    statsmodels.tsa.statespace.mlemodel.MLEResults
    """

    def __init__(self, model, params, filter_results, cov_type=None, **kwargs):
        super(SARIMAXResults, self).__init__(model, params, filter_results, cov_type, **kwargs)
        self.df_resid = np.inf
        self._init_kwds = self.model._get_init_kwds()
        self.specification = Bunch(**{'seasonal_periods': self.model.seasonal_periods, 'measurement_error': self.model.measurement_error, 'time_varying_regression': self.model.time_varying_regression, 'simple_differencing': self.model.simple_differencing, 'enforce_stationarity': self.model.enforce_stationarity, 'enforce_invertibility': self.model.enforce_invertibility, 'hamilton_representation': self.model.hamilton_representation, 'concentrate_scale': self.model.concentrate_scale, 'trend_offset': self.model.trend_offset, 'order': self.model.order, 'seasonal_order': self.model.seasonal_order, 'k_diff': self.model.k_diff, 'k_seasonal_diff': self.model.k_seasonal_diff, 'k_ar': self.model.k_ar, 'k_ma': self.model.k_ma, 'k_seasonal_ar': self.model.k_seasonal_ar, 'k_seasonal_ma': self.model.k_seasonal_ma, 'k_ar_params': self.model.k_ar_params, 'k_ma_params': self.model.k_ma_params, 'trend': self.model.trend, 'k_trend': self.model.k_trend, 'k_exog': self.model.k_exog, 'mle_regression': self.model.mle_regression, 'state_regression': self.model.state_regression})
        self.polynomial_trend = self.model._polynomial_trend
        self.polynomial_ar = self.model._polynomial_ar
        self.polynomial_ma = self.model._polynomial_ma
        self.polynomial_seasonal_ar = self.model._polynomial_seasonal_ar
        self.polynomial_seasonal_ma = self.model._polynomial_seasonal_ma
        self.polynomial_reduced_ar = np.polymul(self.polynomial_ar, self.polynomial_seasonal_ar)
        self.polynomial_reduced_ma = np.polymul(self.polynomial_ma, self.polynomial_seasonal_ma)
        self.model_orders = self.model.model_orders
        self.param_terms = self.model.param_terms
        start = end = 0
        for name in self.param_terms:
            if name == 'ar':
                k = self.model.k_ar_params
            elif name == 'ma':
                k = self.model.k_ma_params
            elif name == 'seasonal_ar':
                k = self.model.k_seasonal_ar_params
            elif name == 'seasonal_ma':
                k = self.model.k_seasonal_ma_params
            else:
                k = self.model_orders[name]
            end += k
            setattr(self, '_params_%s' % name, self.params[start:end])
            start += k
        all_terms = ['ar', 'ma', 'seasonal_ar', 'seasonal_ma', 'variance']
        for name in set(all_terms).difference(self.param_terms):
            setattr(self, '_params_%s' % name, np.empty(0))
        self._data_attr_model.extend(['orig_endog', 'orig_exog'])

    @cache_readonly
    def arroots(self):
        """
        (array) Roots of the reduced form autoregressive lag polynomial
        """
        pass

    @cache_readonly
    def maroots(self):
        """
        (array) Roots of the reduced form moving average lag polynomial
        """
        pass

    @cache_readonly
    def arfreq(self):
        """
        (array) Frequency of the roots of the reduced form autoregressive
        lag polynomial
        """
        pass

    @cache_readonly
    def mafreq(self):
        """
        (array) Frequency of the roots of the reduced form moving average
        lag polynomial
        """
        pass

    @cache_readonly
    def arparams(self):
        """
        (array) Autoregressive parameters actually estimated in the model.
        Does not include seasonal autoregressive parameters (see
        `seasonalarparams`) or parameters whose values are constrained to be
        zero.
        """
        pass

    @cache_readonly
    def seasonalarparams(self):
        """
        (array) Seasonal autoregressive parameters actually estimated in the
        model. Does not include nonseasonal autoregressive parameters (see
        `arparams`) or parameters whose values are constrained to be zero.
        """
        pass

    @cache_readonly
    def maparams(self):
        """
        (array) Moving average parameters actually estimated in the model.
        Does not include seasonal moving average parameters (see
        `seasonalmaparams`) or parameters whose values are constrained to be
        zero.
        """
        pass

    @cache_readonly
    def seasonalmaparams(self):
        """
        (array) Seasonal moving average parameters actually estimated in the
        model. Does not include nonseasonal moving average parameters (see
        `maparams`) or parameters whose values are constrained to be zero.
        """
        pass

class SARIMAXResultsWrapper(MLEResultsWrapper):
    _attrs = {}
    _wrap_attrs = wrap.union_dicts(MLEResultsWrapper._wrap_attrs, _attrs)
    _methods = {}
    _wrap_methods = wrap.union_dicts(MLEResultsWrapper._wrap_methods, _methods)
wrap.populate_wrapper(SARIMAXResultsWrapper, SARIMAXResults)