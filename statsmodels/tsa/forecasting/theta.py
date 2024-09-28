"""
Implementation of the Theta forecasting method of

Assimakopoulos, V., & Nikolopoulos, K. (2000). The theta model: a decomposition
approach to forecasting. International journal of forecasting, 16(4), 521-530.

and updates in

Hyndman, R. J., & Billah, B. (2003). Unmasking the Theta method. International
Journal of Forecasting, 19(2), 287-290.

Fioruci, J. A., Pellegrini, T. R., Louzada, F., & Petropoulos, F. (2015).
The optimized theta method. arXiv preprint arXiv:1503.03529.
"""
from typing import TYPE_CHECKING, Optional, Tuple
import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.iolib.summary import Summary
from statsmodels.iolib.table import SimpleTable
from statsmodels.tools.validation import array_like, bool_like, float_like, int_like, string_like
from statsmodels.tsa.deterministic import DeterministicTerm
from statsmodels.tsa.seasonal import seasonal_decompose
from statsmodels.tsa.statespace.exponential_smoothing import ExponentialSmoothing
from statsmodels.tsa.statespace.sarimax import SARIMAX
from statsmodels.tsa.stattools import acf
from statsmodels.tsa.tsatools import add_trend, freq_to_period
if TYPE_CHECKING:
    import matplotlib.figure

class ThetaModel:
    """
    The Theta forecasting model of Assimakopoulos and Nikolopoulos (2000)

    Parameters
    ----------
    endog : array_like, 1d
        The data to forecast.
    period : int, default None
        The period of the data that is used in the seasonality test and
        adjustment. If None then the period is determined from y's index,
        if available.
    deseasonalize : bool, default True
        A flag indicating whether the deseasonalize the data. If True and
        use_test is True, the data is only deseasonalized if the null of no
        seasonal component is rejected.
    use_test : bool, default True
        A flag indicating whether test the period-th autocorrelation. If this
        test rejects using a size of 10%, then decomposition is used. Set to
        False to skip the test.
    method : {"auto", "additive", "multiplicative"}, default "auto"
        The model used for the seasonal decomposition. "auto" uses a
        multiplicative if y is non-negative and all estimated seasonal
        components are positive. If either of these conditions is False,
        then it uses an additive decomposition.
    difference : bool, default False
        A flag indicating to difference the data before testing for
        seasonality.

    See Also
    --------
    statsmodels.tsa.statespace.exponential_smoothing.ExponentialSmoothing
        Exponential smoothing parameter estimation and forecasting
    statsmodels.tsa.statespace.sarimax.SARIMAX
        Seasonal ARIMA parameter estimation and forecasting

    Notes
    -----
    The Theta model forecasts the future as a weighted combination of two
    Theta lines.  This class supports combinations of models with two
    thetas: 0 and a user-specified choice (default 2). The forecasts are
    then

    .. math::

       \\hat{X}_{T+h|T} = \\frac{\\theta-1}{\\theta} b_0
                         \\left[h - 1 + \\frac{1}{\\alpha}
                         - \\frac{(1-\\alpha)^T}{\\alpha} \\right]
                         + \\tilde{X}_{T+h|T}

    where :math:`\\tilde{X}_{T+h|T}` is the SES forecast of the endogenous
    variable using the parameter :math:`\\alpha`. :math:`b_0` is the
    slope of a time trend line fitted to X using the terms 0, 1, ..., T-1.

    The model is estimated in steps:

    1. Test for seasonality
    2. Deseasonalize if seasonality detected
    3. Estimate :math:`\\alpha` by fitting a SES model to the data and
       :math:`b_0` by OLS.
    4. Forecast the series
    5. Reseasonalize if the data was deseasonalized.

    The seasonality test examines where the autocorrelation at the
    seasonal period is different from zero. The seasonality is then
    removed using a seasonal decomposition with a multiplicative trend.
    If the seasonality estimate is non-positive then an additive trend
    is used instead. The default deseasonalizing method can be changed
    using the options.

    References
    ----------
    .. [1] Assimakopoulos, V., & Nikolopoulos, K. (2000). The theta model: a
       decomposition approach to forecasting. International Journal of
       Forecasting, 16(4), 521-530.
    .. [2] Hyndman, R. J., & Billah, B. (2003). Unmasking the Theta method.
       International Journal of Forecasting, 19(2), 287-290.
    .. [3] Fioruci, J. A., Pellegrini, T. R., Louzada, F., & Petropoulos, F.
       (2015). The optimized theta method. arXiv preprint arXiv:1503.03529.
    """

    def __init__(self, endog, *, period: Optional[int]=None, deseasonalize: bool=True, use_test: bool=True, method: str='auto', difference: bool=False) -> None:
        self._y = array_like(endog, 'endog', ndim=1)
        if isinstance(endog, pd.DataFrame):
            self.endog_orig = endog.iloc[:, 0]
        else:
            self.endog_orig = endog
        self._period = int_like(period, 'period', optional=True)
        self._deseasonalize = bool_like(deseasonalize, 'deseasonalize')
        self._use_test = bool_like(use_test, 'use_test') and self._deseasonalize
        self._diff = bool_like(difference, 'difference')
        self._method = string_like(method, 'model', options=('auto', 'additive', 'multiplicative', 'mul', 'add'))
        if self._method == 'auto':
            self._method = 'mul' if self._y.min() > 0 else 'add'
        if self._period is None and self._deseasonalize:
            idx = getattr(endog, 'index', None)
            pfreq = None
            if idx is not None:
                pfreq = getattr(idx, 'freq', None)
                if pfreq is None:
                    pfreq = getattr(idx, 'inferred_freq', None)
            if pfreq is not None:
                self._period = freq_to_period(pfreq)
            else:
                raise ValueError('You must specify a period or endog must be a pandas object with a DatetimeIndex with a freq not set to None')
        self._has_seasonality = self._deseasonalize

    def fit(self, use_mle: bool=False, disp: bool=False) -> 'ThetaModelResults':
        """
        Estimate model parameters.

        Parameters
        ----------
        use_mle : bool, default False
            Estimate the parameters using MLE by fitting an ARIMA(0,1,1) with
            a drift.  If False (the default), estimates parameters using OLS
            of a constant and a time-trend and by fitting a SES to the model
            data.
        disp : bool, default True
            Display iterative output from fitting the model.

        Notes
        -----
        When using MLE, the parameters are estimated from the ARIMA(0,1,1)

        .. math::

           X_t = X_{t-1} + b_0 + (\\alpha-1)\\epsilon_{t-1} + \\epsilon_t

        When estimating the model using 2-step estimation, the model
        parameters are estimated using the OLS regression

        .. math::

           X_t = a_0 + b_0 (t-1) + \\eta_t

        and the SES

        .. math::

           \\tilde{X}_{t+1} = \\alpha X_{t} + (1-\\alpha)\\tilde{X}_{t}

        Returns
        -------
        ThetaModelResult
            Model results and forecasting
        """
        pass

    @property
    def deseasonalize(self) -> bool:
        """Whether to deseasonalize the data"""
        pass

    @property
    def period(self) -> int:
        """The period of the seasonality"""
        pass

    @property
    def use_test(self) -> bool:
        """Whether to test the data for seasonality"""
        pass

    @property
    def difference(self) -> bool:
        """Whether the data is differenced in the seasonality test"""
        pass

    @property
    def method(self) -> str:
        """The method used to deseasonalize the data"""
        pass

