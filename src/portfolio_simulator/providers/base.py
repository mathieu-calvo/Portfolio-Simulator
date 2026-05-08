"""Data provider protocol and shared types."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Protocol, runtime_checkable

import pandas as pd

from portfolio_simulator.domain.enums import AssetType


@dataclass(frozen=True)
class AssetInfo:
    """Metadata returned by a data provider for a financial instrument."""

    ticker: str
    name: str
    asset_type: AssetType
    currency: str
    ter: float | None = None
    exchange: str | None = None
    isin: str | None = None
    first_trade_date: date | None = None


@runtime_checkable
class DataProvider(Protocol):
    """Protocol that all data sources must implement.

    Implement this for Yahoo Finance, Reuters, Bloomberg, CSV files, etc.
    """

    @property
    def name(self) -> str:
        """Provider identifier (e.g., 'yahoo', 'reuters')."""
        ...

    def get_price_history(
        self,
        ticker: str,
        start: date,
        end: date,
    ) -> pd.Series:
        """Return daily adjusted close prices.

        Args:
            ticker: Instrument ticker symbol.
            start: Start date (inclusive).
            end: End date (inclusive).

        Returns:
            pd.Series with DatetimeIndex and float values (prices).
        """
        ...

    def search_assets(
        self,
        query: str,
        asset_type: AssetType | None = None,
        limit: int = 20,
    ) -> list[AssetInfo]:
        """Search for assets by name or ticker.

        Args:
            query: Search string (name, ticker, ISIN).
            asset_type: Optionally filter by asset type.
            limit: Max number of results.

        Returns:
            List of matching AssetInfo objects.
        """
        ...

    def get_asset_info(self, ticker: str) -> AssetInfo:
        """Return metadata for a single asset.

        Args:
            ticker: Instrument ticker symbol.

        Returns:
            AssetInfo with name, type, currency, etc.
        """
        ...

    def get_fx_rates(
        self,
        base: str,
        quote: str,
        start: date,
        end: date,
    ) -> pd.Series:
        """Return daily FX rates (base/quote).

        Args:
            base: Base currency code (e.g., "EUR").
            quote: Quote currency code (e.g., "USD").
            start: Start date (inclusive).
            end: End date (inclusive).

        Returns:
            pd.Series with DatetimeIndex. Value = how many units of quote per 1 base.
        """
        ...
