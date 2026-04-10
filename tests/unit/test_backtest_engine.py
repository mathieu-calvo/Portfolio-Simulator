"""Tests for the backtest engine."""

from datetime import date

import numpy as np
import pytest

from portfolio_simulator.domain.enums import (
    InvestmentStrategy,
    RebalanceFrequency,
    RebalanceStrategy,
)
from portfolio_simulator.domain.simulation import SimulationConfig
from portfolio_simulator.services.backtest_engine import BacktestEngine
from portfolio_simulator.services.data_service import DataService


class TestBacktestEngine:
    @pytest.fixture
    def engine(self, csv_provider):
        ds = DataService.__new__(DataService)
        ds._provider = csv_provider
        # Bypass cache for testing
        from portfolio_simulator.cache.memory_cache import MemoryCache
        ds._memory = MemoryCache()
        ds._config = type("C", (), {
            "cache_ttl_hours": 24,
            "max_concurrent_fetches": 2,
            "db_path": ":memory:",
        })()
        # Override get_prices_bulk to skip SQLite
        original_get = csv_provider.get_price_history
        import pandas as pd
        def get_bulk(tickers, start, end):
            results = {}
            for t in tickers:
                results[t] = original_get(t, start, end)
            return pd.DataFrame(results).sort_index()
        ds.get_prices_bulk = get_bulk
        return BacktestEngine(ds)

    def test_basic_run(self, engine, sample_portfolio, sample_config):
        result = engine.run(sample_portfolio, sample_config)
        assert result.portfolio_name == "Test 60/40"
        assert len(result.portfolio_value) > 0
        assert result.total_invested == 10_000.0
        # Final value should be reasonable
        assert result.portfolio_value.iloc[-1] > 0

    def test_portfolio_value_starts_near_initial(self, engine, sample_portfolio, sample_config):
        result = engine.run(sample_portfolio, sample_config)
        # First day: initial_investment * (1 + first_day_return)
        assert abs(result.portfolio_value.iloc[0] - 10_000) < 500

    def test_with_rebalancing(self, engine, sample_portfolio):
        config = SimulationConfig(
            start_date=date(2020, 1, 2),
            end_date=date(2022, 12, 30),
            initial_investment=10_000.0,
            rebalance_strategy=RebalanceStrategy.CALENDAR,
            rebalance_frequency=RebalanceFrequency.QUARTERLY,
        )
        result = engine.run(sample_portfolio, config)
        assert len(result.rebalance_dates) > 0
        assert result.portfolio_value.iloc[-1] > 0

    def test_with_dca(self, engine, sample_portfolio):
        config = SimulationConfig(
            start_date=date(2020, 1, 2),
            end_date=date(2022, 12, 30),
            initial_investment=10_000.0,
            recurring_investment=500.0,
            investment_strategy=InvestmentStrategy.DCA,
        )
        result = engine.run(sample_portfolio, config)
        # Total invested should be more than initial
        assert result.total_invested > 10_000.0

    def test_comparison(self, engine, sample_portfolio, sample_config, asset_a, asset_c):
        from portfolio_simulator.domain.portfolio import Portfolio, PortfolioAllocation
        p2 = Portfolio(
            name="All Stock C",
            allocations=[PortfolioAllocation(asset=asset_c, weight=1.0)],
        )
        results = engine.run_comparison([sample_portfolio, p2], sample_config)
        assert len(results) == 2
        assert results[0].portfolio_name == "Test 60/40"
        assert results[1].portfolio_name == "All Stock C"