class ThetaModelResults:
    """
    Results class from estimated Theta Models.

    Parameters
    ----------
    b0 : float
        The estimated trend slope.
    alpha : float
        The estimated SES parameter.
    sigma2 : float
        The estimated residual variance from the SES/IMA model.
    one_step : float
        The one-step forecast from the SES.
    seasonal : ndarray
        An array of estimated seasonal terms.
    use_mle : bool
        A flag indicating that the parameters were estimated using MLE.
    model : ThetaModel
        The model used to produce the results.
    """

    def __init__(self, b0: float, alpha: float, sigma2: Optional[float], one_step: float, seasonal: np.ndarray, use_mle: bool, model: ThetaModel) -> None:
        self._b0 = b0
        self._alpha = alpha
        self._sigma2 = sigma2
        self._one_step = one_step
        self._nobs = model.endog_orig.shape[0]
        self._model = model
        self._seasonal = seasonal
        self._use_mle = use_mle

    @property
    def params(self) -> pd.Series:
        """The forecasting model parameters"""
        pass

    @property
    def sigma2(self) -> float:
        """The estimated residual variance"""
        pass

    @property
    def model(self) -> ThetaModel:
        """The model used to produce the results"""
        pass

    def forecast(self, steps: int=1, theta: float=2) -> pd.Series:
        """
        Forecast the model for a given theta

        Parameters
        ----------
        steps : int
            The number of steps ahead to compute the forecast components.
        theta : float
            The theta value to use when computing the weight to combine
            the trend and the SES forecasts.

        Returns
        -------
        Series
            A Series containing the forecasts

        Notes
        -----
        The forecast is computed as

        .. math::

           \\hat{X}_{T+h|T} = \\frac{\\theta-1}{\\theta} b_0
                             \\left[h - 1 + \\frac{1}{\\alpha}
                             - \\frac{(1-\\alpha)^T}{\\alpha} \\right]
                             + \\tilde{X}_{T+h|T}

        where :math:`\\tilde{X}_{T+h|T}` is the SES forecast of the endogenous
        variable using the parameter :math:`\\alpha`. :math:`b_0` is the
        slope of a time trend line fitted to X using the terms 0, 1, ..., T-1.

        This expression follows from [1]_ and [2]_ when the combination
        weights are restricted to be (theta-1)/theta and 1/theta. This nests
        the original implementation when theta=2 and the two weights are both
        1/2.

        References
        ----------
        .. [1] Hyndman, R. J., & Billah, B. (2003). Unmasking the Theta method.
           International Journal of Forecasting, 19(2), 287-290.
        .. [2] Fioruci, J. A., Pellegrini, T. R., Louzada, F., & Petropoulos,
           F. (2015). The optimized theta method. arXiv preprint
           arXiv:1503.03529.
        """
        pass

    def forecast_components(self, steps: int=1) -> pd.DataFrame:
        """
        Compute the three components of the Theta model forecast

        Parameters
        ----------
        steps : int
            The number of steps ahead to compute the forecast components.

        Returns
        -------
        DataFrame
            A DataFrame with three columns: trend, ses and seasonal containing
            the forecast values of each of the three components.

        Notes
        -----
        For a given value of :math:`\\theta`, the deseasonalized forecast is
        `fcast = w * trend + ses` where :math:`w = \\frac{theta - 1}{theta}`.
        The reseasonalized forecasts are then `seasonal * fcast` if the
        seasonality is multiplicative or `seasonal + fcast` if the seasonality
        is additive.
        """
        pass

    def summary(self) -> Summary:
        """
        Summarize the model

        Returns
        -------
        Summary
            This holds the summary table and text, which can be printed or
            converted to various output formats.

        See Also
        --------
        statsmodels.iolib.summary.Summary
        """
        pass

    def prediction_intervals(self, steps: int=1, theta: float=2, alpha: float=0.05) -> pd.DataFrame:
        """
        Parameters
        ----------
        steps : int, default 1
            The number of steps ahead to compute the forecast components.
        theta : float, default 2
            The theta value to use when computing the weight to combine
            the trend and the SES forecasts.
        alpha : float, default 0.05
            Significance level for the confidence intervals.

        Returns
        -------
        DataFrame
            DataFrame with columns lower and upper

        Notes
        -----
        The variance of the h-step forecast is assumed to follow from the
        integrated Moving Average structure of the Theta model, and so is
        :math:`\\sigma^2(1 + (h-1)(1 + (\\alpha-1)^2)`. The prediction interval
        assumes that innovations are normally distributed.
        """
        pass

    def plot_predict(self, steps: int=1, theta: float=2, alpha: Optional[float]=0.05, in_sample: bool=False, fig: Optional['matplotlib.figure.Figure']=None, figsize: Tuple[float, float]=None) -> 'matplotlib.figure.Figure':
        """
        Plot forecasts, prediction intervals and in-sample values

        Parameters
        ----------
        steps : int, default 1
            The number of steps ahead to compute the forecast components.
        theta : float, default 2
            The theta value to use when computing the weight to combine
            the trend and the SES forecasts.
        alpha : {float, None}, default 0.05
            The tail probability not covered by the confidence interval. Must
            be in (0, 1). Confidence interval is constructed assuming normally
            distributed shocks. If None, figure will not show the confidence
            interval.
        in_sample : bool, default False
            Flag indicating whether to include the in-sample period in the
            plot.
        fig : Figure, default None
            An existing figure handle. If not provided, a new figure is
            created.
        figsize: tuple[float, float], default None
            Tuple containing the figure size.

        Returns
        -------
        Figure
            Figure handle containing the plot.

        Notes
        -----
        The variance of the h-step forecast is assumed to follow from the
        integrated Moving Average structure of the Theta model, and so is
        :math:`\\sigma^2(\\alpha^2 + (h-1))`. The prediction interval assumes
        that innovations are normally distributed.
        """
        pass