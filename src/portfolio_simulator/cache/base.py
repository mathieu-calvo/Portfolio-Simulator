"""Cache backend protocol."""

from __future__ import annotations

from typing import Protocol

import pandas as pd


class CacheBackend(Protocol):
    """Protocol for price data caching backends."""

    def get(self, key: str) -> pd.Series | None:
        """Retrieve cached data, or None if not found / expired."""
        ...

    def put(self, key: str, data: pd.Series, ttl_hours: int = 24) -> None:
        """Store data with a time-to-live."""
        ...

    def invalidate(self, key: str) -> None:
        """Remove a specific cache entry."""
        ...

    def clear(self) -> None:
        """Remove all cache entries."""
        ...
