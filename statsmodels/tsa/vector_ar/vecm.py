from collections import defaultdict
import numpy as np
from numpy import hstack, vstack
from numpy.linalg import inv, svd
import scipy
import scipy.stats
from statsmodels.iolib.summary import Summary
from statsmodels.iolib.table import SimpleTable
from statsmodels.tools.decorators import cache_readonly
from statsmodels.tools.sm_exceptions import HypothesisTestWarning
from statsmodels.tools.validation import string_like
import statsmodels.tsa.base.tsa_model as tsbase
from statsmodels.tsa.coint_tables import c_sja, c_sjt
from statsmodels.tsa.tsatools import duplication_matrix, lagmat, vec
from statsmodels.tsa.vector_ar.hypothesis_test_results import CausalityTestResults, WhitenessTestResults
import statsmodels.tsa.vector_ar.irf as irf
import statsmodels.tsa.vector_ar.plotting as plot
from statsmodels.tsa.vector_ar.util import get_index, seasonal_dummies
from statsmodels.tsa.vector_ar.var_model import VAR, LagOrderResults, _compute_acov, forecast, forecast_interval, ma_rep, orth_ma_rep, test_normality

def select_order(data, maxlags: int, deterministic: str='n', seasons: int=0, exog=None, exog_coint=None):
    """
    Compute lag order selections based on each of the available information
    criteria.

    Parameters
    ----------
    data : array_like (nobs_tot x neqs)
        The observed data.
    maxlags : int
        All orders until maxlag will be compared according to the information
        criteria listed in the Results-section of this docstring.
    deterministic : str {"n", "co", "ci", "lo", "li"}
        * ``"n"`` - no deterministic terms
        * ``"co"`` - constant outside the cointegration relation
        * ``"ci"`` - constant within the cointegration relation
        * ``"lo"`` - linear trend outside the cointegration relation
        * ``"li"`` - linear trend within the cointegration relation

        Combinations of these are possible (e.g. ``"cili"`` or ``"colo"`` for
        linear trend with intercept). See the docstring of the
        :class:`VECM`-class for more information.
    seasons : int, default: 0
        Number of periods in a seasonal cycle.
    exog : ndarray (nobs_tot x neqs) or `None`, default: `None`
        Deterministic terms outside the cointegration relation.
    exog_coint : ndarray (nobs_tot x neqs) or `None`, default: `None`
        Deterministic terms inside the cointegration relation.

    Returns
    -------
    selected_orders : :class:`statsmodels.tsa.vector_ar.var_model.LagOrderResults`
    """
    pass

def _linear_trend(nobs, k_ar, coint=False):
    """
    Construct an ndarray representing a linear trend in a VECM.

    Parameters
    ----------
    nobs : int
        Number of observations excluding the presample.
    k_ar : int
        Number of lags in levels.
    coint : bool, default: False
        If True (False), the returned array represents a linear trend inside
        (outside) the cointegration relation.

    Returns
    -------
    ret : ndarray (nobs)
        An ndarray representing a linear trend in a VECM

    Notes
    -----
    The returned array's size is nobs and not nobs_tot so it cannot be used to
    construct the exog-argument of VECM's __init__ method.
    """
    pass

def _num_det_vars(det_string, seasons=0):
    """Gives the number of deterministic variables specified by det_string and
    seasons.

    Parameters
    ----------
    det_string : str {"n", "co", "ci", "lo", "li"}
        * "n" - no deterministic terms
        * "co" - constant outside the cointegration relation
        * "ci" - constant within the cointegration relation
        * "lo" - linear trend outside the cointegration relation
        * "li" - linear trend within the cointegration relation

        Combinations of these are possible (e.g. "cili" or "colo" for linear
        trend with intercept). See the docstring of the :class:`VECM`-class for
        more information.
    seasons : int
        Number of periods in a seasonal cycle.

    Returns
    -------
    num : int
        Number of deterministic terms and number dummy variables for seasonal
        terms.
    """
    pass

def _deterministic_to_exog(deterministic, seasons, nobs_tot, first_season=0, seasons_centered=False, exog=None, exog_coint=None):
    """
    Translate all information about deterministic terms into a single array.

    These information is taken from `deterministic` and `seasons` as well as
    from the `exog` and `exog_coint` arrays. The resulting array form can then
    be used e.g. in VAR's __init__ method.

    Parameters
    ----------
    deterministic : str
        A string specifying the deterministic terms in the model. See VECM's
        docstring for more information.
    seasons : int
        Number of periods in a seasonal cycle.
    nobs_tot : int
        Number of observations including the presample.
    first_season : int, default: 0
        Season of the first observation.
    seasons_centered : bool, default: False
        If True, the seasonal dummy variables are demeaned such that they are
        orthogonal to an intercept term.
    exog : ndarray (nobs_tot x #det_terms) or None, default: None
        An ndarray representing deterministic terms outside the cointegration
        relation.
    exog_coint : ndarray (nobs_tot x #det_terms_coint) or None, default: None
        An ndarray representing deterministic terms inside the cointegration
        relation.

    Returns
    -------
    exog : ndarray or None
        None, if the function's arguments do not contain deterministic terms.
        Otherwise, an ndarray representing these deterministic terms.
    """
    pass

def _mat_sqrt(_2darray):
    """Calculates the square root of a matrix.

    Parameters
    ----------
    _2darray : ndarray
        A 2-dimensional ndarray representing a square matrix.

    Returns
    -------
    result : ndarray
        Square root of the matrix given as function argument.
    """
    pass

