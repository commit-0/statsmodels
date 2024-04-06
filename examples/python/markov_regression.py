#!/usr/bin/env python

# DO NOT EDIT
# Autogenerated from the notebook markov_regression.ipynb.
# Edit the notebook and then sync the output with this file.
#
# flake8: noqa
# DO NOT EDIT

# ## Markov switching dynamic regression models

# This notebook provides an example of the use of Markov switching models
# in statsmodels to estimate dynamic regression models with changes in
# regime. It follows the examples in the Stata Markov switching
# documentation, which can be found at
# http://www.stata.com/manuals14/tsmswitch.pdf.

import numpy as np
import pandas as pd
import statsmodels.api as sm
import matplotlib.pyplot as plt

# NBER recessions
from pandas_datareader.data import DataReader
from datetime import datetime

usrec = DataReader("USREC",
                   "fred",
                   start=datetime(1947, 1, 1),
                   end=datetime(2013, 4, 1))

# ### Federal funds rate with switching intercept
#
# The first example models the federal funds rate as noise around a
# constant intercept, but where the intercept changes during different
# regimes. The model is simply:
#
# $$r_t = \mu_{S_t} + \varepsilon_t \qquad \varepsilon_t \sim N(0,
# \sigma^2)$$
#
# where $S_t \in \{0, 1\}$, and the regime transitions according to
#
# $$ P(S_t = s_t | S_{t-1} = s_{t-1}) =
# \begin{bmatrix}
# p_{00} & p_{10} \\
# 1 - p_{00} & 1 - p_{10}
# \end{bmatrix}
# $$
#
# We will estimate the parameters of this model by maximum likelihood:
# $p_{00}, p_{10}, \mu_0, \mu_1, \sigma^2$.
#
# The data used in this example can be found at https://www.stata-
# press.com/data/r14/usmacro.

# Get the federal funds rate data
from statsmodels.tsa.regime_switching.tests.test_markov_regression import fedfunds

dta_fedfunds = pd.Series(fedfunds,
                         index=pd.date_range("1954-07-01",
                                             "2010-10-01",
                                             freq="QS"))

# Plot the data
dta_fedfunds.plot(title="Federal funds rate", figsize=(12, 3))

# Fit the model
# (a switching mean is the default of the MarkovRegession model)
mod_fedfunds = sm.tsa.MarkovRegression(dta_fedfunds, k_regimes=2)
res_fedfunds = mod_fedfunds.fit()

res_fedfunds.summary()

# From the summary output, the mean federal funds rate in the first regime
# (the "low regime") is estimated to be $3.7$ whereas in the "high regime"
# it is $9.6$. Below we plot the smoothed probabilities of being in the high
# regime. The model suggests that the 1980's was a time-period in which a
# high federal funds rate existed.

res_fedfunds.smoothed_marginal_probabilities[1].plot(
    title="Probability of being in the high regime", figsize=(12, 3))

# From the estimated transition matrix we can calculate the expected
# duration of a low regime versus a high regime.

print(res_fedfunds.expected_durations)

# A low regime is expected to persist for about fourteen years, whereas
# the high regime is expected to persist for only about five years.

# ### Federal funds rate with switching intercept and lagged dependent
# variable
#
# The second example augments the previous model to include the lagged
# value of the federal funds rate.
#
# $$r_t = \mu_{S_t} + r_{t-1} \beta_{S_t} + \varepsilon_t \qquad
# \varepsilon_t \sim N(0, \sigma^2)$$
#
# where $S_t \in \{0, 1\}$, and the regime transitions according to
#
# $$ P(S_t = s_t | S_{t-1} = s_{t-1}) =
# \begin{bmatrix}
# p_{00} & p_{10} \\
# 1 - p_{00} & 1 - p_{10}
# \end{bmatrix}
# $$
#
# We will estimate the parameters of this model by maximum likelihood:
# $p_{00}, p_{10}, \mu_0, \mu_1, \beta_0, \beta_1, \sigma^2$.

# Fit the model
mod_fedfunds2 = sm.tsa.MarkovRegression(dta_fedfunds.iloc[1:],
                                        k_regimes=2,
                                        exog=dta_fedfunds.iloc[:-1])
res_fedfunds2 = mod_fedfunds2.fit()

res_fedfunds2.summary()

