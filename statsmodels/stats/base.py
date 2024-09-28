"""Base classes for statistical test results

Created on Mon Apr 22 14:03:21 2013

Author: Josef Perktold
"""
from statsmodels.compat.python import lzip
import numpy as np
from statsmodels.tools.testing import Holder

class HolderTuple(Holder):
    """Holder class with indexing

    """

    def __init__(self, tuple_=None, **kwds):
        super(HolderTuple, self).__init__(**kwds)
        if tuple_ is not None:
            self.tuple = tuple((getattr(self, att) for att in tuple_))
        else:
            self.tuple = (self.statistic, self.pvalue)

    def __iter__(self):
        yield from self.tuple

    def __getitem__(self, idx):
        return self.tuple[idx]

    def __len__(self):
        return len(self.tuple)

    def __array__(self, dtype=None):
        return np.asarray(list(self.tuple), dtype=dtype)

class AllPairsResults:
    """Results class for pairwise comparisons, based on p-values

    Parameters
    ----------
    pvals_raw : array_like, 1-D
        p-values from a pairwise comparison test
    all_pairs : list of tuples
        list of indices, one pair for each comparison
    multitest_method : str
        method that is used by default for p-value correction. This is used
        as default by the methods like if the multiple-testing method is not
        specified as argument.
    levels : {list[str], None}
        optional names of the levels or groups
    n_levels : None or int
        If None, then the number of levels or groups is inferred from the
        other arguments. It can be explicitly specified, if the inferred
        number is incorrect.

    Notes
    -----
    This class can also be used for other pairwise comparisons, for example
    comparing several treatments to a control (as in Dunnet's test).

    """

    def __init__(self, pvals_raw, all_pairs, multitest_method='hs', levels=None, n_levels=None):
        self.pvals_raw = pvals_raw
        self.all_pairs = all_pairs
        if n_levels is None:
            self.n_levels = np.max(all_pairs) + 1
        else:
            self.n_levels = n_levels
        self.multitest_method = multitest_method
        self.levels = levels
        if levels is None:
            self.all_pairs_names = ['%r' % (pairs,) for pairs in all_pairs]
        else:
            self.all_pairs_names = ['%s-%s' % (levels[pairs[0]], levels[pairs[1]]) for pairs in all_pairs]

    def pval_corrected(self, method=None):
        """p-values corrected for multiple testing problem

        This uses the default p-value correction of the instance stored in
        ``self.multitest_method`` if method is None.

        """
        pass

    def __str__(self):
        return self.summary()

    def pval_table(self):
        """create a (n_levels, n_levels) array with corrected p_values

        this needs to improve, similar to R pairwise output
        """
        pass

    def summary(self):
        """returns text summarizing the results

        uses the default pvalue correction of the instance stored in
        ``self.multitest_method``
        """
        pass