def _endog_matrices(endog, exog, exog_coint, diff_lags, deterministic, seasons=0, first_season=0):
    """
    Returns different matrices needed for parameter estimation.

    Compare p. 186 in [1]_. The returned matrices consist of elements of the
    data as well as elements representing deterministic terms. A tuple of
    consisting of these matrices is returned.

    Parameters
    ----------
    endog : ndarray (neqs x nobs_tot)
        The whole sample including the presample.
    exog : ndarray (nobs_tot x neqs) or None
        Deterministic terms outside the cointegration relation.
    exog_coint : ndarray (nobs_tot x neqs) or None
        Deterministic terms inside the cointegration relation.
    diff_lags : int
        Number of lags in the VEC representation.
    deterministic : str {``"n"``, ``"co"``, ``"ci"``, ``"lo"``, ``"li"``}
        * ``"n"`` - no deterministic terms
        * ``"co"`` - constant outside the cointegration relation
        * ``"ci"`` - constant within the cointegration relation
        * ``"lo"`` - linear trend outside the cointegration relation
        * ``"li"`` - linear trend within the cointegration relation

        Combinations of these are possible (e.g. ``"cili"`` or ``"colo"`` for
        linear trend with intercept). See the docstring of the
        :class:`VECM`-class for more information.
    seasons : int, default: 0
        Number of periods in a seasonal cycle. 0 (default) means no seasons.
    first_season : int, default: 0
        The season of the first observation. `0` means first season, `1` means
        second season, ..., `seasons-1` means the last season.

    Returns
    -------
    y_1_T : ndarray (neqs x nobs)
        The (transposed) data without the presample.
        `.. math:: (y_1, \\ldots, y_T)
    delta_y_1_T : ndarray (neqs x nobs)
        The first differences of endog.
        `.. math:: (y_1, \\ldots, y_T) - (y_0, \\ldots, y_{T-1})
    y_lag1 : ndarray (neqs x nobs)
        (dimensions assuming no deterministic terms are given)
        Endog of the previous period (lag 1).
        `.. math:: (y_0, \\ldots, y_{T-1})
    delta_x : ndarray (k_ar_diff*neqs x nobs)
        (dimensions assuming no deterministic terms are given)
        Lagged differenced endog, used as regressor for the short term
        equation.

    References
    ----------
    .. [1] Lütkepohl, H. 2005. *New Introduction to Multiple Time Series Analysis*. Springer.
    """
    pass

def _r_matrices(delta_y_1_T, y_lag1, delta_x):
    """Returns two ndarrays needed for parameter estimation as well as the
    calculation of standard errors.

    Parameters
    ----------
    delta_y_1_T : ndarray (neqs x nobs)
        The first differences of endog.
        `.. math:: (y_1, \\ldots, y_T) - (y_0, \\ldots, y_{T-1})
    y_lag1 : ndarray (neqs x nobs)
        (dimensions assuming no deterministic terms are given)
        Endog of the previous period (lag 1).
        `.. math:: (y_0, \\ldots, y_{T-1})
    delta_x : ndarray (k_ar_diff*neqs x nobs)
        (dimensions assuming no deterministic terms are given)
        Lagged differenced endog, used as regressor for the short term
        equation.

    Returns
    -------
    result : tuple
        A tuple of two ndarrays. (See p. 292 in [1]_ for the definition of
        R_0 and R_1.)

    References
    ----------
    .. [1] Lütkepohl, H. 2005. *New Introduction to Multiple Time Series Analysis*. Springer.
    """
    pass

def _sij(delta_x, delta_y_1_T, y_lag1):
    """Returns matrices and eigenvalues and -vectors used for parameter
    estimation and the calculation of a models loglikelihood.

    Parameters
    ----------
    delta_x : ndarray (k_ar_diff*neqs x nobs)
        (dimensions assuming no deterministic terms are given)
    delta_y_1_T : ndarray (neqs x nobs)
        :math:`(y_1, \\ldots, y_T) - (y_0, \\ldots, y_{T-1})`
    y_lag1 : ndarray (neqs x nobs)
        (dimensions assuming no deterministic terms are given)
        :math:`(y_0, \\ldots, y_{T-1})`

    Returns
    -------
    result : tuple
        A tuple of five ndarrays as well as eigenvalues and -vectors of a
        certain (matrix) product of some of the returned ndarrays.
        (See pp. 294-295 in [1]_ for more information on
        :math:`S_0, S_1, \\lambda_i, \\v_i` for
        :math:`i \\in \\{1, \\dots, K\\}`.)

    References
    ----------
    .. [1] Lütkepohl, H. 2005. *New Introduction to Multiple Time Series Analysis*. Springer.
    """
    pass

class CointRankResults:
    """A class for holding the results from testing the cointegration rank.

    Parameters
    ----------
    rank : int (0 <= `rank` <= `neqs`)
        The rank to choose according to the Johansen cointegration rank
        test.
    neqs : int
        Number of variables in the time series.
    test_stats : array_like (`rank` + 1 if `rank` < `neqs` else `rank`)
        A one-dimensional array-like object containing the test statistics of
        the conducted tests.
    crit_vals : array_like (`rank` +1 if `rank` < `neqs` else `rank`)
        A one-dimensional array-like object containing the critical values
        corresponding to the entries in the `test_stats` argument.
    method : str, {``"trace"``, ``"maxeig"``}, default: ``"trace"``
        If ``"trace"``, the trace test statistic is used. If ``"maxeig"``, the
        maximum eigenvalue test statistic is used.
    signif : float, {0.1, 0.05, 0.01}, default: 0.05
        The test's significance level.
    """

    def __init__(self, rank, neqs, test_stats, crit_vals, method='trace', signif=0.05):
        self.rank = rank
        self.neqs = neqs
        self.r_1 = [neqs if method == 'trace' else i + 1 for i in range(min(rank + 1, neqs))]
        self.test_stats = test_stats
        self.crit_vals = crit_vals
        self.method = method
        self.signif = signif

    def __str__(self):
        return self.summary().as_text()

