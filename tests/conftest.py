"""Shared test fixtures."""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import pytest

from portfolio_simulator.domain.asset import Asset
from portfolio_simulator.domain.enums import AssetType, Currency
from portfolio_simulator.domain.portfolio import Portfolio, PortfolioAllocation
from portfolio_simulator.domain.simulation import SimulationConfig
from portfolio_simulator.providers.csv_provider import CSVProvider


@pytest.fixture
def sample_prices() -> pd.DataFrame:
    """Deterministic 3-year daily price data for 3 assets.

    Generates synthetic prices using cumulative random returns with a fixed seed.
    """
    rng = np.random.default_rng(42)
    dates = pd.bdate_range(start="2020-01-02", end="2022-12-30")
    n = len(dates)

    # Simulate log-normal prices
    returns_a = rng.normal(0.0003, 0.01, n)  # ~7.5% annual return, ~16% vol
    returns_b = rng.normal(0.0001, 0.005, n)  # ~2.5% annual return, ~8% vol (bond-like)
    returns_c = rng.normal(0.0004, 0.015, n)  # ~10% annual return, ~24% vol

    prices = pd.DataFrame(
        {
            "STOCK_A": 100 * np.exp(np.cumsum(returns_a)),
            "BOND_B": 100 * np.exp(np.cumsum(returns_b)),
            "STOCK_C": 100 * np.exp(np.cumsum(returns_c)),
        },
        index=dates,
    )
    return prices


@pytest.fixture
def sample_fx_rates() -> pd.DataFrame:
    """Synthetic FX rates (EURUSD) for testing."""
    dates = pd.bdate_range(start="2020-01-02", end="2022-12-30")
    rng = np.random.default_rng(99)
    rates = 1.10 + np.cumsum(rng.normal(0, 0.002, len(dates)))
    return pd.DataFrame({"EURUSD": rates}, index=dates)


@pytest.fixture
def csv_provider(sample_prices: pd.DataFrame, sample_fx_rates: pd.DataFrame) -> CSVProvider:
    """Provider backed by fixture data."""
    return CSVProvider(prices_df=sample_prices, fx_rates_df=sample_fx_rates)


@pytest.fixture
def asset_a() -> Asset:
    return Asset(ticker="STOCK_A", name="Stock A", asset_type=AssetType.STOCK, currency=Currency.USD)


@pytest.fixture
def asset_b() -> Asset:
    return Asset(ticker="BOND_B", name="Bond B", asset_type=AssetType.BOND, currency=Currency.USD)


@pytest.fixture
def asset_c() -> Asset:
    return Asset(ticker="STOCK_C", name="Stock C", asset_type=AssetType.STOCK, currency=Currency.USD)


@pytest.fixture
def sample_portfolio(asset_a: Asset, asset_b: Asset) -> Portfolio:
    """60/40 stock/bond portfolio."""
    return Portfolio(
        name="Test 60/40",
        allocations=[
            PortfolioAllocation(asset=asset_a, weight=0.6),
            PortfolioAllocation(asset=asset_b, weight=0.4),
        ],
        base_currency=Currency.USD,
    )


@pytest.fixture
def sample_config() -> SimulationConfig:
    return SimulationConfig(
        start_date=date(2020, 1, 2),
        end_date=date(2022, 12, 30),
        initial_investment=10_000.0,
    )
