import warnings
import numpy as np
from numpy.linalg import eigh, inv, norm, matrix_rank
import pandas as pd
from scipy.optimize import minimize
from statsmodels.tools.decorators import cache_readonly
from statsmodels.base.model import Model
from statsmodels.iolib import summary2
from statsmodels.graphics.utils import _import_mpl
from .factor_rotation import rotate_factors, promax
_opt_defaults = {'gtol': 1e-07}

class Factor(Model):
    """
    Factor analysis

    Parameters
    ----------
    endog : array_like
        Variables in columns, observations in rows.  May be `None` if
        `corr` is not `None`.
    n_factor : int
        The number of factors to extract
    corr : array_like
        Directly specify the correlation matrix instead of estimating
        it from `endog`.  If provided, `endog` is not used for the
        factor analysis, it may be used in post-estimation.
    method : str
        The method to extract factors, currently must be either 'pa'
        for principal axis factor analysis or 'ml' for maximum
        likelihood estimation.
    smc : True or False
        Whether or not to apply squared multiple correlations (method='pa')
    endog_names : str
        Names of endogenous variables.  If specified, it will be used
        instead of the column names in endog
    nobs : int
        The number of observations, not used if endog is present. Needs to
        be provided for inference if endog is None.
    missing : 'none', 'drop', or 'raise'
        Missing value handling for endog, default is row-wise deletion 'drop'
        If 'none', no nan checking is done. If 'drop', any observations with
        nans are dropped. If 'raise', an error is raised.


    Notes
    -----
    **Experimental**

    Supported rotations: 'varimax', 'quartimax', 'biquartimax',
    'equamax', 'oblimin', 'parsimax', 'parsimony', 'biquartimin',
    'promax'

    If method='ml', the factors are rotated to satisfy condition IC3
    of Bai and Li (2012).  This means that the scores have covariance
    I, so the model for the covariance matrix is L * L' + diag(U),
    where L are the loadings and U are the uniquenesses.  In addition,
    L' * diag(U)^{-1} L must be diagonal.

    References
    ----------
    .. [*] Hofacker, C. (2004). Exploratory Factor Analysis, Mathematical
       Marketing. http://www.openaccesstexts.org/pdf/Quant_Chapter_11_efa.pdf
    .. [*] J Bai, K Li (2012).  Statistical analysis of factor models of high
       dimension.  Annals of Statistics. https://arxiv.org/pdf/1205.6617.pdf
    """

    def __init__(self, endog=None, n_factor=1, corr=None, method='pa', smc=True, endog_names=None, nobs=None, missing='drop'):
        _check_args_1(endog, n_factor, corr, nobs)
        if endog is not None:
            super(Factor, self).__init__(endog, exog=None, missing=missing)
            endog = self.endog
            k_endog = endog.shape[1]
            nobs = endog.shape[0]
            corr = self.corr = np.corrcoef(endog, rowvar=0)
        elif corr is not None:
            corr = self.corr = np.asarray(corr)
            k_endog = self.corr.shape[0]
            self.endog = None
        else:
            msg = 'Either endog or corr must be provided.'
            raise ValueError(msg)
        _check_args_2(endog, n_factor, corr, nobs, k_endog)
        self.n_factor = n_factor
        self.loadings = None
        self.communality = None
        self.method = method
        self.smc = smc
        self.nobs = nobs
        self.method = method
        self.corr = corr
        self.k_endog = k_endog
        if endog_names is None:
            if hasattr(corr, 'index'):
                endog_names = corr.index
            if hasattr(corr, 'columns'):
                endog_names = corr.columns
        self.endog_names = endog_names

    @property
    def endog_names(self):
        """Names of endogenous variables"""
        pass

    def fit(self, maxiter=50, tol=1e-08, start=None, opt_method='BFGS', opt=None, em_iter=3):
        """
        Estimate factor model parameters.

        Parameters
        ----------
        maxiter : int
            Maximum number of iterations for iterative estimation algorithms
        tol : float
            Stopping criteria (error tolerance) for iterative estimation
            algorithms
        start : array_like
            Starting values, currently only used for ML estimation
        opt_method : str
            Optimization method for ML estimation
        opt : dict-like
            Keyword arguments passed to optimizer, only used for ML estimation
        em_iter : int
            The number of EM iterations before starting gradient optimization,
            only used for ML estimation.

        Returns
        -------
        FactorResults
            Results class instance.
        """
        pass

    def _fit_pa(self, maxiter=50, tol=1e-08):
        """
        Extract factors using the iterative principal axis method

        Parameters
        ----------
        maxiter : int
            Maximum number of iterations for communality estimation
        tol : float
            If `norm(communality - last_communality)  < tolerance`,
            estimation stops

        Returns
        -------
        results : FactorResults instance
        """
        pass

    def loglike(self, par):
        """
        Evaluate the log-likelihood function.

        Parameters
        ----------
        par : ndarray or tuple of 2 ndarray's
            The model parameters, either a packed representation of
            the model parameters or a 2-tuple containing a `k_endog x
            n_factor` matrix of factor loadings and a `k_endog` vector
            of uniquenesses.

        Returns
        -------
        float
            The value of the log-likelihood evaluated at par.
        """
        pass

    def score(self, par):
        """
        Evaluate the score function (first derivative of loglike).

        Parameters
        ----------
        par : ndarray or tuple of 2 ndarray's
            The model parameters, either a packed representation of
            the model parameters or a 2-tuple containing a `k_endog x
            n_factor` matrix of factor loadings and a `k_endog` vector
            of uniquenesses.

        Returns
        -------
        ndarray
            The score function evaluated at par.
        """
        pass

    def _fit_ml(self, start, em_iter, opt_method, opt):
        """estimate Factor model using Maximum Likelihood
        """
        pass

    def _fit_ml_em(self, iter, random_state=None):
        """estimate Factor model using EM algorithm
        """
        pass

    def _rotate(self, load, uniq):
        """rotate loadings for MLE
        """
        pass

