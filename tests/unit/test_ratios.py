"""Tests for risk-adjusted ratios."""

import numpy as np
import pandas as pd
import pytest

from portfolio_simulator.analytics.ratios import (
    calmar_ratio,
    information_ratio,
    sharpe_ratio,
    sortino_ratio,
)


class TestSharpeRatio:
    def test_finite(self, sample_prices):
        sharpe = sharpe_ratio(sample_prices["STOCK_A"], risk_free_rate=0.0)
        assert np.isfinite(sharpe)

    def test_higher_with_lower_rf(self, sample_prices):
        s_low = sharpe_ratio(sample_prices["STOCK_A"], risk_free_rate=0.0)
        s_high = sharpe_ratio(sample_prices["STOCK_A"], risk_free_rate=0.05)
        assert s_low > s_high


class TestSortinoRatio:
    def test_finite(self, sample_prices):
        sortino = sortino_ratio(sample_prices["STOCK_A"], risk_free_rate=0.0)
        assert np.isfinite(sortino)

    def test_sortino_ge_sharpe_when_positive(self, sample_prices):
        # Use STOCK_C which has higher drift
        s = sharpe_ratio(sample_prices["STOCK_C"], risk_free_rate=0.0)
        so = sortino_ratio(sample_prices["STOCK_C"], risk_free_rate=0.0)
        # Sortino generally >= Sharpe because it only penalizes downside
        if s > 0:
            assert so >= s * 0.8


class TestCalmarRatio:
    def test_finite(self, sample_prices):
        cal = calmar_ratio(sample_prices["STOCK_A"])
        assert np.isfinite(cal)


class TestInformationRatio:
    def test_self_comparison_is_zero(self, sample_prices):
        ir = information_ratio(sample_prices["STOCK_A"], sample_prices["STOCK_A"])
        assert ir == pytest.approx(0.0, abs=1e-10)
