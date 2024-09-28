"""Multiple Testing and P-Value Correction


Author: Josef Perktold
License: BSD-3

"""
import numpy as np
from statsmodels.stats._knockoff import RegressionFDR
__all__ = ['fdrcorrection', 'fdrcorrection_twostage', 'local_fdr', 'multipletests', 'NullDistribution', 'RegressionFDR']

def _ecdf(x):
    """no frills empirical cdf used in fdrcorrection
    """
    pass
multitest_methods_names = {'b': 'Bonferroni', 's': 'Sidak', 'h': 'Holm', 'hs': 'Holm-Sidak', 'sh': 'Simes-Hochberg', 'ho': 'Hommel', 'fdr_bh': 'FDR Benjamini-Hochberg', 'fdr_by': 'FDR Benjamini-Yekutieli', 'fdr_tsbh': 'FDR 2-stage Benjamini-Hochberg', 'fdr_tsbky': 'FDR 2-stage Benjamini-Krieger-Yekutieli', 'fdr_gbs': 'FDR adaptive Gavrilov-Benjamini-Sarkar'}
_alias_list = [['b', 'bonf', 'bonferroni'], ['s', 'sidak'], ['h', 'holm'], ['hs', 'holm-sidak'], ['sh', 'simes-hochberg'], ['ho', 'hommel'], ['fdr_bh', 'fdr_i', 'fdr_p', 'fdri', 'fdrp'], ['fdr_by', 'fdr_n', 'fdr_c', 'fdrn', 'fdrcorr'], ['fdr_tsbh', 'fdr_2sbh'], ['fdr_tsbky', 'fdr_2sbky', 'fdr_twostage'], ['fdr_gbs']]
multitest_alias = {}
for m in _alias_list:
    multitest_alias[m[0]] = m[0]
    for a in m[1:]:
        multitest_alias[a] = m[0]

def multipletests(pvals, alpha=0.05, method='hs', maxiter=1, is_sorted=False, returnsorted=False):
    """
    Test results and p-value correction for multiple tests

    Parameters
    ----------
    pvals : array_like, 1-d
        uncorrected p-values.   Must be 1-dimensional.
    alpha : float
        FWER, family-wise error rate, e.g. 0.1
    method : str
        Method used for testing and adjustment of pvalues. Can be either the
        full name or initial letters. Available methods are:

        - `bonferroni` : one-step correction
        - `sidak` : one-step correction
        - `holm-sidak` : step down method using Sidak adjustments
        - `holm` : step-down method using Bonferroni adjustments
        - `simes-hochberg` : step-up method  (independent)
        - `hommel` : closed method based on Simes tests (non-negative)
        - `fdr_bh` : Benjamini/Hochberg  (non-negative)
        - `fdr_by` : Benjamini/Yekutieli (negative)
        - `fdr_tsbh` : two stage fdr correction (non-negative)
        - `fdr_tsbky` : two stage fdr correction (non-negative)

    maxiter : int or bool
        Maximum number of iterations for two-stage fdr, `fdr_tsbh` and
        `fdr_tsbky`. It is ignored by all other methods.
        maxiter=1 (default) corresponds to the two stage method.
        maxiter=-1 corresponds to full iterations which is maxiter=len(pvals).
        maxiter=0 uses only a single stage fdr correction using a 'bh' or 'bky'
        prior fraction of assumed true hypotheses.
    is_sorted : bool
        If False (default), the p_values will be sorted, but the corrected
        pvalues are in the original order. If True, then it assumed that the
        pvalues are already sorted in ascending order.
    returnsorted : bool
         not tested, return sorted p-values instead of original sequence

    Returns
    -------
    reject : ndarray, boolean
        true for hypothesis that can be rejected for given alpha
    pvals_corrected : ndarray
        p-values corrected for multiple tests
    alphacSidak : float
        corrected alpha for Sidak method
    alphacBonf : float
        corrected alpha for Bonferroni method

    Notes
    -----
    There may be API changes for this function in the future.

    Except for 'fdr_twostage', the p-value correction is independent of the
    alpha specified as argument. In these cases the corrected p-values
    can also be compared with a different alpha. In the case of 'fdr_twostage',
    the corrected p-values are specific to the given alpha, see
    ``fdrcorrection_twostage``.

    The 'fdr_gbs' procedure is not verified against another package, p-values
    are derived from scratch and are not derived in the reference. In Monte
    Carlo experiments the method worked correctly and maintained the false
    discovery rate.

    All procedures that are included, control FWER or FDR in the independent
    case, and most are robust in the positively correlated case.

    `fdr_gbs`: high power, fdr control for independent case and only small
    violation in positively correlated case

    **Timing**:

    Most of the time with large arrays is spent in `argsort`. When
    we want to calculate the p-value for several methods, then it is more
    efficient to presort the pvalues, and put the results back into the
    original order outside of the function.

    Method='hommel' is very slow for large arrays, since it requires the
    evaluation of n partitions, where n is the number of p-values.
    """
    pass

