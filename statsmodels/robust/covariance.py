# -*- coding: utf-8 -*-
"""robust location, scatter and covariance estimators

Author: Josef Perktold
License: BSD-3


---  for Tyler
copied from "M:\josef\eclipsegworkspace\statsmodels-git\local_scripts\local_scripts\try_cov_tyler.py"

Created on Tue Nov 18 11:53:19 2014

Author: Josef Perktold
License: BSD-3


based on iteration in equ. (14) in Soloveychik and Wiesel

Soloveychik, I., and A. Wiesel. 2014. Tyler's Covariance Matrix Estimator in
Elliptical Models With Convex Structure.
IEEE Transactions on Signal Processing 62 (20): 5251-59.
doi:10.1109/TSP.2014.2348951.

see also related articles by Frahm (which are not easy to read,
too little explanation, too many strange font letters)

shrinkage version is based on article

Chen, Yilun, A. Wiesel, and A.O. Hero. 2011. Robust Shrinkage Estimation of
High-Dimensional Covariance Matrices.
IEEE Transactions on Signal Processing 59 (9): 4097-4107.
doi:10.1109/TSP.2011.2138698.


"""

import numpy as np
from scipy import linalg, stats
from statsmodels import robust
import statsmodels.robust as robust

# shorthand functions
mad = robust.mad
mad0 = lambda x: mad(x, center=0)

class Holder(object):
    def __init__(self, **kwds):
        self.__dict__.update(kwds)


# from scikit-learn
# https://github.com/scikit-learn/scikit-learn/blob/6a7eae5a97b6eba270abaaf17bc82ad56db4290e/sklearn/covariance/tests/test_covariance.py#L190
# Note: this is only intended for internal use
def _naive_ledoit_wolf_shrinkage(x, center):
    # A simple implementation of the formulas from Ledoit & Wolf

    # The computation below achieves the following computations of the
    # "O. Ledoit and M. Wolf, A Well-Conditioned Estimator for
    # Large-Dimensional Covariance Matrices"
    # beta and delta are given in the beginning of section 3.2
    n_samples, n_features = x.shape
    xdm = x - center
    emp_cov = xdm.T.dot(xdm) / n_samples
    mu = np.trace(emp_cov) / n_features
    delta_ = emp_cov.copy()
    delta_.flat[::n_features + 1] -= mu
    delta = (delta_ ** 2).sum() / n_features
    x2 = x ** 2
    beta_ = 1. / (n_features * n_samples) \
        * np.sum(np.dot(x2.T, x2) / n_samples - emp_cov ** 2)

    beta = min(beta_, delta)
    shrinkage = beta / delta
    return shrinkage * emp_cov


# reweight adapted from OGK reweight step
def _reweight(x, loc, cov, trim_frac=0.975, ddof=1):
    beta = trim_frac
    nobs, k_vars = x.shape
    #d = (((z - loc_z) / scale_z)**2).sum(1) # for orthogonal
    d = mahalanobis(x - loc, cov)
    # only hard thresholding right now
    dmed = np.median(d)
    cutoff = dmed * stats.chi2.isf(1-beta, k_vars) / stats.chi2.ppf(0.5, k_vars)
    mask = d <= cutoff
    sample = x[mask]
    loc = sample.mean(0)
    cov = np.cov(sample.T, ddof=ddof)
    return cov, loc


