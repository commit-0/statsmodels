"""
Markov switching regression models

Author: Chad Fulton
License: BSD-3
"""
import numpy as np
import statsmodels.base.wrapper as wrap
from statsmodels.tsa.regime_switching import markov_switching

class MarkovRegression(markov_switching.MarkovSwitching):
    """
    First-order k-regime Markov switching regression model

    Parameters
    ----------
    endog : array_like
        The endogenous variable.
    k_regimes : int
        The number of regimes.
    trend : {'n', 'c', 't', 'ct'}
        Whether or not to include a trend. To include an intercept, time trend,
        or both, set `trend='c'`, `trend='t'`, or `trend='ct'`. For no trend,
        set `trend='n'`. Default is an intercept.
    exog : array_like, optional
        Array of exogenous regressors, shaped nobs x k.
    order : int, optional
        The order of the model describes the dependence of the likelihood on
        previous regimes. This depends on the model in question and should be
        set appropriately by subclasses.
    exog_tvtp : array_like, optional
        Array of exogenous or lagged variables to use in calculating
        time-varying transition probabilities (TVTP). TVTP is only used if this
        variable is provided. If an intercept is desired, a column of ones must
        be explicitly included in this array.
    switching_trend : bool or iterable, optional
        If a boolean, sets whether or not all trend coefficients are
        switching across regimes. If an iterable, should be of length equal
        to the number of trend variables, where each element is
        a boolean describing whether the corresponding coefficient is
        switching. Default is True.
    switching_exog : bool or iterable, optional
        If a boolean, sets whether or not all regression coefficients are
        switching across regimes. If an iterable, should be of length equal
        to the number of exogenous variables, where each element is
        a boolean describing whether the corresponding coefficient is
        switching. Default is True.
    switching_variance : bool, optional
        Whether or not there is regime-specific heteroskedasticity, i.e.
        whether or not the error term has a switching variance. Default is
        False.

    Notes
    -----
    This model is new and API stability is not guaranteed, although changes
    will be made in a backwards compatible way if possible.

    The model can be written as:

    .. math::

        y_t = a_{S_t} + x_t' \\beta_{S_t} + \\varepsilon_t \\\\
        \\varepsilon_t \\sim N(0, \\sigma_{S_t}^2)

    i.e. the model is a dynamic linear regression where the coefficients and
    the variance of the error term may be switching across regimes.

    The `trend` is accommodated by prepending columns to the `exog` array. Thus
    if `trend='c'`, the passed `exog` array should not already have a column of
    ones.

    See the notebook `Markov switching dynamic regression
    <../examples/notebooks/generated/markov_regression.html>`__ for an
    overview.

    References
    ----------
    Kim, Chang-Jin, and Charles R. Nelson. 1999.
    "State-Space Models with Regime Switching:
    Classical and Gibbs-Sampling Approaches with Applications".
    MIT Press Books. The MIT Press.
    """

    def __init__(self, endog, k_regimes, trend='c', exog=None, order=0, exog_tvtp=None, switching_trend=True, switching_exog=True, switching_variance=False, dates=None, freq=None, missing='none'):
        from statsmodels.tools.validation import string_like
        self.trend = string_like(trend, 'trend', options=('n', 'c', 'ct', 't'))
        self.switching_trend = switching_trend
        self.switching_exog = switching_exog
        self.switching_variance = switching_variance
        self.k_exog, exog = markov_switching.prepare_exog(exog)
        nobs = len(endog)
        self.k_trend = 0
        self._k_exog = self.k_exog
        trend_exog = None
        if trend == 'c':
            trend_exog = np.ones((nobs, 1))
            self.k_trend = 1
        elif trend == 't':
            trend_exog = (np.arange(nobs) + 1)[:, np.newaxis]
            self.k_trend = 1
        elif trend == 'ct':
            trend_exog = np.c_[np.ones((nobs, 1)), (np.arange(nobs) + 1)[:, np.newaxis]]
            self.k_trend = 2
        if trend_exog is not None:
            exog = trend_exog if exog is None else np.c_[trend_exog, exog]
            self._k_exog += self.k_trend
        super(MarkovRegression, self).__init__(endog, k_regimes, order=order, exog_tvtp=exog_tvtp, exog=exog, dates=dates, freq=freq, missing=missing)
        if self.switching_trend is True or self.switching_trend is False:
            self.switching_trend = [self.switching_trend] * self.k_trend
        elif not len(self.switching_trend) == self.k_trend:
            raise ValueError('Invalid iterable passed to `switching_trend`.')
        if self.switching_exog is True or self.switching_exog is False:
            self.switching_exog = [self.switching_exog] * self.k_exog
        elif not len(self.switching_exog) == self.k_exog:
            raise ValueError('Invalid iterable passed to `switching_exog`.')
        self.switching_coeffs = np.r_[self.switching_trend, self.switching_exog].astype(bool).tolist()
        self.parameters['exog'] = self.switching_coeffs
        self.parameters['variance'] = [1] if self.switching_variance else [0]

    def predict_conditional(self, params):
        """
        In-sample prediction, conditional on the current regime

        Parameters
        ----------
        params : array_like
            Array of parameters at which to perform prediction.

        Returns
        -------
        predict : array_like
            Array of predictions conditional on current, and possibly past,
            regimes
        """
        pass

    def _conditional_loglikelihoods(self, params):
        """
        Compute loglikelihoods conditional on the current period's regime
        """
        pass

    def _em_iteration(self, params0):
        """
        EM iteration

        Notes
        -----
        This uses the inherited _em_iteration method for computing the
        non-TVTP transition probabilities and then performs the EM step for
        regression coefficients and variances.
        """
        pass

    def _em_exog(self, result, endog, exog, switching, tmp=None):
        """
        EM step for regression coefficients
        """
        pass

    def _em_variance(self, result, endog, exog, betas, tmp=None):
        """
        EM step for variances
        """
        pass

    @property
    def start_params(self):
        """
        (array) Starting parameters for maximum likelihood estimation.

        Notes
        -----
        These are not very sophisticated and / or good. We set equal transition
        probabilities and interpolate regression coefficients between zero and
        the OLS estimates, where the interpolation is based on the regime
        number. We rely heavily on the EM algorithm to quickly find much better
        starting parameters, which are then used by the typical scoring
        approach.
        """
        pass

    @property
    def param_names(self):
        """
        (list of str) List of human readable parameter names (for parameters
        actually included in the model).
        """
        pass

    def transform_params(self, unconstrained):
        """
        Transform unconstrained parameters used by the optimizer to constrained
        parameters used in likelihood evaluation

        Parameters
        ----------
        unconstrained : array_like
            Array of unconstrained parameters used by the optimizer, to be
            transformed.

        Returns
        -------
        constrained : array_like
            Array of constrained parameters which may be used in likelihood
            evaluation.
        """
        pass

    def untransform_params(self, constrained):
        """
        Transform constrained parameters used in likelihood evaluation
        to unconstrained parameters used by the optimizer

        Parameters
        ----------
        constrained : array_like
            Array of constrained parameters used in likelihood evaluation, to
            be transformed.

        Returns
        -------
        unconstrained : array_like
            Array of unconstrained parameters used by the optimizer.
        """
        pass

class MarkovRegressionResults(markov_switching.MarkovSwitchingResults):
    """
    Class to hold results from fitting a Markov switching regression model

    Parameters
    ----------
    model : MarkovRegression instance
        The fitted model instance
    params : ndarray
        Fitted parameters
    filter_results : HamiltonFilterResults or KimSmootherResults instance
        The underlying filter and, optionally, smoother output
    cov_type : str
        The type of covariance matrix estimator to use. Can be one of 'approx',
        'opg', 'robust', or 'none'.

    Attributes
    ----------
    model : Model instance
        A reference to the model that was fit.
    filter_results : HamiltonFilterResults or KimSmootherResults instance
        The underlying filter and, optionally, smoother output
    nobs : float
        The number of observations used to fit the model.
    params : ndarray
        The parameters of the model.
    scale : float
        This is currently set to 1.0 and not used by the model or its results.
    """
    pass

class MarkovRegressionResultsWrapper(markov_switching.MarkovSwitchingResultsWrapper):
    pass
wrap.populate_wrapper(MarkovRegressionResultsWrapper, MarkovRegressionResults)