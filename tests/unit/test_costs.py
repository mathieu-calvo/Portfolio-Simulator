"""Tests for cost analytics."""

import numpy as np
import pandas as pd
import pytest

from portfolio_simulator.analytics.costs import (
    apply_ter_to_returns,
    cumulative_fee_impact,
    management_fee_daily,
    tax_on_gains,
    ter_drag_daily,
    transaction_cost_impact,
)


class TestTER:
    def test_ter_drag_positive(self):
        drag = ter_drag_daily(0.002)  # 0.2% annual TER
        assert drag > 0
        assert drag < 0.001  # Should be very small daily

    def test_apply_ter_reduces_returns(self):
        returns = pd.Series([0.01, 0.02, -0.01, 0.005])
        adjusted = apply_ter_to_returns(returns, 0.002)
        assert (adjusted < returns).all()


class TestTransactionCosts:
    def test_basic_calculation(self):
        cost = transaction_cost_impact(100_000, 0.10, 0.001)
        assert cost == pytest.approx(10.0)  # 100k * 10% turnover * 0.1% cost

    def test_zero_turnover(self):
        cost = transaction_cost_impact(100_000, 0.0, 0.001)
        assert cost == 0.0


class TestManagementFee:
    def test_daily_fee(self):
        daily = management_fee_daily(0.01)  # 1% annual
        assert daily == pytest.approx(0.01 / 252)


class TestTax:
    def test_tax_on_positive_gain(self):
        tax = tax_on_gains(1000.0, 0.15)
        assert tax == 150.0

    def test_no_tax_on_loss(self):
        tax = tax_on_gains(-500.0, 0.15)
        assert tax == 0.0


class TestCumulativeFeeImpact:
    def test_fees_reduce_value(self):
        values = pd.Series(np.linspace(10000, 12000, 252))
        adjusted = cumulative_fee_impact(values, 0.01)
        assert adjusted.iloc[-1] < values.iloc[-1]
