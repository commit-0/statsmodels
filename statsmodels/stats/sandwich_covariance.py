"""Sandwich covariance estimators


Created on Sun Nov 27 14:10:57 2011

Author: Josef Perktold
Author: Skipper Seabold for HCxxx in linear_model.RegressionResults
License: BSD-3

Notes
-----

for calculating it, we have two versions

version 1: use pinv
pinv(x) scale pinv(x)   used currently in linear_model, with scale is
1d (or diagonal matrix)
(x'x)^(-1) x' scale x (x'x)^(-1),  scale in general is (nobs, nobs) so
pretty large general formulas for scale in cluster case are in [4],
which can be found (as of 2017-05-20) at
http://www.tandfonline.com/doi/abs/10.1198/jbes.2010.07136
This paper also has the second version.

version 2:
(x'x)^(-1) S (x'x)^(-1)    with S = x' scale x,    S is (kvar,kvars),
(x'x)^(-1) is available as normalized_covparams.



S = sum (x*u) dot (x*u)' = sum x*u*u'*x'  where sum here can aggregate
over observations or groups. u is regression residual.

x is (nobs, k_var)
u is (nobs, 1)
x*u is (nobs, k_var)


For cluster robust standard errors, we first sum (x*w) over other groups
(including time) and then take the dot product (sum of outer products)

S = sum_g(x*u)' dot sum_g(x*u)
For HAC by clusters, we first sum over groups for each time period, and then
use HAC on the group sums of (x*w).
If we have several groups, we have to sum first over all relevant groups, and
then take the outer product sum. This can be done by summing using indicator
functions or matrices or with explicit loops. Alternatively we calculate
separate covariance matrices for each group, sum them and subtract the
duplicate counted intersection.

Not checked in details yet: degrees of freedom or small sample correction
factors, see (two) references (?)


This is the general case for MLE and GMM also

in MLE     hessian H, outerproduct of jacobian S,   cov_hjjh = HJJH,
which reduces to the above in the linear case, but can be used
generally, e.g. in discrete, and is misnomed in GenericLikelihoodModel

in GMM it's similar but I would have to look up the details, (it comes
out in sandwich form by default, it's in the sandbox), standard Newey
West or similar are on the covariance matrix of the moment conditions

quasi-MLE: MLE with mis-specified model where parameter estimates are
fine (consistent ?) but cov_params needs to be adjusted similar or
same as in sandwiches. (I did not go through any details yet.)

TODO
----
* small sample correction factors, Done for cluster, not yet for HAC
* automatic lag-length selection for Newey-West HAC,
  -> added: nlag = floor[4(T/100)^(2/9)]  Reference: xtscc paper, Newey-West
     note this will not be optimal in the panel context, see Peterson
* HAC should maybe return the chosen nlags
* get consistent notation, varies by paper, S, scale, sigma?
* replace diag(hat_matrix) calculations in cov_hc2, cov_hc3


References
----------
[1] John C. Driscoll and Aart C. Kraay, “Consistent Covariance Matrix Estimation
with Spatially Dependent Panel Data,” Review of Economics and Statistics 80,
no. 4 (1998): 549-560.

[2] Daniel Hoechle, "Robust Standard Errors for Panel Regressions with
Cross-Sectional Dependence", The Stata Journal

[3] Mitchell A. Petersen, “Estimating Standard Errors in Finance Panel Data
Sets: Comparing Approaches,” Review of Financial Studies 22, no. 1
(January 1, 2009): 435 -480.

[4] A. Colin Cameron, Jonah B. Gelbach, and Douglas L. Miller, “Robust Inference
With Multiway Clustering,” Journal of Business and Economic Statistics 29
(April 2011): 238-249.


not used yet:
A.C. Cameron, J.B. Gelbach, and D.L. Miller, “Bootstrap-based improvements
for inference with clustered errors,” The Review of Economics and
Statistics 90, no. 3 (2008): 414–427.

"""
import numpy as np
from statsmodels.tools.grouputils import combine_indices, group_sums
from statsmodels.stats.moment_helpers import se_cov
__all__ = ['cov_cluster', 'cov_cluster_2groups', 'cov_hac', 'cov_nw_panel', 'cov_white_simple', 'cov_hc0', 'cov_hc1', 'cov_hc2', 'cov_hc3', 'se_cov', 'weights_bartlett', 'weights_uniform']
"\n    HC0_se\n        White's (1980) heteroskedasticity robust standard errors.\n        Defined as sqrt(diag(X.T X)^(-1)X.T diag(e_i^(2)) X(X.T X)^(-1)\n        where e_i = resid[i]\n        HC0_se is a property.  It is not evaluated until it is called.\n        When it is called the RegressionResults instance will then have\n        another attribute cov_HC0, which is the full heteroskedasticity\n        consistent covariance matrix and also `het_scale`, which is in\n        this case just resid**2.  HCCM matrices are only appropriate for OLS.\n    HC1_se\n        MacKinnon and White's (1985) alternative heteroskedasticity robust\n        standard errors.\n        Defined as sqrt(diag(n/(n-p)*HC_0)\n        HC1_se is a property.  It is not evaluated until it is called.\n        When it is called the RegressionResults instance will then have\n        another attribute cov_HC1, which is the full HCCM and also `het_scale`,\n        which is in this case n/(n-p)*resid**2.  HCCM matrices are only\n        appropriate for OLS.\n    HC2_se\n        MacKinnon and White's (1985) alternative heteroskedasticity robust\n        standard errors.\n        Defined as (X.T X)^(-1)X.T diag(e_i^(2)/(1-h_ii)) X(X.T X)^(-1)\n        where h_ii = x_i(X.T X)^(-1)x_i.T\n        HC2_se is a property.  It is not evaluated until it is called.\n        When it is called the RegressionResults instance will then have\n        another attribute cov_HC2, which is the full HCCM and also `het_scale`,\n        which is in this case is resid^(2)/(1-h_ii).  HCCM matrices are only\n        appropriate for OLS.\n    HC3_se\n        MacKinnon and White's (1985) alternative heteroskedasticity robust\n        standard errors.\n        Defined as (X.T X)^(-1)X.T diag(e_i^(2)/(1-h_ii)^(2)) X(X.T X)^(-1)\n        where h_ii = x_i(X.T X)^(-1)x_i.T\n        HC3_se is a property.  It is not evaluated until it is called.\n        When it is called the RegressionResults instance will then have\n        another attribute cov_HC3, which is the full HCCM and also `het_scale`,\n        which is in this case is resid^(2)/(1-h_ii)^(2).  HCCM matrices are\n        only appropriate for OLS.\n\n"

