"""Yahoo Finance data provider implementation."""

from __future__ import annotations

import logging
from datetime import date, timedelta

import pandas as pd
import yfinance as yf

from portfolio_simulator.domain.enums import AssetType
from portfolio_simulator.providers.base import AssetInfo

logger = logging.getLogger(__name__)

# Map yfinance quoteType to our AssetType
_QUOTE_TYPE_MAP = {
    "ETF": AssetType.ETF,
    "EQUITY": AssetType.STOCK,
    "MUTUALFUND": AssetType.MUTUAL_FUND,
    "INDEX": AssetType.INDEX,
    "FUTURE": AssetType.FUTURES,
    "CRYPTOCURRENCY": AssetType.CRYPTO,
}


class YahooFinanceProvider:
    """Data provider backed by Yahoo Finance (via yfinance)."""

    @property
    def name(self) -> str:
        return "yahoo"

    def get_price_history(
        self,
        ticker: str,
        start: date,
        end: date,
    ) -> pd.Series:
        # yfinance end date is exclusive, so add one day
        end_adj = end + timedelta(days=1)
        df = yf.download(
            ticker,
            start=start.isoformat(),
            end=end_adj.isoformat(),
            progress=False,
            auto_adjust=True,
        )
        if df.empty:
            raise ValueError(f"No data returned for {ticker} between {start} and {end}")

        series = df["Close"].squeeze()
        if isinstance(series, pd.DataFrame):
            series = series.iloc[:, 0]
        series.name = ticker
        series.index = pd.DatetimeIndex(series.index).tz_localize(None)
        return series

    def search_assets(
        self,
        query: str,
        asset_type: AssetType | None = None,
        limit: int = 20,
    ) -> list[AssetInfo]:
        try:
            results = yf.Search(query, max_results=limit)
            quotes = results.quotes if hasattr(results, "quotes") else []
        except Exception:
            logger.warning(f"Search failed for query: {query}", exc_info=True)
            return []

        assets = []
        for q in quotes:
            yf_type = q.get("quoteType", "EQUITY")
            at = _QUOTE_TYPE_MAP.get(yf_type, AssetType.STOCK)
            if asset_type is not None and at != asset_type:
                continue
            assets.append(
                AssetInfo(
                    ticker=q.get("symbol", ""),
                    name=q.get("longname") or q.get("shortname", ""),
                    asset_type=at,
                    currency=q.get("currency", "USD"),
                    exchange=q.get("exchange"),
                )
            )
        return assets[:limit]

    def get_asset_info(self, ticker: str) -> AssetInfo:
        info = yf.Ticker(ticker).info
        yf_type = info.get("quoteType", "EQUITY")
        return AssetInfo(
            ticker=ticker,
            name=info.get("longName") or info.get("shortName", ticker),
            asset_type=_QUOTE_TYPE_MAP.get(yf_type, AssetType.STOCK),
            currency=info.get("currency", "USD"),
            ter=info.get("annualReportExpenseRatio"),
            exchange=info.get("exchange"),
            isin=info.get("isin"),
        )

    def get_fx_rates(
        self,
        base: str,
        quote: str,
        start: date,
        end: date,
    ) -> pd.Series:
        if base == quote:
            idx = pd.bdate_range(start=start, end=end)
            return pd.Series(1.0, index=idx, name=f"{base}{quote}=X")

        pair = f"{base}{quote}=X"
        return self.get_price_history(pair, start, end)