def select_coint_rank(endog, det_order, k_ar_diff, method='trace', signif=0.05):
    """Calculate the cointegration rank of a VECM.

    Parameters
    ----------
    endog : array_like (nobs_tot x neqs)
        The data with presample.
    det_order : int
        * -1 - no deterministic terms
        * 0 - constant term
        * 1 - linear trend
    k_ar_diff : int, nonnegative
        Number of lagged differences in the model.
    method : str, {``"trace"``, ``"maxeig"``}, default: ``"trace"``
        If ``"trace"``, the trace test statistic is used. If ``"maxeig"``, the
        maximum eigenvalue test statistic is used.
    signif : float, {0.1, 0.05, 0.01}, default: 0.05
        The test's significance level.

    Returns
    -------
    rank : :class:`CointRankResults`
        A :class:`CointRankResults` object containing the cointegration rank suggested
        by the test and allowing a summary to be printed.
    """
    pass

def coint_johansen(endog, det_order, k_ar_diff):
    """
    Johansen cointegration test of the cointegration rank of a VECM

    Parameters
    ----------
    endog : array_like (nobs_tot x neqs)
        Data to test
    det_order : int
        * -1 - no deterministic terms
        * 0 - constant term
        * 1 - linear trend
    k_ar_diff : int, nonnegative
        Number of lagged differences in the model.

    Returns
    -------
    result : JohansenTestResult
        An object containing the test's results. The most important attributes
        of the result class are:

        * trace_stat and trace_stat_crit_vals
        * max_eig_stat and max_eig_stat_crit_vals

    Notes
    -----
    The implementation might change to make more use of the existing VECM
    framework.

    See Also
    --------
    statsmodels.tsa.vector_ar.vecm.select_coint_rank

    References
    ----------
    .. [1] Lütkepohl, H. 2005. New Introduction to Multiple Time Series
        Analysis. Springer.
    """
    pass

class JohansenTestResult:
    """
    Results class for Johansen's cointegration test

    Notes
    -----
    See p. 292 in [1]_ for r0t and rkt

    References
    ----------
    .. [1] Lütkepohl, H. 2005. New Introduction to Multiple Time Series
        Analysis. Springer.
    """

    def __init__(self, rkt, r0t, eig, evec, lr1, lr2, cvt, cvm, ind):
        self._meth = 'johansen'
        self._rkt = rkt
        self._r0t = r0t
        self._eig = eig
        self._evec = evec
        self._lr1 = lr1
        self._lr2 = lr2
        self._cvt = cvt
        self._cvm = cvm
        self._ind = ind

    @property
    def rkt(self):
        """Residuals for :math:`Y_{-1}`"""
        pass

    @property
    def r0t(self):
        """Residuals for :math:`\\Delta Y`."""
        pass

    @property
    def eig(self):
        """Eigenvalues of VECM coefficient matrix"""
        pass

    @property
    def evec(self):
        """Eigenvectors of VECM coefficient matrix"""
        pass

    @property
    def trace_stat(self):
        """Trace statistic"""
        pass

    @property
    def lr1(self):
        """Trace statistic"""
        pass

    @property
    def max_eig_stat(self):
        """Maximum eigenvalue statistic"""
        pass

    @property
    def lr2(self):
        """Maximum eigenvalue statistic"""
        pass

    @property
    def trace_stat_crit_vals(self):
        """Critical values (90%, 95%, 99%) of trace statistic"""
        pass

    @property
    def cvt(self):
        """Critical values (90%, 95%, 99%) of trace statistic"""
        pass

    @property
    def cvm(self):
        """Critical values (90%, 95%, 99%) of maximum eigenvalue statistic."""
        pass

    @property
    def max_eig_stat_crit_vals(self):
        """Critical values (90%, 95%, 99%) of maximum eigenvalue statistic."""
        pass

    @property
    def ind(self):
        """Order of eigenvalues"""
        pass

    @property
    def meth(self):
        """Test method"""
        pass