def _outlier_gy(d, distr=None, k_endog=1, trim_prob=0.975):
    """determine outlier fraction given reference distribution

    This implements the outlier cutoff of Gervini and Yohai 2002
    for use in efficient reweighting.

    Parameters
    ----------
    d : array_like, 1-D
        array of squared standardized residuals or Mahalanobis distance
    distr : None or distribution instance
        reference distribution of d, needs cdf and ppf methods.
        If None, then chisquare with k_endog degrees of freedom is
        used. Otherwise, it should be a callable that provides the
        cdf function
    k_endog : int or float
        used only if cdf is None. In that case, it provides the degrees
        of freedom for the chisquare distribution.
    trim_prob : float in (0.5, 1)
        threshold for the tail probability at which the search for
        trimming or outlier fraction starts.

    Returns
    -------
    frac : float
        fraction of outliers
    cutoff : float
        cutoff value, values with `d > cutoff` are considered outliers
    ntail : int
        number of outliers
    ntail0 : int
        initial number of outliers based on trim tail probability.
    cutoff0 : float
        initial cutoff value based on trim tail probability.

    Notes
    -----
    This does not fully correct for multiple testing and does not
    maintain a familywise error rate or false discovery rate.
    The error rate goes to zero asymptotically under the null model,
    i.e. if there are no outliers.

    This might not handle threshold points correctly with discrete
    distribution.
    TODO: check weak versus strict inequalities (e.g. in isf)

    This only checks the upper tail of the distribution and of `d`.

    """
    d = np.asarray(d)
    nobs = d.shape[0]
    if distr is None:
        distr = stats.chi2(k_endog)

    threshold = distr.isf(1 - trim_prob)

    # get sorted array, we only need upper tail
    dtail = np.sort(d[d >= threshold])
    ntail0 = len(dtail)
    if ntail0 == 0:
        # no values above threshold
        return 0, threshold, 0, 0, threshold

    # using (n-1) / n as in GY2002
    ranks = np.arange(nobs - ntail0, nobs) / nobs

    frac = np.maximum(0, distr.cdf(dtail) - ranks).max()
    ntail = int(nobs * frac)  # rounding down
    if ntail > 0:
        cutoff = dtail[-ntail - 1]
    else:
        cutoff = dtail[-1] + 1e-15  # not sure, check inequality
    if (dtail > cutoff).sum() < ntail:
        import warnings
        warnings.warn('ties at cutoff, cutoff rule produces fewer'
                      'outliers than `ntail`')
    return frac, cutoff, ntail, ntail0, threshold


### GK and OGK ###

def _weight_mean(x, c):
    x = np.asarray(x)
    w = (1 - (x / c)**2)**2 * (np.abs(x) <= c)
    return w

def _winsor(x, c):
    return np.minimum(x**2, c**2)


def scale_tau(data, cm=4.5, cs=3, weight_mean=_weight_mean,
              weight_scale=_winsor, normalize=True, ddof=2):
    """tau estimator of univariate scale

    Experimental, API will change

    Parameters
    ----------
    data : array_like, 1-D or 2-D
        If data is 2d, then the location and scale estimates
        are calculated for each column
    cm : float
        constant used in call to weight_mean
    cs : float
        constant used in call to weight_scale
    weight_mean : callable
        function to calculate weights for weighted mean
    weight_scale : callable
        function to calculate scale, "rho" function
    normalize : bool
        rescale the scale estimate so it is consistent when the data is
        normally distributed. The computation assumes winsorized (truncated)
        variance.

    Returns
    -------
    mean : nd_array
        robust mean
    std : nd_array
        robust estimate of scale (standard deviation)

    Notes
    -----
    Uses definition of Maronna and Zamar 2002, with weighted mean and
    trimmed variance.
    The normalization has been added to match R robustbase.
    R robustbase uses by default ddof=0, with option to set it to 2.

    """

    x = np.asarray(data)
    nobs = x.shape[0]

    med_x = np.median(x, 0)
    xdm = x - med_x
    mad_x = np.median(np.abs(xdm), 0)
    wm = weight_mean(xdm / mad_x, cm)
    mean = (wm * x).sum(0) / wm.sum(0)
    var = mad_x**2 * weight_scale((x - mean) / mad_x, cs).sum(0) / (nobs - ddof)

    cf = 1
    if normalize:
        c =  cs * stats.norm.ppf(0.75)
        cf = 2 * ((1 - c**2) * stats.norm.cdf(c) - c * stats.norm.pdf(c)
                 + c**2) - 1
    #return Holder(loc=mean, scale=np.sqrt(var / cf))
    return mean, np.sqrt(var / cf)