def _HCCM(results, scale):
    """
    sandwich with pinv(x) * diag(scale) * pinv(x).T

    where pinv(x) = (X'X)^(-1) X
    and scale is (nobs,)
    """
    pass

def cov_hc0(results):
    """
    See statsmodels.RegressionResults
    """
    pass

def cov_hc1(results):
    """
    See statsmodels.RegressionResults
    """
    pass

def cov_hc2(results):
    """
    See statsmodels.RegressionResults
    """
    pass

def cov_hc3(results):
    """
    See statsmodels.RegressionResults
    """
    pass

def _get_sandwich_arrays(results, cov_type=''):
    """Helper function to get scores from results

    Parameters
    """
    pass

def _HCCM1(results, scale):
    """
    sandwich with pinv(x) * scale * pinv(x).T

    where pinv(x) = (X'X)^(-1) X
    and scale is (nobs, nobs), or (nobs,) with diagonal matrix diag(scale)

    Parameters
    ----------
    results : result instance
       need to contain regression results, uses results.model.pinv_wexog
    scale : ndarray (nobs,) or (nobs, nobs)
       scale matrix, treated as diagonal matrix if scale is one-dimensional

    Returns
    -------
    H : ndarray (k_vars, k_vars)
        robust covariance matrix for the parameter estimates

    """
    pass

def _HCCM2(hessian_inv, scale):
    """
    sandwich with (X'X)^(-1) * scale * (X'X)^(-1)

    scale is (kvars, kvars)
    this uses results.normalized_cov_params for (X'X)^(-1)

    Parameters
    ----------
    results : result instance
       need to contain regression results, uses results.normalized_cov_params
    scale : ndarray (k_vars, k_vars)
       scale matrix

    Returns
    -------
    H : ndarray (k_vars, k_vars)
        robust covariance matrix for the parameter estimates

    """
    pass

def weights_bartlett(nlags):
    """Bartlett weights for HAC

    this will be moved to another module

    Parameters
    ----------
    nlags : int
       highest lag in the kernel window, this does not include the zero lag

    Returns
    -------
    kernel : ndarray, (nlags+1,)
        weights for Bartlett kernel

    """
    pass

def weights_uniform(nlags):
    """uniform weights for HAC

    this will be moved to another module

    Parameters
    ----------
    nlags : int
       highest lag in the kernel window, this does not include the zero lag

    Returns
    -------
    kernel : ndarray, (nlags+1,)
        weights for uniform kernel

    """
    pass
kernel_dict = {'bartlett': weights_bartlett, 'uniform': weights_uniform}