class VECM(tsbase.TimeSeriesModel):
    """
    Class representing a Vector Error Correction Model (VECM).

    A VECM(:math:`k_{ar}-1`) has the following form

    .. math:: \\Delta y_t = \\Pi y_{t-1} + \\Gamma_1 \\Delta y_{t-1} + \\ldots + \\Gamma_{k_{ar}-1} \\Delta y_{t-k_{ar}+1} + u_t

    where

    .. math:: \\Pi = \\alpha \\beta'

    as described in chapter 7 of [1]_.

    Parameters
    ----------
    endog : array_like (nobs_tot x neqs)
        2-d endogenous response variable.
    exog : ndarray (nobs_tot x neqs) or None
        Deterministic terms outside the cointegration relation.
    exog_coint : ndarray (nobs_tot x neqs) or None
        Deterministic terms inside the cointegration relation.
    dates : array_like of datetime, optional
        See :class:`statsmodels.tsa.base.tsa_model.TimeSeriesModel` for more
        information.
    freq : str, optional
        See :class:`statsmodels.tsa.base.tsa_model.TimeSeriesModel` for more
        information.
    missing : str, optional
        See :class:`statsmodels.base.model.Model` for more information.
    k_ar_diff : int
        Number of lagged differences in the model. Equals :math:`k_{ar} - 1` in
        the formula above.
    coint_rank : int
        Cointegration rank, equals the rank of the matrix :math:`\\Pi` and the
        number of columns of :math:`\\alpha` and :math:`\\beta`.
    deterministic : str {``"n"``, ``"co"``, ``"ci"``, ``"lo"``, ``"li"``}
        * ``"n"`` - no deterministic terms
        * ``"co"`` - constant outside the cointegration relation
        * ``"ci"`` - constant within the cointegration relation
        * ``"lo"`` - linear trend outside the cointegration relation
        * ``"li"`` - linear trend within the cointegration relation

        Combinations of these are possible (e.g. ``"cili"`` or ``"colo"`` for
        linear trend with intercept). When using a constant term you have to
        choose whether you want to restrict it to the cointegration relation
        (i.e. ``"ci"``) or leave it unrestricted (i.e. ``"co"``). Do not use
        both ``"ci"`` and ``"co"``. The same applies for ``"li"`` and ``"lo"``
        when using a linear term. See the Notes-section for more information.
    seasons : int, default: 0
        Number of periods in a seasonal cycle. 0 means no seasons.
    first_season : int, default: 0
        Season of the first observation.

    Notes
    -----
    A VECM(:math:`k_{ar} - 1`) with deterministic terms has the form

    .. math::

       \\Delta y_t = \\alpha \\begin{pmatrix}\\beta' & \\eta'\\end{pmatrix} \\begin{pmatrix}y_{t-1}\\\\D^{co}_{t-1}\\end{pmatrix} + \\Gamma_1 \\Delta y_{t-1} + \\dots + \\Gamma_{k_{ar}-1} \\Delta y_{t-k_{ar}+1} + C D_t + u_t.

    In :math:`D^{co}_{t-1}` we have the deterministic terms which are inside
    the cointegration relation (or restricted to the cointegration relation).
    :math:`\\eta` is the corresponding estimator. To pass a deterministic term
    inside the cointegration relation, we can use the `exog_coint` argument.
    For the two special cases of an intercept and a linear trend there exists
    a simpler way to declare these terms: we can pass ``"ci"`` and ``"li"``
    respectively to the `deterministic` argument. So for an intercept inside
    the cointegration relation we can either pass ``"ci"`` as `deterministic`
    or `np.ones(len(data))` as `exog_coint` if `data` is passed as the
    `endog` argument. This ensures that :math:`D_{t-1}^{co} = 1` for all
    :math:`t`.

    We can also use deterministic terms outside the cointegration relation.
    These are defined in :math:`D_t` in the formula above with the
    corresponding estimators in the matrix :math:`C`. We specify such terms by
    passing them to the `exog` argument. For an intercept and/or linear trend
    we again have the possibility to use `deterministic` alternatively. For
    an intercept we pass ``"co"`` and for a linear trend we pass ``"lo"`` where
    the `o` stands for `outside`.

    The following table shows the five cases considered in [2]_. The last
    column indicates which string to pass to the `deterministic` argument for
    each of these cases.

    ====  ===============================  ===================================  =============
    Case  Intercept                        Slope of the linear trend            `deterministic`
    ====  ===============================  ===================================  =============
    I     0                                0                                    ``"n"``
    II    :math:`- \\alpha \\beta^T \\mu`     0                                    ``"ci"``
    III   :math:`\\neq 0`                   0                                    ``"co"``
    IV    :math:`\\neq 0`                   :math:`- \\alpha \\beta^T \\gamma`      ``"coli"``
    V     :math:`\\neq 0`                   :math:`\\neq 0`                       ``"colo"``
    ====  ===============================  ===================================  =============

    References
    ----------
    .. [1] Lütkepohl, H. 2005. *New Introduction to Multiple Time Series Analysis*. Springer.

    .. [2] Johansen, S. 1995. *Likelihood-Based Inference in Cointegrated *
           *Vector Autoregressive Models*. Oxford University Press.
    """

    def __init__(self, endog, exog=None, exog_coint=None, dates=None, freq=None, missing='none', k_ar_diff=1, coint_rank=1, deterministic='n', seasons=0, first_season=0):
        super().__init__(endog, exog, dates, freq, missing=missing)
        if exog_coint is not None and (not exog_coint.shape[0] == endog.shape[0]):
            raise ValueError('exog_coint must have as many rows as enodg_tot!')
        if self.endog.ndim == 1:
            raise ValueError('Only gave one variable to VECM')
        self.y = self.endog.T
        self.exog_coint = exog_coint
        self.neqs = self.endog.shape[1]
        self.k_ar = k_ar_diff + 1
        self.k_ar_diff = k_ar_diff
        self.coint_rank = coint_rank
        self.deterministic = deterministic
        self.seasons = seasons
        self.first_season = first_season
        self.load_coef_repr = 'ec'

    def fit(self, method='ml'):
        """
        Estimates the parameters of a VECM.

        The estimation procedure is described on pp. 269-304 in [1]_.

        Parameters
        ----------
        method : str {"ml"}, default: "ml"
            Estimation method to use. "ml" stands for Maximum Likelihood.

        Returns
        -------
        est : :class:`VECMResults`

        References
        ----------
        .. [1] Lütkepohl, H. 2005. *New Introduction to Multiple Time Series Analysis*. Springer.
        """
        pass

    @property
    def _lagged_param_names(self):
        """
        Returns parameter names (for Gamma and deterministics) for the summary.

        Returns
        -------
        param_names : list of str
            Returns a list of parameter names for the lagged endogenous
            parameters which are called :math:`\\Gamma` in [1]_
            (see chapter 6).
            If present in the model, also names for deterministic terms outside
            the cointegration relation are returned. They name the elements of
            the matrix C in [1]_ (p. 299).

        References
        ----------
        .. [1] Lütkepohl, H. 2005. *New Introduction to Multiple Time Series Analysis*. Springer.
        """
        pass

    @property
    def _load_coef_param_names(self):
        """
        Returns parameter names (for alpha) for the summary.

        Returns
        -------
        param_names : list of str
            Returns a list of parameter names for the loading coefficients
            which are called :math:`\\alpha` in [1]_ (see chapter 6).

        References
        ----------
        .. [1] Lütkepohl, H. 2005. *New Introduction to Multiple Time Series Analysis*. Springer.
        """
        pass

    @property
    def _coint_param_names(self):
        """
        Returns parameter names (for beta and deterministics) for the summary.

        Returns
        -------
        param_names : list of str
            Returns a list of parameter names for the cointegration matrix
            as well as deterministic terms inside the cointegration relation
            (if present in the model).
        """
        pass

