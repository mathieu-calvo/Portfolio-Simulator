"""Data service: orchestrates providers and caching for market data access."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date

import pandas as pd

from portfolio_simulator.cache.memory_cache import MemoryCache
from portfolio_simulator.cache.sqlite_cache import SQLiteCache
from portfolio_simulator.config import Settings, settings
from portfolio_simulator.providers.base import AssetInfo, DataProvider

logger = logging.getLogger(__name__)


class DataService:
    """Single point of access for all market data.

    Composes a DataProvider with a two-tier cache (memory -> SQLite).
    Supports bulk parallel fetching for multiple tickers.
    """

    def __init__(
        self,
        provider: DataProvider,
        config: Settings | None = None,
    ) -> None:
        self._provider = provider
        self._config = config or settings
        self._sqlite = SQLiteCache(self._config.db_path)
        self._memory = MemoryCache(default_ttl_hours=self._config.cache_ttl_hours)

    def _cache_key(self, kind: str, ticker: str, start: date, end: date) -> str:
        return f"{self._provider.name}:{kind}:{ticker}:{start}:{end}"

    def get_prices(self, ticker: str, start: date, end: date) -> pd.Series:
        """Get daily prices for a single ticker, using cache when available."""
        key = self._cache_key("price", ticker, start, end)

        # Tier 1: memory
        cached = self._memory.get(key)
        if cached is not None:
            return cached

        # Tier 2: SQLite
        cached = self._sqlite.get(key)
        if cached is not None:
            self._memory.put(key, cached)
            return cached

        # Tier 3: fetch from provider
        logger.info(f"Fetching {ticker} from {self._provider.name} ({start} to {end})")
        series = self._provider.get_price_history(ticker, start, end)
        self._sqlite.put(key, series, ttl_hours=self._config.cache_ttl_hours)
        self._memory.put(key, series)
        return series

    def get_prices_bulk(
        self,
        tickers: list[str],
        start: date,
        end: date,
    ) -> pd.DataFrame:
        """Fetch prices for multiple tickers in parallel.

        Returns a DataFrame with DatetimeIndex and one column per ticker.
        """
        results: dict[str, pd.Series] = {}
        to_fetch: list[str] = []

        # Check caches first
        for ticker in tickers:
            key = self._cache_key("price", ticker, start, end)
            cached = self._memory.get(key)
            if cached is None:
                cached = self._sqlite.get(key)
            if cached is not None:
                results[ticker] = cached
                self._memory.put(key, cached)
            else:
                to_fetch.append(ticker)

        # Parallel fetch uncached tickers
        if to_fetch:
            max_workers = min(len(to_fetch), self._config.max_concurrent_fetches)
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {
                    executor.submit(self._provider.get_price_history, t, start, end): t
                    for t in to_fetch
                }
                for future in as_completed(futures):
                    ticker = futures[future]
                    try:
                        series = future.result()
                        key = self._cache_key("price", ticker, start, end)
                        self._sqlite.put(key, series, ttl_hours=self._config.cache_ttl_hours)
                        self._memory.put(key, series)
                        results[ticker] = series
                    except Exception:
                        logger.error(f"Failed to fetch {ticker}", exc_info=True)
                        raise

        # Combine into DataFrame, aligned on date index
        df = pd.DataFrame(results)
        df = df.sort_index()
        return df

    def get_fx_rates(self, base: str, quote: str, start: date, end: date) -> pd.Series:
        """Get FX rates with caching."""
        if base == quote:
            idx = pd.bdate_range(start=start, end=end)
            return pd.Series(1.0, index=idx, name=f"{base}{quote}")

        key = self._cache_key("fx", f"{base}{quote}", start, end)
        cached = self._memory.get(key)
        if cached is None:
            cached = self._sqlite.get(key)
        if cached is not None:
            self._memory.put(key, cached)
            return cached

        series = self._provider.get_fx_rates(base, quote, start, end)
        self._sqlite.put(key, series, ttl_hours=self._config.cache_ttl_hours)
        self._memory.put(key, series)
        return series

    def search_assets(
        self,
        query: str,
        asset_type: str | None = None,
        limit: int = 20,
    ) -> list[AssetInfo]:
        """Search for assets (pass-through to provider, no caching)."""
        from portfolio_simulator.domain.enums import AssetType

        at = AssetType(asset_type) if asset_type else None
        return self._provider.search_assets(query, at, limit)

    def get_asset_info(self, ticker: str) -> AssetInfo:
        """Get asset metadata (pass-through to provider)."""
        return self._provider.get_asset_info(ticker)
