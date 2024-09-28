"""
Module of kernels that are able to handle continuous as well as categorical
variables (both ordered and unordered).

This is a slight deviation from the current approach in
statsmodels.nonparametric.kernels where each kernel is a class object.

Having kernel functions rather than classes makes extension to a multivariate
kernel density estimation much easier.

NOTE: As it is, this module does not interact with the existing API
"""
import numpy as np
from scipy.special import erf

def aitchison_aitken(h, Xi, x, num_levels=None):
    """
    The Aitchison-Aitken kernel, used for unordered discrete random variables.

    Parameters
    ----------
    h : 1-D ndarray, shape (K,)
        The bandwidths used to estimate the value of the kernel function.
    Xi : 2-D ndarray of ints, shape (nobs, K)
        The value of the training set.
    x : 1-D ndarray, shape (K,)
        The value at which the kernel density is being estimated.
    num_levels : bool, optional
        Gives the user the option to specify the number of levels for the
        random variable.  If False, the number of levels is calculated from
        the data.

    Returns
    -------
    kernel_value : ndarray, shape (nobs, K)
        The value of the kernel function at each training point for each var.

    Notes
    -----
    See p.18 of [2]_ for details.  The value of the kernel L if :math:`X_{i}=x`
    is :math:`1-\\lambda`, otherwise it is :math:`\\frac{\\lambda}{c-1}`.
    Here :math:`c` is the number of levels plus one of the RV.

    References
    ----------
    .. [*] J. Aitchison and C.G.G. Aitken, "Multivariate binary discrimination
           by the kernel method", Biometrika, vol. 63, pp. 413-420, 1976.
    .. [*] Racine, Jeff. "Nonparametric Econometrics: A Primer," Foundation
           and Trends in Econometrics: Vol 3: No 1, pp1-88., 2008.
    """
    pass

def wang_ryzin(h, Xi, x):
    """
    The Wang-Ryzin kernel, used for ordered discrete random variables.

    Parameters
    ----------
    h : scalar or 1-D ndarray, shape (K,)
        The bandwidths used to estimate the value of the kernel function.
    Xi : ndarray of ints, shape (nobs, K)
        The value of the training set.
    x : scalar or 1-D ndarray of shape (K,)
        The value at which the kernel density is being estimated.

    Returns
    -------
    kernel_value : ndarray, shape (nobs, K)
        The value of the kernel function at each training point for each var.

    Notes
    -----
    See p. 19 in [1]_ for details.  The value of the kernel L if
    :math:`X_{i}=x` is :math:`1-\\lambda`, otherwise it is
    :math:`\\frac{1-\\lambda}{2}\\lambda^{|X_{i}-x|}`, where :math:`\\lambda` is
    the bandwidth.

    References
    ----------
    .. [*] Racine, Jeff. "Nonparametric Econometrics: A Primer," Foundation
           and Trends in Econometrics: Vol 3: No 1, pp1-88., 2008.
           http://dx.doi.org/10.1561/0800000009
    .. [*] M.-C. Wang and J. van Ryzin, "A class of smooth estimators for
           discrete distributions", Biometrika, vol. 68, pp. 301-309, 1981.
    """
    pass

def gaussian(h, Xi, x):
    """
    Gaussian Kernel for continuous variables
    Parameters
    ----------
    h : 1-D ndarray, shape (K,)
        The bandwidths used to estimate the value of the kernel function.
    Xi : 1-D ndarray, shape (K,)
        The value of the training set.
    x : 1-D ndarray, shape (K,)
        The value at which the kernel density is being estimated.

    Returns
    -------
    kernel_value : ndarray, shape (nobs, K)
        The value of the kernel function at each training point for each var.
    """
    pass

def tricube(h, Xi, x):
    """
    Tricube Kernel for continuous variables
    Parameters
    ----------
    h : 1-D ndarray, shape (K,)
        The bandwidths used to estimate the value of the kernel function.
    Xi : 1-D ndarray, shape (K,)
        The value of the training set.
    x : 1-D ndarray, shape (K,)
        The value at which the kernel density is being estimated.

    Returns
    -------
    kernel_value : ndarray, shape (nobs, K)
        The value of the kernel function at each training point for each var.
    """
    pass

def gaussian_convolution(h, Xi, x):
    """ Calculates the Gaussian Convolution Kernel """
    pass

def aitchison_aitken_reg(h, Xi, x):
    """
    A version for the Aitchison-Aitken kernel for nonparametric regression.

    Suggested by Li and Racine.
    """
    pass

def wang_ryzin_reg(h, Xi, x):
    """
    A version for the Wang-Ryzin kernel for nonparametric regression.

    Suggested by Li and Racine in [1] ch.4
    """
    pass