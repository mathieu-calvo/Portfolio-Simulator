"""Yahoo Finance data provider implementation."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache

import pandas as pd
import yfinance as yf

from portfolio_simulator.domain.enums import AssetType
from portfolio_simulator.providers.base import AssetInfo

logger = logging.getLogger(__name__)


def _epoch_to_date(value) -> date | None:
    """Convert a Yahoo epoch field (seconds, milliseconds, or datetime) to a date."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        v = int(value)
    except (TypeError, ValueError):
        return None
    # Heuristic: values > ~10^12 are milliseconds, smaller are seconds.
    if v > 10**12:
        v //= 1000
    try:
        return datetime.fromtimestamp(v, tz=timezone.utc).date()
    except (OSError, ValueError):
        return None


def _first_trade_from_quote(q: dict) -> date | None:
    """Best-effort extraction of an asset's first-trade date from a Yahoo quote dict.

    Yahoo's search payload exposes the inception either as
    `firstTradeDateMilliseconds` (newer) or `firstTradeDateEpochUtc` (seconds).
    """
    for k in ("firstTradeDateMilliseconds", "firstTradeDateEpochUtc", "firstTradeDate"):
        v = q.get(k)
        d = _epoch_to_date(v)
        if d is not None:
            return d
    return None


@lru_cache(maxsize=2048)
def _fetch_first_trade_date(ticker: str) -> date | None:
    """Fetch first-trade date for a single ticker via the chart endpoint.

    Yahoo's search endpoint omits `firstTradeDate` for many quotes, so we fall
    back to `Ticker.history_metadata` (a single lightweight chart call). Cached
    to avoid refetching across reruns/searches.
    """
    try:
        meta = yf.Ticker(ticker).history_metadata
    except Exception:
        return None
    if not isinstance(meta, dict):
        return None
    return _epoch_to_date(meta.get("firstTradeDate"))

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
                    first_trade_date=_first_trade_from_quote(q),
                )
            )
        assets = assets[:limit]

        # Yahoo's search payload usually omits the inception date; enrich any
        # missing entries in parallel via the chart-metadata endpoint.
        missing_idx = [i for i, a in enumerate(assets) if a.first_trade_date is None and a.ticker]
        if missing_idx:
            with ThreadPoolExecutor(max_workers=min(8, len(missing_idx))) as pool:
                fetched = list(pool.map(_fetch_first_trade_date, [assets[i].ticker for i in missing_idx]))
            for i, ftd in zip(missing_idx, fetched):
                if ftd is not None:
                    a = assets[i]
                    assets[i] = AssetInfo(
                        ticker=a.ticker,
                        name=a.name,
                        asset_type=a.asset_type,
                        currency=a.currency,
                        ter=a.ter,
                        exchange=a.exchange,
                        isin=a.isin,
                        first_trade_date=ftd,
                    )
        return assets

    def get_asset_info(self, ticker: str) -> AssetInfo:
        info = yf.Ticker(ticker).info
        yf_type = info.get("quoteType", "EQUITY")
        ftd = _first_trade_from_quote(info) or _fetch_first_trade_date(ticker)
        return AssetInfo(
            ticker=ticker,
            name=info.get("longName") or info.get("shortName", ticker),
            asset_type=_QUOTE_TYPE_MAP.get(yf_type, AssetType.STOCK),
            currency=info.get("currency", "USD"),
            ter=info.get("annualReportExpenseRatio"),
            exchange=info.get("exchange"),
            isin=info.get("isin"),
            first_trade_date=ftd,
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