def S_hac_simple(x, nlags=None, weights_func=weights_bartlett):
    """inner covariance matrix for HAC (Newey, West) sandwich

    assumes we have a single time series with zero axis consecutive, equal
    spaced time periods


    Parameters
    ----------
    x : ndarray (nobs,) or (nobs, k_var)
        data, for HAC this is array of x_i * u_i
    nlags : int or None
        highest lag to include in kernel window. If None, then
        nlags = floor(4(T/100)^(2/9)) is used.
    weights_func : callable
        weights_func is called with nlags as argument to get the kernel
        weights. default are Bartlett weights

    Returns
    -------
    S : ndarray, (k_vars, k_vars)
        inner covariance matrix for sandwich

    Notes
    -----
    used by cov_hac_simple

    options might change when other kernels besides Bartlett are available.

    """
    pass

def S_white_simple(x):
    """inner covariance matrix for White heteroscedastistity sandwich


    Parameters
    ----------
    x : ndarray (nobs,) or (nobs, k_var)
        data, for HAC this is array of x_i * u_i

    Returns
    -------
    S : ndarray, (k_vars, k_vars)
        inner covariance matrix for sandwich

    Notes
    -----
    this is just dot(X.T, X)

    """
    pass

def S_hac_groupsum(x, time, nlags=None, weights_func=weights_bartlett):
    """inner covariance matrix for HAC over group sums sandwich

    This assumes we have complete equal spaced time periods.
    The number of time periods per group need not be the same, but we need
    at least one observation for each time period

    For a single categorical group only, or a everything else but time
    dimension. This first aggregates x over groups for each time period, then
    applies HAC on the sum per period.

    Parameters
    ----------
    x : ndarray (nobs,) or (nobs, k_var)
        data, for HAC this is array of x_i * u_i
    time : ndarray, (nobs,)
        timeindes, assumed to be integers range(n_periods)
    nlags : int or None
        highest lag to include in kernel window. If None, then
        nlags = floor[4(T/100)^(2/9)] is used.
    weights_func : callable
        weights_func is called with nlags as argument to get the kernel
        weights. default are Bartlett weights

    Returns
    -------
    S : ndarray, (k_vars, k_vars)
        inner covariance matrix for sandwich

    References
    ----------
    Daniel Hoechle, xtscc paper
    Driscoll and Kraay

    """
    pass

def S_crosssection(x, group):
    """inner covariance matrix for White on group sums sandwich

    I guess for a single categorical group only,
    categorical group, can also be the product/intersection of groups

    This is used by cov_cluster and indirectly verified

    """
    pass

def cov_crosssection_0(results, group):
    """this one is still wrong, use cov_cluster instead"""
    pass

def cov_cluster(results, group, use_correction=True):
    """cluster robust covariance matrix

    Calculates sandwich covariance matrix for a single cluster, i.e. grouped
    variables.

    Parameters
    ----------
    results : result instance
       result of a regression, uses results.model.exog and results.resid
       TODO: this should use wexog instead
    use_correction : bool
       If true (default), then the small sample correction factor is used.

    Returns
    -------
    cov : ndarray, (k_vars, k_vars)
        cluster robust covariance matrix for parameter estimates

    Notes
    -----
    same result as Stata in UCLA example and same as Peterson

    """
    pass

def cov_cluster_2groups(results, group, group2=None, use_correction=True):
    """cluster robust covariance matrix for two groups/clusters

    Parameters
    ----------
    results : result instance
       result of a regression, uses results.model.exog and results.resid
       TODO: this should use wexog instead
    use_correction : bool
       If true (default), then the small sample correction factor is used.

    Returns
    -------
    cov_both : ndarray, (k_vars, k_vars)
        cluster robust covariance matrix for parameter estimates, for both
        clusters
    cov_0 : ndarray, (k_vars, k_vars)
        cluster robust covariance matrix for parameter estimates for first
        cluster
    cov_1 : ndarray, (k_vars, k_vars)
        cluster robust covariance matrix for parameter estimates for second
        cluster

    Notes
    -----

    verified against Peterson's table, (4 decimal print precision)
    """
    pass

def cov_white_simple(results, use_correction=True):
    """
    heteroscedasticity robust covariance matrix (White)

    Parameters
    ----------
    results : result instance
       result of a regression, uses results.model.exog and results.resid
       TODO: this should use wexog instead

    Returns
    -------
    cov : ndarray, (k_vars, k_vars)
        heteroscedasticity robust covariance matrix for parameter estimates

    Notes
    -----
    This produces the same result as cov_hc0, and does not include any small
    sample correction.

    verified (against LinearRegressionResults and Peterson)

    See Also
    --------
    cov_hc1, cov_hc2, cov_hc3 : heteroscedasticity robust covariance matrices
        with small sample corrections

    """
    pass

