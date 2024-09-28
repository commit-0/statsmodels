"""
News for state space models

Author: Chad Fulton
License: BSD-3
"""
from statsmodels.compat.pandas import FUTURE_STACK
import numpy as np
import pandas as pd
from statsmodels.iolib.summary import Summary
from statsmodels.iolib.table import SimpleTable
from statsmodels.iolib.tableformatting import fmt_params

class NewsResults:
    """
    Impacts of data revisions and news on estimates of variables of interest

    Parameters
    ----------
    news_results : SimpleNamespace instance
        Results from `KalmanSmoother.news`.
    model : MLEResults
        The results object associated with the model from which the NewsResults
        was generated.
    updated : MLEResults
        The results object associated with the model containing the updated
        dataset.
    previous : MLEResults
        The results object associated with the model containing the previous
        dataset.
    impacted_variable : str, list, array, or slice, optional
        Observation variable label or slice of labels specifying particular
        impacted variables to display in output. The impacted variable(s)
        describe the variables that were *affected* by the news. If you do not
        know the labels for the variables, check the `endog_names` attribute of
        the model instance.
    tolerance : float, optional
        The numerical threshold for determining zero impact. Default is that
        any impact less than 1e-10 is assumed to be zero.
    row_labels : iterable
        Row labels (often dates) for the impacts of the revisions and news.

    Attributes
    ----------
    total_impacts : pd.DataFrame
        Updates to forecasts of impacted variables from both news and data
        revisions, E[y^i | post] - E[y^i | previous].
    update_impacts : pd.DataFrame
        Updates to forecasts of impacted variables from the news,
        E[y^i | post] - E[y^i | revisions] where y^i are the impacted variables
        of interest.
    revision_impacts : pd.DataFrame
        Updates to forecasts of impacted variables from all data revisions,
        E[y^i | revisions] - E[y^i | previous].
    news : pd.DataFrame
        The unexpected component of the updated data,
        E[y^u | post] - E[y^u | revisions] where y^u are the updated variables.
    weights : pd.DataFrame
        Weights describing the effect of news on variables of interest.
    revisions : pd.DataFrame
        The revisions between the current and previously observed data, for
        revisions for which detailed impacts were computed.
    revisions_all : pd.DataFrame
        The revisions between the current and previously observed data,
        y^r_{revised} - y^r_{previous} where y^r are the revised variables.
    revision_weights : pd.DataFrame
        Weights describing the effect of revisions on variables of interest,
        for revisions for which detailed impacts were computed.
    revision_weights_all : pd.DataFrame
        Weights describing the effect of revisions on variables of interest,
        with a new entry that includes NaNs for the revisions for which
        detailed impacts were not computed.
    update_forecasts : pd.DataFrame
        Forecasts based on the previous dataset of the variables that were
        updated, E[y^u | previous].
    update_realized : pd.DataFrame
        Actual observed data associated with the variables that were
        updated, y^u
    revisions_details_start : int
        Integer index of first period in which detailed revision impacts were
        computed.
    revision_detailed_impacts : pd.DataFrame
        Updates to forecasts of impacted variables from data revisions with
        detailed impacts, E[y^i | revisions] - E[y^i | grouped revisions].
    revision_grouped_impacts : pd.DataFrame
        Updates to forecasts of impacted variables from data revisions that
        were grouped together, E[y^i | grouped revisions] - E[y^i | previous].
    revised_prev : pd.DataFrame
        Previously observed data associated with the variables that were
        revised, for revisions for which detailed impacts were computed.
    revised_prev_all : pd.DataFrame
        Previously observed data associated with the variables that were
        revised, y^r_{previous}
    revised : pd.DataFrame
        Currently observed data associated with the variables that were
        revised, for revisions for which detailed impacts were computed.
    revised_all : pd.DataFrame
        Currently observed data associated with the variables that were
        revised, y^r_{revised}
    prev_impacted_forecasts : pd.DataFrame
        Previous forecast of the variables of interest, E[y^i | previous].
    post_impacted_forecasts : pd.DataFrame
        Forecast of the variables of interest after taking into account both
        revisions and updates, E[y^i | post].
    revisions_iloc : pd.DataFrame
        The integer locations of the data revisions in the dataset.
    revisions_ix : pd.DataFrame
        The label-based locations of the data revisions in the dataset.
    revisions_iloc_detailed : pd.DataFrame
        The integer locations of the data revisions in the dataset for which
        detailed impacts were computed.
    revisions_ix_detailed : pd.DataFrame
        The label-based locations of the data revisions in the dataset for
        which detailed impacts were computed.
    updates_iloc : pd.DataFrame
        The integer locations of the updated data points.
    updates_ix : pd.DataFrame
        The label-based locations of updated data points.
    state_index : array_like
        Index of state variables used to compute impacts.

    References
    ----------
    .. [1] Bańbura, Marta, and Michele Modugno.
           "Maximum likelihood estimation of factor models on datasets with
           arbitrary pattern of missing data."
           Journal of Applied Econometrics 29, no. 1 (2014): 133-160.
    .. [2] Bańbura, Marta, Domenico Giannone, and Lucrezia Reichlin.
           "Nowcasting."
           The Oxford Handbook of Economic Forecasting. July 8, 2011.
    .. [3] Bańbura, Marta, Domenico Giannone, Michele Modugno, and Lucrezia
           Reichlin.
           "Now-casting and the real-time data flow."
           In Handbook of economic forecasting, vol. 2, pp. 195-237.
           Elsevier, 2013.
    """

    def __init__(self, news_results, model, updated, previous, impacted_variable=None, tolerance=1e-10, row_labels=None):
        self.model = model
        self.updated = updated
        self.previous = previous
        self.news_results = news_results
        self._impacted_variable = impacted_variable
        self._tolerance = tolerance
        self.row_labels = row_labels
        self.params = []
        self.endog_names = self.updated.model.endog_names
        self.k_endog = len(self.endog_names)
        self.n_revisions = len(self.news_results.revisions_ix)
        self.n_revisions_detailed = len(self.news_results.revisions_details)
        self.n_revisions_grouped = len(self.news_results.revisions_grouped)
        index = self.updated.model._index
        columns = np.atleast_1d(self.endog_names)
        self.post_impacted_forecasts = pd.DataFrame(news_results.post_impacted_forecasts.T, index=self.row_labels, columns=columns).rename_axis(index='impact date', columns='impacted variable')
        self.prev_impacted_forecasts = pd.DataFrame(news_results.prev_impacted_forecasts.T, index=self.row_labels, columns=columns).rename_axis(index='impact date', columns='impacted variable')
        self.update_impacts = pd.DataFrame(news_results.update_impacts, index=self.row_labels, columns=columns).rename_axis(index='impact date', columns='impacted variable')
        self.revision_detailed_impacts = pd.DataFrame(news_results.revision_detailed_impacts, index=self.row_labels, columns=columns, dtype=float).rename_axis(index='impact date', columns='impacted variable')
        self.revision_impacts = pd.DataFrame(news_results.revision_impacts, index=self.row_labels, columns=columns, dtype=float).rename_axis(index='impact date', columns='impacted variable')
        self.revision_grouped_impacts = self.revision_impacts - self.revision_detailed_impacts.fillna(0)
        if self.n_revisions_grouped == 0:
            self.revision_grouped_impacts.loc[:] = 0
        self.total_impacts = self.post_impacted_forecasts - self.prev_impacted_forecasts
        self.revisions_details_start = news_results.revisions_details_start
        self.revisions_iloc = pd.DataFrame(list(zip(*news_results.revisions_ix)), index=['revision date', 'revised variable']).T
        iloc = self.revisions_iloc
        if len(iloc) > 0:
            self.revisions_ix = pd.DataFrame({'revision date': index[iloc['revision date']], 'revised variable': columns[iloc['revised variable']]})
        else:
            self.revisions_ix = iloc.copy()
        mask = iloc['revision date'] >= self.revisions_details_start
        self.revisions_iloc_detailed = self.revisions_iloc[mask]
        self.revisions_ix_detailed = self.revisions_ix[mask]
        self.updates_iloc = pd.DataFrame(list(zip(*news_results.updates_ix)), index=['update date', 'updated variable']).T
        iloc = self.updates_iloc
        if len(iloc) > 0:
            self.updates_ix = pd.DataFrame({'update date': index[iloc['update date']], 'updated variable': columns[iloc['updated variable']]})
        else:
            self.updates_ix = iloc.copy()
        self.state_index = news_results.state_index
        r_ix_all = pd.MultiIndex.from_arrays([self.revisions_ix['revision date'], self.revisions_ix['revised variable']])
        r_ix = pd.MultiIndex.from_arrays([self.revisions_ix_detailed['revision date'], self.revisions_ix_detailed['revised variable']])
        u_ix = pd.MultiIndex.from_arrays([self.updates_ix['update date'], self.updates_ix['updated variable']])
        if news_results.news is None:
            self.news = pd.Series([], index=u_ix, name='news', dtype=model.params.dtype)
        else:
            self.news = pd.Series(news_results.news, index=u_ix, name='news')
        if news_results.revisions_all is None:
            self.revisions_all = pd.Series([], index=r_ix_all, name='revision', dtype=model.params.dtype)
        else:
            self.revisions_all = pd.Series(news_results.revisions_all, index=r_ix_all, name='revision')
        if news_results.revisions is None:
            self.revisions = pd.Series([], index=r_ix, name='revision', dtype=model.params.dtype)
        else:
            self.revisions = pd.Series(news_results.revisions, index=r_ix, name='revision')
        if news_results.update_forecasts is None:
            self.update_forecasts = pd.Series([], index=u_ix, dtype=model.params.dtype)
        else:
            self.update_forecasts = pd.Series(news_results.update_forecasts, index=u_ix)
        if news_results.revised_all is None:
            self.revised_all = pd.Series([], index=r_ix_all, dtype=model.params.dtype, name='revised')
        else:
            self.revised_all = pd.Series(news_results.revised_all, index=r_ix_all, name='revised')
        if news_results.revised is None:
            self.revised = pd.Series([], index=r_ix, dtype=model.params.dtype, name='revised')
        else:
            self.revised = pd.Series(news_results.revised, index=r_ix, name='revised')
        if news_results.revised_prev_all is None:
            self.revised_prev_all = pd.Series([], index=r_ix_all, dtype=model.params.dtype)
        else:
            self.revised_prev_all = pd.Series(news_results.revised_prev_all, index=r_ix_all)
        if news_results.revised_prev is None:
            self.revised_prev = pd.Series([], index=r_ix, dtype=model.params.dtype)
        else:
            self.revised_prev = pd.Series(news_results.revised_prev, index=r_ix)
        if news_results.update_realized is None:
            self.update_realized = pd.Series([], index=u_ix, dtype=model.params.dtype)
        else:
            self.update_realized = pd.Series(news_results.update_realized, index=u_ix)
        cols = pd.MultiIndex.from_product([self.row_labels, columns])
        if len(self.updates_iloc):
            weights = news_results.gain.reshape(len(cols), len(u_ix))
        else:
            weights = np.zeros((len(cols), len(u_ix)))
        self.weights = pd.DataFrame(weights, index=cols, columns=u_ix).T
        self.weights.columns.names = ['impact date', 'impacted variable']
        if self.n_revisions_detailed > 0:
            revision_weights = news_results.revision_weights.reshape(len(cols), len(r_ix))
        else:
            revision_weights = np.zeros((len(cols), len(r_ix)))
        self.revision_weights = pd.DataFrame(revision_weights, index=cols, columns=r_ix).T
        self.revision_weights.columns.names = ['impact date', 'impacted variable']
        self.revision_weights_all = self.revision_weights.reindex(self.revised_all.index)

    @property
    def data_revisions(self):
        """
        Revisions to data points that existed in the previous dataset

        Returns
        -------
        data_revisions : pd.DataFrame
            Index is as MultiIndex consisting of `revision date` and
            `revised variable`. The columns are:

            - `observed (prev)`: the value of the data as it was observed
              in the previous dataset.
            - `revised`: the revised value of the data, as it is observed
              in the new dataset
            - `detailed impacts computed`: whether or not detailed impacts have
              been computed in these NewsResults for this revision

        See also
        --------
        data_updates
        """
        pass

    @property
    def data_updates(self):
        """
        Updated data; new entries that did not exist in the previous dataset

        Returns
        -------
        data_updates : pd.DataFrame
            Index is as MultiIndex consisting of `update date` and
            `updated variable`. The columns are:

            - `forecast (prev)`: the previous forecast of the new entry,
              based on the information available in the previous dataset
              (recall that for these updated data points, the previous dataset
              had no observed value for them at all)
            - `observed`: the value of the new entry, as it is observed in the
              new dataset

        See also
        --------
        data_revisions
        """
        pass

    @property
    def details_by_impact(self):
        """
        Details of forecast revisions from news, organized by impacts first

        Returns
        -------
        details : pd.DataFrame
            Index is as MultiIndex consisting of:

            - `impact date`: the date of the impact on the variable of interest
            - `impacted variable`: the variable that is being impacted
            - `update date`: the date of the data update, that results in
              `news` that impacts the forecast of variables of interest
            - `updated variable`: the variable being updated, that results in
              `news` that impacts the forecast of variables of interest

            The columns are:

            - `forecast (prev)`: the previous forecast of the new entry,
              based on the information available in the previous dataset
            - `observed`: the value of the new entry, as it is observed in the
              new dataset
            - `news`: the news associated with the update (this is just the
              forecast error: `observed` - `forecast (prev)`)
            - `weight`: the weight describing how the `news` effects the
              forecast of the variable of interest
            - `impact`: the impact of the `news` on the forecast of the
              variable of interest

        Notes
        -----
        This table decomposes updated forecasts of variables of interest from
        the `news` associated with each updated datapoint from the new data
        release.

        This table does not summarize the impacts or show the effect of
        revisions. That information can be found in the `impacts` or
        `revision_details_by_impact` tables.

        This form of the details table is organized so that the impacted
        dates / variables are first in the index. This is convenient for
        slicing by impacted variables / dates to view the details of data
        updates for a particular variable or date.

        However, since the `forecast (prev)` and `observed` columns have a lot
        of duplication, printing the entire table gives a result that is less
        easy to parse than that produced by the `details_by_update` property.
        `details_by_update` contains the same information but is organized to
        be more convenient for displaying the entire table of detailed updates.
        At the same time, `details_by_update` is less convenient for
        subsetting.

        See Also
        --------
        details_by_update
        revision_details_by_update
        impacts
        """
        pass

    @property
    def revision_details_by_impact(self):
        """
        Details of forecast revisions from revised data, organized by impacts

        Returns
        -------
        details : pd.DataFrame
            Index is as MultiIndex consisting of:

            - `impact date`: the date of the impact on the variable of interest
            - `impacted variable`: the variable that is being impacted
            - `revision date`: the date of the data revision, that results in
              `revision` that impacts the forecast of variables of interest
            - `revised variable`: the variable being revised, that results in
              `news` that impacts the forecast of variables of interest

            The columns are:

            - `observed (prev)`: the previous value of the observation, as it
              was given in the previous dataset
            - `revised`: the value of the revised entry, as it is observed in
              the new dataset
            - `revision`: the revision (this is `revised` - `observed (prev)`)
            - `weight`: the weight describing how the `revision` effects the
              forecast of the variable of interest
            - `impact`: the impact of the `revision` on the forecast of the
              variable of interest

        Notes
        -----
        This table decomposes updated forecasts of variables of interest from
        the `revision` associated with each revised datapoint from the new data
        release.

        This table does not summarize the impacts or show the effect of
        new datapoints. That information can be found in the
        `impacts` or `details_by_impact` tables.

        Grouped impacts are shown in this table, with a "revision date" equal
        to the last period prior to which detailed revisions were computed and
        with "revised variable" set to the string "all prior revisions". For
        these rows, all columns except "impact" will be set to NaNs.

        This form of the details table is organized so that the impacted
        dates / variables are first in the index. This is convenient for
        slicing by impacted variables / dates to view the details of data
        updates for a particular variable or date.

        However, since the `observed (prev)` and `revised` columns have a lot
        of duplication, printing the entire table gives a result that is less
        easy to parse than that produced by the `details_by_revision` property.
        `details_by_revision` contains the same information but is organized to
        be more convenient for displaying the entire table of detailed
        revisions. At the same time, `details_by_revision` is less convenient
        for subsetting.

        See Also
        --------
        details_by_revision
        details_by_impact
        impacts
        """
        pass

    @property
    def details_by_update(self):
        """
        Details of forecast revisions from news, organized by updates first

        Returns
        -------
        details : pd.DataFrame
            Index is as MultiIndex consisting of:

            - `update date`: the date of the data update, that results in
              `news` that impacts the forecast of variables of interest
            - `updated variable`: the variable being updated, that results in
              `news` that impacts the forecast of variables of interest
            - `forecast (prev)`: the previous forecast of the new entry,
              based on the information available in the previous dataset
            - `observed`: the value of the new entry, as it is observed in the
              new dataset
            - `impact date`: the date of the impact on the variable of interest
            - `impacted variable`: the variable that is being impacted

            The columns are:

            - `news`: the news associated with the update (this is just the
              forecast error: `observed` - `forecast (prev)`)
            - `weight`: the weight describing how the `news` affects the
              forecast of the variable of interest
            - `impact`: the impact of the `news` on the forecast of the
              variable of interest

        Notes
        -----
        This table decomposes updated forecasts of variables of interest from
        the `news` associated with each updated datapoint from the new data
        release.

        This table does not summarize the impacts or show the effect of
        revisions. That information can be found in the `impacts` table.

        This form of the details table is organized so that the updated
        dates / variables are first in the index, and in this table the index
        also contains the forecasts and observed values of the updates. This is
        convenient for displaying the entire table of detailed updates because
        it allows sparsifying duplicate entries.

        However, since it includes forecasts and observed values in the index
        of the table, it is not convenient for subsetting by the variable of
        interest. Instead, the `details_by_impact` property is organized to
        make slicing by impacted variables / dates easy. This allows, for
        example, viewing the details of data updates on a particular variable
        or date of interest.

        See Also
        --------
        details_by_impact
        impacts
        """
        pass

    @property
    def revision_details_by_update(self):
        """
        Details of forecast revisions from revisions, organized by updates

        Returns
        -------
        details : pd.DataFrame
            Index is as MultiIndex consisting of:

            - `revision date`: the date of the data revision, that results in
              `revision` that impacts the forecast of variables of interest
            - `revised variable`: the variable being revised, that results in
              `news` that impacts the forecast of variables of interest
            - `observed (prev)`: the previous value of the observation, as it
              was given in the previous dataset
            - `revised`: the value of the revised entry, as it is observed in
              the new dataset
            - `impact date`: the date of the impact on the variable of interest
            - `impacted variable`: the variable that is being impacted

            The columns are:

            - `revision`: the revision (this is `revised` - `observed (prev)`)
            - `weight`: the weight describing how the `revision` affects the
              forecast of the variable of interest
            - `impact`: the impact of the `revision` on the forecast of the
              variable of interest

        Notes
        -----
        This table decomposes updated forecasts of variables of interest from
        the `revision` associated with each revised datapoint from the new data
        release.

        This table does not summarize the impacts or show the effect of
        new datapoints, see `details_by_update` instead.

        Grouped impacts are shown in this table, with a "revision date" equal
        to the last period prior to which detailed revisions were computed and
        with "revised variable" set to the string "all prior revisions". For
        these rows, all columns except "impact" will be set to NaNs.

        This form of the details table is organized so that the revision
        dates / variables are first in the index, and in this table the index
        also contains the previously observed and revised values. This is
        convenient for displaying the entire table of detailed revisions
        because it allows sparsifying duplicate entries.

        However, since it includes previous observations and revisions in the
        index of the table, it is not convenient for subsetting by the variable
        of interest. Instead, the `revision_details_by_impact` property is
        organized to make slicing by impacted variables / dates easy. This
        allows, for example, viewing the details of data revisions on a
        particular variable or date of interest.

        See Also
        --------
        details_by_impact
        impacts
        """
        pass

    @property
    def impacts(self):
        """
        Impacts from news and revisions on all dates / variables of interest

        Returns
        -------
        impacts : pd.DataFrame
            Index is as MultiIndex consisting of:

            - `impact date`: the date of the impact on the variable of interest
            - `impacted variable`: the variable that is being impacted

            The columns are:

            - `estimate (prev)`: the previous estimate / forecast of the
              date / variable of interest.
            - `impact of revisions`: the impact of all data revisions on
              the estimate of the date / variable of interest.
            - `impact of news`: the impact of all news on the estimate of
              the date / variable of interest.
            - `total impact`: the total impact of both revisions and news on
              the estimate of the date / variable of interest.
            - `estimate (new)`: the new estimate / forecast of the
              date / variable of interest after taking into account the effects
              of the revisions and news.

        Notes
        -----
        This table decomposes updated forecasts of variables of interest into
        the overall effect from revisions and news.

        This table does not break down the detail by the updated
        dates / variables. That information can be found in the
        `details_by_impact` `details_by_update` tables.

        See Also
        --------
        details_by_impact
        details_by_update
        """
        pass

    def summary_impacts(self, impact_date=None, impacted_variable=None, groupby='impact date', show_revisions_columns=None, sparsify=True, float_format='%.2f'):
        """
        Create summary table with detailed impacts from news; by date, variable

        Parameters
        ----------
        impact_date : int, str, datetime, list, array, or slice, optional
            Observation index label or slice of labels specifying particular
            impact periods to display. The impact date(s) describe the periods
            in which impacted variables were *affected* by the news. If this
            argument is given, the output table will only show this impact date
            or dates. Note that this argument is passed to the Pandas `loc`
            accessor, and so it should correspond to the labels of the model's
            index. If the model was created with data in a list or numpy array,
            then these labels will be zero-indexes observation integers.
        impacted_variable : str, list, array, or slice, optional
            Observation variable label or slice of labels specifying particular
            impacted variables to display. The impacted variable(s) describe
            the variables that were *affected* by the news. If you do not know
            the labels for the variables, check the `endog_names` attribute of
            the model instance.
        groupby : {impact date, impacted date}
            The primary variable for grouping results in the impacts table. The
            default is to group by update date.
        show_revisions_columns : bool, optional
            If set to False, the impacts table will not show the impacts from
            data revisions or the total impacts. Default is to show the
            revisions and totals columns if any revisions were made and
            otherwise to hide them.
        sparsify : bool, optional, default True
            Set to False for the table to include every one of the multiindex
            keys at each row.
        float_format : str, optional
            Formatter format string syntax for converting numbers to strings.
            Default is '%.2f'.

        Returns
        -------
        impacts_table : SimpleTable
            Table describing total impacts from both revisions and news. See
            the documentation for the `impacts` attribute for more details
            about the index and columns.

        See Also
        --------
        impacts
        """
        pass

    def summary_details(self, source='news', impact_date=None, impacted_variable=None, update_date=None, updated_variable=None, groupby='update date', sparsify=True, float_format='%.2f', multiple_tables=False):
        """
        Create summary table with detailed impacts; by date, variable

        Parameters
        ----------
        source : {news, revisions}
            The source of impacts to summarize. Default is "news".
        impact_date : int, str, datetime, list, array, or slice, optional
            Observation index label or slice of labels specifying particular
            impact periods to display. The impact date(s) describe the periods
            in which impacted variables were *affected* by the news. If this
            argument is given, the output table will only show this impact date
            or dates. Note that this argument is passed to the Pandas `loc`
            accessor, and so it should correspond to the labels of the model's
            index. If the model was created with data in a list or numpy array,
            then these labels will be zero-indexes observation integers.
        impacted_variable : str, list, array, or slice, optional
            Observation variable label or slice of labels specifying particular
            impacted variables to display. The impacted variable(s) describe
            the variables that were *affected* by the news. If you do not know
            the labels for the variables, check the `endog_names` attribute of
            the model instance.
        update_date : int, str, datetime, list, array, or slice, optional
            Observation index label or slice of labels specifying particular
            updated periods to display. The updated date(s) describe the
            periods in which the new data points were available that generated
            the news). See the note on `impact_date` for details about what
            these labels are.
        updated_variable : str, list, array, or slice, optional
            Observation variable label or slice of labels specifying particular
            updated variables to display. The updated variable(s) describe the
            variables that were *affected* by the news. If you do not know the
            labels for the variables, check the `endog_names` attribute of the
            model instance.
        groupby : {update date, updated date, impact date, impacted date}
            The primary variable for grouping results in the details table. The
            default is to group by update date.
        sparsify : bool, optional, default True
            Set to False for the table to include every one of the multiindex
            keys at each row.
        float_format : str, optional
            Formatter format string syntax for converting numbers to strings.
            Default is '%.2f'.
        multiple_tables : bool, optional
            If set to True, this function will return a list of tables, one
            table for each of the unique `groupby` levels. Default is False,
            in which case this function returns a single table.

        Returns
        -------
        details_table : SimpleTable or list of SimpleTable
            Table or list of tables describing how the news from each update
            (i.e. news from a particular variable / date) translates into
            changes to the forecasts of each impacted variable variable / date.

            This table contains information about the updates and about the
            impacts. Updates are newly observed datapoints that were not
            available in the previous results set. Each update leads to news,
            and the news may cause changes in the forecasts of the impacted
            variables. The amount that a particular piece of news (from an
            update to some variable at some date) impacts a variable at some
            date depends on weights that can be computed from the model
            results.

            The data contained in this table that refer to updates are:

            - `update date` : The date at which a new datapoint was added.
            - `updated variable` : The variable for which a new datapoint was
              added.
            - `forecast (prev)` : The value that had been forecast by the
              previous model for the given updated variable and date.
            - `observed` : The observed value of the new datapoint.
            - `news` : The news is the difference between the observed value
              and the previously forecast value for a given updated variable
              and date.

            The data contained in this table that refer to impacts are:

            - `impact date` : A date associated with an impact.
            - `impacted variable` : A variable that was impacted by the news.
            - `weight` : The weight of news from a given `update date` and
              `update variable` on a given `impacted variable` at a given
              `impact date`.
            - `impact` : The revision to the smoothed estimate / forecast of
              the impacted variable at the impact date based specifically on
              the news generated by the `updated variable` at the
              `update date`.

        See Also
        --------
        details_by_impact
        details_by_update
        """
        pass

    def summary_revisions(self, sparsify=True):
        """
        Create summary table showing revisions to the previous results' data

        Parameters
        ----------
        sparsify : bool, optional, default True
            Set to False for the table to include every one of the multiindex
            keys at each row.

        Returns
        -------
        revisions_table : SimpleTable
            Table showing revisions to the previous results' data. Columns are:

            - `revision date` : date associated with a revised data point
            - `revised variable` : variable that was revised at `revision date`
            - `observed (prev)` : the observed value prior to the revision
            - `revised` : the new value after the revision
            - `revision` : the new value after the revision
            - `detailed impacts computed` : whether detailed impacts were
              computed for this revision
        """
        pass

    def summary_news(self, sparsify=True):
        """
        Create summary table showing news from new data since previous results

        Parameters
        ----------
        sparsify : bool, optional, default True
            Set to False for the table to include every one of the multiindex
            keys at each row.

        Returns
        -------
        updates_table : SimpleTable
            Table showing new datapoints that were not in the previous results'
            data. Columns are:

            - `update date` : date associated with a new data point.
            - `updated variable` : variable for which new data was added at
              `update date`.
            - `forecast (prev)` : the forecast value for the updated variable
              at the update date in the previous results object (i.e. prior to
              the data being available).
            - `observed` : the observed value of the new datapoint.

        See Also
        --------
        data_updates
        """
        pass

    def summary(self, impact_date=None, impacted_variable=None, update_date=None, updated_variable=None, revision_date=None, revised_variable=None, impacts_groupby='impact date', details_groupby='update date', show_revisions_columns=None, sparsify=True, include_details_tables=None, include_revisions_tables=False, float_format='%.2f'):
        """
        Create summary tables describing news and impacts

        Parameters
        ----------
        impact_date : int, str, datetime, list, array, or slice, optional
            Observation index label or slice of labels specifying particular
            impact periods to display. The impact date(s) describe the periods
            in which impacted variables were *affected* by the news. If this
            argument is given, the impact and details tables will only show
            this impact date or dates. Note that this argument is passed to the
            Pandas `loc` accessor, and so it should correspond to the labels of
            the model's index. If the model was created with data in a list or
            numpy array, then these labels will be zero-indexes observation
            integers.
        impacted_variable : str, list, array, or slice, optional
            Observation variable label or slice of labels specifying particular
            impacted variables to display. The impacted variable(s) describe
            the variables that were *affected* by the news. If you do not know
            the labels for the variables, check the `endog_names` attribute of
            the model instance.
        update_date : int, str, datetime, list, array, or slice, optional
            Observation index label or slice of labels specifying particular
            updated periods to display. The updated date(s) describe the
            periods in which the new data points were available that generated
            the news). See the note on `impact_date` for details about what
            these labels are.
        updated_variable : str, list, array, or slice, optional
            Observation variable label or slice of labels specifying particular
            updated variables to display. The updated variable(s) describe the
            variables that newly added in the updated dataset and which
            generated the news. If you do not know the labels for the
            variables, check the `endog_names` attribute of the model instance.
        revision_date : int, str, datetime, list, array, or slice, optional
            Observation index label or slice of labels specifying particular
            revision periods to display. The revision date(s) describe the
            periods in which the data points were revised. See the note on
            `impact_date` for details about what these labels are.
        revised_variable : str, list, array, or slice, optional
            Observation variable label or slice of labels specifying particular
            revised variables to display. The updated variable(s) describe the
            variables that were *revised*. If you do not know the labels for
            the variables, check the `endog_names` attribute of the model
            instance.
        impacts_groupby : {impact date, impacted date}
            The primary variable for grouping results in the impacts table. The
            default is to group by update date.
        details_groupby : str
            One of "update date", "updated date", "impact date", or
            "impacted date". The primary variable for grouping results in the
            details table. Only used if the details tables are included. The
            default is to group by update date.
        show_revisions_columns : bool, optional
            If set to False, the impacts table will not show the impacts from
            data revisions or the total impacts. Default is to show the
            revisions and totals columns if any revisions were made and
            otherwise to hide them.
        sparsify : bool, optional, default True
            Set to False for the table to include every one of the multiindex
            keys at each row.
        include_details_tables : bool, optional
            If set to True, the summary will show tables describing the details
            of how news from specific updates translate into specific impacts.
            These tables can be very long, particularly in cases where there
            were many updates and in multivariate models. The default is to
            show detailed tables only for univariate models.
        include_revisions_tables : bool, optional
            If set to True, the summary will show tables describing the
            revisions and updates that lead to impacts on variables of
            interest.
        float_format : str, optional
            Formatter format string syntax for converting numbers to strings.
            Default is '%.2f'.

        Returns
        -------
        summary_tables : Summary
            Summary tables describing news and impacts. Basic tables include:

            - A table with general information about the sample.
            - A table describing the impacts of revisions and news.
            - Tables describing revisions in the dataset since the previous
              results set (unless `include_revisions_tables=False`).

            In univariate models or if `include_details_tables=True`, one or
            more tables will additionally be included describing the details
            of how news from specific updates translate into specific impacts.

        See Also
        --------
        summary_impacts
        summary_details
        summary_revisions
        summary_updates
        """
        pass