def fdrcorrection(pvals, alpha=0.05, method='indep', is_sorted=False):
    """
    pvalue correction for false discovery rate.

    This covers Benjamini/Hochberg for independent or positively correlated and
    Benjamini/Yekutieli for general or negatively correlated tests.

    Parameters
    ----------
    pvals : array_like, 1d
        Set of p-values of the individual tests.
    alpha : float, optional
        Family-wise error rate. Defaults to ``0.05``.
    method : {'i', 'indep', 'p', 'poscorr', 'n', 'negcorr'}, optional
        Which method to use for FDR correction.
        ``{'i', 'indep', 'p', 'poscorr'}`` all refer to ``fdr_bh``
        (Benjamini/Hochberg for independent or positively
        correlated tests). ``{'n', 'negcorr'}`` both refer to ``fdr_by``
        (Benjamini/Yekutieli for general or negatively correlated tests).
        Defaults to ``'indep'``.
    is_sorted : bool, optional
        If False (default), the p_values will be sorted, but the corrected
        pvalues are in the original order. If True, then it assumed that the
        pvalues are already sorted in ascending order.

    Returns
    -------
    rejected : ndarray, bool
        True if a hypothesis is rejected, False if not
    pvalue-corrected : ndarray
        pvalues adjusted for multiple hypothesis testing to limit FDR

    Notes
    -----
    If there is prior information on the fraction of true hypothesis, then alpha
    should be set to ``alpha * m/m_0`` where m is the number of tests,
    given by the p-values, and m_0 is an estimate of the true hypothesis.
    (see Benjamini, Krieger and Yekuteli)

    The two-step method of Benjamini, Krieger and Yekutiel that estimates the number
    of false hypotheses will be available (soon).

    Both methods exposed via this function (Benjamini/Hochberg, Benjamini/Yekutieli)
    are also available in the function ``multipletests``, as ``method="fdr_bh"`` and
    ``method="fdr_by"``, respectively.

    See also
    --------
    multipletests

    """
    pass

def fdrcorrection_twostage(pvals, alpha=0.05, method='bky', maxiter=1, iter=None, is_sorted=False):
    """(iterated) two stage linear step-up procedure with estimation of number of true
    hypotheses

    Benjamini, Krieger and Yekuteli, procedure in Definition 6

    Parameters
    ----------
    pvals : array_like
        set of p-values of the individual tests.
    alpha : float
        error rate
    method : {'bky', 'bh')
        see Notes for details

        * 'bky' - implements the procedure in Definition 6 of Benjamini, Krieger
           and Yekuteli 2006
        * 'bh' - the two stage method of Benjamini and Hochberg

    maxiter : int or bool
        Maximum number of iterations.
        maxiter=1 (default) corresponds to the two stage method.
        maxiter=-1 corresponds to full iterations which is maxiter=len(pvals).
        maxiter=0 uses only a single stage fdr correction using a 'bh' or 'bky'
        prior fraction of assumed true hypotheses.
        Boolean maxiter is allowed for backwards compatibility with the
        deprecated ``iter`` keyword.
        maxiter=False is two-stage fdr (maxiter=1)
        maxiter=True is full iteration (maxiter=-1 or maxiter=len(pvals))

        .. versionadded:: 0.14

            Replacement for ``iter`` with additional features.

    iter : bool
        ``iter`` is deprecated use ``maxiter`` instead.
        If iter is True, then only one iteration step is used, this is the
        two-step method.
        If iter is False, then iterations are stopped at convergence which
        occurs in a finite number of steps (at most len(pvals) steps).

        .. deprecated:: 0.14

            Use ``maxiter`` instead of ``iter``.

    Returns
    -------
    rejected : ndarray, bool
        True if a hypothesis is rejected, False if not
    pvalue-corrected : ndarray
        pvalues adjusted for multiple hypotheses testing to limit FDR
    m0 : int
        ntest - rej, estimated number of true (not rejected) hypotheses
    alpha_stages : list of floats
        A list of alphas that have been used at each stage

    Notes
    -----
    The returned corrected p-values are specific to the given alpha, they
    cannot be used for a different alpha.

    The returned corrected p-values are from the last stage of the fdr_bh
    linear step-up procedure (fdrcorrection0 with method='indep') corrected
    for the estimated fraction of true hypotheses.
    This means that the rejection decision can be obtained with
    ``pval_corrected <= alpha``, where ``alpha`` is the original significance
    level.
    (Note: This has changed from earlier versions (<0.5.0) of statsmodels.)

    BKY described several other multi-stage methods, which would be easy to implement.
    However, in their simulation the simple two-stage method (with iter=False) was the
    most robust to the presence of positive correlation

    TODO: What should be returned?

    """
    pass