def mahalanobis(data, cov=None, cov_inv=None):
    """Mahalanobis distance

    """
    x = np.asarray(data)
    if cov_inv is not None:
        d = (x * cov_inv.dot(x.T).T).sum(1)
    elif cov is not None:
        d = (x * np.linalg.solve(cov, x.T).T).sum(1)
    else:
        raise ValueError('either cov or cov_inv needs to be given')

    return d


def cov_gk1(x, y, scale_func=mad):
    """Gnanadesikan and Kettenring covariance between two variables

    """
    s1 = scale_func((x + y))
    s2 = scale_func((x - y))
    return (s1**2 - s2**2) / 4


def cov_gk(data, scale_func=mad):
    """Gnanadesikan and Kettenring covariance estimator

    uses loop with cov_gk1

    """
    x = np.asarray(data)
    if x.ndim != 2:
        raise ValueError('data needs to be two dimensional')
    nobs, k_vars = x.shape
    cov = np.diag(scale_func(x)**2)
    for i in range(k_vars):
        for j in range(i):
            cij = cov_gk1(x[:, i], x[:, j], scale_func=scale_func)
            cov[i, j] = cov[j, i] = cij
    return cov


def cov_ogk(data, maxiter=2, scale_func=mad, cov_func=cov_gk,
            loc_func=lambda x:np.median(x, axis=0), reweight=0.9, ddof=1):
    """orthogonalized Gnanadesikan and Kettenring covariance estimator


    based on Maronna and Zamar 2002

    Parameters
    ----------
    data : array_like, 2-D

    maxiter : int
        number of iteration steps. According to Maronna and Zamar the
        estimate doesn't improve much after the second iteration and the
        iterations do not converge.

    scale_func : callable

    cov_func : callable

    loc_func : callable

    reweight : float in (0, 1) or None
        API for this will change.
        If reweight is None, then the reweighting step is skipped.
        Otherwise, reweight is the chisquare probability beta for the
        trimming based on estimated robust distances.
        Hard-rejection is currently the only weight function.
    ddof : int
        Degrees of freedom correction for the reweighted sample
        covariance.

    Notes
    -----
    compared to R: In robustbase covOGK the default scale and location are
    given by tau_scale with normalization but ddof=0.
    CovOGK of R package rrcov does not agree with this in the default options.

    """
    beta = reweight  #alias, need more reweighting options
    x = np.asarray(data)
    if x.ndim != 2:
        raise ValueError('data needs to be two dimensional')
    nobs, k_vars = x.shape
    z = x
    transf0 = np.eye(k_vars)
    for i in range(maxiter):
        scale = scale_func(z)
        zs = z / scale
        corr = cov_func(zs, scale_func=scale_func)
        # Maronna, Zamar set diagonal to 1, otherwise small difference to 1
        corr[np.arange(k_vars), np.arange(k_vars)] = 1
        evals, evecs = np.linalg.eigh(corr)
        transf = evecs * scale[:, None]   # A matrix in Maronna, Zamar
        #z = np.linalg.solve(transf, z.T).T
        z = zs.dot(evecs)
        transf0 = transf0.dot(transf)

    scale_z = scale_func(z)
    cov = (transf0 * scale_z**2).dot(transf0.T)

    loc_z = loc_func(z)
    loc = transf0.dot(loc_z)
    # prepare for results
    cov_ogk_raw = cov
    loc_ogk_raw = loc
    mask = None
    d = None
    if reweight is not None:
        d = (((z - loc_z) / scale_z)**2).sum(1)
        #d = mahalanobis(x - loc, cov)
        # only hard thresholding right now
        dmed = np.median(d)
        cutoff = dmed * stats.chi2.isf(1-beta, k_vars) / stats.chi2.ppf(0.5, k_vars)
        mask = d <= cutoff
        sample = x[mask]
        loc = sample.mean(0)
        cov = np.cov(sample.T, ddof=ddof)

    # duplicate name loc mean center, choose consistent naming
    res = Holder(cov=cov, loc=loc, mean=loc, mask=mask, mahalanobis=d,
                 cov_ogk_raw=cov_ogk_raw, loc_ogk_raw=loc_ogk_raw,
                 transf0=transf0)

    return res