class VECMResults:
    """Class for holding estimation related results of a vector error
    correction model (VECM).

    Parameters
    ----------
    endog : ndarray (neqs x nobs_tot)
        Array of observations.
    exog : ndarray (nobs_tot x neqs) or `None`
        Deterministic terms outside the cointegration relation.
    exog_coint : ndarray (nobs_tot x neqs) or `None`
        Deterministic terms inside the cointegration relation.
    k_ar : int, >= 1
        Lags in the VAR representation. This implies that the number of lags in
        the VEC representation (=lagged differences) equals :math:`k_{ar} - 1`.
    coint_rank : int, 0 <= `coint_rank` <= neqs
        Cointegration rank, equals the rank of the matrix :math:`\\Pi` and the
        number of columns of :math:`\\alpha` and :math:`\\beta`.
    alpha : ndarray (neqs x `coint_rank`)
        Estimate for the parameter :math:`\\alpha` of a VECM.
    beta : ndarray (neqs x `coint_rank`)
        Estimate for the parameter :math:`\\beta` of a VECM.
    gamma : ndarray (neqs x neqs*(k_ar-1))
        Array containing the estimates of the :math:`k_{ar}-1` parameter
        matrices :math:`\\Gamma_1, \\dots, \\Gamma_{k_{ar}-1}` of a
        VECM(:math:`k_{ar}-1`). The submatrices are stacked horizontally from
        left to right.
    sigma_u : ndarray (neqs x neqs)
        Estimate of white noise process covariance matrix :math:`\\Sigma_u`.
    deterministic : str {``"n"``, ``"co"``, ``"ci"``, ``"lo"``, ``"li"``}
        * ``"n"`` - no deterministic terms
        * ``"co"`` - constant outside the cointegration relation
        * ``"ci"`` - constant within the cointegration relation
        * ``"lo"`` - linear trend outside the cointegration relation
        * ``"li"`` - linear trend within the cointegration relation

        Combinations of these are possible (e.g. ``"cili"`` or ``"colo"`` for
        linear trend with intercept). See the docstring of the
        :class:`VECM`-class for more information.
    seasons : int, default: 0
        Number of periods in a seasonal cycle. 0 means no seasons.
    first_season : int, default: 0
        Season of the first observation.
    delta_y_1_T : ndarray or `None`, default: `None`
        Auxiliary array for internal computations. It will be calculated if
        not given as parameter.
    y_lag1 : ndarray or `None`, default: `None`
        Auxiliary array for internal computations. It will be calculated if
        not given as parameter.
    delta_x : ndarray or `None`, default: `None`
        Auxiliary array for internal computations. It will be calculated if
        not given as parameter.
    model : :class:`VECM`
        An instance of the :class:`VECM`-class.
    names : list of str
        Each str in the list represents the name of a variable of the time
        series.
    dates : array_like
        For example a DatetimeIndex of length nobs_tot.

    Attributes
    ----------
    nobs : int
        Number of observations (excluding the presample).
    model : see Parameters
    y_all : see `endog` in Parameters
    exog : see Parameters
    exog_coint : see Parameters
    names : see Parameters
    dates : see Parameters
    neqs : int
        Number of variables in the time series.
    k_ar : see Parameters
    deterministic : see Parameters
    seasons : see Parameters
    first_season : see Parameters
    alpha : see Parameters
    beta : see Parameters
    gamma : see Parameters
    sigma_u : see Parameters
    det_coef_coint : ndarray (#(determinist. terms inside the coint. rel.) x `coint_rank`)
        Estimated coefficients for the all deterministic terms inside the
        cointegration relation.
    const_coint : ndarray (1 x `coint_rank`)
        If there is a constant deterministic term inside the cointegration
        relation, then `const_coint` is the first row of `det_coef_coint`.
        Otherwise it's an ndarray of zeros.
    lin_trend_coint : ndarray (1 x `coint_rank`)
        If there is a linear deterministic term inside the cointegration
        relation, then `lin_trend_coint` contains the corresponding estimated
        coefficients. As such it represents the corresponding row of
        `det_coef_coint`. If there is no linear deterministic term inside
        the cointegration relation, then `lin_trend_coint` is an ndarray of
        zeros.
    exog_coint_coefs : ndarray (exog_coint.shape[1] x `coint_rank`) or `None`
        If deterministic terms inside the cointegration relation are passed via
        the `exog_coint` parameter, then `exog_coint_coefs` contains the
        corresponding estimated coefficients. As such `exog_coint_coefs`
        represents the last rows of `det_coef_coint`.
        If no deterministic terms were passed via the `exog_coint` parameter,
        this attribute is `None`.
    det_coef : ndarray (neqs x #(deterministic terms outside the coint. rel.))
        Estimated coefficients for the all deterministic terms outside the
        cointegration relation.
    const : ndarray (neqs x 1) or (neqs x 0)
        If a constant deterministic term outside the cointegration is specified
        within the deterministic parameter, then `const` is the first column
        of `det_coef_coint`. Otherwise it's an ndarray of size zero.
    seasonal : ndarray (neqs x seasons)
        If the `seasons` parameter is > 0, then seasonal contains the
        estimated coefficients corresponding to the seasonal terms. Otherwise
        it's an ndarray of size zero.
    lin_trend : ndarray (neqs x 1) or (neqs x 0)
        If a linear deterministic term outside the cointegration is specified
        within the deterministic parameter, then `lin_trend` contains the
        corresponding estimated coefficients. As such it represents the
        corresponding column of `det_coef_coint`. If there is no linear
        deterministic term outside the cointegration relation, then
        `lin_trend` is an ndarray of size zero.
    exog_coefs : ndarray (neqs x exog_coefs.shape[1])
        If deterministic terms outside the cointegration relation are passed
        via the `exog` parameter, then `exog_coefs` contains the
        corresponding estimated coefficients. As such `exog_coefs` represents
        the last columns of `det_coef`.
        If no deterministic terms were passed via the `exog` parameter, this
        attribute is an ndarray of size zero.
    _delta_y_1_T : see delta_y_1_T in Parameters
    _y_lag1 : see y_lag1 in Parameters
    _delta_x : see delta_x in Parameters
    coint_rank : int
        Cointegration rank, equals the rank of the matrix :math:`\\Pi` and the
        number of columns of :math:`\\alpha` and :math:`\\beta`.
    llf : float
        The model's log-likelihood.
    cov_params : ndarray (d x d)
        Covariance matrix of the parameters. The number of rows and columns, d
        (used in the dimension specification of this argument),
        is equal to neqs * (neqs+num_det_coef_coint + neqs*(k_ar-1)+number of
        deterministic dummy variables outside the cointegration relation). For
        the case with no deterministic terms this matrix is defined on p. 287
        in [1]_ as :math:`\\Sigma_{co}` and its relationship to the
        ML-estimators can be seen in eq. (7.2.21) on p. 296 in [1]_.
    cov_params_wo_det : ndarray
        Covariance matrix of the parameters
        :math:`\\tilde{\\Pi}, \\tilde{\\Gamma}` where
        :math:`\\tilde{\\Pi} = \\tilde{\\alpha} \\tilde{\\beta'}`.
        Equals `cov_params` without the rows and columns related to
        deterministic terms. This matrix is defined as :math:`\\Sigma_{co}` on
        p. 287 in [1]_.
    stderr_params : ndarray (d)
        Array containing the standard errors of :math:`\\Pi`, :math:`\\Gamma`,
        and estimated parameters related to deterministic terms.
    stderr_coint : ndarray (neqs+num_det_coef_coint x `coint_rank`)
        Array containing the standard errors of :math:`\\beta` and estimated
        parameters related to deterministic terms inside the cointegration
        relation.
    stderr_alpha :  ndarray (neqs x `coint_rank`)
        The standard errors of :math:`\\alpha`.
    stderr_beta : ndarray (neqs x `coint_rank`)
        The standard errors of :math:`\\beta`.
    stderr_det_coef_coint : ndarray (num_det_coef_coint x `coint_rank`)
        The standard errors of estimated the parameters related to
        deterministic terms inside the cointegration relation.
    stderr_gamma : ndarray (neqs x neqs*(k_ar-1))
        The standard errors of :math:`\\Gamma_1, \\ldots, \\Gamma_{k_{ar}-1}`.
    stderr_det_coef : ndarray (neqs x det. terms outside the coint. relation)
        The standard errors of estimated the parameters related to
        deterministic terms outside the cointegration relation.
    tvalues_alpha : ndarray (neqs x `coint_rank`)
    tvalues_beta : ndarray (neqs x `coint_rank`)
    tvalues_det_coef_coint : ndarray (num_det_coef_coint x `coint_rank`)
    tvalues_gamma : ndarray (neqs x neqs*(k_ar-1))
    tvalues_det_coef : ndarray (neqs x det. terms outside the coint. relation)
    pvalues_alpha : ndarray (neqs x `coint_rank`)
    pvalues_beta : ndarray (neqs x `coint_rank`)
    pvalues_det_coef_coint : ndarray (num_det_coef_coint x `coint_rank`)
    pvalues_gamma : ndarray (neqs x neqs*(k_ar-1))
    pvalues_det_coef : ndarray (neqs x det. terms outside the coint. relation)
    var_rep : (k_ar x neqs x neqs)
        KxK parameter matrices :math:`A_i` of the corresponding VAR
        representation. If the return value is assigned to a variable ``A``,
        these matrices can be accessed via ``A[i]`` for
        :math:`i=0, \\ldots, k_{ar}-1`.
    cov_var_repr : ndarray (neqs**2 * k_ar x neqs**2 * k_ar)
        This matrix is called :math:`\\Sigma^{co}_{\\alpha}` on p. 289 in [1]_.
        It is needed e.g. for impulse-response-analysis.
    fittedvalues : ndarray (nobs x neqs)
        The predicted in-sample values of the models' endogenous variables.
    resid : ndarray (nobs x neqs)
        The residuals.

    References
    ----------
    .. [1] Lütkepohl, H. 2005. *New Introduction to Multiple Time Series Analysis*. Springer.
    """

    def __init__(self, endog, exog, exog_coint, k_ar, coint_rank, alpha, beta, gamma, sigma_u, deterministic='n', seasons=0, first_season=0, delta_y_1_T=None, y_lag1=None, delta_x=None, model=None, names=None, dates=None):
        self.model = model
        self.y_all = endog
        self.exog = exog
        self.exog_coint = exog_coint
        self.names = names
        self.dates = dates
        self.neqs = endog.shape[0]
        self.k_ar = k_ar
        deterministic = string_like(deterministic, 'deterministic')
        self.deterministic = deterministic
        self.seasons = seasons
        self.first_season = first_season
        self.coint_rank = coint_rank
        if alpha.dtype == np.complex128 and np.all(np.imag(alpha) == 0):
            alpha = np.real_if_close(alpha)
        if beta.dtype == np.complex128 and np.all(np.imag(beta) == 0):
            beta = np.real_if_close(beta)
        if gamma.dtype == np.complex128 and np.all(np.imag(gamma) == 0):
            gamma = np.real_if_close(gamma)
        self.alpha = alpha
        self.beta, self.det_coef_coint = np.vsplit(beta, [self.neqs])
        self.gamma, self.det_coef = np.hsplit(gamma, [self.neqs * (self.k_ar - 1)])
        if 'ci' in deterministic:
            self.const_coint = self.det_coef_coint[:1, :]
        else:
            self.const_coint = np.zeros(coint_rank).reshape((1, -1))
        if 'li' in deterministic:
            start = 1 if 'ci' in deterministic else 0
            self.lin_trend_coint = self.det_coef_coint[start:start + 1, :]
        else:
            self.lin_trend_coint = np.zeros(coint_rank).reshape(1, -1)
        if self.exog_coint is not None:
            start = ('ci' in deterministic) + ('li' in deterministic)
            self.exog_coint_coefs = self.det_coef_coint[start:, :]
        else:
            self.exog_coint_coefs = None
        split_const_season = 1 if 'co' in deterministic else 0
        split_season_lin = split_const_season + (seasons - 1 if seasons else 0)
        if 'lo' in deterministic:
            split_lin_exog = split_season_lin + 1
        else:
            split_lin_exog = split_season_lin
        self.const, self.seasonal, self.lin_trend, self.exog_coefs = np.hsplit(self.det_coef, [split_const_season, split_season_lin, split_lin_exog])
        self.sigma_u = sigma_u
        if y_lag1 is not None and delta_x is not None and (delta_y_1_T is not None):
            self._delta_y_1_T = delta_y_1_T
            self._y_lag1 = y_lag1
            self._delta_x = delta_x
        else:
            _y_1_T, self._delta_y_1_T, self._y_lag1, self._delta_x = _endog_matrices(endog, self.exog, k_ar, deterministic, seasons)
        self.nobs = self._y_lag1.shape[1]

    @cache_readonly
    def llf(self):
        """
        Compute the VECM's loglikelihood.
        """
        pass

    @cache_readonly
    def stderr_coint(self):
        """
        Standard errors of beta and deterministic terms inside the
        cointegration relation.

        Notes
        -----
        See p. 297 in [1]_. Using the rule

        .. math::

           vec(B R) = (B' \\otimes I) vec(R)

        for two matrices B and R which are compatible for multiplication.
        This is rule (3) on p. 662 in [1]_.

        References
        ----------
        .. [1] Lütkepohl, H. 2005. *New Introduction to Multiple Time Series Analysis*. Springer.
        """
        pass

    @cache_readonly
    def cov_var_repr(self):
        """
        Gives the covariance matrix of the corresponding VAR-representation.

        More precisely, the covariance matrix of the vector consisting of the
        columns of the corresponding VAR coefficient matrices (i.e.
        vec(self.var_rep)).

        Returns
        -------
        cov : array (neqs**2 * k_ar x neqs**2 * k_ar)
        """
        pass

    def orth_ma_rep(self, maxn=10, P=None):
        """Compute orthogonalized MA coefficient matrices.

        For this purpose a matrix  P is used which fulfills
        :math:`\\Sigma_u = PP^\\prime`. P defaults to the Cholesky
        decomposition of :math:`\\Sigma_u`

        Parameters
        ----------
        maxn : int
            Number of coefficient matrices to compute
        P : ndarray (neqs x neqs), optional
            Matrix such that :math:`\\Sigma_u = PP'`. Defaults to Cholesky
            decomposition.

        Returns
        -------
        coefs : ndarray (maxn x neqs x neqs)
        """
        pass

    def predict(self, steps=5, alpha=None, exog_fc=None, exog_coint_fc=None):
        """
        Calculate future values of the time series.

        Parameters
        ----------
        steps : int
            Prediction horizon.
        alpha : float, 0 < `alpha` < 1 or None
            If None, compute point forecast only.
            If float, compute confidence intervals too. In this case the
            argument stands for the confidence level.
        exog : ndarray (steps x self.exog.shape[1])
            If self.exog is not None, then information about the future values
            of exog have to be passed via this parameter. The ndarray may be
            larger in it's first dimension. In this case only the first steps
            rows will be considered.

        Returns
        -------
        forecast - ndarray (steps x neqs) or three ndarrays
            In case of a point forecast: each row of the returned ndarray
            represents the forecast of the neqs variables for a specific
            period. The first row (index [0]) is the forecast for the next
            period, the last row (index [steps-1]) is the steps-periods-ahead-
            forecast.
        """
        pass

    def plot_forecast(self, steps, alpha=0.05, plot_conf_int=True, n_last_obs=None):
        """
        Plot the forecast.

        Parameters
        ----------
        steps : int
            Prediction horizon.
        alpha : float, 0 < `alpha` < 1
            The confidence level.
        plot_conf_int : bool, default: True
            If True, plot bounds of confidence intervals.
        n_last_obs : int or None, default: None
            If int, restrict plotted history to n_last_obs observations.
            If None, include the whole history in the plot.
        """
        pass

    def test_granger_causality(self, caused, causing=None, signif=0.05):
        """
        Test for Granger-causality.

        The concept of Granger-causality is described in chapter 7.6.3 of [1]_.
        Test |H0|: "The variables in `causing` do not Granger-cause those in
        `caused`" against  |H1|: "`causing` is Granger-causal for
        `caused`".

        Parameters
        ----------
        caused : int or str or sequence of int or str
            If int or str, test whether the variable specified via this index
            (int) or name (str) is Granger-caused by the variable(s) specified
            by `causing`.
            If a sequence of int or str, test whether the corresponding
            variables are Granger-caused by the variable(s) specified
            by `causing`.
        causing : int or str or sequence of int or str or `None`, default: `None`
            If int or str, test whether the variable specified via this index
            (int) or name (str) is Granger-causing the variable(s) specified by
            `caused`.
            If a sequence of int or str, test whether the corresponding
            variables are Granger-causing the variable(s) specified by
            `caused`.
            If `None`, `causing` is assumed to be the complement of
            `caused` (the remaining variables of the system).
        signif : float, 0 < `signif` < 1, default 5 %
            Significance level for computing critical values for test,
            defaulting to standard 0.05 level.

        Returns
        -------
        results : :class:`statsmodels.tsa.vector_ar.hypothesis_test_results.CausalityTestResults`

        References
        ----------
        .. [1] Lütkepohl, H. 2005. *New Introduction to Multiple Time Series Analysis*. Springer.

        .. |H0| replace:: H\\ :sub:`0`

        .. |H1| replace:: H\\ :sub:`1`
        """
        pass

    def test_inst_causality(self, causing, signif=0.05):
        """
        Test for instantaneous causality.

        The concept of instantaneous causality is described in chapters 3.6.3
        and 7.6.4 of [1]_. Test |H0|: "No instantaneous causality between the
        variables in `caused` and those in `causing`" against |H1|:
        "Instantaneous causality between `caused` and `causing` exists".
        Note that instantaneous causality is a symmetric relation
        (i.e. if `causing` is "instantaneously causing" `caused`, then also
        `caused` is "instantaneously causing" `causing`), thus the naming of
        the parameters (which is chosen to be in accordance with
        :meth:`test_granger_causality()`) may be misleading.

        Parameters
        ----------
        causing : int or str or sequence of int or str
            If int or str, test whether the corresponding variable is causing
            the variable(s) specified in caused.
            If sequence of int or str, test whether the corresponding variables
            are causing the variable(s) specified in caused.
        signif : float, 0 < `signif` < 1, default 5 %
            Significance level for computing critical values for test,
            defaulting to standard 0.05 level.

        Returns
        -------
        results : :class:`statsmodels.tsa.vector_ar.hypothesis_test_results.CausalityTestResults`

        Notes
        -----
        This method is not returning the same result as `JMulTi`. This is
        because the test is based on a VAR(k_ar) model in `statsmodels` (in
        accordance to pp. 104, 320-321 in [1]_) whereas `JMulTi` seems to be
        using a VAR(k_ar+1) model. Reducing the lag order by one in `JMulTi`
        leads to equal results in `statsmodels` and `JMulTi`.

        References
        ----------
        .. [1] Lütkepohl, H. 2005. *New Introduction to Multiple Time Series Analysis*. Springer.

        .. |H0| replace:: H\\ :sub:`0`

        .. |H1| replace:: H\\ :sub:`1`
        """
        pass

    @cache_readonly
    def fittedvalues(self):
        """
        Return the in-sample values of endog calculated by the model.

        Returns
        -------
        fitted : array (nobs x neqs)
            The predicted in-sample values of the models' endogenous variables.
        """
        pass

    @cache_readonly
    def resid(self):
        """
        Return the difference between observed and fitted values.

        Returns
        -------
        resid : array (nobs x neqs)
            The residuals.
        """
        pass

    def test_normality(self, signif=0.05):
        """
        Test assumption of normal-distributed errors using Jarque-Bera-style
        omnibus :math:`\\\\chi^2` test.

        Parameters
        ----------
        signif : float
            The test's significance level.

        Returns
        -------
        result : :class:`statsmodels.tsa.vector_ar.hypothesis_test_results.NormalityTestResults`

        Notes
        -----
        |H0| : data are generated by a Gaussian-distributed process

        .. |H0| replace:: H\\ :sub:`0`
        """
        pass

    def test_whiteness(self, nlags=10, signif=0.05, adjusted=False):
        """
        Test the whiteness of the residuals using the Portmanteau test.

        This test is described in [1]_, chapter 8.4.1.

        Parameters
        ----------
        nlags : int > 0
        signif : float, 0 < `signif` < 1
        adjusted : bool, default False

        Returns
        -------
        result : :class:`statsmodels.tsa.vector_ar.hypothesis_test_results.WhitenessTestResults`

        References
        ----------
        .. [1] Lütkepohl, H. 2005. *New Introduction to Multiple Time Series Analysis*. Springer.
        """
        pass

    def plot_data(self, with_presample=False):
        """
        Plot the input time series.

        Parameters
        ----------
        with_presample : bool, default: `False`
            If `False`, the pre-sample data (the first `k_ar` values) will
            not be plotted.
        """
        pass

    def summary(self, alpha=0.05):
        """
        Return a summary of the estimation results.

        Parameters
        ----------
        alpha : float 0 < `alpha` < 1, default 0.05
            Significance level of the shown confidence intervals.

        Returns
        -------
        summary : :class:`statsmodels.iolib.summary.Summary`
            A summary containing information about estimated parameters.
        """
        pass