"""Tests for risk metrics."""

import numpy as np
import pandas as pd
import pytest

from portfolio_simulator.analytics.risk import (
    annualized_volatility,
    conditional_value_at_risk,
    drawdown_series,
    max_drawdown,
    rolling_volatility,
    value_at_risk,
)


class TestVolatility:
    def test_positive(self, sample_prices):
        vol = annualized_volatility(sample_prices["STOCK_A"])
        assert vol > 0

    def test_bond_less_volatile_than_stock(self, sample_prices):
        stock_vol = annualized_volatility(sample_prices["STOCK_A"])
        bond_vol = annualized_volatility(sample_prices["BOND_B"])
        assert bond_vol < stock_vol

    def test_constant_prices_zero_vol(self):
        prices = pd.Series([100.0] * 100, index=pd.bdate_range("2020-01-02", periods=100))
        assert annualized_volatility(prices) == 0.0


class TestDrawdown:
    def test_drawdown_non_positive(self, sample_prices):
        dd = drawdown_series(sample_prices["STOCK_A"])
        assert (dd <= 0).all()

    def test_starts_at_zero(self, sample_prices):
        dd = drawdown_series(sample_prices["STOCK_A"])
        assert dd.iloc[0] == 0.0

    def test_max_drawdown_negative(self, sample_prices):
        dd_info = max_drawdown(sample_prices["STOCK_A"])
        assert dd_info.max_drawdown < 0
        assert dd_info.peak_date < dd_info.trough_date


class TestRollingVolatility:
    def test_output_length(self, sample_prices):
        vol = rolling_volatility(sample_prices["STOCK_A"], window_days=63)
        # Should have NaN for first 62 entries, then values
        assert len(vol) == len(sample_prices) - 1  # pct_change drops 1
        assert vol.dropna().shape[0] > 0


class TestVaR:
    def test_var_is_negative(self, sample_prices):
        var = value_at_risk(sample_prices["STOCK_A"])
        assert var < 0

    def test_cvar_worse_than_var(self, sample_prices):
        var = value_at_risk(sample_prices["STOCK_A"])
        cvar = conditional_value_at_risk(sample_prices["STOCK_A"])
        assert cvar <= var  # CVaR is the average of the tail, always worse