# There are several things to notice from the summary output:
#
# 1. The information criteria have decreased substantially, indicating
# that this model has a better fit than the previous model.
# 2. The interpretation of the regimes, in terms of the intercept, have
# switched. Now the first regime has the higher intercept and the second
# regime has a lower intercept.
#
# Examining the smoothed probabilities of the high regime state, we now
# see quite a bit more variability.

res_fedfunds2.smoothed_marginal_probabilities[0].plot(
    title="Probability of being in the high regime", figsize=(12, 3))

# Finally, the expected durations of each regime have decreased quite a
# bit.

print(res_fedfunds2.expected_durations)

# ### Taylor rule with 2 or 3 regimes
#
# We now include two additional exogenous variables - a measure of the
# output gap and a measure of inflation - to estimate a switching Taylor-
# type rule with both 2 and 3 regimes to see which fits the data better.
#
# Because the models can be often difficult to estimate, for the 3-regime
# model we employ a search over starting parameters to improve results,
# specifying 20 random search repetitions.

# Get the additional data
from statsmodels.tsa.regime_switching.tests.test_markov_regression import ogap, inf

dta_ogap = pd.Series(ogap,
                     index=pd.date_range("1954-07-01", "2010-10-01",
                                         freq="QS"))
dta_inf = pd.Series(inf,
                    index=pd.date_range("1954-07-01", "2010-10-01", freq="QS"))

exog = pd.concat((dta_fedfunds.shift(), dta_ogap, dta_inf), axis=1).iloc[4:]

# Fit the 2-regime model
mod_fedfunds3 = sm.tsa.MarkovRegression(dta_fedfunds.iloc[4:],
                                        k_regimes=2,
                                        exog=exog)
res_fedfunds3 = mod_fedfunds3.fit()

# Fit the 3-regime model
np.random.seed(12345)
mod_fedfunds4 = sm.tsa.MarkovRegression(dta_fedfunds.iloc[4:],
                                        k_regimes=3,
                                        exog=exog)
res_fedfunds4 = mod_fedfunds4.fit(search_reps=20)

res_fedfunds3.summary()

res_fedfunds4.summary()

# Due to lower information criteria, we might prefer the 3-state model,
# with an interpretation of low-, medium-, and high-interest rate regimes.
# The smoothed probabilities of each regime are plotted below.

fig, axes = plt.subplots(3, figsize=(10, 7))

ax = axes[0]
ax.plot(res_fedfunds4.smoothed_marginal_probabilities[0])
ax.set(title="Smoothed probability of a low-interest rate regime")

ax = axes[1]
ax.plot(res_fedfunds4.smoothed_marginal_probabilities[1])
ax.set(title="Smoothed probability of a medium-interest rate regime")

ax = axes[2]
ax.plot(res_fedfunds4.smoothed_marginal_probabilities[2])
ax.set(title="Smoothed probability of a high-interest rate regime")

fig.tight_layout()

# ### Switching variances
#
# We can also accommodate switching variances. In particular, we consider
# the model
#
# $$
# y_t = \mu_{S_t} + y_{t-1} \beta_{S_t} + \varepsilon_t \quad
# \varepsilon_t \sim N(0, \sigma_{S_t}^2)
# $$
#
# We use maximum likelihood to estimate the parameters of this model:
# $p_{00}, p_{10}, \mu_0, \mu_1, \beta_0, \beta_1, \sigma_0^2, \sigma_1^2$.
#
# The application is to absolute returns on stocks, where the data can be
# found at https://www.stata-press.com/data/r14/snp500.

# Get the federal funds rate data
from statsmodels.tsa.regime_switching.tests.test_markov_regression import areturns

dta_areturns = pd.Series(areturns,
                         index=pd.date_range("2004-05-04",
                                             "2014-5-03",
                                             freq="W"))

# Plot the data
dta_areturns.plot(title="Absolute returns, S&P500", figsize=(12, 3))

# Fit the model
mod_areturns = sm.tsa.MarkovRegression(
    dta_areturns.iloc[1:],
    k_regimes=2,
    exog=dta_areturns.iloc[:-1],
    switching_variance=True,
)
res_areturns = mod_areturns.fit()

res_areturns.summary()

# The first regime is a low-variance regime and the second regime is a
# high-variance regime. Below we plot the probabilities of being in the low-
# variance regime. Between 2008 and 2012 there does not appear to be a clear
# indication of one regime guiding the economy.

res_areturns.smoothed_marginal_probabilities[0].plot(
    title="Probability of being in a low-variance regime", figsize=(12, 3))