### Tyler ###



def cov_tyler(data, start_cov=None, normalize=False, maxiter=100, eps=1e-13):
    """Tyler's M-estimator for normalized covariance (scatter)

    The underlying (population) mean of the data is assumed to be zero.

    Parameters
    ----------
    data : ndarray
        data array with observations in rows and variables in columns
    start_cov : None or ndarray
        starting covariance for iterative solution
    normalize : bool
        If True, then the scatter matrix is normalized to have trace equalt
        to the number of columns in the data.
    maxiter : int
        maximum number of iterations to find the solution
    eps : float
        convergence criterion. The maximum absolute distance needs to be
        smaller than eps for convergence.

    Returns
    -------
    result instance with the following attributes
    cov : ndarray
        estimate of the scatter matrix
    iter : int
        number of iterations used in finding a solution. If iter is less than
        maxiter, then the iteration converged.
    """
    x = np.asarray(data)
    nobs, k_vars = x.shape
    kn = k_vars * 1. / nobs
    if start_cov is not None:
        c = start_cov
    else:
        c = np.diag(robust.mad(x, center=0)**2)

    #Tyler's M-estimator of shape (scatter) matrix
    for i in range(maxiter):
        c_inv = np.linalg.pinv(c)
        c_old = c
        # this could be vectorized but could use a lot of memory
        # TODO:  try to work in vectorized batches
        c = kn * sum(np.outer(xi, xi) / np.inner(xi, c_inv.dot(xi)) for xi in x)
        diff = np.max(np.abs(c - c_old))
        if diff < eps:
            break
    if normalize:
        c /= np.trace(c) / k_vars

    return Holder(cov=c, n_iter=i)


def cov_tyler_regularized(data, start_cov=None, normalize=False,
                          shrinkage_factor=None,
                          maxiter=100, eps=1e-13):
    """Tyler's M-estimator for normalized covariance (scatter)

    The underlying (population) mean of the data is assumed to be zero.

    Parameters
    ----------
    data : ndarray
        data array with observations in rows and variables in columns.
    start_cov : None or ndarray
        starting covariance for iterative solution
    normalize : bool
        If True, then the scatter matrix is normalized to have trace equalt
        to the number of columns in the data.
    shrinkage_factor : None or float in [0, 1]
        Shrinkage for the scatter estimate. If it is zero, then no shrinkage
        is performed. If it is None, then the shrinkage factor will be
        determined by a plugin estimator
    maxiter : int
        maximum number of iterations to find the solution
    eps : float
        convergence criterion. The maximum absolute distance needs to be
        smaller than eps for convergence.

    Returns
    -------
    result instance with the following attributes
    cov : ndarray
        estimate of the scatter matrix
    iter : int
        number of iterations used in finding a solution. If iter is less than
        maxiter, then the iteration converged.
    shrinkage_factor : float
        shrinkage factor that was used in the estimation. This will be the
        same as the function argument if it was not None.

    Notes
    -----
    If the shrinkage factor is None, then a plugin is used as described in
    Chen and Wiesel 2011. The required trace for a pilot scatter estimate is
    obtained by the covariance rescaled by MAD estimate for the variance.

    """
    x = np.asarray(data)
    nobs, k_vars = x.shape
    kn = k_vars * 1. / nobs

    # calculate MAD only once if needed
    if start_cov is None or shrinkage_factor is None:
        scale_mad = robust.mad(x, center=0)

    corr = None
    if shrinkage_factor is None:
        # maybe some things here are redundant
        xd = x / x.std(0) #scale_mad
        corr = xd.T.dot(xd)
        corr * np.outer(scale_mad, scale_mad)
        corr *= k_vars / np.trace(corr)
        tr = np.trace(corr.dot(corr))

        n, k = nobs, k_vars
        # Chen and Wiesel 2011 equation (13)
        sf = k*k + (1 - 2./k) * tr
        sf /= (k*k - n*k - 2*n) + (n + 1 + 2. * (n - 1.) / k) * tr
        shrinkage_factor = sf

    if start_cov is not None:
        c = start_cov
    else:
        c = np.diag(scale_mad**2)

    identity = np.eye(k_vars)

    for i in range(maxiter):
        c_inv = np.linalg.pinv(c)
        c_old = c
        # this could be vectorized but could use a lot of memory
        # TODO:  try to work in vectorized batches
        c0 = kn * sum(np.outer(xi, xi) / np.inner(xi, c_inv.dot(xi)) for xi in x)
        if shrinkage_factor != 0:
            c = (1 - shrinkage_factor) * c0 + shrinkage_factor * identity
        else:
            c = c0

        c *= k_vars / np.trace(c)

        diff = np.max(np.abs(c - c_old))
        if diff < eps:
            break

    res = Holder(cov=c, n_iter=i, shrinkage_factor=shrinkage_factor,
                 corr=corr)
    return res