class FactorResults:
    """
    Factor results class

    For result summary, scree/loading plots and factor rotations

    Parameters
    ----------
    factor : Factor
        Fitted Factor class

    Attributes
    ----------
    uniqueness : ndarray
        The uniqueness (variance of uncorrelated errors unique to
        each variable)
    communality : ndarray
        1 - uniqueness
    loadings : ndarray
        Each column is the loading vector for one factor
    loadings_no_rot : ndarray
        Unrotated loadings, not available under maximum likelihood
        analysis.
    eigenvals : ndarray
        The eigenvalues for a factor analysis obtained using
        principal components; not available under ML estimation.
    n_comp : int
        Number of components (factors)
    nbs : int
        Number of observations
    fa_method : str
        The method used to obtain the decomposition, either 'pa' for
        'principal axes' or 'ml' for maximum likelihood.
    df : int
        Degrees of freedom of the factor model.

    Notes
    -----
    Under ML estimation, the default rotation (used for `loadings`) is
    condition IC3 of Bai and Li (2012).  Under this rotation, the
    factor scores are iid and standardized.  If `G` is the canonical
    loadings and `U` is the vector of uniquenesses, then the
    covariance matrix implied by the factor analysis is `GG' +
    diag(U)`.

    Status: experimental, Some refactoring will be necessary when new
        features are added.
    """

    def __init__(self, factor):
        self.model = factor
        self.endog_names = factor.endog_names
        self.loadings_no_rot = factor.loadings
        if hasattr(factor, 'eigenvals'):
            self.eigenvals = factor.eigenvals
        self.communality = factor.communality
        self.uniqueness = factor.uniqueness
        self.rotation_method = None
        self.fa_method = factor.method
        self.n_comp = factor.loadings.shape[1]
        self.nobs = factor.nobs
        self._factor = factor
        if hasattr(factor, 'mle_retvals'):
            self.mle_retvals = factor.mle_retvals
        p, k = self.loadings_no_rot.shape
        self.df = ((p - k) ** 2 - (p + k)) // 2
        self.loadings = factor.loadings
        self.rotation_matrix = np.eye(self.n_comp)

    def __str__(self):
        return self.summary().__str__()

    def rotate(self, method):
        """
        Apply rotation, inplace modification of this Results instance

        Parameters
        ----------
        method : str
            Rotation to be applied.  Allowed methods are varimax,
            quartimax, biquartimax, equamax, oblimin, parsimax,
            parsimony, biquartimin, promax.

        Returns
        -------
        None : nothing returned, modifications are inplace


        Notes
        -----
        Warning: 'varimax', 'quartimax' and 'oblimin' are verified against R or
        Stata. Some rotation methods such as promax do not produce the same
        results as the R or Stata default functions.

        See Also
        --------
        factor_rotation : subpackage that implements rotation methods
        """
        pass

    def _corr_factors(self):
        """correlation of factors implied by rotation

        If the rotation is oblique, then the factors are correlated.

        currently not cached

        Returns
        -------
        corr_f : ndarray
            correlation matrix of rotated factors, assuming initial factors are
            orthogonal
        """
        pass

    def factor_score_params(self, method='bartlett'):
        """
        Compute factor scoring coefficient matrix

        The coefficient matrix is not cached.

        Parameters
        ----------
        method : 'bartlett' or 'regression'
            Method to use for factor scoring.
            'regression' can be abbreviated to `reg`

        Returns
        -------
        coeff_matrix : ndarray
            matrix s to compute factors f from a standardized endog ys.
            ``f = ys dot s``

        Notes
        -----
        The `regression` method follows the Stata definition.
        Method bartlett and regression are verified against Stats.
        Two unofficial methods, 'ols' and 'gls', produce similar factor scores
        but are not verified.

        See Also
        --------
        statsmodels.multivariate.factor.FactorResults.factor_scoring
        """
        pass

    def factor_scoring(self, endog=None, method='bartlett', transform=True):
        """
        factor scoring: compute factors for endog

        If endog was not provided when creating the factor class, then
        a standarized endog needs to be provided here.

        Parameters
        ----------
        method : 'bartlett' or 'regression'
            Method to use for factor scoring.
            'regression' can be abbreviated to `reg`
        transform : bool
            If transform is true and endog is provided, then it will be
            standardized using mean and scale of original data, which has to
            be available in this case.
            If transform is False, then a provided endog will be used unchanged.
            The original endog in the Factor class will
            always be standardized if endog is None, independently of `transform`.

        Returns
        -------
        factor_score : ndarray
            estimated factors using scoring matrix s and standarized endog ys
            ``f = ys dot s``

        Notes
        -----
        Status: transform option is experimental and might change.

        See Also
        --------
        statsmodels.multivariate.factor.FactorResults.factor_score_params
        """
        pass

    def summary(self):
        """Summary"""
        pass

    def get_loadings_frame(self, style='display', sort_=True, threshold=0.3, highlight_max=True, color_max='yellow', decimals=None):
        """get loadings matrix as DataFrame or pandas Styler

        Parameters
        ----------
        style : 'display' (default), 'raw' or 'strings'
            Style to use for display

            * 'raw' returns just a DataFrame of the loadings matrix, no options are
               applied
            * 'display' add sorting and styling as defined by other keywords
            * 'strings' returns a DataFrame with string elements with optional sorting
               and suppressing small loading coefficients.

        sort_ : bool
            If True, then the rows of the DataFrame is sorted by contribution of each
            factor. applies if style is either 'display' or 'strings'
        threshold : float
            If the threshold is larger than zero, then loading coefficients are
            either colored white (if style is 'display') or replace by empty
            string (if style is 'strings').
        highlight_max : bool
            This add a background color to the largest coefficient in each row.
        color_max : html color
            default is 'yellow'. color for background of row maximum
        decimals : None or int
            If None, then pandas default precision applies. Otherwise values are
            rounded to the specified decimals. If style is 'display', then the
            underlying dataframe is not changed. If style is 'strings', then
            values are rounded before conversion to strings.

        Returns
        -------
        loadings : DataFrame or pandas Styler instance
            The return is a pandas Styler instance, if style is 'display' and
            at least one of highlight_max, threshold or decimals is applied.
            Otherwise, the returned loadings is a DataFrame.

        Examples
        --------
        >>> mod = Factor(df, 3, smc=True)
        >>> res = mod.fit()
        >>> res.get_loadings_frame(style='display', decimals=3, threshold=0.2)

        To get a sorted DataFrame, all styling options need to be turned off:

        >>> df_sorted = res.get_loadings_frame(style='display',
        ...             highlight_max=False, decimals=None, threshold=0)

        Options except for highlighting are available for plain test or Latex
        usage:

        >>> lds = res_u.get_loadings_frame(style='strings', decimals=3,
        ...                                threshold=0.3)
        >>> print(lds.to_latex())
        """
        pass

    def plot_scree(self, ncomp=None):
        """
        Plot of the ordered eigenvalues and variance explained for the loadings

        Parameters
        ----------
        ncomp : int, optional
            Number of loadings to include in the plot.  If None, will
            included the same as the number of maximum possible loadings

        Returns
        -------
        Figure
            Handle to the figure.
        """
        pass

    def plot_loadings(self, loading_pairs=None, plot_prerotated=False):
        """
        Plot factor loadings in 2-d plots

        Parameters
        ----------
        loading_pairs : None or a list of tuples
            Specify plots. Each tuple (i, j) represent one figure, i and j is
            the loading number for x-axis and y-axis, respectively. If `None`,
            all combinations of the loadings will be plotted.
        plot_prerotated : True or False
            If True, the loadings before rotation applied will be plotted. If
            False, rotated loadings will be plotted.

        Returns
        -------
        figs : a list of figure handles
        """
        pass

    @cache_readonly
    def fitted_cov(self):
        """
        Returns the fitted covariance matrix.
        """
        pass

    @cache_readonly
    def uniq_stderr(self, kurt=0):
        """
        The standard errors of the uniquenesses.

        Parameters
        ----------
        kurt : float
            Excess kurtosis

        Notes
        -----
        If excess kurtosis is known, provide as `kurt`.  Standard
        errors are only available if the model was fit using maximum
        likelihood.  If `endog` is not provided, `nobs` must be
        provided to obtain standard errors.

        These are asymptotic standard errors.  See Bai and Li (2012)
        for conditions under which the standard errors are valid.

        The standard errors are only applicable to the original,
        unrotated maximum likelihood solution.
        """
        pass

    @cache_readonly
    def load_stderr(self):
        """
        The standard errors of the loadings.

        Standard errors are only available if the model was fit using
        maximum likelihood.  If `endog` is not provided, `nobs` must be
        provided to obtain standard errors.

        These are asymptotic standard errors.  See Bai and Li (2012)
        for conditions under which the standard errors are valid.

        The standard errors are only applicable to the original,
        unrotated maximum likelihood solution.
        """
        pass