def local_fdr(zscores, null_proportion=1.0, null_pdf=None, deg=7, nbins=30, alpha=0):
    """
    Calculate local FDR values for a list of Z-scores.

    Parameters
    ----------
    zscores : array_like
        A vector of Z-scores
    null_proportion : float
        The assumed proportion of true null hypotheses
    null_pdf : function mapping reals to positive reals
        The density of null Z-scores; if None, use standard normal
    deg : int
        The maximum exponent in the polynomial expansion of the
        density of non-null Z-scores
    nbins : int
        The number of bins for estimating the marginal density
        of Z-scores.
    alpha : float
        Use Poisson ridge regression with parameter alpha to estimate
        the density of non-null Z-scores.

    Returns
    -------
    fdr : array_like
        A vector of FDR values

    References
    ----------
    B Efron (2008).  Microarrays, Empirical Bayes, and the Two-Groups
    Model.  Statistical Science 23:1, 1-22.

    Examples
    --------
    Basic use (the null Z-scores are taken to be standard normal):

    >>> from statsmodels.stats.multitest import local_fdr
    >>> import numpy as np
    >>> zscores = np.random.randn(30)
    >>> fdr = local_fdr(zscores)

    Use a Gaussian null distribution estimated from the data:

    >>> null = EmpiricalNull(zscores)
    >>> fdr = local_fdr(zscores, null_pdf=null.pdf)
    """
    pass

class NullDistribution:
    """
    Estimate a Gaussian distribution for the null Z-scores.

    The observed Z-scores consist of both null and non-null values.
    The fitted distribution of null Z-scores is Gaussian, but may have
    non-zero mean and/or non-unit scale.

    Parameters
    ----------
    zscores : array_like
        The observed Z-scores.
    null_lb : float
        Z-scores between `null_lb` and `null_ub` are all considered to be
        true null hypotheses.
    null_ub : float
        See `null_lb`.
    estimate_mean : bool
        If True, estimate the mean of the distribution.  If False, the
        mean is fixed at zero.
    estimate_scale : bool
        If True, estimate the scale of the distribution.  If False, the
        scale parameter is fixed at 1.
    estimate_null_proportion : bool
        If True, estimate the proportion of true null hypotheses (i.e.
        the proportion of z-scores with expected value zero).  If False,
        this parameter is fixed at 1.

    Attributes
    ----------
    mean : float
        The estimated mean of the empirical null distribution
    sd : float
        The estimated standard deviation of the empirical null distribution
    null_proportion : float
        The estimated proportion of true null hypotheses among all hypotheses

    References
    ----------
    B Efron (2008).  Microarrays, Empirical Bayes, and the Two-Groups
    Model.  Statistical Science 23:1, 1-22.

    Notes
    -----
    See also:

    http://nipy.org/nipy/labs/enn.html#nipy.algorithms.statistics.empirical_pvalue.NormalEmpiricalNull.fdr
    """

    def __init__(self, zscores, null_lb=-1, null_ub=1, estimate_mean=True, estimate_scale=True, estimate_null_proportion=False):
        ii = np.flatnonzero((zscores >= null_lb) & (zscores <= null_ub))
        if len(ii) == 0:
            raise RuntimeError('No Z-scores fall between null_lb and null_ub')
        zscores0 = zscores[ii]
        n_zs, n_zs0 = (len(zscores), len(zscores0))

        def xform(params):
            mean = 0.0
            sd = 1.0
            prob = 1.0
            ii = 0
            if estimate_mean:
                mean = params[ii]
                ii += 1
            if estimate_scale:
                sd = np.exp(params[ii])
                ii += 1
            if estimate_null_proportion:
                prob = 1 / (1 + np.exp(-params[ii]))
            return (mean, sd, prob)
        from scipy.stats.distributions import norm

        def fun(params):
            """
            Negative log-likelihood of z-scores.

            The function has three arguments, packed into a vector:

            mean : location parameter
            logscale : log of the scale parameter
            logitprop : logit of the proportion of true nulls

            The implementation follows section 4 from Efron 2008.
            """
            d, s, p = xform(params)
            central_mass = norm.cdf((null_ub - d) / s) - norm.cdf((null_lb - d) / s)
            cp = p * central_mass
            rval = n_zs0 * np.log(cp) + (n_zs - n_zs0) * np.log(1 - cp)
            zv = (zscores0 - d) / s
            rval += np.sum(-zv ** 2 / 2) - n_zs0 * np.log(s)
            rval -= n_zs0 * np.log(central_mass)
            return -rval
        from scipy.optimize import minimize
        mz = minimize(fun, np.r_[0.0, 0, 3], method='Nelder-Mead')
        mean, sd, prob = xform(mz['x'])
        self.mean = mean
        self.sd = sd
        self.null_proportion = prob

    def pdf(self, zscores):
        """
        Evaluates the fitted empirical null Z-score density.

        Parameters
        ----------
        zscores : scalar or array_like
            The point or points at which the density is to be
            evaluated.

        Returns
        -------
        The empirical null Z-score density evaluated at the given
        points.
        """
        pass