def cov_tyler_pairs_regularized(data_iterator, start_cov=None, normalize=False,
                          shrinkage_factor=None, nobs=None, k_vars=None,
                          maxiter=100, eps=1e-13):
    """Tyler's M-estimator for normalized covariance (scatter)

    The underlying (population) mean of the data is assumed to be zero.

    experimental, calculation of startcov and shrinkage factor doesn't work
    This is intended for cluster robust and HAC covariance matrices that need
    to iterate over pairs of observations that are correlated.

    Parameters
    ----------
    data_iterator : restartable iterator
        needs to provide three elements xi, xj and w
    start_cov : None or ndarray
        starting covariance for iterative solution
    normalize : bool
        If True, then the scatter matrix is normalized to have trace equalt
        to the number of columns in the data.
    shrinkage_factor : None or float in [0, 1]
        Shrinkage for the scatter estimate. If it is zero, then no shrinkage
        is performed. If it is None, then the shrinkage factor will be
        determined by a plugin estimator
    maxiter : int
        maximum number of iterations to find the solution
    eps : float
        convergence criterion. The maximum absolute distance needs to be
        smaller than eps for convergence.

    Returns
    -------
    scatter : ndarray
        estimate of the scatter matrix
    iter : int
        number of iterations used in finding a solution. If iter is less than
        maxiter, then the iteration converged.
    shrinkage_factor : float
        shrinkage factor that was used in the estimation. This will be the
        same as the function argument if it was not None.

    Notes
    -----
    If the shrinkage factor is None, then a plugin is used as described in
    Chen and Wiesel 2011. The required trace for a pilot scatter estimate is
    obtained by the covariance rescaled by MAD estimate for the variance.

    """
    x = data_iterator
    #x = np.asarray(data)
    #nobs, k_vars = x.shape

    # calculate MAD only once if needed
    if start_cov is None or shrinkage_factor is None:
        scale_mad = mad(x, center=0)

    corr = None
    if shrinkage_factor is None:
        # maybe some things here are redundant
        xd = x / x.std(0) #scale_mad
        corr = xd.T.dot(xd)
        corr * np.outer(scale_mad, scale_mad)
        corr *= k_vars / np.trace(corr)
        tr = np.trace(corr.dot(corr))

        n, k = nobs, k_vars
        # Chen and Wiesel 2011 equation (13)
        sf = k*k + (1 - 2./k) * tr
        sf /= (k*k - n*k - 2*n) + (n + 1 + 2. * (n - 1.) / k) * tr
        shrinkage_factor = sf

    if start_cov is not None:
        c = start_cov
    else:
        c = np.diag(scale_mad**2)

    identity = np.eye(k_vars)
    kn = k_vars * 1. / nobs
    for i in range(maxiter):
        c_inv = np.linalg.pinv(c)
        c_old = c
        # this could be vectorized but could use a lot of memory
        # TODO:  try to work in vectorized batches
        # weights is a problem if iterator should be ndarray
        #c0 = kn * sum(np.outer(xi, xj) / np.inner(xi, c_inv.dot(xj)) for xi, xj in x)
        c0 = kn * sum(np.outer(xij[0], xij[1]) / np.inner(xij[0], c_inv.dot(xij[1])) for xij in x)
        if shrinkage_factor != 0:
            c = (1 - shrinkage_factor) * c0 + shrinkage_factor * identity
        else:
            c = c0

        c *= k_vars / np.trace(c)

        diff = np.max(np.abs(c - c_old))
        if diff < eps:
            break

    res = Holder(cov=c, n_iter=i, shrinkage_factor=shrinkage_factor,
                 corr=corr)
    return res


