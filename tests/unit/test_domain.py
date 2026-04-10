"""Tests for domain models."""

import pytest
from pydantic import ValidationError

from portfolio_simulator.domain.asset import Asset
from portfolio_simulator.domain.enums import AssetType, Currency
from portfolio_simulator.domain.portfolio import Portfolio, PortfolioAllocation
from portfolio_simulator.domain.simulation import SimulationConfig
from datetime import date


class TestAsset:
    def test_create_asset(self):
        asset = Asset(ticker="SPY", name="S&P 500 ETF", asset_type=AssetType.ETF)
        assert asset.ticker == "SPY"
        assert asset.ter == 0.0

    def test_asset_is_frozen(self):
        asset = Asset(ticker="SPY", name="S&P 500 ETF")
        with pytest.raises(ValidationError):
            asset.ticker = "VTI"

    def test_asset_equality_by_ticker(self):
        a1 = Asset(ticker="SPY", name="A")
        a2 = Asset(ticker="SPY", name="B")
        assert a1 == a2

    def test_asset_hashable(self):
        a = Asset(ticker="SPY", name="Test")
        assert hash(a) == hash("SPY")
        s = {a}  # can be used in sets
        assert len(s) == 1


class TestPortfolio:
    def test_valid_portfolio(self, asset_a, asset_b):
        p = Portfolio(
            name="Test",
            allocations=[
                PortfolioAllocation(asset=asset_a, weight=0.6),
                PortfolioAllocation(asset=asset_b, weight=0.4),
            ],
        )
        assert len(p.allocations) == 2
        assert p.weights.sum() == pytest.approx(1.0)

    def test_weights_must_sum_to_one(self, asset_a, asset_b):
        with pytest.raises(ValueError, match="must sum to 1.0"):
            Portfolio(
                name="Bad",
                allocations=[
                    PortfolioAllocation(asset=asset_a, weight=0.5),
                    PortfolioAllocation(asset=asset_b, weight=0.3),
                ],
            )

    def test_tickers_property(self, sample_portfolio):
        assert sample_portfolio.tickers == ["STOCK_A", "BOND_B"]

    def test_weight_for(self, sample_portfolio):
        assert sample_portfolio.weight_for("STOCK_A") == 0.6
        with pytest.raises(KeyError):
            sample_portfolio.weight_for("NONEXISTENT")

    def test_serialization_roundtrip(self, sample_portfolio):
        data = sample_portfolio.to_dict()
        restored = Portfolio.from_dict(data)
        assert restored.name == sample_portfolio.name
        assert len(restored.allocations) == len(sample_portfolio.allocations)
        assert restored.weights.sum() == pytest.approx(1.0)


class TestSimulationConfig:
    def test_defaults(self):
        config = SimulationConfig(start_date=date(2020, 1, 1), end_date=date(2023, 1, 1))
        assert config.initial_investment == 10_000.0
        assert config.include_ter is True

    def test_negative_investment_rejected(self):
        with pytest.raises(ValidationError):
            SimulationConfig(
                start_date=date(2020, 1, 1),
                end_date=date(2023, 1, 1),
                initial_investment=-1000,
            )
