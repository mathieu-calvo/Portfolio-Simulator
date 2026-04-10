"""CSV-based data provider for testing and offline use."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from portfolio_simulator.domain.enums import AssetType
from portfolio_simulator.providers.base import AssetInfo


class CSVProvider:
    """Data provider backed by local CSV files.

    Expects a CSV with a 'date' column and one column per ticker (prices).
    Optionally accepts a separate FX rates CSV with the same format.
    """

    def __init__(
        self,
        prices_path: str | Path | None = None,
        fx_rates_path: str | Path | None = None,
        prices_df: pd.DataFrame | None = None,
        fx_rates_df: pd.DataFrame | None = None,
    ):
        if prices_df is not None:
            self._prices = prices_df
        elif prices_path is not None:
            self._prices = self._load_csv(prices_path)
        else:
            self._prices = pd.DataFrame()

        if fx_rates_df is not None:
            self._fx_rates = fx_rates_df
        elif fx_rates_path is not None:
            self._fx_rates = self._load_csv(fx_rates_path)
        else:
            self._fx_rates = pd.DataFrame()

    @staticmethod
    def _load_csv(path: str | Path) -> pd.DataFrame:
        df = pd.read_csv(path, parse_dates=["date"], index_col="date")
        df.index = pd.DatetimeIndex(df.index)
        return df

    @property
    def name(self) -> str:
        return "csv"

    def get_price_history(
        self,
        ticker: str,
        start: date,
        end: date,
    ) -> pd.Series:
        if ticker not in self._prices.columns:
            raise ValueError(f"Ticker {ticker} not found in CSV data")
        series = self._prices[ticker].loc[str(start) : str(end)].dropna()
        series.name = ticker
        return series

    def search_assets(
        self,
        query: str,
        asset_type: AssetType | None = None,
        limit: int = 20,
    ) -> list[AssetInfo]:
        matches = [col for col in self._prices.columns if query.upper() in col.upper()]
        return [
            AssetInfo(ticker=t, name=t, asset_type=asset_type or AssetType.ETF, currency="USD")
            for t in matches[:limit]
        ]

    def get_asset_info(self, ticker: str) -> AssetInfo:
        if ticker not in self._prices.columns:
            raise ValueError(f"Ticker {ticker} not found in CSV data")
        return AssetInfo(ticker=ticker, name=ticker, asset_type=AssetType.ETF, currency="USD")

    def get_fx_rates(
        self,
        base: str,
        quote: str,
        start: date,
        end: date,
    ) -> pd.Series:
        if base == quote:
            idx = pd.bdate_range(start=start, end=end)
            return pd.Series(1.0, index=idx, name=f"{base}{quote}")

        pair = f"{base}{quote}"
        if pair not in self._fx_rates.columns:
            raise ValueError(f"FX pair {pair} not found in CSV data")
        series = self._fx_rates[pair].loc[str(start) : str(end)].dropna()
        series.name = pair
        return series