### iterative, M-estimators and related

def cov_weighted(data, weights, center=None, weights_cov=None,
                 weights_cov_denom=None, ddof=1):
    """weighted mean and covariance (for M-estimators)

    wmean = sum (weights * data) / sum(weights)
    wcov = sum (weights_cov * data_i data_i') / weights_cov_denom

    The options for weights_cov_denom are described in Parameters.
    By default both mean and cov are averages based on the same
    weights.

    Parameters
    ----------
    data : array_like, 2-D
        observations in rows, variables in columns
        no missing value handling
    weights : ndarray, 1-D
        weights array with length equal to the number of observations
    center : None or ndarray (optional)
        If None, then the weighted mean is subtracted from the data
        If center is provided, then it is used instead of the
        weighted mean.
    weights_cov : None, ndarray or "det" (optional)
        If None, then the same weights as for the mean are used.
    weights_cov_denom : None, float or "det" (optional)
        specified the denominator for the weighted covariance
        If None, then the sum of weights are used and the covariance is
        an average cross product
        If "det", then the weighted covariance is normalized such that
        det(wcov) is 1.
        If float, then it is used directly as denominator.
    ddof : int or float
        covariance degrees of freedom correction, only used if
        weights_cov_denom is None or a float.

    Notes
    -----
    The extra options are available to cover the general M-estimator
    for location and scatter with estimating equations (using data x):

    sum (weights * (x - m)) = 0
    sum (weights_cov * (x_i - m) * (x_i - m)') - weights_cov_denom * cov = 0

    where the weights are functions of the mahalonibis distance of the
    residuals, and m is the mean.

    In the default case
    wmean = ave (w_i x)i)
    wcov = ave (w_i (x_i - m) (x_i - m)')

    References
    ----------
    Rocke, D. M., and D. L. Woodruff. 1993. Computation of Robust Estimates
    of Multivariate Location and Shape. Statistica Neerlandica 47 (1): 27-42.
    doi:10.1111/j.1467-9574.1993.tb01404.x.


    """

    wsum = weights.sum()
    if weights_cov is None:
        weights_cov = weights
        wsum_cov = wsum
    else:
        wsum_cov = None  # calculate below only if needed

    if center is None:
        wmean = weights.dot(data) / wsum
    else:
        wmean = center

    xdm = data - wmean
    wcov = (weights_cov * xdm.T).dot(xdm)
    if weights_cov_denom is None:
        if wsum_cov is None:
            wsum_cov = weights_cov.sum()
        wcov /= (wsum_cov - ddof)
    elif weights_cov_denom == "det":
        wcov /= np.linalg.det(wcov)**(1 / wcov.shape[0])
    elif weights_cov_denom == 1:
        pass
    else:
        wcov /= (weights_cov_denom - ddof)

    return wcov, wmean


def weights_mvt(distance, df, k_vars):
    """weight function based on multivariate t distribution

    Parameters
    ----------
    distance : ndarray
        mahalanobis distance
    df : int or float
        degrees of freedom of the t distribution
    k_vars : int
        number of variables in the multivariate sample

    Returns
    -------
    weights : ndarray
        weights calculated for the given distances.

    References
    ----------

    Finegold, Michael A., and Mathias Drton. 2014. Robust Graphical
    Modeling with T-Distributions. arXiv:1408.2033 [Cs, Stat], August.
    http://arxiv.org/abs/1408.2033.

    Finegold, Michael, and Mathias Drton. 2011. ROBUST GRAPHICAL
    MODELING OF GENE NETWORKS USING CLASSICAL AND ALTERNATIVE
    T-DISTRIBUTIONS. The Annals of Applied Statistics 5 (2A): 1057-80.


    """
    w = (df + k_vars) / (df + distance)
    return w


