"""Tests for return calculations."""

import numpy as np
import pandas as pd
import pytest

from portfolio_simulator.analytics.returns import (
    annualized_return,
    calendar_year_returns,
    cumulative_return,
    daily_returns,
    monthly_returns,
    multi_horizon_returns,
    quarterly_returns,
    rolling_returns,
)


@pytest.fixture
def simple_prices():
    """Simple price series: starts at 100, ends at 200 over ~2 years."""
    dates = pd.bdate_range("2020-01-02", "2021-12-31")
    # Linear growth from 100 to 200
    prices = pd.Series(
        np.linspace(100, 200, len(dates)),
        index=dates,
        name="TEST",
    )
    return prices


class TestCumulativeReturn:
    def test_basic(self, simple_prices):
        ret = cumulative_return(simple_prices)
        assert ret == pytest.approx(1.0, rel=1e-3)  # 100 -> 200 = 100%

    def test_flat_prices(self):
        prices = pd.Series([100, 100, 100], index=pd.bdate_range("2020-01-02", periods=3))
        assert cumulative_return(prices) == 0.0


class TestAnnualizedReturn:
    def test_basic(self, sample_prices):
        prices = sample_prices["STOCK_A"]
        ann = annualized_return(prices)
        # Should be a finite, reasonable number
        assert -1 < ann < 2


class TestDailyReturns:
    def test_length(self, sample_prices):
        prices = sample_prices["STOCK_A"]
        ret = daily_returns(prices)
        assert len(ret) == len(prices) - 1

    def test_name_preserved(self, sample_prices):
        prices = sample_prices["STOCK_A"]
        ret = daily_returns(prices)
        assert ret.name == "STOCK_A"


class TestCalendarYearReturns:
    def test_one_entry_per_year(self, sample_prices):
        prices = sample_prices["STOCK_A"]
        yr = calendar_year_returns(prices)
        # 2020, 2021, 2022
        assert len(yr) == 3
        assert 2020 in yr.index
        assert 2022 in yr.index


class TestQuarterlyReturns:
    def test_produces_period_index(self, sample_prices):
        prices = sample_prices["STOCK_A"]
        q = quarterly_returns(prices)
        assert isinstance(q.index, pd.PeriodIndex)
        assert len(q) >= 4  # At least 4 quarters in 3 years


class TestMonthlyReturns:
    def test_produces_period_index(self, sample_prices):
        prices = sample_prices["STOCK_A"]
        m = monthly_returns(prices)
        assert isinstance(m.index, pd.PeriodIndex)
        assert len(m) >= 12


class TestMultiHorizonReturns:
    def test_includes_full_period(self, sample_prices):
        prices = sample_prices["STOCK_A"]
        horizons = multi_horizon_returns(prices)
        assert "Full Period" in horizons
        assert "annualized" in horizons["Full Period"]
        assert "cumulative" in horizons["Full Period"]

    def test_short_series_skips_long_horizons(self):
        dates = pd.bdate_range("2022-01-03", "2022-06-30")
        prices = pd.Series(np.linspace(100, 110, len(dates)), index=dates)
        horizons = multi_horizon_returns(prices)
        # 6 months of data shouldn't produce 3Y, 5Y, or 10Y
        assert "3Y" not in horizons
        assert "5Y" not in horizons
        assert "10Y" not in horizons