def cov_hac_simple(results, nlags=None, weights_func=weights_bartlett, use_correction=True):
    """
    heteroscedasticity and autocorrelation robust covariance matrix (Newey-West)

    Assumes we have a single time series with zero axis consecutive, equal
    spaced time periods


    Parameters
    ----------
    results : result instance
       result of a regression, uses results.model.exog and results.resid
       TODO: this should use wexog instead
    nlags : int or None
        highest lag to include in kernel window. If None, then
        nlags = floor[4(T/100)^(2/9)] is used.
    weights_func : callable
        weights_func is called with nlags as argument to get the kernel
        weights. default are Bartlett weights

    Returns
    -------
    cov : ndarray, (k_vars, k_vars)
        HAC robust covariance matrix for parameter estimates

    Notes
    -----
    verified only for nlags=0, which is just White
    just guessing on correction factor, need reference

    options might change when other kernels besides Bartlett are available.

    """
    pass
cov_hac = cov_hac_simple

def lagged_groups(x, lag, groupidx):
    """
    assumes sorted by time, groupidx is tuple of start and end values
    not optimized, just to get a working version, loop over groups
    """
    pass

def S_nw_panel(xw, weights, groupidx):
    """inner covariance matrix for HAC for panel data

    no denominator nobs used

    no reference for this, just accounting for time indices
    """
    pass

def cov_nw_panel(results, nlags, groupidx, weights_func=weights_bartlett, use_correction='hac'):
    """Panel HAC robust covariance matrix

    Assumes we have a panel of time series with consecutive, equal spaced time
    periods. Data is assumed to be in long format with time series of each
    individual stacked into one array. Panel can be unbalanced.

    Parameters
    ----------
    results : result instance
       result of a regression, uses results.model.exog and results.resid
       TODO: this should use wexog instead
    nlags : int or None
        Highest lag to include in kernel window. Currently, no default
        because the optimal length will depend on the number of observations
        per cross-sectional unit.
    groupidx : list of tuple
        each tuple should contain the start and end index for an individual.
        (groupidx might change in future).
    weights_func : callable
        weights_func is called with nlags as argument to get the kernel
        weights. default are Bartlett weights
    use_correction : 'cluster' or 'hac' or False
        If False, then no small sample correction is used.
        If 'cluster' (default), then the same correction as in cov_cluster is
        used.
        If 'hac', then the same correction as in single time series, cov_hac
        is used.


    Returns
    -------
    cov : ndarray, (k_vars, k_vars)
        HAC robust covariance matrix for parameter estimates

    Notes
    -----
    For nlags=0, this is just White covariance, cov_white.
    If kernel is uniform, `weights_uniform`, with nlags equal to the number
    of observations per unit in a balance panel, then cov_cluster and
    cov_hac_panel are identical.

    Tested against STATA `newey` command with same defaults.

    Options might change when other kernels besides Bartlett and uniform are
    available.

    """
    pass

def cov_nw_groupsum(results, nlags, time, weights_func=weights_bartlett, use_correction=0):
    """Driscoll and Kraay Panel robust covariance matrix

    Robust covariance matrix for panel data of Driscoll and Kraay.

    Assumes we have a panel of time series where the time index is available.
    The time index is assumed to represent equal spaced periods. At least one
    observation per period is required.

    Parameters
    ----------
    results : result instance
       result of a regression, uses results.model.exog and results.resid
       TODO: this should use wexog instead
    nlags : int or None
        Highest lag to include in kernel window. Currently, no default
        because the optimal length will depend on the number of observations
        per cross-sectional unit.
    time : ndarray of int
        this should contain the coding for the time period of each observation.
        time periods should be integers in range(maxT) where maxT is obs of i
    weights_func : callable
        weights_func is called with nlags as argument to get the kernel
        weights. default are Bartlett weights
    use_correction : 'cluster' or 'hac' or False
        If False, then no small sample correction is used.
        If 'hac' (default), then the same correction as in single time series, cov_hac
        is used.
        If 'cluster', then the same correction as in cov_cluster is
        used.

    Returns
    -------
    cov : ndarray, (k_vars, k_vars)
        HAC robust covariance matrix for parameter estimates

    Notes
    -----
    Tested against STATA xtscc package, which uses no small sample correction

    This first averages relevant variables for each time period over all
    individuals/groups, and then applies the same kernel weighted averaging
    over time as in HAC.

    Warning:
    In the example with a short panel (few time periods and many individuals)
    with mainly across individual variation this estimator did not produce
    reasonable results.

    Options might change when other kernels besides Bartlett and uniform are
    available.

    References
    ----------
    Daniel Hoechle, xtscc paper
    Driscoll and Kraay

    """
    pass