def weights_quantile(distance, frac=0.5, rescale=True):
    cutoff = np.percentile(distance, frac * 100)
    w = (distance < cutoff).astype(int)
    return w


def _cov_iter(data, weights_func, weights_args=None, cov_init=None,
             rescale='med', maxiter=3, atol=1e-14, rtol=1e-6):
    """iterative robust covariance estimation using weights

    This is in the style of M-estimators for given weight function.

    Note: ??? Whether this is normalized to be consistent with the
    multivariate normal case depends on the weight function.
    maybe it is consistent, it's just a weighted cov.

    TODO: options for rescale instead of just median

    Parameters
    ----------
    data : array_like
    weights_func : callable
        function to calculate weights from the distances and weights_args
    weights_args : tuple
        extra arguments for the weights_func
    cov_init : ndarray, square 2-D
        initial covariance matrix
    rescale : "med" or "none"
        If "med" then the resulting covariance matrix is normalized so it is
        approximately consistent with the normal distribution. Rescaling is
        based on the median of the distances and of the chisquare distribution.
        Other options are not yet available.
        If rescale is the string "none", then no rescaling is performed.

    Returns
    -------
    this will still change
    cov, mean, w, dist, it, converged

    Notes
    -----
    This iterates over calculating the mahalanobis distance and weighted
    covariance. See Feingold and Drton 2014 for the motivation using weights
    based on the multivariate t distribution. Note that this does not calculate
    their alternative t distribution which requires numerical or Monte Carlo
    integration.

    """
    data = np.asarray(data)
    nobs, k_vars = data.shape

    if cov_init is None:
        cov_init = np.cov(data.T)

    converged = False
    cov = cov_old = cov_init
    for it in range(maxiter):
        dist = mahalanobis(data, cov=cov)
        w = weights_func(dist, *weights_args)
        cov, mean = cov_weighted(data, w)
        if np.allclose(cov, cov_old, atol=atol, rtol=rtol):
            converged = True
            break

    if rescale == 'none':
        s = 1
    if rescale == 'med':
        s = np.median(dist) / stats.chi2.ppf(0.5, k_vars)
        cov *= s
    else:
        raise NotImplementedError('only rescale="med" is currently available')

    res = Holder(cov=cov, mean=mean, weights=w, mahalanobis=dist,
                 scale_factor=s, n_iter=it, converged=converged)
    return res


def _cov_starting(data, is_standardized=True, quantile=0.5):
    """compute some robust starting covariances

    The returned covariance matrices are intended as starting values
    for further processing. The main purpose is for DetXXX algorithms.
    The quality as standalone covariance matrices varies and might not
    be very good.


    """
    x = np.asarray(data)
    nobs, k_vars = x.shape
    if not is_standardized:
        # there should be a helper function/class
        center = np.median(data, axis=0)
        xs = (x - center)
        std = mad0(data)
        xs /= std
    else:
        xs = x - np.median(data, axis=0)

    cov_all = []
    d = mahalanobis(xs, cov=None, cov_inv=np.eye(k_vars))
    cutoffs = np.percentile(d, [(k_vars+2) / nobs * 100, 25, 50])
    for cutoff in cutoffs:
        xsp = xs[d<cutoff]
        c0 = np.cov(xsp.T)
        c01 = _cov_iter(xs, weights_quantile, weights_args=(quantile,),
                        rescale="med", cov_init=c0, maxiter=100)

        c02 = _naive_ledoit_wolf_shrinkage(xsp, 0)
        c03 = _cov_iter(xs, weights_quantile, weights_args=(quantile,),
                        rescale="med", cov_init=c02, maxiter=100)

        cov_all.extend([c0, c01, c02, c03])

    c2 = cov_ogk(xs)
    cov_all.append(c2)

    # TODO: rescale back to original space using center and std
    return cov_all
