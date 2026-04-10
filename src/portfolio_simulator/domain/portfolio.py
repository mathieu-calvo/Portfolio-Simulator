"""Portfolio domain model."""

from __future__ import annotations

import numpy as np
from pydantic import BaseModel, Field, model_validator

from portfolio_simulator.domain.asset import Asset
from portfolio_simulator.domain.enums import Currency


class PortfolioAllocation(BaseModel):
    """A single asset and its target weight within a portfolio."""

    asset: Asset
    weight: float = Field(ge=0.0, le=1.0)

    model_config = {"frozen": True}


class Portfolio(BaseModel):
    """A named collection of assets with target weights."""

    name: str
    allocations: list[PortfolioAllocation]
    base_currency: Currency = Currency.USD

    @model_validator(mode="after")
    def _validate_weights_sum(self) -> Portfolio:
        total = sum(a.weight for a in self.allocations)
        if not np.isclose(total, 1.0, atol=1e-6):
            raise ValueError(f"Portfolio weights must sum to 1.0, got {total:.6f}")
        return self

    @property
    def tickers(self) -> list[str]:
        return [a.asset.ticker for a in self.allocations]

    @property
    def weights(self) -> np.ndarray:
        return np.array([a.weight for a in self.allocations])

    @property
    def assets(self) -> list[Asset]:
        return [a.asset for a in self.allocations]

    def weight_for(self, ticker: str) -> float:
        """Get the target weight for a specific ticker."""
        for a in self.allocations:
            if a.asset.ticker == ticker:
                return a.weight
        raise KeyError(f"Ticker {ticker} not in portfolio")

    def to_dict(self) -> dict:
        """Serialize to a plain dict for JSON storage."""
        return {
            "name": self.name,
            "base_currency": self.base_currency.value,
            "allocations": [
                {
                    "ticker": a.asset.ticker,
                    "name": a.asset.name,
                    "asset_type": a.asset.asset_type.value,
                    "currency": a.asset.currency.value,
                    "ter": a.asset.ter,
                    "weight": a.weight,
                }
                for a in self.allocations
            ],
        }

    @classmethod
    def from_dict(cls, data: dict) -> Portfolio:
        """Deserialize from a plain dict."""
        allocations = [
            PortfolioAllocation(
                asset=Asset(
                    ticker=a["ticker"],
                    name=a["name"],
                    asset_type=a.get("asset_type", "etf"),
                    currency=a.get("currency", "USD"),
                    ter=a.get("ter", 0.0),
                ),
                weight=a["weight"],
            )
            for a in data["allocations"]
        ]
        return cls(
            name=data["name"],
            allocations=allocations,
            base_currency=data.get("base_currency", "USD"),
        )
